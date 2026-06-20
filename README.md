# Karthikey - Python Web Merge (Termux-friendly)

This repo contains a Flask app that reproduces the original index.html UI and provides a pipeline you can control remotely (useful from Termux).

This update adds:
- Proxy support via environment variables: HTTP_PROXY, HTTPS_PROXY, SOCKS_PROXY
- An AI agent endpoint (/api/agent) that forwards queries to an external AI API whose URL and key are provided via environment variables (AI_API_URL, AI_API_KEY)
- Optional API token (API_TOKEN) to protect /api endpoints. If API_TOKEN is set, include it in requests using X-API-TOKEN or Authorization: Bearer <token>
- Agent rate limiting (AGENT_RATE_LIMIT, default 60 req/min)

Quick Termux setup (on your Android device):

1. Install Python in Termux:
   pkg update && pkg upgrade
   pkg install python git

2. Clone this repo or pull changes:
   git clone https://github.com/lezarexplainer-create/Karthikey.git
   cd Karthikey

3. Install dependencies:
   pip install -r requirements.txt

4. Make run.sh executable (if you use it):
   chmod +x run.sh

5. Configure environment variables (example):

# Proxy (optional)
export HTTP_PROXY="http://username:password@proxy-host:3128"
export HTTPS_PROXY="http://username:password@proxy-host:3128"
# or a SOCKS proxy
export SOCKS_PROXY="socks5://username:password@proxy-host:1080"

# AI provider (you must set these yourself)
export AI_API_URL="https://api.example.com/v1/research"
export AI_API_KEY="sk-REPLACE_WITH_YOUR_KEY"

# Optional protection for local API endpoints
export API_TOKEN="choose-a-strong-token-if-you-will-expose-this"

# Optional: change agent rate limit per minute
export AGENT_RATE_LIMIT=60

# Start app (background helper provided by run.sh)
./run.sh start

# Or run in foreground for debugging
python app.py

API examples (if API_TOKEN is set, include X-API-TOKEN header):

# Add site to pipeline
curl -X POST -H "Content-Type: application/json" -H "X-API-TOKEN: $API_TOKEN" \
  -d '{"name":"Hugging Face", "url":"https://huggingface.co"}' \
  http://localhost:5000/api/pipeline

# Run pipeline
curl -X POST -H "X-API-TOKEN: $API_TOKEN" http://localhost:5000/api/run

# Agent query
curl -X POST -H "Content-Type: application/json" -H "X-API-TOKEN: $API_TOKEN" \
  -d '{"query": "Summarize the latest research on retrieval-augmented generation"}' \
  http://localhost:5000/api/agent

Security & policy notes:
- I will NOT store or commit any private API keys. Set AI_API_KEY locally in Termux.
- Do not publish credentials in the repo or commit them.
- This agent simply forwards queries to the configured AI API. It does not bypass provider limits or payment requirements.
- Using proxies to skirt rate limits or access restrictions may violate terms of service of providers or target sites. Use responsibly.

If you want, I can also:
- Add simple HTTP Basic auth or OAuth support for the web UI
- Add Dockerfile and systemd/Termux:Boot examples
- Implement concurrent pipeline execution with configurable concurrency and retry policies

