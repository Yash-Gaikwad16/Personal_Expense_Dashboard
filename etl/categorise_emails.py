import json
import os
import re
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain.output_parsers import StructuredOutputParser, ResponseSchema
from dotenv import load_dotenv
load_dotenv()

class ExpenseCategorizer:

    def __init__(self, rules_file="rules.json"):
        self.rules_file = rules_file
        self.rules = self.load_rules()

        # init LLM
        self.llm = ChatOpenAI()

        # Structured output parser
        schema = [ResponseSchema(name="category", description="Predicted category")]
        self.output_parser = StructuredOutputParser.from_response_schemas(schema)
        self.format_instructions = self.output_parser.get_format_instructions()

        # Build prompt
        self.prompt = PromptTemplate(
            template=(
                "Classify the given merchant name into one of these categories:\n"
                "Food, Person, Petrol, Grocery, Clothing, Salon, Hospital, Sports, Others.\n"
                "Return ONLY the category name.\n\n"
                "merchant: {text}\n\n"
                "{format_instructions}"
            ),
            input_variables=["text"],
            partial_variables={"format_instructions": self.format_instructions},
        )

        # Build chain
        self.chain = self.prompt | self.llm | self.output_parser

    # --------------------
    #  Load & Save Rules
    # --------------------
    def load_rules(self):
        if not os.path.exists(self.rules_file):
            return {"Food": [], "Petrol": [], "Grocery": [], "Person": [],"Rent": [], "Others": []}

        with open(self.rules_file, "r") as f:
            return json.load(f)

    def save_rules(self):
        with open(self.rules_file, "w") as f:
            json.dump(self.rules, f, indent=4)

    # --------------------
    #  Rule-Based Matching
    # --------------------
    def rule_based_category(self, merchant):
        merchant_lower = merchant.lower()

        for category, keywords in self.rules.items():
            for kw in keywords:
                if kw.lower() in merchant_lower:
                    return category

        return None  # no rule matched

    # ------------------------
    #  LLM Categorization
    # ------------------------
    def llm_categorize(self, merchant):
        result = self.chain.invoke({"text": merchant})
        category = result["category"]

        # Clean output
        return category.strip()

    # ------------------------
    #  Final Categorize Logic
    # ------------------------
    def categorize(self, merchant):
        merchant_clean = merchant.strip()

        # 1️⃣ Try rule-based
        category = self.rule_based_category(merchant_clean)
        if category:
            return category

        # 2️⃣ Fallback to LLM
        category = self.llm_categorize(merchant_clean)

        # 3️⃣ Auto-learn: update rules
        self.rules[category].append(merchant_clean.lower())
        self.save_rules()

        return category
categorizer = ExpenseCategorizer()
def categorize(mails):
    for mail in mails:
        print("*"*80)
        print(mail)
        merchant_name = mail['Paid_to']
        if merchant_name:
            result = categorizer.categorize(merchant_name)
            mail['Category'] = result
        else :
            mail['Category'] = "SIP"
    return mails