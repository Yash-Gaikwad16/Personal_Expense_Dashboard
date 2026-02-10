"""
HDFC Bank Statement PDF Extractor
Extracts transactions from HDFC bank statement PDFs
"""

import pdfplumber
import pandas as pd
import re


def extract_bank_statement(pdf_path, pdf_password):
    """
    Extract all transactions from HDFC bank statement PDF
    
    Parameters:
    -----------
    pdf_path : str
        Path to the PDF file
    pdf_password : str
        Password to open the PDF
    
    Returns:
    --------
    pandas.DataFrame
        DataFrame with columns: Date, Narration, ChqNo, Type, Amount
    """
    
    def clean_amount(val):
        """Clean and convert amount strings to float"""
        if not val:
            return None
        try:
            cleaned = val.replace(",", "").strip()
            return float(cleaned) if cleaned else None
        except (ValueError, AttributeError):
            return None
    
    
    def clean_narration(narration):
        """
        Extract merchant/payee name from UPI transactions
        Pattern: UPI-[MERCHANT NAME]-[UPI_HANDLE]@[BANK]
        Returns: [MERCHANT NAME] only
        """
        if not narration:
            return None
        
        # Find UPI- pattern
        if 'UPI-' in narration:
            parts = narration.split('UPI-', 1)
            if len(parts) > 1:
                after_upi = parts[1]
                
                # Find the @ symbol
                if '@' in after_upi:
                    before_at = after_upi.split('@')[0]
                    
                    # Find the last dash - merchant name is before it
                    last_dash_idx = before_at.rfind('-')
                    
                    if last_dash_idx > 0:
                        merchant_name = before_at[:last_dash_idx].strip()
                        if merchant_name:
                            return merchant_name
                    else:
                        merchant_name = before_at.strip()
                        if merchant_name:
                            return merchant_name
                
                # Fallback
                merchant = re.sub(r'-[A-Z0-9]{10,}.*$', '', after_upi)
                merchant = merchant.strip()
                if merchant:
                    return merchant
        
        # For non-UPI transactions, return as is
        return narration.strip()
    
    
    def extract_page(page):
        """Extract transactions from a single page"""
        text = page.extract_text(layout=True)
        lines = text.split('\n')
        
        transactions = []
        current_txn = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Stop at footer
            if any(x in line for x in ['HDFCBANKLIMITED', 'Closingbalance', '*Closing']):
                break
            
            # Check if line starts with date (DD/MM/YY)
            date_match = re.match(r'^(\d{2}/\d{2}/\d{2})\s+(.+)$', line)
            
            if date_match:
                if current_txn:
                    transactions.append(current_txn)
                
                date = date_match.group(1)
                rest = date_match.group(2)
                parts = rest.split()
                
                # Parse backwards: balance, amount, value_date, chq_no, narration
                i = len(parts) - 1
                balance = parts[i] if i >= 0 and re.match(r'^[\d,]+\.?\d*$', parts[i]) else None
                i -= 1
                
                amount = parts[i] if i >= 0 and re.match(r'^[\d,]+\.?\d*$', parts[i]) else None
                i -= 1
                
                value_date = parts[i] if i >= 0 and re.match(r'^\d{2}/\d{2}/\d{2}$', parts[i]) else None
                i -= 1
                
                chq_no = parts[i] if i >= 0 and re.match(r'^\d{16}$', parts[i]) else None
                i -= 1
                
                narration_parts = parts[0:i+1]
                
                current_txn = {
                    'Date': date,
                    'Narration': ' '.join(narration_parts),
                    'ChqNo': chq_no,
                    'Amount': amount,
                    'Balance': balance
                }
            else:
                # Continuation line
                if current_txn and line:
                    if any(skip in line for skip in ['HDFCBANK', 'Closing', 'Contents', 'State', 'Registered']):
                        continue
                    if not re.match(r'^[A-Z\s\*]+$', line):
                        existing = current_txn.get('Narration', '')
                        current_txn['Narration'] = existing + ' ' + line if existing else line
        
        if current_txn:
            transactions.append(current_txn)
        
        return transactions
    
    
    # Main extraction logic
    all_transactions = []
    
    with pdfplumber.open(pdf_path, password=pdf_password) as pdf:
        for page_num, page in enumerate(pdf.pages):
            try:
                page_txns = extract_page(page)
                all_transactions.extend(page_txns)
            except Exception:
                continue
    
    # Create DataFrame
    df = pd.DataFrame(all_transactions)
    
    if len(df) == 0:
        return pd.DataFrame(columns=['Date', 'Narration', 'ChqNo', 'Type', 'Amount'])
    
    # Process amounts and types
    df['Amount_Clean'] = df['Amount'].apply(clean_amount)
    df['Balance_Clean'] = df['Balance'].apply(clean_amount)
    
    df['Type'] = None
    df['Final_Amount'] = None
    
    for i in range(len(df)):
        if i == 0:
            if df.loc[i, 'Amount_Clean']:
                df.loc[i, 'Type'] = 'Debit'
                df.loc[i, 'Final_Amount'] = df.loc[i, 'Amount_Clean']
        else:
            prev_bal = df.loc[i-1, 'Balance_Clean']
            curr_bal = df.loc[i, 'Balance_Clean']
            
            if prev_bal and curr_bal:
                delta = curr_bal - prev_bal
                if delta < 0:
                    df.loc[i, 'Type'] = 'Debit'
                    df.loc[i, 'Final_Amount'] = abs(delta)
                elif delta > 0:
                    df.loc[i, 'Type'] = 'Credit'
                    df.loc[i, 'Final_Amount'] = abs(delta)
    
    # Clean narrations
    df['Narration_Clean'] = df['Narration'].apply(clean_narration)
    
    # Final DataFrame
    result = df[['Final_Amount', 'Narration_Clean','Type', 'ChqNo', 'Date']].copy()
    result.columns = ['Amount', 'Paid_to', 'Type', 'Reference_number','Date']
    return result.to_dict('records')



