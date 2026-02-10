from googleapiclient.discovery import build
from extract_emails import fetch_emails,set_creds,fetch_emails_by_date
from preprocess_emails import final_result
from categorise_emails import categorize
from normalize_functions import add_hash
from pg_utils import insert_expense
from extract_statement import extract_bank_statement

# PDF_PATH = "Novemeber_statement.pdf"
# PDF_PASSWORD = "308327029"
service = build('gmail', 'v1', credentials=set_creds())
# mails = fetch_emails(service)
mails = fetch_emails_by_date(service,"2026-02-09")
email_result = final_result(mails)
#pdf_result = extract_bank_statement(PDF_PATH, PDF_PASSWORD)
final_result = email_result
# if pdf_result:
#     final_result = email_result + pdf_result
categorized_result = categorize(final_result)
hashed_results = add_hash(categorized_result)
insert_expense(hashed_results)
#print(hashed_results)