"""
Infrastructure: delegated OAuth email sender for the mailbox owner.

Implements email delivery through Microsoft Graph using a delegated OAuth
refresh token for the mailbox owner.

Required environment variables:
    OAUTH_TENANT_ID: Microsoft Entra tenant ID
    OAUTH_CLIENT_ID: App registration client ID
    OAUTH_REFRESH_TOKEN: Delegated refresh token for the mailbox owner

Optional environment variables:
    OAUTH_CLIENT_SECRET: Client secret for confidential clients
    OAUTH_TOKEN_URL: OAuth token endpoint override
    OAUTH_GRAPH_SENDMAIL_URL: Graph sendMail endpoint override
    OAUTH_FROM_EMAIL: Mailbox address used for the From header

Dependencies:
    pip install playwright
    playwright install chromium
"""

import os
import re
import base64
from typing import Optional

import requests


class OAuthConfigError(Exception):
    """Raised when delegated OAuth configuration is missing or invalid."""


class EmailSender:
    """
    Sends performance reports through Microsoft Graph using delegated OAuth.

    The access token is minted from a refresh token belonging to the mailbox
    owner, so mail is sent as the signed-in owner via the `/me/sendMail`
    endpoint.
    """

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self._load_config()

    def _load_config(self) -> None:
        """Load and validate delegated OAuth configuration."""
        self.tenant_id = os.getenv("OAUTH_TENANT_ID")
        self.client_id = os.getenv("OAUTH_CLIENT_ID")
        self.client_secret = os.getenv("OAUTH_CLIENT_SECRET")
        self.refresh_token = os.getenv("OAUTH_REFRESH_TOKEN")
        self.from_email = os.getenv("OAUTH_FROM_EMAIL")

        default_token_url = (
            f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
            if self.tenant_id
            else None
        )
        self.token_url = os.getenv("OAUTH_TOKEN_URL") or default_token_url
        self.sendmail_url = (
            os.getenv("OAUTH_GRAPH_SENDMAIL_URL")
            or "https://graph.microsoft.com/v1.0/me/sendMail"
        )

        missing = [
            name
            for name, value in [
                ("OAUTH_TENANT_ID", self.tenant_id),
                ("OAUTH_CLIENT_ID", self.client_id),
                ("OAUTH_REFRESH_TOKEN", self.refresh_token),
            ]
            if not value
        ]
        if missing:
            raise OAuthConfigError(
                f"Missing required OAuth environment variables: {', '.join(missing)}"
            )

        if not self.token_url:
            raise OAuthConfigError(
                "Unable to determine OAuth token endpoint. Set OAUTH_TOKEN_URL."
            )

    def _get_access_token(self) -> str:
        """Exchange the mailbox owner's refresh token for a Graph access token."""
        token_request = {
            "client_id": self.client_id,
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "scope": "https://graph.microsoft.com/Mail.Send offline_access",
        }
        if self.client_secret:
            token_request["client_secret"] = self.client_secret

        response = requests.post(self.token_url, data=token_request, timeout=30)

        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            details = ""
            try:
                payload = response.json()
                error = payload.get("error")
                description = payload.get("error_description")
                if error or description:
                    details = f" ({error}: {description})"
            except ValueError:
                pass
            raise RuntimeError(
                f"OAuth token request failed with status {response.status_code}{details}"
            ) from exc

        payload = response.json()
        access_token = payload.get("access_token")
        if not access_token:
            raise RuntimeError("OAuth token response did not include access_token")
        return access_token

    @staticmethod
    def _build_pdf_and_filename(
        runner_name: str, report_html_string: str
    ) -> tuple[bytes, str, str]:
        """Render the HTML report to PDF and compute safe attachment names."""
        from playwright.sync_api import sync_playwright

        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page()
            page.set_content(report_html_string, wait_until="networkidle")
            pdf_bytes = page.pdf(
                format="A4",
                print_background=True,
                margin={
                    "top": "16mm",
                    "bottom": "16mm",
                    "left": "14mm",
                    "right": "14mm",
                },
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
        Convert an HTML report to PDF and send it via delegated OAuth.

        Args:
            to_email: Recipient email address
            runner_name: Name of the runner (used in subject and filename)
            report_html_string: Complete standalone HTML of the report
            subject: Email subject (auto-generated if not provided)

        Returns:
            True if the email was sent successfully, False otherwise
        """
        if not subject:
            subject = f"Your Interval Training Report — {runner_name}"

        pdf_bytes, pdf_filename, html_filename = self._build_pdf_and_filename(
            runner_name, report_html_string
        )
        payload = {
            "message": {
                "subject": subject,
                "body": {
                    "contentType": "Text",
                    "content": (
                        f"Hi {runner_name},\n\n"
                        f"Your interval training performance report is attached.\n\n"
                        f"— Splits"
                    ),
                },
                "toRecipients": [
                    {
                        "emailAddress": {
                            "address": to_email,
                        }
                    }
                ],
                "attachments": [
                    {
                        "@odata.type": "#microsoft.graph.fileAttachment",
                        "name": pdf_filename,
                        "contentType": "application/pdf",
                        "contentBytes": base64.b64encode(pdf_bytes).decode("ascii"),
                    },
                    {
                        "@odata.type": "#microsoft.graph.fileAttachment",
                        "name": html_filename,
                        "contentType": "text/html",
                        "contentBytes": base64.b64encode(
                            report_html_string.encode("utf-8")
                        ).decode("ascii"),
                    },
                ],
            },
            "saveToSentItems": True,
        }
        if self.from_email:
            payload["message"]["replyTo"] = [
                {"emailAddress": {"address": self.from_email}}
            ]

        if self.dry_run:
            print(f"  [DRY RUN] Would send {pdf_filename} to {to_email} via Microsoft Graph")
            return True

        access_token = self._get_access_token()
        response = requests.post(
            self.sendmail_url,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=30,
        )

        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            details = ""
            try:
                payload = response.json()
                error = payload.get("error", {})
                code = error.get("code")
                message = error.get("message")
                if code or message:
                    details = f" ({code}: {message})"
            except ValueError:
                pass
            raise RuntimeError(
                f"Graph sendMail request failed with status {response.status_code}{details}"
            ) from exc

        print(f"  [✓] Email sent to {to_email} via Microsoft Graph")
        return True
