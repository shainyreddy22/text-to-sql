# 🤖 Dynamic Text-To-SQL Bot

An automated, AI-powered Database Assistant that seamlessly translates natural language questions into complex, real-time SQL queries. Powered by **Google Gemini 2.5 Flash** with enterprise-grade rate limiting and error handling.

Currently deployed on **Render** and tested with the **Sakila DVD Rental Database** (SQLite, 20+ tables).

**🌐 Live Demo:** [Deploy URL on Render]

---

## ✨ Key Features

### 🎯 Core Functionality
- **Natural Language to SQL:** Ask questions in English, get SQL queries and results back
- **Advanced Prompt Engineering:** COSTAR + Chain of Thought framework for complex queries
- **Multi-Table JOINs:** Handles 5-6 table joins across normalized schemas
- **Web UI:** Interactive HTML frontend for real-time query testing
- **Persistent Chat Memory:** Maintains conversation context across queries

### 🛡️ Security & Reliability
- **Read-Only Protection:** Blocks any SQL modifications (UPDATE, DELETE, DROP, INSERT, ALTER)
- **Guardrail Validation:** Refuses out-of-domain queries unrelated to database schema
- **Smart Rate Limiting:** Exponential backoff retry logic with configurable delays
- **Request Throttling:** Minimum 2-second interval between API calls prevents 429 quota errors
- **Graceful Degradation:** Returns raw results if rate limits hit during summarization

### 🔄 Production-Ready Features
- **FastAPI Backend:** Async HTTP server with CORS support
- **Validation Loop:** 3-attempt retry mechanism for failed queries
- **Error Recovery:** Automatic SQL regeneration with feedback when validation fails
- **Structured Output:** JSON responses with attempt logs and error details

---

## 🚀 Tech Stack

| Component | Technology |
|-----------|-----------|
| **Backend** | FastAPI + Uvicorn |
| **LLM** | Google Gemini 2.5 Flash API |
| **Database** | SQLite (Sakila) + Pandas |
| **Hosting** | Render (Cloud) |
| **Frontend** | HTML + Vanilla JavaScript |

---

## ⚙️ Setup & Installation

