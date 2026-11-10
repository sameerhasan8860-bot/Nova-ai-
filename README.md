# Nova AI

A private, all-in-one AI chat web app powered by the Groq API. It includes a responsive chat UI, browser-local chat history, PDF/TXT/MD text extraction, a password gate, and a temporary Cloudflare Tunnel URL launched from GitHub Actions.

## Features in this first version

- Responsive website for desktop and mobile browsers
- Groq-powered AI chat (model configurable)
- Code-friendly plain text responses
- PDF, TXT, and Markdown text extraction
- Browser-local conversation history
- Password-protected access
- Simple per-IP request throttling
- Manual GitHub Actions launch with a temporary public URL

## Required GitHub Actions secrets

In **Settings → Secrets and variables → Actions → New repository secret**, add:

| Secret | Value |
|---|---|
| `GROQ_API_KEY` | Your Groq API key |
| `APP_ACCESS_PASSWORD` | A strong private password for opening the app |
| `SESSION_SECRET` | Optional long random secret for Flask sessions |

Optional repository variable under **Settings → Secrets and variables → Actions → Variables**:

- `GROQ_MODEL` — defaults to `openai/gpt-oss-20b`. Set a model currently available to your Groq account.

Never paste API keys into source files, chat messages, or commit history.

## Run on GitHub Actions

1. Keep this repository public if you want standard GitHub-hosted Actions runners to be free.
2. Add the required secrets above.
3. Open the **Actions** tab.
4. Select **Run Nova AI**.
5. Click **Run workflow**.
6. Open the latest successful/in-progress run and find **Nova AI is online** in the workflow summary.
7. Open the temporary URL and enter your `APP_ACCESS_PASSWORD`.

The temporary URL works only while the workflow and runner are alive. This workflow stops after about 5 hours 45 minutes, or earlier if GitHub cancels it. Start a new run to get a new temporary URL.

## Local development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export GROQ_API_KEY="your-key"
export APP_ACCESS_PASSWORD="choose-a-strong-password"
python app.py
```

Open http://127.0.0.1:8000.

## Important limits

- GitHub Actions is a temporary runner, not permanent hosting.
- Groq free-tier availability and rate limits are controlled by Groq and may change.
- Uploaded documents are extracted in memory and are not stored by this app.
- Chat history is stored in the current browser's local storage, not synced between devices.
- This starter version extracts text from PDFs; it does not yet understand images, audio, or video.
- Do not share the temporary public URL or access password publicly. Add stronger production security and persistent storage before opening the app to the public.
