"""
Gmail OAuth email sender.

Sends performance reports via the Gmail API using a stored OAuth refresh token.
Tokens are managed by gmail_auth.py and saved in the user data directory.

Required environment variables:
    GMAIL_CLIENT_ID: Google OAuth client ID
    GMAIL_CLIENT_SECRET: Google OAuth client secret

Dependencies:
    pip install playwright requests
    playwright install chromium
"""

import base64
import json
import os
import re
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional


import requests


class GmailConfigError(Exception):
    """Raised when Gmail OAuth configuration is missing or tokens are absent."""


class EmailSender:
    """
    Sends performance reports via Gmail API using stored OAuth tokens.
    """

    TOKENS_FILENAME = "gmail_tokens.json"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    SEND_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self._load_config()

    def _tokens_path(self) -> Path:
        from persistence.user_data_dir import get_user_data_dir
        return get_user_data_dir() / self.TOKENS_FILENAME

    def _load_config(self) -> None:
        self.client_id = os.getenv("GMAIL_CLIENT_ID")
        self.client_secret = os.getenv("GMAIL_CLIENT_SECRET")

        missing = [n for n, v in [
            ("GMAIL_CLIENT_ID", self.client_id),
            ("GMAIL_CLIENT_SECRET", self.client_secret),
        ] if not v]
        if missing:
            raise GmailConfigError(
                f"Missing required environment variables: {', '.join(missing)}"
            )

        tokens_path = self._tokens_path()
        if not tokens_path.exists():
            raise GmailConfigError(
                "Not signed in to Gmail. Go to Settings → Email to sign in."
            )
        try:
            tokens = json.loads(tokens_path.read_text())
            self.refresh_token = tokens.get("refresh_token")
            self.from_email = tokens.get("email")
        except Exception as e:
            raise GmailConfigError(f"Failed to read Gmail tokens: {e}") from e

        if not self.refresh_token:
            raise GmailConfigError(
                "Gmail refresh token is missing. Please sign in again in Settings → Email."
            )

    def _get_access_token(self) -> str:
        resp = requests.post(
            self.TOKEN_URL,
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": self.refresh_token,
                "grant_type": "refresh_token",
            },
            timeout=30,
        )
        try:
            resp.raise_for_status()
        except requests.HTTPError as exc:
            details = ""
            try:
                payload = resp.json()
                error = payload.get("error")
                desc = payload.get("error_description")
                if error or desc:
                    details = f" ({error}: {desc})"
            except ValueError:
                pass
            raise RuntimeError(
                f"Gmail token refresh failed with status {resp.status_code}{details}"
            ) from exc

        access_token = resp.json().get("access_token")
        if not access_token:
            raise RuntimeError("Gmail token response did not include access_token")
        return access_token

    @staticmethod
    def _build_pdf_and_filename(
        runner_name: str, report_html_string: str
    ) -> tuple[bytes, str, str]:
        """Render the HTML report to PDF and return safe attachment names."""
        from playwright.sync_api import sync_playwright

        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page()
            page.set_content(report_html_string, wait_until="networkidle")
            pdf_bytes = page.pdf(
                format="A4",
                print_background=True,
                margin={"top": "16mm", "bottom": "16mm", "left": "14mm", "right": "14mm"},
            )
            browser.close()

        safe_name = re.sub(r"[^A-Za-z0-9_-]", "_", runner_name)
        return pdf_bytes, f"{safe_name}_report.pdf", f"{safe_name}_report.html"

    def send_report(
        self,
        to_email: str,
        runner_name: str,
        report_html_string: str,
        subject: Optional[str] = None,
    ) -> bool:
        """
        Render the report to PDF and send it via the Gmail API.

        Args:
            to_email: Recipient email address
            runner_name: Athlete name (used in subject and filename)
            report_html_string: Complete standalone HTML for the report
            subject: Email subject (auto-generated if omitted)

        Returns:
            True on success.
        """
        if not subject:
            subject = f"Your Interval Training Report — {runner_name}"

        pdf_bytes, pdf_filename, html_filename = self._build_pdf_and_filename(
            runner_name, report_html_string
        )

        msg = MIMEMultipart()
        msg["To"] = to_email
        msg["Subject"] = subject
        if self.from_email:
            msg["From"] = self.from_email

        msg.attach(MIMEText(
            f"Hi {runner_name},\n\n"
            "Your interval training performance report is attached.\n\n"
            "— Splits",
            "plain",
        ))

        pdf_part = MIMEApplication(pdf_bytes, _subtype="pdf")
        pdf_part.add_header("Content-Disposition", "attachment", filename=pdf_filename)
        msg.attach(pdf_part)

        html_part = MIMEText(report_html_string, "html", "utf-8")
        html_part.add_header("Content-Disposition", "attachment", filename=html_filename)
        msg.attach(html_part)

        if self.dry_run:
            print(f"  [DRY RUN] Would send {pdf_filename} to {to_email} via Gmail API")
            return True

        access_token = self._get_access_token()
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()

        resp = requests.post(
            self.SEND_URL,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            json={"raw": raw},
            timeout=30,
        )
        try:
            resp.raise_for_status()
        except requests.HTTPError as exc:
            details = ""
            try:
                payload = resp.json()
                error = payload.get("error", {})
                code = error.get("code") if isinstance(error, dict) else error
                message = error.get("message") if isinstance(error, dict) else None
                if code or message:
                    details = f" ({code}: {message})"
            except ValueError:
                pass
            raise RuntimeError(
                f"Gmail send failed with status {resp.status_code}{details}"
            ) from exc

        print(f"  [✓] Email sent to {to_email} via Gmail API")
        return True
