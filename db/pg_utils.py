import psycopg2
from configparser import ConfigParser
import os
import pandas as pd
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.ini")
def load_db_config(path=CONFIG_PATH):
    config = ConfigParser()
    config.read(path)

    db_config = {
        "dbname": config.get("DATABASE", "dbname"),
        "user": config.get("DATABASE", "user"),
        "password": config.get("DATABASE", "password"),
        "host": config.get("DATABASE", "host"),
        "port": config.get("DATABASE", "port")
    }
    return db_config


def get_connection():
    db_config = load_db_config()
    try :
        conn = psycopg2.connect(
        database=db_config["dbname"],
        user=db_config["user"],
        password=db_config["password"],
        host=db_config["host"],
        port=db_config["port"]
        )
        # print("Connection established")
        return conn
    except Exception as e :
        print("Error connecting to PostgreSQL")
        return None

def insert_expense_old(expenses):
    conn = get_connection()
    if conn is None:
        print("No connection established, Hence cannot insert expenses")
        return None
    cur = conn.cursor()
    for expense in expenses:
        try:
            cur.execute(
            """
            INSERT INTO expenses (amount, paid_to, reference_no, txn_date, category, hashcode)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                expense["Amount"],
                expense["Paid_to"],
                expense["Reference_number"],
                expense["Date"],
                expense["Category"],
                expense["hashcode"]
            )
            )
            print("Inserted:", expense["hashcode"])
        except psycopg2.errors.UniqueViolation:
            conn.rollback()
            print("Duplicate skipped:", expense["hashcode"])
    conn.commit()
    cur.close()
    conn.close()
    return None

def insert_expense(expenses):
    conn = get_connection()
    if conn is None:
        print("No connection established")
        return

    cur = conn.cursor()

    for expense in expenses:
        try:
            cur.execute("""
                INSERT INTO public.expenses (amount, paid_to, reference_no, txn_date, category, hashcode, txn_type)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                expense["Amount"],
                expense["Paid_to"],
                expense["Reference_number"],
                expense["Date"],
                expense["Category"],
                expense["hashcode"],
                expense["Type"]
            ))

            print("Inserted:", expense["hashcode"])

        except psycopg2.errors.UniqueViolation:
            conn.rollback()
            print("Duplicate skipped:", expense["hashcode"])

        except Exception as e:
            conn.rollback()
            print("❌ Insert FAILED for:", expense)
            print("❌ ERROR:", e)
        finally :
            conn.commit()
    cur.close()
    conn.close()

def get_all_data():
    conn = get_connection()
    if conn is None:
        print("No connection established")
        return None
    cur = conn.cursor()
    cur.execute('''Select hashcode,txn_date,category,txn_type,amount,paid_to from expenses;''')
    rows = cur.fetchall()
    conn.close()

    return [
        {
            "hashcode": r[0],
            "txn_date": str(r[1]),
            "category": r[2],
            "txn_type": r[3],
            "amount": int(r[4]),
            "paid_to": r[5]
        }
        for r in rows
    ]


from datetime import date
def get_today_data():
    conn = get_connection()
    cur = conn.cursor()

    today = date.today()

    cur.execute("""
        SELECT
            hashcode,
            txn_date,
            category,
            txn_type,
            amount,
            paid_to
        FROM expenses
        WHERE txn_date = %s
    """, (today,))

    rows = cur.fetchall()
    conn.close()

    return [
        {
            "hashcode": r[0],
            "txn_date": str(r[1]),
            "category": r[2],
            "txn_type": r[3],
            "amount": int(r[4]),
            "paid_to": r[5]
        }
        for r in rows
    ]

def execute_query(query):
    #print("Query ",query)
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(query)
        result = cur.fetchall()
        if result :
            return result
    except :
        return None