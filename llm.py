from google import genai
from google.genai import types
import os
import re
import time
from dotenv import load_dotenv
from schema_loader import get_schema

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
DB_PATH = os.getenv("DB_PATH", "sakila.db")
SCHEMA = get_schema(DB_PATH)

# How many seconds to wait between retries to avoid 429 rate limit
RETRY_DELAY_SECONDS = int(os.getenv("RETRY_DELAY_SECONDS", "30"))

# Global rate limiter: minimum seconds between any Gemini API calls
MIN_REQUEST_INTERVAL = 2
last_request_time = 0

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
- The output MUST be a complete, valid SQL query. It MUST contain a SELECT statement.
- Never truncate or cut off the query mid-way. Always output the full query ending with a semicolon.
- GUARDRAIL: If the user asks a question COMPLETELY UNRELATED to the domain represented by the database tables, DO NOT GENERATE SQL. Output exactly: "GUARDRAIL_VIOLATION: I am a database assistant strictly for '{DB_PATH}'. I can only assist with queries related to its specific schema."
- SECURITY GUARDRAIL: If the user asks to modify or delete data (e.g., UPDATE, INSERT, DROP, DELETE), DO NOT GENERATE SQL. Output exactly: "GUARDRAIL_VIOLATION: I am a read-only assistant for '{DB_PATH}'. I cannot modify the database."
"""

# Persistent chat session — LLM remembers conversation context
chat_session = client.chats.create(
    model="gemini-2.5-flash",
    config=types.GenerateContentConfig(
        system_instruction=system_prompt,
        temperature=0.2,
        max_output_tokens=2048   # bumped up: was 1024, truncation risk reduced
    )
)


def _clean_sql(raw: str) -> str:
    """
    Strip markdown fences and language tags robustly.
    Handles: ```sql, ```SQL, ```, and bare backtick lines.
    """
    text = raw.strip()

    # Remove opening fence (```sql or ```)
    text = re.sub(r'^```[a-zA-Z]*\n?', '', text, flags=re.MULTILINE)
    # Remove closing fence
    text = re.sub(r'```\s*$', '', text, flags=re.MULTILINE)

    return text.strip()


def _enforce_rate_limit():
    """
    Enforce minimum interval between Gemini API requests.
    Prevents back-to-back requests that trigger 429 errors.
    """
    global last_request_time
    now = time.time()
    time_since_last = now - last_request_time
    if time_since_last < MIN_REQUEST_INTERVAL:
        wait_time = MIN_REQUEST_INTERVAL - time_since_last
        print(f"[llm] Throttling: waiting {wait_time:.1f}s before next API call…")
        time.sleep(wait_time)
    last_request_time = time.time()


def _extract_retry_delay(error_str: str) -> int:
    """
    Parse the retryDelay seconds from a 429 error message if present.
    Falls back to RETRY_DELAY_SECONDS env var.
    """
    match = re.search(r'retry[Dd]elay.*?(\d+)s', error_str)
    if match:
        return int(match.group(1)) + 2   # small buffer on top
    return RETRY_DELAY_SECONDS


def _call_with_rate_limit_retry(fn, *args, **kwargs):
    """
    Call fn(*args, **kwargs) with exponential backoff retry logic.
    - Enforces minimum interval between API calls
    - On 429/quota error: waits with exponential backoff and retries up to 3 times
    - All other errors are re-raised immediately
    """
    max_retries = 3
    
    for attempt in range(max_retries):
        _enforce_rate_limit()
        
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            err = str(e)
            is_rate_limit = "429" in err or "RESOURCE_EXHAUSTED" in err or "quota" in err.lower()
            
            if not is_rate_limit:
                # Non-rate-limit errors fail immediately
                raise
            
            if attempt < max_retries - 1:
                # Calculate exponential backoff: 30s, 60s, 120s
                wait_time = RETRY_DELAY_SECONDS * (2 ** attempt)
                print(f"[llm] Rate limit hit (attempt {attempt + 1}/{max_retries}) — "
                      f"waiting {wait_time}s before retry…")
                time.sleep(wait_time)
            else:
                # Last attempt failed — re-raise
                raise


def generate_sql(user_query: str) -> str:
    """Generate a SQL query from a natural language question."""
    def _call():
        return chat_session.send_message(user_query)

    response = _call_with_rate_limit_retry(_call)
    return _clean_sql(response.text)


def regenerate_sql_with_feedback(user_query: str, previous_sql: str, validation_error: str) -> str:
    """
    Ask the LLM to fix a previously generated SQL that failed validation.
    Sends the failure reason so the model can self-correct.
    Uses central rate limiting to avoid back-to-back 429s.
    """
    feedback_prompt = (
        f"The SQL you previously generated for the question: \"{user_query}\"\n\n"
        f"SQL attempted:\n{previous_sql}\n\n"
        f"VALIDATION FAILED with reason: {validation_error}\n\n"
        f"Please carefully reconsider and generate a COMPLETE, corrected SQL query "
        f"that addresses this issue. The query MUST include a full SELECT statement "
        f"and end with a semicolon. Follow the same strict format as before."
    )

    def _call():
        return chat_session.send_message(feedback_prompt)

    response = _call_with_rate_limit_retry(_call)
    return _clean_sql(response.text)


def generate_natural_answer(user_query: str, sql_query: str, df_string: str) -> str:
    """Convert raw DB results into a friendly conversational response."""
    prompt = (
        f"The user asked: \"{user_query}\"\n"
        f"We ran this SQL: {sql_query}\n"
        f"The database returned this raw data:\n{df_string}\n\n"
        f"INSTRUCTIONS:\n"
        f"- If the data contains multiple rows/columns (like a long list of actors or films), "
        f"simply output exactly: SHOW_RAW_TABLE\n"
        f"- If the data is very short (like a single word, a number, or 1-2 items), "
        f"write a short, friendly, conversational sentence answering the user's question "
        f"using ONLY the provided data."
    )
    def _call():
        return client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.4)
        )

    try:
        response = _call_with_rate_limit_retry(_call)
        return response.text.strip()
    except Exception as e:
        err = str(e)
        # Handle rate limit gracefully — return raw table instead of failing
        if "429" in err or "quota" in err.lower() or "exhausted" in err.lower():
            print("[llm] Rate limit on natural answer generation — returning raw table")
            return "SHOW_RAW_TABLE"
        # Other errors also degrade gracefully
        print(f"[llm] Error generating natural answer: {err}")
        return "SHOW_RAW_TABLE"
