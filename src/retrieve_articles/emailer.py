from __future__ import annotations

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from retrieve_articles.models import ArticleSelection

TEMPLATES_DIR = Path(__file__).parent / "templates"


def _render_template(selection: ArticleSelection) -> str:
    env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template("daily_email.html")
    return template.render(
        headline=selection.headline,
        title=selection.title,
        url=selection.selected_url,
        summary=selection.summary,
        why_it_matters=selection.why_it_matters,
        read_time_minutes=selection.read_time_minutes,
        content_type=selection.content_type,
        source_name=selection.source_name,
    )


def send_article_email(
    *,
    gmail_address: str,
    gmail_app_password: str,
    recipient: str,
    selection: ArticleSelection,
) -> None:
    html_body = _render_template(selection)
    subject = f"Today's read: {selection.headline}"

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = gmail_address
    message["To"] = recipient
    message.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        try:
            server.login(gmail_address, gmail_app_password)
        except smtplib.SMTPAuthenticationError as exc:
            raise RuntimeError(
                "Gmail login failed (SMTP 535). Check that:\n"
                "  1. GMAIL_ADDRESS is your full Gmail address\n"
                "  2. GMAIL_APP_PASSWORD is a 16-character app password, not your normal Gmail password\n"
                "  3. 2-Step Verification is enabled: https://myaccount.google.com/security\n"
                "  4. Create an app password at: https://myaccount.google.com/apppasswords\n"
                "  5. If the password has special characters, quote it in .env:\n"
                '     GMAIL_APP_PASSWORD="abcdefghijklmnop"'
            ) from exc
        server.sendmail(gmail_address, [recipient], message.as_string())


def send_test_email(
    *,
    gmail_address: str,
    gmail_app_password: str,
    recipient: str,
) -> None:
    selection = ArticleSelection(
        selected_url="https://example.com/test-article",
        headline="Test email from Daily Article Agent",
        summary=(
            "This is a test email from your Daily Article Agent setup. "
            "If you received this, Gmail SMTP is configured correctly."
        ),
        why_it_matters=[
            "Confirms your email credentials work.",
            "You can now run a full daily job.",
        ],
        read_time_minutes=1,
        content_type="blog",
        title="Test Article",
        source_name="Daily Article Agent",
    )
    send_article_email(
        gmail_address=gmail_address,
        gmail_app_password=gmail_app_password,
        recipient=recipient,
        selection=selection,
    )


def send_no_candidates_email(
    *,
    gmail_address: str,
    gmail_app_password: str,
    recipient: str,
) -> None:
    selection = ArticleSelection(
        selected_url="https://example.com",
        headline="No new articles today",
        summary=(
            "The agent could not find any unseen articles matching your interests "
            "in the lookback window. It will try again tomorrow."
        ),
        why_it_matters=["Your reading list is fully caught up for now."],
        read_time_minutes=1,
        content_type="news",
        title="No new articles",
        source_name="Daily Article Agent",
    )
    send_article_email(
        gmail_address=gmail_address,
        gmail_app_password=gmail_app_password,
        recipient=recipient,
        selection=selection,
    )
