# Gemini API Rate Limit Guide

## Problem
The Gemini API free tier has strict rate limits (approximately 1-2 requests per minute). This text-to-SQL application makes multiple API calls per query:
1. Initial SQL generation
2. SQL regeneration (if validation fails)
3. Natural language answer generation

Back-to-back requests can quickly exhaust the quota, resulting in 429 errors.

## Solutions Implemented

### 1. **Exponential Backoff Retry Logic**
When a 429 rate limit error occurs, the application now:
- Waits 30 seconds before first retry
- Waits 60 seconds before second retry  
- Waits 120 seconds before third retry
- Maximum 3 retry attempts per API call

```python
# Example wait sequence:
Attempt 1: Immediate
ERROR 429 → Wait 30s → Attempt 2
ERROR 429 → Wait 60s → Attempt 3
ERROR 429 → Wait 120s → Attempt 4 (fails)
```

### 2. **Global Request Throttling**
All Gemini API calls enforce a minimum 2-second interval between requests:
- Prevents back-to-back calls to the same API
- Works alongside chat session and separate model calls
- Prints throttling messages for debugging

### 3. **Graceful Degradation**
- **Natural answer generation**: If rate limited, returns raw table instead of failing
- **SQL generation**: Retries with exponential backoff before failing
- **SQL regeneration**: Same robust retry logic

## Configuration

### Environment Variables
In your `.env` file:

```env
# Set retry delay (default: 30 seconds)
RETRY_DELAY_SECONDS=30

# Gemini API key
GEMINI_API_KEY=your_api_key_here

# Database path
DB_PATH=sakila.db
```

## Best Practices for Testing

### ✅ DO
- **Wait 60+ seconds** between test queries on the free tier
- **Upgrade your API quota** for frequent testing: https://aistudio.google.com/apikey
- **Test with simple queries first** to minimize retry attempts
- **Check API usage**: https://aistudio.google.com/app/apikey

### ❌ DON'T
- **Send multiple queries in quick succession** (< 60 seconds apart)
- **Generate intentionally failing queries** to test retry logic on production
- **Modify SQL_RETRIES in code** without understanding implications

## Testing Recommendation

When testing the "Show me film titles but only return the film_id and length columns" query:

1. Execute the query
2. **Wait 60 seconds** (not 30!)
3. Execute the next query

This allows the API quota to refresh and avoids consecutive 429 errors.

## Monitoring

The application logs all rate limit events:

```
[llm] Throttling: waiting 1.5s before next API call…
[llm] Rate limit hit (attempt 1/3) — waiting 30s before retry…
[llm] Rate limit hit (attempt 2/3) — waiting 60s before retry…
```

## Upgrading to Paid API

For production use or frequent testing:

1. Go to https://aistudio.google.com/apikey
2. Click "Enable" next to Gemini API
3. Set up billing
4. Your quota increases to 2,000+ requests per minute

## API Call Sequence

For a typical query:

```
User submits query
    ↓
API Call 1: generate_sql()
    ├─ If rate limited: Exponential backoff retry (up to 3 times)
    ├─ If successful: Continue
    ↓
Validate SQL execution
    ├─ If validation fails & attempt < 3:
    │   API Call 2: regenerate_sql_with_feedback()
    │   ├─ If rate limited: Exponential backoff retry
    │   └─ Retry validation (loop if needed)
    ├─ If validation succeeds: Continue
    ↓
API Call 3: generate_natural_answer()
    ├─ If rate limited: Gracefully return raw table
    └─ Return response
```

## Troubleshooting

### Error: "quota exceeded"
- **Cause**: Free tier limit reached (≈1-2 req/min)
- **Fix**: Wait 60 seconds, then try again
- **Long-term**: Upgrade API at https://aistudio.google.com/apikey

### Error after upgrading API quota
- **Cause**: Upgraded tier might have different rate limiting
- **Fix**: Adjust `RETRY_DELAY_SECONDS` in `.env` (try 10-15 seconds)

### Multiple consecutive 429 errors
- **Cause**: Testing too fast with the free tier
- **Fix**: Ensure 60+ seconds between queries; check logs for throttling

## For Developers

To further customize rate limiting, modify these variables in `llm.py`:

```python
# Global rate limiter: minimum seconds between any Gemini API calls
MIN_REQUEST_INTERVAL = 2  # Seconds between API calls

# Retry delay configuration
RETRY_DELAY_SECONDS = 30  # Initial backoff (exponentially multiplied)
```

The retry logic uses exponential backoff: `wait_time = RETRY_DELAY_SECONDS * (2 ** attempt)`
