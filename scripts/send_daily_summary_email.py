import os
import re
import base64
from datetime import datetime, date
from send_daily_summary import email_summary
from email.mime.text import MIMEText
from extract_emails import set_creds
from googleapiclient.discovery import build

TO_EMAIL = "yashgaikwad475@gmail.com"
FROM_EMAIL = "me"                  # Gmail API uses "me"
SUBJECT_PREFIX = "Daily Expense Pipeline Summary"

def create_message(to_email: str, subject: str, body: str):
    msg = MIMEText(body)
    msg["to"] = to_email
    msg["from"] = FROM_EMAIL
    msg["subject"] = subject

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    return {"raw": raw}


def send_email(service, to_email: str, subject: str, body: str):
    message = create_message(to_email, subject, body)
    sent = service.users().messages().send(userId="me", body=message).execute()
    return sent

# ---------------- MAIN ----------------
def main():

    summary = email_summary()
    print(summary)
    today = summary['Date']
    if summary["Error_found"]:
        subject = f"❌ ERROR | {SUBJECT_PREFIX} | {today}"
    else:
        subject = f"✅ SUCCESS | {SUBJECT_PREFIX} | {today}"

    body = []
    body.append(f"📌 Summary for {today}")
    body.append("")
    body.append(f"Emails found: {summary['Emails_found']}")
    body.append(f"Inserted: {summary['Inserted']}")
    body.append(f"Duplicate skipped: {summary['Duplicates']}")
    body.append(f"Error_found: {summary['Error_found']}")
    if summary["Error_found"]:
        body.append("")
        body.append("Error:")
        body.append(summary["Error"])

    body.append("")

    body_text = "\n".join(body)
    service = build('gmail', 'v1', credentials=set_creds())
    sent = send_email(service, TO_EMAIL, subject, body_text)
    print("✅ Email sent successfully:", sent.get("id"))


if __name__ == "__main__":
    main()
