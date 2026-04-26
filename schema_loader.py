import sqlite3


def get_schema(db_path: str) -> str:
    """
    Load schema from a SQLite database including:
    - Table names & column definitions
    - Foreign key relationships (for better JOIN accuracy)
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Enable foreign key info
    cursor.execute("PRAGMA foreign_keys = ON;")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
    tables = cursor.fetchall()

    schema_text = ""

    for (table_name,) in tables:
        schema_text += f"Table: {table_name}\nColumns:\n"
        cursor.execute(f"PRAGMA table_info({table_name})")
        cols = cursor.fetchall()
        for col in cols:
            pk_marker = " [PRIMARY KEY]" if col[5] else ""
            not_null = " NOT NULL" if col[3] else ""
            schema_text += f"  - {col[1]} ({col[2]}){pk_marker}{not_null}\n"

        # Foreign keys for this table
        cursor.execute(f"PRAGMA foreign_key_list({table_name})")
        fks = cursor.fetchall()
        if fks:
            schema_text += "Foreign Keys:\n"
            for fk in fks:
                schema_text += f"  - {table_name}.{fk[3]} → {fk[2]}.{fk[4]}\n"

        schema_text += "\n"

    conn.close()
    return schema_text
