import sqlite3
import pandas as pd
import os
import re


def is_safe_query(query: str) -> tuple:
    """
    Guard against SQL injection or prompt hacking.
    Ensures the generated SQL is strictly Read-Only.
    """
    forbidden_keywords = [
        "DROP", "DELETE", "UPDATE", "INSERT",
        "ALTER", "TRUNCATE", "REPLACE", "GRANT", "REVOKE"
    ]
    query_upper = query.upper()

    for word in forbidden_keywords:
        if re.search(rf'\b{word}\b', query_upper):
            return False, word

    if not re.search(r'\bSELECT\b', query_upper):
        return False, "MISSING_SELECT"

    return True, None


def execute_sql(query: str) -> pd.DataFrame:
    """Execute a validated SELECT query and return a DataFrame."""
    safe, broken_rule = is_safe_query(query)
    if not safe:
        raise PermissionError(
            f"SECURITY BLOCK: The AI attempted to execute a forbidden "
            f"operation ({broken_rule}). The system is strictly Read-Only."
        )

    db_path = os.getenv("DB_PATH", "sakila.db")
    conn = sqlite3.connect(db_path)
    try:
        df = pd.read_sql_query(query, conn)
    finally:
        conn.close()
    return df


def _has_text_column(df: pd.DataFrame) -> bool:
    """Return True if any column contains string/text data."""
    for col in df.columns:
        dtype = df[col].dtype
        if pd.api.types.is_string_dtype(dtype) or pd.api.types.is_object_dtype(dtype):
            return True
    return False


def _is_aggregation_query(query_lower: str) -> bool:
    """Return True if the question is asking for a count/aggregate."""
    agg_signals = ["how many", "count", "total", "sum", "average", "avg", "number of"]
    return any(kw in query_lower for kw in agg_signals)


def validate_result(user_query: str, df: pd.DataFrame) -> tuple:
    """
    Semantic validation checks on the returned DataFrame to catch
    obvious LLM mistakes before showing results to the user.

    Returns (is_valid, reason_if_invalid).
    """
    lowered = user_query.lower()

    # Check 1: Empty result on an aggregation question
    if df is None or df.empty:
        if _is_aggregation_query(lowered):
            return False, (
                "The query returned no rows, but the question implies "
                "an aggregate result should exist."
            )
        # Empty list (e.g. "list actors in X") is valid — means none found
        return True, ""

    # Check 2: All columns are unnamed/garbage
    unnamed = [c for c in df.columns if str(c).strip() in ("", "None", "nan")]
    if len(unnamed) == len(df.columns):
        return False, (
            "All returned columns appear to be unnamed, which suggests "
            "the SQL selected wrong fields."
        )

    # Check 3: Name/title query but result has only numeric columns.
    # Skip this check for aggregation queries — e.g. "how many customers"
    # legitimately returns a single number.
    name_signals = [
        "name", "title", "actor", "film",
        "city", "country", "category", "staff", "list"
    ]
    is_agg = _is_aggregation_query(lowered)
    if not is_agg and any(sig in lowered for sig in name_signals):
        if not _has_text_column(df) and len(df.columns) <= 2:
            return False, (
                "The question asks for names/titles but the result "
                "contains only numeric columns."
            )

    return True, ""
