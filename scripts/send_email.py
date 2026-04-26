"""
Send the latest brief by email. Invoked by the GitHub Actions workflow.

Reads the most recently dated subdirectory under briefs/ and sends a
multipart message with the markdown as the plain-text body, the
generated brief.html as the HTML body, and the analog.png embedded
inline (referenced as cid:analog so it renders inside the HTML).

Configured by env vars (set as GitHub Actions secrets):
  SMTP_HOST          e.g. smtp.fastmail.com
  SMTP_PORT          default 465 (SSL); set to 587 for STARTTLS
  SMTP_USER          your SMTP username
  SMTP_PASS          your SMTP app password
  BRIEF_RECIPIENT    the address to send to
"""

import os
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path


def latest_brief_dir() -> Path:
    root = Path(__file__).resolve().parent.parent / "briefs"
    candidates = sorted([p for p in root.iterdir() if p.is_dir()])
    if not candidates:
        raise SystemExit("no brief directories found")
    return candidates[-1]


def main():
    smtp_host = os.environ["SMTP_HOST"]
    smtp_port = int(os.environ.get("SMTP_PORT", "465"))
    smtp_user = os.environ["SMTP_USER"]
    smtp_pass = os.environ["SMTP_PASS"]
    recipient = os.environ["BRIEF_RECIPIENT"]

    brief_dir = latest_brief_dir()
    brief_md = (brief_dir / "brief.md").read_text()
    brief_html_path = brief_dir / "brief.html"
    chart = brief_dir / "analog.png"

    msg = EmailMessage()
    msg["Subject"] = f"El Nino brief: {brief_dir.name}"
    msg["From"] = smtp_user
    msg["To"] = recipient
    msg.set_content(brief_md)

    if brief_html_path.exists():
        html = brief_html_path.read_text()
        # Rewrite the analog.png src to a cid reference so the inline
        # image renders in the email client.
        html = html.replace('src="analog.png"', 'src="cid:analog"')
        msg.add_alternative(html, subtype="html")
        if chart.exists():
            html_part = msg.get_payload()[-1]
            html_part.add_related(chart.read_bytes(), maintype="image",
                                  subtype="png", cid="<analog>",
                                  filename=chart.name)
    elif chart.exists():
        msg.add_attachment(chart.read_bytes(), maintype="image",
                           subtype="png", filename=chart.name)

    if smtp_port == 465:
        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL(smtp_host, smtp_port, context=ctx) as s:
            s.login(smtp_user, smtp_pass)
            s.send_message(msg)
    else:
        with smtplib.SMTP(smtp_host, smtp_port) as s:
            s.starttls()
            s.login(smtp_user, smtp_pass)
            s.send_message(msg)
    print(f"sent: {brief_dir.name} -> {recipient}")


if __name__ == "__main__":
    main()
