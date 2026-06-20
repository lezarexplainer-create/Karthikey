from flask import Flask, render_template, request, redirect, url_for, jsonify
import requests
import time
from pathlib import Path
import json
from threading import Lock

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False

# Location to persist pipeline on disk
DATA_DIR = Path(__file__).parent
PIPELINE_FILE = DATA_DIR / "pipeline.json"
_file_lock = Lock()

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
            r = requests.get(url, timeout=timeout)
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
@app.route("/api/pipeline", methods=["GET"])
def api_get_pipeline():
    return jsonify(load_pipeline())


@app.route("/api/pipeline", methods=["POST"])
def api_add_pipeline():
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
    pipeline = load_pipeline()
    if 0 <= index < len(pipeline):
        pipeline.pop(index)
        save_pipeline(pipeline)
        return jsonify({"ok": True, "pipeline": pipeline})
    return (jsonify({"error": "index out of range"}), 400)


@app.route("/api/pipeline", methods=["DELETE"])
def api_clear_pipeline():
    save_pipeline([])
    return jsonify({"ok": True})


@app.route("/api/run", methods=["POST"])
def api_run_pipeline():
    pipeline = load_pipeline()
    results = run_pipeline(pipeline)
    return jsonify(results)


if __name__ == "__main__":
    # Make sure data dir exists
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    # Create pipeline file if missing
    if not PIPELINE_FILE.exists():
        save_pipeline([])

    # Bind to all interfaces so you can access from other devices including Termux remote control
    app.run(host="0.0.0.0", port=5000, debug=False)
