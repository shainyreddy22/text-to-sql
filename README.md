# Dynamic Text-To-SQL Bot

This project is an automated, AI-powered Database Assistant. It seamlessly translates natural language questions into complex, real-time SQL queries, executes those queries directly against a database, and returns the formatted results. 

Currently, the project uses the **Sakila DVD Rental Database** via SQLite, highlighting its capability to handle highly normalized, complex databases with over 20 tables.

## 🛠 Features Currently Implemented
- **Dynamic Database Loading:** Seamlessly swap databases by just modifying the `.env` file without ever breaking the core python logic.
- **Advanced Prompt Engineering:** Implements advanced Prompt Engineering frameworks (**COSTAR** and **Chain of Thought**) to guarantee robust and incredibly accurate SQL syntax—even for massive queries across five different tables.
- **Pandas Execution Engine:** Queries are executed internally via standard `pandas` data frames to ensure safety, readability, and compatibility on all systems.

## 🚀 Future Milestones Roadmap

Below is the detailed milestone roadmap we are currently checking off one by one, to elevate this AI bot to full production readiness:

### 1. Dynamic Setup & Prompt Exploration (✅ Completed)
- Enabled `.env` database swapping (`sakila.db`).
- Explored advanced Prompt Engineering. Added Chain of Thought (CoT) and the COSTAR framework so the AI literally "thinks" through the table schemas before generating the final query code.

### 2. Conversational Bot Memory (✅ Completed)
- Upgrade the standard one-off AI generation into a persistent "Chat Session". This will allow the LLM to remember follow-up questions seamlessly (e.g. Asking "Who directed Inception?" followed directly by "What was its budget?").

### 3. Complex 5-Table JOINS & Testing (✅ Completed)
- Rigorously tested the bot using the strict normalized Sakila database on heavy multi-table operations.
- Successfully executed 5-table and 6-table joins natively (e.g., aggregating geospacial customer data with individual rental history).
- See `TEST_QUERIES.md` for fully documented edge-cases and final data results.

### 4. Guardrails & Unrelated Questions (✅ Completed)
- Injected robust logic directly into the LLM system instructions to prevent the model from answering out-of-domain queries. 
- Polled unrelated queries (e.g., asking for a recipe) bypass SQL execution entirely, instead throwing a polite `GUARDRAIL_VIOLATION` refusal directly to the user.

### 5. Adversarial "Red Team" Breaking (✅ Completed)
- Implemented strict Read-Only Python validations directly inside `db.py`'s execution flow.
- Any generated SQL must pass a REGEX parse. If the AI is successfully "Jailbroken" and attempts to alter the database (using `DROP`, `ALTER`, `UPDATE`, `INSERT`, `DELETE`, etc.), the backend programmatically intercepts the query and throws a `PermissionError` security block, keeping the database unconditionally secure.

## ⚙️ Running Locally

Because this project dynamically reads from the `sakila.db` file shipped in the repository, you only need to install Python dependencies to get it running!

### For Windows
1. Create a virtual environment: `python -m venv venv`
2. Activate it: `.\venv\Scripts\activate`
3. Install dependencies: `pip install -r requirements.txt`
4. Make sure you create your `.env` file!
5. Launch the bot: `python main.py`

### For Mac / Linux
1. Create a virtual environment: `python3 -m venv venv`
2. Activate it: `source venv/bin/activate`
3. Install dependencies: `pip install -r requirements.txt`
4. Make sure you create your `.env` file!
5. Launch the bot: `python3 main.py`
