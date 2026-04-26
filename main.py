"""
CLI entrypoint — still works for terminal usage.
For the Web UI, run:  uvicorn api:app --reload --port 8000
"""
from llm import generate_sql, regenerate_sql_with_feedback, generate_natural_answer
from db import execute_sql, validate_result

MAX_RETRIES = 3


def main():
    print("Dynamic Text-to-SQL Bot Ready (v2 — with validation loop)")
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

            print(f"\nGenerated SQL:\n{sql_query}")

            # ── Validation retry loop ──────────────────────────────
            result = None
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    result = execute_sql(sql_query)
                except PermissionError as pe:
                    print(f"\n🔒 {pe}")
                    result = None
                    break
                except Exception as exec_err:
                    validation_error = f"SQL execution error: {exec_err}"
                    print(f"\n⚠ Attempt {attempt}/{MAX_RETRIES} failed: {validation_error}")
                else:
                    is_valid, reason = validate_result(user_query, result)
                    if is_valid:
                        print(f"✅ Validated on attempt {attempt}")
                        break
                    else:
                        validation_error = reason
                        print(f"\n⚠ Attempt {attempt}/{MAX_RETRIES} validation issue: {reason}")
                        result = None

                if attempt < MAX_RETRIES:
                    print(f"   Asking AI to self-correct…")
                    sql_query = regenerate_sql_with_feedback(user_query, sql_query, validation_error)
                    print(f"   New SQL:\n{sql_query}")

            if result is None:
                print(f"\n❌ Could not produce a valid result after {MAX_RETRIES} attempts.\n")
                continue

            print("\nResult:\n")
            print(result)
            print("\n--- AI Summary ---")
            df_str = result.to_string() if hasattr(result, "to_string") else str(result)
            reply = generate_natural_answer(user_query, sql_query, df_str)
            if "SHOW_RAW_TABLE" not in reply:
                print(reply)
            else:
                print("(Summary skipped — large dataset)")

        except Exception as e:
            print(f"Error: {e}")
        print()


if __name__ == "__main__":
    main()
