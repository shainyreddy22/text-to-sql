import sqlite3
import pandas as pd
import os
import re

def is_safe_query(query):
    """
    Milestone 5: Guard against SQL injection or prompt hacking.
    Ensure the generated SQL is strictly Read-Only.
    """
    forbidden_keywords = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE", "REPLACE", "GRANT", "REVOKE"]
    query_upper = query.upper()
    
    for word in forbidden_keywords:
        # Regex checks for standalone blocked keywords (prevents false positive if a column is named `update_time`)
        if re.search(rf'\b{word}\b', query_upper):
            return False, word
            
    # As a secondary stricter check, ensure the query actually has a SELECT
    if not re.search(r'\bSELECT\b', query_upper):
         return False, "MISSING_SELECT"
         
    return True, None

def execute_sql(query):
    print("INSIDE DB.PY")    # 🔥 debug
    
    # Perform strict Security Checks before execution
    safe, broken_rule = is_safe_query(query)
    if not safe:
        raise PermissionError(f"SECURITY BLOCK: The AI attempted to execute a forbidden operation ({broken_rule}). The system is strictly Read-Only.")
        
    db_path = os.getenv("DB_PATH", "movies.db")
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query(query, conn)
    conn.close()
    print(type(df))          # 🔥 debug
    return df
