import re
from datetime import datetime


LOG_FILE = "/home/ag-admin/Yash/Projects/cron.log"   # change if needed


def extract_run_block_for_date(log_file, run_date: str):
    """
    Extracts the log block for the given run_date (YYYY-MM-DD).
    Logic:
      - Find first line that matches: RUN_START <run_date>
      - Collect lines until next RUN_START or EOF
    """
    run_start_re = re.compile(rf"=+ RUN_START {re.escape(run_date)} .* =+")

    collecting = False
    block = []

    with open(log_file, "r") as f:
        for line in f:
            line = line.rstrip("\n")

            # Start collecting when today's RUN_START found
            if not collecting and run_start_re.search(line):
                collecting = True
                continue

            # Stop collecting at next RUN_START (new block begins)
            if collecting and "RUN_START" in line:
                break

            if collecting:
                block.append(line)

    return block


def parse_summary_from_block(block_lines):
    """
    From the extracted block, compute:
    - emails_found
    - inserted_count
    - duplicate_skipped_count
    - error_found
    """
    inserted_count = 0
    duplicate_skipped_count = 0
    emails_found = 0
    error_found = False
    error = []
    for line in block_lines:
        if "Total emails found for" in line:
            # Example: Total emails found for 2026/01/19: 1
            try:
                emails_found = int(line.split(":")[-1].strip())
            except:
                emails_found = 0

        if "Inserted:" in line:
            inserted_count += 1

        if "Duplicate skipped:" in line:
            duplicate_skipped_count += 1

        if "Traceback (most recent call last)" in line:
            error_found = True
            error=block_lines[-1]
        if "RuntimeError:" in line or "Error" in line:
            error_found = True
            error = block_lines[-1]
    return {
        "emails_found": emails_found,
        "inserted": inserted_count,
        "duplicate_skipped": duplicate_skipped_count,
        "error_found": error_found,
        "error": error
    }


def email_summary():
    today = datetime.now().strftime("%Y-%m-%d")

    block = extract_run_block_for_date(LOG_FILE, today)
    if not block:
        return None

    summary = parse_summary_from_block(block)

    return{"Date":today,"Emails_found":summary['emails_found'],"Inserted":summary['inserted'],"Duplicates":summary['duplicate_skipped'],"Error_found":summary['error_found'],"Error":summary['error']}
