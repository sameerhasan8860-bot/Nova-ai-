import os
import time
from collections import defaultdict, deque
from functools import wraps

import requests
from flask import Flask, jsonify, render_template, request, session, redirect, url_for
from pypdf import PdfReader
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET") or os.urandom(32)
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    MAX_CONTENT_LENGTH=5 * 1024 * 1024,
)

ACCESS_PASSWORD = os.environ.get("APP_ACCESS_PASSWORD", "")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
rate_log = defaultdict(deque)

SYSTEM_PROMPT = """You are Nova, a helpful all-in-one AI assistant.
Help with general questions, learning, writing, coding, debugging, planning,
and explaining documents. Be accurate, clear, and practical. If unsure, say so.
For cybersecurity topics, focus on authorized defensive learning and safe testing.
Use the user's language when practical. Format code in fenced code blocks."""

def require_login(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("authenticated"):
            return jsonify({"error": "Please sign in first."}), 401
        return fn(*args, **kwargs)
    return wrapper

def rate_limit(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        ip = request.headers.get("CF-Connecting-IP", request.remote_addr or "unknown")
        now = time.time()
        bucket = rate_log[ip]
        while bucket and now - bucket[0] > 60:
            bucket.popleft()
        if len(bucket) >= 20:
            return jsonify({"error": "Too many requests. Please wait one minute."}), 429
        bucket.append(now)
        return fn(*args, **kwargs)
    return wrapper

@app.get("/")
def home():
    if not session.get("authenticated"):
        return redirect(url_for("login"))
    return render_template("index.html", model=GROQ_MODEL)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if not ACCESS_PASSWORD:
            return render_template("login.html", error="APP_ACCESS_PASSWORD is not configured on the server.")
        supplied = request.form.get("password", "")
        if supplied and supplied == ACCESS_PASSWORD:
            session.clear()
            session["authenticated"] = True
            return redirect(url_for("home"))
        return render_template("login.html", error="Incorrect password. Try again.")
    return render_template("login.html", error="")

@app.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.get("/api/health")
def health():
    return jsonify({"ok": True, "service": "Nova AI", "model": GROQ_MODEL})

@app.post("/api/chat")
@require_login
@rate_limit
def chat():
    if not GROQ_API_KEY:
        return jsonify({"error": "GROQ_API_KEY is missing. Add it in GitHub repository Actions secrets."}), 503
    data = request.get_json(silent=True) or {}
    messages = data.get("messages", [])
    if not isinstance(messages, list) or not messages:
        return jsonify({"error": "Please enter a message."}), 400

    safe_messages = []
    for item in messages[-12:]:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = item.get("content")
        if role not in ("user", "assistant") or not isinstance(content, str):
            continue
        content = content.strip()[:12000]
        if content:
            safe_messages.append({"role": role, "content": content})

    if not safe_messages or safe_messages[-1]["role"] != "user":
        return jsonify({"error": "The latest message must be from the user."}), 400

    payload = {
        "model": GROQ_MODEL,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + safe_messages,
        "temperature": 0.6,
        "max_tokens": 1800,
    }
    try:
        response = requests.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json=payload,
            timeout=90,
        )
        if response.status_code >= 400:
            try:
                detail = response.json().get("error", {}).get("message", response.text)
            except Exception:
                detail = response.text
            return jsonify({"error": f"AI provider error ({response.status_code}): {str(detail)[:500]}"}), 502
        result = response.json()
        answer = result["choices"][0]["message"]["content"]
        return jsonify({"reply": answer, "model": GROQ_MODEL})
    except requests.Timeout:
        return jsonify({"error": "The AI request timed out. Please try again."}), 504
    except Exception as exc:
        app.logger.exception("Chat request failed")
        return jsonify({"error": f"Unexpected server error: {str(exc)[:250]}"}), 500

@app.post("/api/upload")
@require_login
@rate_limit
def upload():
    file = request.files.get("file")
    if not file or not file.filename:
        return jsonify({"error": "Choose a PDF, TXT, or MD file."}), 400
    filename = secure_filename(file.filename)
    ext = os.path.splitext(filename)[1].lower()
    if ext not in (".pdf", ".txt", ".md"):
        return jsonify({"error": "Only PDF, TXT, and MD files are supported in this version."}), 400
    try:
        if ext == ".pdf":
            import io
            reader = PdfReader(io.BytesIO(file.read()))
            text = "\n".join((page.extract_text() or "") for page in reader.pages)
        else:
            text = file.read().decode("utf-8", errors="replace")
        text = text[:30000].strip()
        if not text:
            return jsonify({"error": "No readable text was found in this file."}), 422
        return jsonify({"filename": filename, "text": text})
    except Exception as exc:
        return jsonify({"error": f"Could not read file: {str(exc)[:200]}"}), 400

@app.errorhandler(413)
def too_large(_error):
    return jsonify({"error": "File is too large. Maximum upload size is 5 MB."}), 413

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    app.run(host="0.0.0.0", port=port)
