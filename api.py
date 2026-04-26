"""
FastAPI backend for Text-to-SQL Web UI.

Endpoints:
  POST /api/query   — main chat endpoint with 3-attempt validation loop
  GET  /api/health  — health check
  GET  /            — serves the Web UI (index.html)
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from llm import generate_sql, regenerate_sql_with_feedback, generate_natural_answer
from db import execute_sql, validate_result

MAX_RETRIES = 3

app = FastAPI(title="Text-to-SQL API", version="2.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    question: str


class AttemptDetail(BaseModel):
    attempt: int
    sql: str
    validation_error: str | None = None
    success: bool


class QueryResponse(BaseModel):
    success: bool
    question: str
    sql: str | None = None
    columns: list | None = None
    rows: list | None = None
    row_count: int | None = None
    summary: str | None = None
    guardrail_message: str | None = None
    validation_attempts: list = []
    error: str | None = None
    show_table: bool = False


def _is_rate_limit(err: Exception) -> bool:
    s = str(err)
    return "429" in s or "RESOURCE_EXHAUSTED" in s or "quota" in s.lower()


def _is_truncated_sql(err: Exception) -> bool:
    """
    PermissionError with MISSING_SELECT means the LLM returned an
    incomplete/truncated response — this is retryable, not a security block.
    """
    return isinstance(err, PermissionError) and "MISSING_SELECT" in str(err)


@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    html_path = Path(__file__).parent / "index.html"
    if html_path.exists():
        return HTMLResponse(content=html_path.read_text())
    return HTMLResponse(
        content="<h1>UI not found. Place index.html next to api.py.</h1>",
        status_code=404
    )


@app.get("/api/health")
async def health():
    db_path = os.getenv("DB_PATH", "sakila.db")
    return {"status": "ok", "db": db_path}


@app.post("/api/query", response_model=QueryResponse)
async def handle_query(req: QueryRequest):
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    attempts: list[AttemptDetail] = []
    current_sql = None
    last_validation_error = None

    # ── Step 1: Generate initial SQL ──────────────────────────────────────
    try:
        current_sql = generate_sql(question)
    except Exception as e:
        if _is_rate_limit(e):
            return QueryResponse(
                success=False,
                question=question,
                error="⏳ Gemini API rate limit reached. Please wait 60+ seconds before trying again. "
                      "The free tier allows ~1-2 requests per minute. For frequent testing, "
                      "upgrade your API quota on https://aistudio.google.com/apikey"
            )
        return QueryResponse(
            success=False,
            question=question,
            error=f"LLM error during SQL generation: {str(e)}"
        )

    # ── Guardrail check ───────────────────────────────────────────────────
    if "GUARDRAIL_VIOLATION" in current_sql:
        message = current_sql.replace("GUARDRAIL_VIOLATION:", "").strip()
        return QueryResponse(
            success=True,
            question=question,
            guardrail_message=message
        )

    # ── Step 2: Validation retry loop (up to MAX_RETRIES attempts) ────────
    df = None
    for attempt_num in range(1, MAX_RETRIES + 1):
        exec_error = None

        try:
            df = execute_sql(current_sql)

        except PermissionError as pe:
            if _is_truncated_sql(pe):
                # LLM returned incomplete SQL (no SELECT) — treat as retryable
                exec_error = (
                    "The generated SQL was incomplete (missing SELECT statement). "
                    "Please generate a complete, valid SQL query."
                )
                attempts.append(AttemptDetail(
                    attempt=attempt_num,
                    sql=current_sql,
                    validation_error=exec_error,
                    success=False
                ))
                last_validation_error = exec_error
            else:
                # True security block (DROP/DELETE/etc.) — hard stop, never retry
                return QueryResponse(
                    success=False,
                    question=question,
                    sql=current_sql,
                    error=f"🔒 {str(pe)}",
                    validation_attempts=[a.__dict__ for a in attempts]
                )

        except Exception as e:
            exec_error = f"SQL execution error: {str(e)}"
            attempts.append(AttemptDetail(
                attempt=attempt_num,
                sql=current_sql,
                validation_error=exec_error,
                success=False
            ))
            last_validation_error = exec_error

        else:
            # Execution succeeded — semantically validate the result
            is_valid, reason = validate_result(question, df)
            if is_valid:
                attempts.append(AttemptDetail(
                    attempt=attempt_num,
                    sql=current_sql,
                    validation_error=None,
                    success=True
                ))
                break  # ✅ Good result — exit retry loop
            else:
                last_validation_error = reason
                attempts.append(AttemptDetail(
                    attempt=attempt_num,
                    sql=current_sql,
                    validation_error=reason,
                    success=False
                ))
                df = None  # reset so we don't accidentally use a bad result

        # ── Ask LLM to self-correct before next attempt ────────────────
        if attempt_num < MAX_RETRIES:
            feedback_error = exec_error or last_validation_error or "Unknown validation failure"
            try:
                current_sql = regenerate_sql_with_feedback(question, current_sql, feedback_error)

                # Guard: LLM might return a guardrail message even on retry
                if "GUARDRAIL_VIOLATION" in current_sql:
                    message = current_sql.replace("GUARDRAIL_VIOLATION:", "").strip()
                    return QueryResponse(
                        success=True,
                        question=question,
                        guardrail_message=message,
                        validation_attempts=[a.__dict__ for a in attempts]
                    )

            except Exception as e:
                if _is_rate_limit(e):
                    # Rate limit during regeneration — stop retrying, surface a clear message
                    return QueryResponse(
                        success=False,
                        question=question,
                        sql=current_sql,
                        error=(
                            f"⏳ Gemini API rate limit hit during retry #{attempt_num + 1}. "
                            f"Please wait ~30 seconds and try your question again."
                        ),
                        validation_attempts=[a.__dict__ for a in attempts]
                    )
                return QueryResponse(
                    success=False,
                    question=question,
                    error=f"LLM regeneration error: {str(e)}",
                    validation_attempts=[a.__dict__ for a in attempts]
                )

    # ── All attempts exhausted without a valid result ─────────────────────
    if df is None:
        return QueryResponse(
            success=False,
            question=question,
            sql=current_sql,
            error=(
                f"❌ Unable to produce a valid result after {MAX_RETRIES} attempts. "
                f"Last issue: {last_validation_error}. "
                f"Please try rephrasing your question."
            ),
            validation_attempts=[a.__dict__ for a in attempts]
        )

    # ── Step 3: Build response from successful DataFrame ──────────────────
    df_str = df.to_string() if hasattr(df, "to_string") else str(df)
    summary = generate_natural_answer(question, current_sql, df_str)
    show_table = "SHOW_RAW_TABLE" in summary or df.shape[0] > 5 or df.shape[1] > 4

    return QueryResponse(
        success=True,
        question=question,
        sql=current_sql,
        columns=list(df.columns),
        rows=df.values.tolist(),
        row_count=len(df),
        summary=None if show_table else summary,
        show_table=show_table,
        validation_attempts=[a.__dict__ for a in attempts]
    )
