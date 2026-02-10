import re
def extract_txn_type(text):
    text = text.lower()

    # Debit indicators
    if ("debited" in text or
        "upi/dr" in text or
        "spent" in text or
        "withdrawn" in text or
        "purchase" in text):
        return "Debit"

    # Credit indicators
    if ("credited" in text or
        "upi/cr" in text or
        "received" in text or
        "refund" in text):
        return "Credit"

    return "Unknown"

def parse_hdfc_text(text):
    # 1. Amount
    m = re.search(r"Rs\.?\s?([\d.,]+)", text)
    amount = m.group(1) if m else None

    # 2. Paid to (after @xyz and before 'on')
    m = re.search(r"@[a-zA-Z]+\s+(.+?)\s+on", text)
    paid_to = m.group(1).strip() if m else None

    # 3. Reference number
    m = re.search(r"reference number is\s+(\d+)", text, re.IGNORECASE)
    reference_number = m.group(1) if m else None

    # 4. Date (after the word 'on')
    m = re.search(r"\bon\s+(\d{1,2}-\d{1,2}-\d{2,4})", text)
    date = m.group(1) if m else None

    type = extract_txn_type(text)

    return {
        "Amount": amount,
        "Paid_to": paid_to,
        "Type": type,
        "Reference_number": reference_number,
        "Date": date
    }

def final_result(mails):
    final_result = []
    if mails and len(mails)>0:
        for mail in mails:
            result=parse_hdfc_text(mail)
            if result['Reference_number']:
                final_result.append(result)
    else:
        return []
    return final_result