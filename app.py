from flask import Flask, render_template, request, redirect, url_for, jsonify, abort
import requests
import time
from pathlib import Path
import json
from threading import Lock
import os

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False

# Location to persist pipeline on disk
DATA_DIR = Path(__file__).parent
PIPELINE_FILE = DATA_DIR / "pipeline.json"
_file_lock = Lock()

# Optional API token to protect local /api endpoints (set in env as API_TOKEN)
API_TOKEN = os.environ.get("API_TOKEN")

# Predefined services (copied from original HTML)
SERVICES = [
    {"name": "Google", "url": "https://www.google.com"},
    {"name": "Jules", "url": "https://www.jules.com"},
    {"name": "Codex", "url": "https://www.codex.com"},
    {"name": "Kimi", "url": "https://www.kimi2.6.com"},
    {"name": "Google AI for Developers", "url": "https://ai.google.dev"},
    {"name": "Google Shell", "url": "https://shell.cloud.google.com"},
    {"name": "Perplexity", "url": "https://www.perplexity.com"},
    {"name": "Hugging Face", "url": "https://huggingface.co"},
]


def load_pipeline():
    with _file_lock:
        if not PIPELINE_FILE.exists():
            return []
        try:
            return json.loads(PIPELINE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []


def save_pipeline(pipeline_list):
    with _file_lock:
        PIPELINE_FILE.write_text(json.dumps(pipeline_list, ensure_ascii=False, indent=2), encoding="utf-8")


def _build_proxies():
    """Build a proxies dict for requests from environment variables.
    Supports HTTP_PROXY, HTTPS_PROXY and SOCKS_PROXY. If SOCKS_PROXY is set
    and no HTTP/HTTPS proxies are provided, it will be used for both.
    """
    proxies = {}
    http_p = os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy")
    https_p = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    socks_p = os.environ.get("SOCKS_PROXY") or os.environ.get("socks_proxy")

    if http_p:
        proxies["http"] = http_p
    if https_p:
        proxies["https"] = https_p
    # If SOCKS provided and no explicit http/https, use it for both
    if socks_p and not proxies:
        proxies["http"] = socks_p
        proxies["https"] = socks_p
    return proxies or None


def requests_get_with_proxies(url, timeout=10, **kwargs):
    proxies = _build_proxies()
    # requests will also use env vars automatically if proxies=None, but we build explicitly
    try:
        return requests.get(url, timeout=timeout, proxies=proxies, **kwargs)
    except Exception:
        # Re-raise to caller
        raise


@app.route("/")
def index():
    pipeline = load_pipeline()
    return render_template("index.html", services=SERVICES, pipeline=pipeline)


@app.route("/add_to_pipeline", methods=["POST"])
def add_to_pipeline():
    name = request.form.get("name")
    url = request.form.get("url")
    if not url:
        return redirect(url_for("index"))
    pipeline = load_pipeline()
    pipeline.append({"name": name or url, "url": url})
    save_pipeline(pipeline)
    return redirect(url_for("index"))


@app.route("/remove_from_pipeline", methods=["POST"])
def remove_from_pipeline():
    idx = request.form.get("index")
    if idx is not None:
        try:
            idx = int(idx)
            pipeline = load_pipeline()
            if 0 <= idx < len(pipeline):
                pipeline.pop(idx)
                save_pipeline(pipeline)
        except ValueError:
            pass
    return redirect(url_for("index"))


@app.route("/clear_pipeline", methods=["POST"])
def clear_pipeline():
    save_pipeline([])
    return redirect(url_for("index"))


@app.route("/pipeline", methods=["GET", "POST"])
def pipeline_view():
    pipeline = load_pipeline()
    results = []
    if request.method == "POST":
        results = run_pipeline(pipeline)
    return render_template("pipeline.html", pipeline=pipeline, results=results)


def run_pipeline(pipeline_list, timeout=10):
    results = []
    for entry in pipeline_list:
        url = entry.get("url")
        name = entry.get("name", url)
        start = time.time()
        try:
            r = requests_get_with_proxies(url, timeout=timeout)
            elapsed = r.elapsed.total_seconds() if getattr(r, "elapsed", None) else round(time.time() - start, 3)
            results.append({
                "name": name,
                "url": url,
                "status": r.status_code,
                "ok": r.ok,
                "elapsed": round(elapsed, 3),
            })
        except Exception as e:
            elapsed = round(time.time() - start, 3)
            results.append({
                "name": name,
                "url": url,
                "status": "error",
                "error": str(e),
                "elapsed": elapsed,
            })
    return results


# --- Simple JSON API for remote control (useful from Termux or other remote clients) ---
def _require_api_token():
    if not API_TOKEN:
        return True
    # Accept token in X-API-TOKEN header or Authorization: Bearer <token>
    header = request.headers.get("X-API-TOKEN") or request.headers.get("Authorization")
    if not header:
        return False
    if header.startswith("Bearer "):
        token = header.split(" ", 1)[1].strip()
    else:
        token = header.strip()
    return token == API_TOKEN


@app.route("/api/pipeline", methods=["GET"])
def api_get_pipeline():
    if not _require_api_token():
        return (jsonify({"error": "unauthorized"}), 401)
    return jsonify(load_pipeline())


@app.route("/api/pipeline", methods=["POST"])
def api_add_pipeline():
    if not _require_api_token():
        return (jsonify({"error": "unauthorized"}), 401)
    data = request.json or {}
    name = data.get("name")
    url = data.get("url")
    if not url:
        return (jsonify({"error": "missing url"}), 400)
    pipeline = load_pipeline()
    pipeline.append({"name": name or url, "url": url})
    save_pipeline(pipeline)
    return jsonify(pipeline)


@app.route("/api/pipeline/<int:index>", methods=["DELETE"])
def api_remove_pipeline(index):
    if not _require_api_token():
        return (jsonify({"error": "unauthorized"}), 401)
    pipeline = load_pipeline()
    if 0 <= index < len(pipeline):
        pipeline.pop(index)
        save_pipeline(pipeline)
        return jsonify({"ok": True, "pipeline": pipeline})
    return (jsonify({"error": "index out of range"}), 400)


@app.route("/api/pipeline", methods=["DELETE"])
def api_clear_pipeline():
    if not _require_api_token():
        return (jsonify({"error": "unauthorized"}), 401)
    save_pipeline([])
    return jsonify({"ok": True})


@app.route("/api/run", methods=["POST"])
def api_run_pipeline():
    if not _require_api_token():
        return (jsonify({"error": "unauthorized"}), 401)
    pipeline = load_pipeline()
    results = run_pipeline(pipeline)
    return jsonify(results)


# --- AI agent endpoint skeleton (requires AI_API_URL and AI_API_KEY set in env) ---
_agent_last_run = {"ts": 0, "count": 0}
_AGENT_RATE_LIMIT = int(os.environ.get("AGENT_RATE_LIMIT", "60"))  # requests per minute


@app.route("/api/agent", methods=["POST"])
def api_agent():
    if not _require_api_token():
        return (jsonify({"error": "unauthorized"}), 401)

    data = request.json or {}
    query = data.get("query")
    if not query:
        return jsonify({"error": "missing query"}), 400

    # basic rate limiting
    now = int(time.time())
    if now - _agent_last_run["ts"] >= 60:
        _agent_last_run["ts"] = now
        _agent_last_run["count"] = 0
    _agent_last_run["count"] += 1
    if _agent_last_run["count"] > _AGENT_RATE_LIMIT:
        return jsonify({"error": "rate limit exceeded"}), 429

    # read provider config from env
    api_url = os.environ.get("AI_API_URL")
    api_key = os.environ.get("AI_API_KEY")
    if not api_url or not api_key:
        return jsonify({"error": "AI API not configured on server (set AI_API_URL and AI_API_KEY)"}), 500

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    # payload shape may differ by provider. This is a minimal example and may need adapting.
    payload = {"input": query}

    # Use proxies for provider requests as well (if configured)
    proxies = _build_proxies()

    try:
        r = requests.post(api_url, json=payload, headers=headers, timeout=60, proxies=proxies)
        r.raise_for_status()
        # Return raw provider response under provider_response
        try:
            body = r.json()
        except Exception:
            body = {"text": r.text}
        return jsonify({"provider_response": body}), 200
    except requests.RequestException as e:
        return jsonify({"error": "provider request failed", "detail": str(e)}), 502


if __name__ == "__main__":
    # Make sure data dir exists
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    # Create pipeline file if missing
    if not PIPELINE_FILE.exists():
        save_pipeline([])

    # Bind to all interfaces so you can access from other devices including Termux remote control
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=False)
