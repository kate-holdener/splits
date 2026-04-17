"""
Infrastructure: SMTP email sender.

Implements email delivery via SMTP protocol using environment variables
for configuration.

Dependencies:
    pip install playwright
    playwright install chromium
"""

import os
import re
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional


class SMTPConfigError(Exception):
    """Raised when SMTP configuration is missing or invalid."""
    pass


class EmailSender:
    """
    Sends performance reports as PDF attachments via SMTP.

    Configuration is loaded from environment variables:
    - SMTP_HOST: SMTP server hostname
    - SMTP_PORT: SMTP server port (default: 587)
    - SMTP_USERNAME: Username for authentication
    - SMTP_PASSWORD: Password for authentication
    - SMTP_FROM_EMAIL: From email address (optional, defaults to username)
    """

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self._load_config()

    def _load_config(self) -> None:
        """Load and validate SMTP configuration from environment variables."""
        self.host = os.getenv('SMTP_HOST')
        self.port = int(os.getenv('SMTP_PORT', '587'))
        self.username = os.getenv('SMTP_USERNAME')
        self.password = os.getenv('SMTP_PASSWORD')
        self.from_email = (
            os.getenv('SMTP_FROM_EMAIL')
            or os.getenv('SMTP_SENDER_EMAIL')
            or self.username
        )

        missing = [
            v for v, val in [
                ('SMTP_HOST', self.host),
                ('SMTP_USERNAME', self.username),
                ('SMTP_PASSWORD', self.password),
            ] if not val
        ]
        if missing:
            raise SMTPConfigError(
                f"Missing required SMTP environment variables: {', '.join(missing)}"
            )

    def send_report(
        self,
        to_email: str,
        runner_name: str,
        report_html_string: str,
        subject: Optional[str] = None,
    ) -> bool:
        """
        Convert an HTML report to PDF and send it as an email attachment.

        Args:
            to_email: Recipient email address
            runner_name: Name of the runner (used in subject and filename)
            report_html_string: Complete standalone HTML of the report
            subject: Email subject (auto-generated if not provided)

        Returns:
            True if the email was sent successfully, False otherwise
        """
        from playwright.sync_api import sync_playwright

        if not subject:
            subject = f"Your Interval Training Report — {runner_name}"

        # Convert HTML → PDF in memory via headless Chromium
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page()
            page.set_content(report_html_string, wait_until='networkidle')
            pdf_bytes = page.pdf(format='A4', print_background=True,
                                 margin={'top': '16mm', 'bottom': '16mm',
                                         'left': '14mm', 'right': '14mm'})
            browser.close()

        # Safe filename: replace anything that isn't alphanumeric/hyphen/underscore
        safe_name = re.sub(r'[^A-Za-z0-9_-]', '_', runner_name)
        filename = f"{safe_name}_report.pdf"

        msg = MIMEMultipart()
        msg['From'] = self.from_email
        msg['To'] = to_email
        msg['Subject'] = subject

        msg.attach(MIMEText(
            f"Hi {runner_name},\n\n"
            f"Your interval training performance report is attached.\n\n"
            f"— IntervalTrack",
            'plain'
        ))

        attachment = MIMEApplication(pdf_bytes, _subtype='pdf')
        attachment.add_header('Content-Disposition', 'attachment', filename=filename)
        msg.attach(attachment)

        # Also attach the raw HTML file
        html_attachment = MIMEText(report_html_string, 'html', 'utf-8')
        html_attachment.add_header('Content-Disposition', 'attachment',
                                   filename=f'{safe_name}_report.html')
        msg.attach(html_attachment)

        if self.dry_run:
            print(f"  [DRY RUN] Would send {filename} to {to_email}")
            return True

        with smtplib.SMTP(self.host, self.port) as server:
            server.starttls()
            server.login(self.username, self.password)
            server.send_message(msg)
        print(f"  [✓] Email sent to {to_email}")
        return True
