# Lingua

A context-aware multilingual chatbot with a FastAPI backend, Hugging Face / Transformers inference, and a responsive browser workspace. Includes conversation history, configurable reply languages, intent insights, local persistence, and text export.

Choose **Forest**, **Midnight**, **Ocean**, or **Daylight** from the top-bar color theme menu. The choice is remembered in your browser.

For a beginner-friendly explanation of what we built, how it works, the technologies used, and running it in VS Code, see [PROJECT_NOTES.md](PROJECT_NOTES.md).

## Quick start — Windows PowerShell

Python 3.11 or 3.12 is recommended. The included `.venv` belongs to this computer; recreate it when moving the project.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env  # Only if .env does not already exist
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open **http://127.0.0.1:8000**. Interactive API documentation: **http://127.0.0.1:8000/docs**.

Once installed, `powershell -ExecutionPolicy Bypass -File scripts/start.ps1` also starts the app. On Linux/macOS, create `.venv`, install requirements using `.venv/bin/python`, and run `sh scripts/start.sh`.

## Enable real AI

This workspace is configured for **local AI**: Torch, Transformers, and both model weights are installed, with `CHAT_MODE=local` and `INTENT_MODE=transformer` in `.env`. A real context-recall smoke test returned “Your name is Mira.” from earlier conversation turns.

The shareable `.env.example` starts in **demo mode**, with visibly labeled prepared responses and keyword intent rules. Demo mode is for testing the interface and persistence; it does not perform transformer inference or arbitrary translation. No fabricated model confidence is displayed. For reproducible installation on a compatible Python/Windows setup, use `pip install -r requirements-lock.txt`.

### Option A — Local Transformers (no API token)

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-ml.txt
.\.venv\Scripts\python.exe scripts/download_models.py
```

Update `.env` and restart:

```dotenv
CHAT_MODE=local
INTENT_MODE=transformer
```

The default intent model is `MoritzLaurer/multilingual-MiniLMv2-L6-mnli-xnli`, a multilingual zero-shot NLI transformer. Generation uses `Qwen/Qwen2.5-0.5B-Instruct`, a small CPU-friendly starting point. Initial download requires internet access and several GB of free disk/RAM are advisable. Models load lazily on the first request and remain in memory. CPU inference can be slow; small models have limited reasoning and uneven language coverage. For better quality, configure a larger compatible instruct model and appropriate hardware.

Model files use the Hugging Face cache. Set the standard `HF_HOME` environment variable before starting Python if you want to relocate that cache. The `models/` directory is reserved for custom local model files; model settings can also point to local directories.

### Option B — Hugging Face hosted generation

Create a Hugging Face token with inference access, configure a chat model available through your provider, and update `.env`:

```dotenv
CHAT_MODE=huggingface
HF_TOKEN=your_private_token
HF_CHAT_MODEL=Qwen/Qwen2.5-7B-Instruct
INTENT_MODE=transformer
```

Install `requirements-ml.txt` for the local transformer intent classifier. Hosted model availability, permissions, rate limits, and billing depend on your Hugging Face account/provider. The configured model is an editable starting point, not a guarantee of current provider availability. Token values stay on the backend and are never returned to the browser. Recent conversation text is sent to the selected provider in this mode.

Reference: [Hugging Face inference client](https://huggingface.co/docs/huggingface_hub/en/package_reference/inference_client), [multilingual intent model](https://huggingface.co/MoritzLaurer/multilingual-MiniLMv2-L6-mnli-xnli), [local generation model](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct).

## Project structure

```text
LLM/
├── app/
│   ├── main.py                 # FastAPI lifespan, routes, static web app
│   ├── api/routes.py           # Validated chat and conversation endpoints
│   ├── core/config.py          # Typed .env settings
│   ├── core/database.py        # SQLite transactions and conversation storage
│   └── services/
│       ├── nlp.py              # Language detection and transformer intent routing
│       └── chat.py             # Local, hosted, and explicit demo engines
├── web/
│   ├── index.html              # Accessible, responsive chat workspace
│   ├── styles.css              # Design system and mobile layouts
│   ├── app.js                  # API integration and browser interactions
│   └── icon.svg
├── scripts/                    # Start commands and model download helper
├── tests/                      # API, context, isolation, and provider contract tests
├── data/                       # SQLite database (gitignored)
├── models/                     # Optional custom local model files
├── .venv/                      # Isolated Python environment (gitignored)
├── .env                        # Local configuration and secrets (gitignored)
├── .env.example                # Shareable configuration template
├── requirements.txt            # App, hosted inference, and test dependencies
├── requirements-ml.txt         # Adds Torch and Transformers
└── requirement.text            # Requested alias for full dependency installation
```

`requirements.txt` and `requirement.text` are files, as required by pip, rather than folders.

## How context and intents work

1. Validate the message and selected reply language.
2. Load up to `CONTEXT_MESSAGES` previous messages from that conversation.
3. Detect input language using deterministic `langdetect` plus a Devanagari heuristic. Short text may remain unknown; language detection is approximate.
4. In transformer mode, classify the current request with recent context into greeting, translation, summarization, writing, coding, explanation, planning, or general conversation. Low scores fall back to general conversation. Scores are model scores, not calibrated probabilities.
5. Add intent-specific guidance and the selected reply language to the system prompt, then generate from the current message and history.
6. Save both sides of the exchange in one SQLite transaction. If inference fails, neither side is saved and the browser retains your draft for retry.

Conversation storage retains all turns; only a rolling window is sent to the model. This is short-term conversation memory, not retrieval-augmented generation or a permanent semantic memory. Intent handlers guide responses; they do not execute code or external actions. Explicit language selection overrides automatic response language.

## Checks

```powershell
.\.venv\Scripts\python.exe -m pytest -q
node --check web/app.js
```

Tests run in demo mode and use temporary databases. Provider contract tests use stubs so routine checks do not download models or consume inference credits. Run a real chat in local/hosted mode to verify your chosen model and hardware.

## API

| Method       | Endpoint                           | Purpose                                                   |
| ------------ | ---------------------------------- | --------------------------------------------------------- |
| GET          | `/api/health`                      | Engine configuration and supported UI language selections |
| GET / POST   | `/api/conversations`               | List / create a conversation                              |
| GET / DELETE | `/api/conversations/{id}`          | Read / delete a conversation                              |
| POST         | `/api/conversations/{id}/messages` | Send `{ "message": "Hello", "language": "auto" }`         |

## Deployment scope

This is a personal, local web application, not a multi-tenant hosted service. Run one Uvicorn worker: per-conversation inference locks are process-local. Before exposing it publicly, add authentication and user-scoped records, rate limits, HTTPS, bounded inference queues, and backup/retention policies. All users of a shared instance would otherwise share its conversations. Use a Python-capable host for this FastAPI/Torch stack. The frontend is served by the same origin; no frontend build or Node runtime is required.

Google Fonts are an optional visual enhancement; system sans-serif fonts are used if unavailable.
