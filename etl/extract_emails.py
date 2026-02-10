import os.path
import os
print("CWD:", os.getcwd())
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from base64 import urlsafe_b64decode
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import os
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly","https://www.googleapis.com/auth/gmail.send"]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN_PATH = os.path.join(BASE_DIR, "token.json")
CREDS_PATH = os.path.join(BASE_DIR, "credentials.json")

def set_creds(interactive=False):
    creds = None

    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            print("✅ Token refreshed successfully")
        except Exception as e:
            raise RuntimeError(
                "Token refresh failed. Delete token.json and re-run manually."
            ) from e

    if not creds:
        if not interactive:
            raise RuntimeError(
                "token.json missing. Run once with interactive=True to authenticate."
            )

        flow = InstalledAppFlow.from_client_secrets_file(
            CREDS_PATH, SCOPES
        )
        creds = flow.run_local_server(port=0)

    with open(TOKEN_PATH, "w") as token:
        token.write(creds.to_json())

    return creds
# # If modifying these scopes, delete the file token.json.
# SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
#
# def set_creds():
#     """Shows basic usage of the Gmail API.
#     Lists the user's Gmail labels.
#     """
#     creds = None
#     if os.path.exists("token.json"):
#         creds = Credentials.from_authorized_user_file("token.json", SCOPES)
#     if not creds or not creds.valid:
#         if creds and creds.expired and creds.refresh_token:
#           creds.refresh(Request())
#         else:
#           flow = InstalledAppFlow.from_client_secrets_file(
#               "credentials.json", SCOPES
#           )
#           creds = flow.run_local_server(port=0)
#     with open("token.json", "w") as token:
#       token.write(creds.to_json())
#     return creds

def extract_full_html(payload):
    # Case 1: Email has multiple parts
    if "parts" in payload:
        for part in payload["parts"]:
            mime = part.get("mimeType", "")

            # HTML part usually contains the full message
            if mime == "text/html":
                data = part["body"].get("data")
                if data:
                    return urlsafe_b64decode(data).decode()

            # If nested parts exist, search recursively
            if "parts" in part:
                html = extract_full_html(part)
                if html:
                    return html

    # Case 2: Simple email without parts
    if "body" in payload and "data" in payload["body"]:
        return urlsafe_b64decode(payload["body"]["data"]).decode()

    return ""

def fetch_emails_old(service):
    #query = 'from:alerts@hdfcbank.net'  # wide search to capture all HDFC debit emails
    # query = 'from:alerts@hdfcbank.bank.in'
    query = (
        'from:hdfcbank '
        '(debit OR spent OR transaction OR "Rs." OR "INR")'
    )

    results = service.users().messages().list(
        userId="me", q=query, maxResults=500
    ).execute()

    messages = results.get("messages", [])
    print("Found", len(messages), "emails\n")
    result = []
    for msg in messages:
        # Get full email data including all MIME parts
        msg_data = service.users().messages().get(
            userId="me",
            id=msg["id"],
            format="full"
        ).execute()

        payload = msg_data["payload"]
        html = extract_full_html(payload)

        soup = BeautifulSoup(html, "html.parser")
        clean_text = soup.get_text(separator="\n")
        lines = clean_text.split("\n")
        lines = [line.strip() for line in lines if line.strip() != ""]
        clean_text = "\n".join(lines)
        result.append(clean_text)
    return result

def fetch_emails(service):
    today = datetime.now()
    gmail_today = today.strftime("%Y/%m/%d")
    gmail_tomorrow = (today + timedelta(days=1)).strftime("%Y/%m/%d")

    # Date range query (correct for timezone issues)
    # query = f'from:alerts@hdfcbank.net after:{gmail_today} before:{gmail_tomorrow}'
    query = (
        f'from:hdfcbank '
        f'(debit OR spent OR transaction OR "Rs." OR "INR") '
        f'after:{gmail_today} before:{gmail_tomorrow}'
    )

    all_messages = []
    next_page_token = None

    while True:
        results = service.users().messages().list(
            userId="me",
            q=query,
            maxResults=50,
            pageToken=next_page_token
        ).execute()

        messages = results.get("messages", [])
        all_messages.extend(messages)

        next_page_token = results.get("nextPageToken")
        if not next_page_token:
            break

    print(f"Total emails found for {gmail_today}: {len(all_messages)}")

    result = []

    for msg in all_messages:
        msg_data = service.users().messages().get(
            userId="me",
            id=msg["id"],
            format="full"
        ).execute()

        payload = msg_data["payload"]

        html = extract_full_html(payload)
        soup = BeautifulSoup(html, "html.parser")
        clean_text = soup.get_text(separator="\n")

        lines = clean_text.split("\n")
        lines = [line.strip() for line in lines if line.strip() != ""]
        clean_text = "\n".join(lines)

        result.append(clean_text)

    return result

from datetime import datetime, timedelta
from bs4 import BeautifulSoup

def fetch_emails_by_date(service, target_date):
    """
    target_date: string in 'YYYY-MM-DD' format
    Example: '2026-02-10'
    """

    # Convert string date to datetime
    date_obj = datetime.strptime(target_date, "%Y-%m-%d")

    gmail_today = date_obj.strftime("%Y/%m/%d")
    gmail_tomorrow = (date_obj + timedelta(days=1)).strftime("%Y/%m/%d")

    # query = f'from:alerts@hdfcbank.net after:{gmail_today} before:{gmail_tomorrow}'
    query = (
        f'from:hdfcbank '
        f'(debit OR spent OR transaction OR "Rs." OR "INR") '
        f'after:{gmail_today} before:{gmail_tomorrow}'
    )

    all_messages = []
    print("All messages : ",all_messages)
    next_page_token = None

    while True:
        results = service.users().messages().list(
            userId="me",
            q=query,
            maxResults=50,
            pageToken=next_page_token
        ).execute()

        messages = results.get("messages", [])
        all_messages.extend(messages)

        next_page_token = results.get("nextPageToken")
        if not next_page_token:
            break

    print(f"Total emails found for {gmail_today}: {len(all_messages)}")

    result = []

    for msg in all_messages:
        msg_data = service.users().messages().get(
            userId="me",
            id=msg["id"],
            format="full"
        ).execute()

        payload = msg_data["payload"]

        html = extract_full_html(payload)
        soup = BeautifulSoup(html, "html.parser")
        clean_text = soup.get_text(separator="\n")

        lines = clean_text.split("\n")
        lines = [line.strip() for line in lines if line.strip()]
        clean_text = "\n".join(lines)

        result.append(clean_text)

    return result
