from llm import generate_sql, generate_natural_answer
from db import execute_sql

def main():
    print("Dynamic Text-to-SQL Bot Ready")
    print("Type 'exit' to quit.\n")
    
    while True:
        user_query = input("Enter your query: ").strip()
        
        if not user_query:
            print("Please enter a valid query.")
            continue
            
        if user_query.lower() == "exit":
            print("Exiting...")
            break
            
        try:
            sql_query = generate_sql(user_query)
            
            if "GUARDRAIL_VIOLATION" in sql_query:
                print(f"\n🤖 Bot: {sql_query.replace('GUARDRAIL_VIOLATION:', '').strip()}\n")
                continue
                
            print("Generated SQL:")
            print(sql_query)
            result = execute_sql(sql_query)
            print("\nResult:\n")
            print(result)
            print("\n--- AI Summary ---")
            
            df_str = result.to_string() if hasattr(result, "to_string") else str(result)
            conversational_reply = generate_natural_answer(user_query, sql_query, df_str)
            
            if "SHOW_RAW_TABLE" not in conversational_reply:
                print(conversational_reply)
            else:
                print("(Summary skipped due to large dataset)")
                
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()
