from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import PromptTemplate
from pydantic import BaseModel
from typing import Optional,Literal
from pg_utils import execute_query
from rag_utlis import semantic_search
import json
load_dotenv()
model = ChatOpenAI()

class Filters(BaseModel):
    category: Optional[str]
    txn_type: Literal['Credit', 'Debit']
    month: Optional[str]
    year: Optional[int]
    paid_to: Optional[str]

class Intent(BaseModel):
    metric: str
    field: str
    filters: Filters


def categorise_query(query):
    user_input = query
    query = f'''Classify the following user query as:
    - "analytical" (needs SQL computation)
    - "semantic" (needs similarity / explanation)
    Query : {user_input} \n
    Answer only with one word
    '''
    result = model.invoke(query)
    return result.content

def retrieve_intent(query):
    parser = PydanticOutputParser(pydantic_object=Intent)
    prompt = PromptTemplate(template="""
You are an intent extraction engine.
Do NOT answer the question.
Return ONLY valid JSON.
{format_instructions}
Rules:
- metric must be one of: sum, max, min, count, avg
- field is always "amount"
- If information is missing, use null
- Month must be full month name (January, February, etc.)
- Year must be a number
Query: "{user_query}"
""",
        input_variables=["user_query"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )
    chain = prompt | model | parser
    return chain.invoke({"user_query": query})


# print(retrieve_intent("What is my Biggest expense to Raut Petroleumn in January 2026?"))
METRIC_SQL = {
    "sum": "SUM",
    "avg": "AVG",
    "max": "MAX",
    "min": "MIN",
    "count": "COUNT"
}

MONTH_MAP = {
    "January": 1,
    "February": 2,
    "March": 3,
    "April": 4,
    "May": 5,
    "June": 6,
    "July": 7,
    "August": 8,
    "September": 9,
    "October": 10,
    "November": 11,
    "December": 12
}

def build_sql(query):
    intent = retrieve_intent(query)
    print(intent)
    metric = METRIC_SQL[intent.metric]
    where_clauses = []
    params = []

    # Filters
    f = intent.filters

    if f.category:
        where_clauses.append(f"category = '{f.category}'")
        params.append(f.category)

    if f.txn_type:
        where_clauses.append(f"txn_type = '{f.txn_type}'")
        params.append(f.txn_type)

    if f.paid_to:
        where_clauses.append(f"paid_to ILIKE '%{f.paid_to}%'")
        params.append(f"%{f.paid_to}%")

    if f.month:
        month = MONTH_MAP[f.month]
        where_clauses.append(f"EXTRACT(MONTH FROM txn_date) = '{month}'")
        params.append(MONTH_MAP[f.month])

    if f.year:
        where_clauses.append(f"EXTRACT(YEAR FROM txn_date) = '{f.year}'")
        params.append(f.year)

    where_sql = ""
    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)

    sql = f"""SELECT {metric} ({intent.field}) AS result FROM expenses {where_sql};
    """

    return sql, params

def create_sql_query(query):
    prompt = f"""
You are a Postgres SQL generator.

Rules:
- Output ONLY a valid Postgres SQL query
- NO explanations
- NO markdown
- NO comments
- NO extra text

Table: expenses
Columns: amount, paid_to, txn_date, category, txn_type

Rules:
- txn_type ∈ ('Debit', 'Credit')
- If category is mentioned → txn_type = 'Debit'
- Use EXTRACT(MONTH FROM txn_date) = <number>
- Use EXTRACT(YEAR FROM txn_date) = <year>

Example:
User: Which is biggest expense on petrol in January 2026?
Output:
SELECT MAX(amount) AS result
FROM expenses
WHERE category = 'Petrol'
  AND txn_type = 'Debit'
  AND EXTRACT(MONTH FROM txn_date) = 1
  AND EXTRACT(YEAR FROM txn_date) = 2026;

User: {query}
"""

    result = model.invoke(prompt)
    return result.content.strip()

def create_chroma_filter(query):
    prompt = """
You are a ChromaDB metadata filter generator.

Rules:
- Output ONLY a valid JSON object
- The output MUST be valid JSON (double-quoted strings)
- NO explanations
- NO markdown
- NO comments
- NO extra text

Metadata fields:
- category (string)
- paid_to (string)
- txn_type ("Debit" or "Credit")
- txn_month (string: January, February, ...)
- txn_year (number)
- amount (number)

Rules:
- If category is mentioned → txn_type = "Debit"
- Convert all month expressions (Jan, first month, etc.) to FULL month name
  (January, February, March, ...)
- Use "$and" when multiple filters exist
- Use comparison operators for amount:
  "$gt", "$lt", "$gte", "$lte"
- If a field is not mentioned, DO NOT include it

Examples:

User: Why did I pay John so much last January?
Output:
{
  "$and": [
    {"paid_to": "John"},
    {"txn_month": "January"},
    {"txn_year": 2026},
    {"txn_type": "Debit"}
  ]
}

User: Show expenses above 10000 in petrol category in third month of 2025
Output:
{
  "$and": [
    {"category": "Petrol"},
    {"amount": {"$gt": 10000}},
    {"txn_month": "March"},
    {"txn_year": 2025},
    {"txn_type": "Debit"}
  ]
}
""" + f"User: {query}"
    result = model.invoke(prompt)
    return json.loads(result.content.strip())


def rag_ans(query,semantic_ans):
    prompt = f'''You are an analyst and you will be passed a semantic query by user along with the matching documnets from our data. Your work is to analyze the query and
    give appropriate answers based on relevant documents you will be passed \n User query = {query} \n Relevant Documents : {semantic_ans}'''
    result = model.invoke(prompt)
    return result.content.strip()

def sql_answer(query,sql_ans):
    prompt = f"""You are an analyst you will be passed a analytical query by user and also its answer which is a output of sql query you have to 
properly examine the query and output and properly form the answer in a human tone dont add keywords like SQL or technical .\n User query = {query} \n SQL Answer : {sql_ans}"""
    result = model.invoke(prompt)
    return result.content.strip()

def chatbot_ans(query):
    category = categorise_query(query)
    if category.lower() == "analytical":
        ans = create_sql_query(query)
        sql_ans = execute_query(ans)
        if sql_ans:
            result = sql_answer(query,sql_ans)
        else:
            result = "Cannot define answer."
    elif category.lower() == "semantic":
        filter_query = create_chroma_filter(query)
        ans = semantic_search(query,filter_query)
        #print(ans)
        semantic_ans = ""
        if ans:
            for i in ans[0]:
                semantic_ans = i + "." + semantic_ans
        result = rag_ans(query, semantic_ans)
    else :
        result = "Cannot define answer."
    return result


# query = "Name the category and amount which has largest expense in January 2026?"
#
# print(chatbot_ans(query))