### Prerequisites
- Python 3.9+
- `pip` (Python package manager)
- Google Gemini API key (free tier available at [aistudio.google.com](https://aistudio.google.com))

### Local Development

#### Mac / Linux
```bash
# Clone repository
git clone https://github.com/YOUR-USERNAME/text-to-sql-main.git
cd text-to-sql-main

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cat > .env << EOF
GEMINI_API_KEY=your_api_key_here
DB_PATH=sakila.db
RETRY_DELAY_SECONDS=30
EOF

# Start server
uvicorn api:app --reload --port 8000
```

Visit `http://localhost:8000` in your browser.

#### Windows
```bash
# Clone repository
git clone https://github.com/YOUR-USERNAME/text-to-sql-main.git
cd text-to-sql-main

# Create virtual environment
python -m venv venv
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
echo GEMINI_API_KEY=your_api_key_here > .env
echo DB_PATH=sakila.db >> .env
echo RETRY_DELAY_SECONDS=30 >> .env

# Start server
uvicorn api:app --reload --port 8000
```

---

## 🌐 Deployment on Render

This project is deployed on **Render.com** for free (with limitations). Follow these steps:

### 1. Push Code to GitHub
```bash
git add .
git commit -m "Deploy to Render"
git push origin main
```

### 2. Create Render Web Service
1. Go to [render.com](https://render.com)
2. Click **New +** → **Web Service**
3. Connect your GitHub repository
4. Set these values:
   - **Name:** `text-to-sql-main`
   - **Runtime:** `Python 3.11`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn api:app --host 0.0.0.0 --port 8000`

### 3. Configure Environment Variables
In Render dashboard → Environment:
```
GEMINI_API_KEY = your_api_key_here
DB_PATH = sakila.db
RETRY_DELAY_SECONDS = 30
```

### 4. Deploy
- Click **Create Web Service**
- Render automatically deploys on every GitHub push
- Live URL appears on dashboard (e.g., `https://text-to-sql-main.onrender.com`)

> **Note:** Free tier on Render spins down after 15 minutes of inactivity. Upgrade to Pro ($7/month) for always-on hosting.

---

## 📡 API Endpoints

### POST `/api/query`
Generate SQL and execute against database.

**Request:**
```json
{
  "question": "Show me film titles but only return the film_id and length columns"
}
```

**Response (Success):**
```json
{
  "success": true,
  "question": "Show me film titles but only return the film_id and length columns",
  "sql": "SELECT film_id, length FROM film;",
  "columns": ["film_id", "length"],
  "rows": [[1, 86], [2, 169], ...],
  "row_count": 1000,
  "summary": "Retrieved 1000 films with their IDs and lengths.",
  "validation_attempts": [
    {
      "attempt": 1,
      "sql": "SELECT film_id, length FROM film;",
      "validation_error": null,
      "success": true
    }
  ],
  "show_table": true
}
```

**Response (Rate Limit):**
```json
{
  "success": false,
  "question": "...",
  "error": "⏳ Gemini API rate limit reached. Please wait 60+ seconds before trying again..."
}
```

### GET `/api/health`
Health check endpoint.

**Response:**
```json
{
  "status": "ok",
  "db": "sakila.db"
}
```

### GET `/`
Serves the interactive Web UI (index.html).

---

## ⚠️ Rate Limiting Guide

**Free Tier Limits:** ~1-2 requests per minute (Gemini API)

### How the App Handles Rate Limits
1. **Request Throttling:** Minimum 2-seconds between API calls
2. **Exponential Backoff:** 
   - 1st retry: 30 seconds
   - 2nd retry: 60 seconds
   - 3rd retry: 120 seconds
3. **Graceful Degradation:** Returns raw results if AI summary generation fails

### Best Practices
- ✅ Wait **60+ seconds** between test queries
- ✅ Upgrade to paid tier for frequent testing: https://aistudio.google.com/apikey
- ❌ Don't test multiple queries rapidly on free tier
- ❌ Check your API quota regularly

See [RATE_LIMIT_GUIDE.md](RATE_LIMIT_GUIDE.md) for complete rate limiting documentation.

---

## 🧪 Testing

### Local Testing
```bash
# Terminal 1: Start the server
uvicorn api:app --reload --port 8000

# Terminal 2: Send test requests
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "How many films are in the database?"}'

# Or use the Web UI
# Navigate to http://localhost:8000
```

### Test Queries
See [TEST_QUERIES.md](TEST_QUERIES.md) for comprehensive test cases including:
- Multi-table JOINs
- Aggregations
- Edge cases
- Expected results

---

## 📁 Project Structure

```
text-to-sql-main/
├── api.py                 # FastAPI server + main endpoints
├── llm.py                 # Gemini API integration + rate limiting
├── db.py                  # Database execution + security validation
├── schema_loader.py       # Dynamic schema extraction
├── index.html             # Web UI
├── requirements.txt       # Python dependencies
├── sakila.db              # SQLite database (included)
├── .env.example           # Environment variables template
├── .gitignore             # Git ignore rules
├── README.md              # This file
├── TEST_QUERIES.md        # Test cases & results
└── RATE_LIMIT_GUIDE.md    # Rate limiting strategy docs
```

---

## 🔐 Security Features

✅ **Read-Only Mode:** SQL statements checked for modification keywords  
✅ **Domain Guardrails:** Refuses off-topic queries  
✅ **Input Validation:** Query parameters validated before execution  
✅ **Error Isolation:** Sensitive errors logged, safe messages to frontend  
✅ **No SQL Injection:** Queries generated by LLM, not concatenated  

---

## 🎯 Deployment Checklist

Before deploying to Render:
- [ ] Push all changes to GitHub
- [ ] Set `GEMINI_API_KEY` in Render environment
- [ ] Test `/api/health` endpoint on live URL
- [ ] Try a simple query via web UI
- [ ] Verify database is accessible
- [ ] Monitor logs for rate limit errors
- [ ] Document live URL

---

## 💡 Example Queries

Try these questions via the Web UI:

1. **Simple Select:** "Show me all film titles"
2. **Column Selection:** "Show me film titles but only return the film_id and length columns"
3. **Filters:** "Which films are longer than 120 minutes?"
4. **Joins:** "Show me customer names and their rental history"
5. **Aggregations:** "How many rentals were made in each month?"
6. **Complex:** "Find the top 5 customers by total rental amount"

---

## 📈 Future Enhancements

- [ ] Support for multiple database types (PostgreSQL, MySQL)
- [ ] Query caching to reduce API calls
- [ ] User authentication and session management
- [ ] Advanced analytics dashboard
- [ ] Webhook integration for automated reporting
- [ ] WebSocket support for real-time query streaming

---

## 🤝 Contributing

Contributions welcome! Fork the repo, create a feature branch, and submit a PR.

---

## 📝 License

MIT License - Feel free to use this project for personal or commercial work.

---

## 📞 Support

- **Issues:** GitHub Issues tab
- **Questions:** Check TEST_QUERIES.md and RATE_LIMIT_GUIDE.md
- **Rate Limits:** See RATE_LIMIT_GUIDE.md for troubleshooting
- **Deployment:** Render docs at [render.com/docs](https://render.com/docs)
