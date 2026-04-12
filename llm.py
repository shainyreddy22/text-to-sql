from google import genai
from google.genai import types
import os
from dotenv import load_dotenv
from schema_loader import get_schema

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
DB_PATH = os.getenv("DB_PATH", "movies.db")
SCHEMA = get_schema(DB_PATH)

system_prompt = f"""
You are an expert SQL database administrator (Role).
Your objective is to write an accurate SQLite query to answer the user's question (Objective).

DATABASE SCHEMA:
{SCHEMA}

CRITICAL INSTRUCTIONS:
Before writing the final query, you MUST think step-by-step.
List out your reasoning inside SQL comments so the code remains valid SQL.
Use the COSTAR framework mentally, and apply Chain of Thought (CoT).

Strictly format your entire response like this:
/*
THINKING PROCESS:
1. Tables Needed: <list tables>
2. JOIN Conditions: <list keys to join>
3. Columns to Select: <list columns>
*/
SELECT ... ;

STRICT RULES:
- Only use the exact tables and columns provided in the schema.
- Use proper SQLite syntax.
- Do not hallucinate tables or columns.
- The output MUST be a valid SQL query starting with comments and ending with the SELECT statement.
- GUARDRAIL: If the user asks a question COMPLETELY UNRELATED to the domain represented by the database tables, DO NOT GENERATE SQL. Output exactly: "GUARDRAIL_VIOLATION: I am a database assistant strictly for '{DB_PATH}'. I can only assist with queries related to its specific schema."
- SECURITY GUARDRAIL: If the user asks to modify or delete data (e.g., UPDATE, INSERT, DROP, DELETE), DO NOT GENERATE SQL. Output exactly: "GUARDRAIL_VIOLATION: I am a read-only assistant for '{DB_PATH}'. I cannot modify the database."
"""

# Initialize a global chat session so the LLM remembers previous context
chat_session = client.chats.create(
    model="gemini-2.5-flash",
    config=types.GenerateContentConfig(
        system_instruction=system_prompt,
        temperature=0.2,
        max_output_tokens=1024
    )
)

def generate_sql(user_query):
    response = chat_session.send_message(user_query)
    
    sql = response.text.strip()
    if sql.startswith("```"):
        sql = sql.split("\n", 1)[-1]
    if sql.endswith("```"):
        sql = sql[:-3]
    return sql.strip()

def generate_natural_answer(user_query, sql_query, df_string):
    prompt = f"""
The user asked: "{user_query}"
We ran this SQL: {sql_query}
The database returned this raw data:
{df_string}

INSTRUCTIONS:
- If the data contains multiple rows/columns (like a long list of actors or films), simply output exactly: SHOW_RAW_TABLE
- If the data is very short (like a single word, a number, or 1-2 items), write a short, friendly, conversational sentence answering the user's question using ONLY the provided data.
"""
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.4)
        )
        return response.text.strip()
    except Exception as e:
        if "429" in str(e) or "quota" in str(e).lower() or "exhausted" in str(e).lower():
            return "(AI Summary explicitly skipped: Gemini API Rate Limit Exceeded. You are making too many queries too fast. Please wait 60 seconds.)"
        return "SHOW_RAW_TABLE"
