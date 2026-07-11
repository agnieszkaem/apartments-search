import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List
from src.models import Apartment

def send_notification_email(apartments: List[Apartment]) -> bool:
    if not apartments:
        print("No new apartments to email.")
        return False

    # loading SMTP settings from env
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port_str = os.getenv("SMTP_PORT", "587")
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    notification_email = os.getenv("NOTIFICATION_EMAIL")

    if not all([smtp_host, smtp_user, smtp_pass, notification_email]):
        print("SMTP settings are incomplete. Skipping email notification.")
        print(f"SMTP_HOST: {smtp_host}, SMTP_USER: {smtp_user}, SMTP_PASS: {'***' if smtp_pass else None}, NOTIFICATION_EMAIL: {notification_email}")
        return False

    try:
        smtp_port = int(smtp_port_str)
    except ValueError:
        smtp_port = 587

    # apartments by source for email layout
    grouped_apts = {}
    for apt in apartments:
        grouped_apts.setdefault(apt.source, []).append(apt)

    # HTML body for email
    html_content = f"""
    <html>
    <head>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                color: #333333;
                line-height: 1.6;
                background-color: #f8fafc;
                margin: 0;
                padding: 20px;
            }}
            .container {{
                max-width: 600px;
                background-color: #ffffff;
                border-radius: 8px;
                border: 1px solid #e2e8f0;
                padding: 24px;
                margin: 0 auto;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
            }}
            .header {{
                border-bottom: 2px solid #3b82f6;
                padding-bottom: 12px;
                margin-bottom: 20px;
            }}
            .header h1 {{
                font-size: 20px;
                color: #1e3a8a;
                margin: 0;
            }}
            .source-section {{
                margin-bottom: 24px;
            }}
            .source-title {{
                font-size: 16px;
                font-weight: bold;
                color: #2563eb;
                border-bottom: 1px solid #e2e8f0;
                padding-bottom: 4px;
                margin-bottom: 12px;
                text-transform: uppercase;
                letter-spacing: 0.05em;
            }}
            .apt-card {{
                border-left: 3px solid #3b82f6;
                background-color: #f8fafc;
                padding: 12px 16px;
                margin-bottom: 12px;
                border-radius: 0 6px 6px 0;
            }}
            .apt-title {{
                font-size: 15px;
                font-weight: 600;
                color: #1e293b;
                margin: 0 0 6px 0;
            }}
            .apt-details {{
                font-size: 13px;
                color: #475569;
                margin: 0 0 8px 0;
            }}
            .apt-link {{
                font-size: 13px;
                color: #2563eb;
                text-decoration: none;
                font-weight: 500;
            }}
            .apt-link:hover {{
                text-decoration: underline;
            }}
            .footer {{
                font-size: 11px;
                color: #94a3b8;
                border-top: 1px solid #e2e8f0;
                padding-top: 12px;
                margin-top: 24px;
                text-align: center;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1> New apartment listings found!</h1>
                <p style="margin: 4px 0 0 0; font-size: 13px; color: #64748b;">We checked your selected websites and found {len(apartments)} new immediate match(es).</p>
            </div>
    """

    for source, apt_list in sorted(grouped_apts.items()):
        html_content += f"""
            <div class="source-section">
                <div class="source-title">{source}</div>
        """
        for apt in apt_list:
            details_str = f"<b>{apt.price} €</b> | {apt.size_sqm} m² | {apt.rooms} Zi. | {apt.location}"
            html_content += f"""
                <div class="apt-card">
                    <h3 class="apt-title">{apt.title}</h3>
                    <p class="apt-details">{details_str}</p>
                    <a href="{apt.url}" target="_blank" class="apt-link">View Listing -> </a>
                </div>
            """
        html_content += "</div>"

    html_content += """
            <div class="footer">
                Automated report from your Apartment Monitor.
            </div>
        </div>
    </body>
    </html>
    """

    # Email Message
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"{len(apartments)} New apartment match(es)!"
    msg["From"] = smtp_user
    msg["To"] = notification_email

    msg.attach(MIMEText(html_content, "html"))

    try:
        # connect to server
        server = smtplib.SMTP(smtp_host, smtp_port)
        if smtp_port == 587:
            server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, notification_email, msg.as_string())
        server.quit()
        print(f"Notification email successfully sent to {notification_email} with {len(apartments)} listings.")
        return True
    except Exception as e:
        print(f"Failed to send email notification: {e}")
        return False
