import sqlite3
def get_schema(db_path: str):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    schema_text = ""
    
    for (table_name,) in tables:
        schema_text += f"Table: {table_name}\nColumns:\n"
        cursor.execute(f"PRAGMA table_info({table_name})")
        cols = cursor.fetchall()
        for col in cols:
            schema_text += f"- {col[1]} ({col[2]})\n"
        schema_text += "\n"
        
    conn.close()
    return schema_text
