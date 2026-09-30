# Lingua — Project notes and VS Code guide

## 1. What we made

Lingua is a personal, context-aware multilingual chatbot with a professional responsive web interface. It runs in a browser and uses a Python FastAPI server on your computer.

Features implemented:

- AI-generated conversations using a local Hugging Face transformer model.
- Conversation context: earlier messages help the model answer follow-up questions.
- Transformer-based intent classification and intent-specific response instructions.
- Automatic input-language detection and a selectable reply language.
- Saved conversations in SQLite, separate chat histories, deletion, copying, and text export.
- A live insights panel with detected language, intent, model score, and context count.
- Desktop and mobile layouts, suggested prompts, loading states, and retryable errors.
- Four selectable color themes: **Forest**, **Midnight**, **Ocean**, and **Daylight**. The top-bar theme menu updates the whole interface immediately. The selected theme is saved in browser localStorage and restored on reload.
- Three response modes: local AI, hosted Hugging Face inference, and clearly labeled demo mode.

This is a responsive web app, not a native desktop/mobile application. It is designed for personal local use; public multi-user hosting would need authentication and user-specific data access.

## 2. Which technologies we used

| Technology | Purpose |
| --- | --- |
| Python | Backend application and NLP services |
| FastAPI | HTTP API, request validation, and serving the web interface |
| Uvicorn | Runs the FastAPI application |
| Hugging Face Transformers | Loads the intent and text-generation pipelines |
| PyTorch | Executes local transformer models on the CPU |
| Hugging Face Hub | Downloads model weights and supports optional hosted inference |
| Multilingual MiniLMv2 | Zero-shot intent classification |
| Qwen2.5-0.5B-Instruct | Local conversational text generation |
| langdetect | Approximate input-language detection, with a Devanagari heuristic |
| SQLite | Stores conversations and messages locally |
| Pydantic / pydantic-settings | Validates requests and reads typed `.env` settings |
| HTML, CSS, vanilla JavaScript | Responsive browser interface; no frontend build required |
| CSS custom properties | Shared theme palettes for backgrounds, text, controls, and accents |
| Browser localStorage | Remembers the color theme and last selected conversation |
| pytest and HTTPX | API tests and provider contract checks |

Exact installed versions are recorded in `requirements-lock.txt`.

## 3. How we made it

### Request flow

1. The browser sends the user's message, conversation ID, and selected reply language to FastAPI.
2. Pydantic validates the message and language selection.
3. The backend loads recent messages for that conversation from SQLite.
4. The NLP service estimates the input language and classifies intent using the multilingual transformer.
5. The generation service combines system instructions, intent guidance, recent history, and the latest message.
6. The local Qwen model generates a reply, or the configured hosted Hugging Face provider generates it.
7. Both sides of the exchange are saved together in a SQLite transaction. A failed generation does not save a partial exchange.
8. The browser displays the reply and updates the conversation insights.

### What “context-aware” means here

The default configuration sends up to 12 earlier messages to the model. That lets a follow-up such as “What is my name?” refer to an earlier message. All turns remain saved in SQLite, but only the recent window goes into each generation request. This is conversation history, not permanent semantic memory or document retrieval.

### How intent handling works

The classifier compares the request with greeting, translation, summarization, writing, coding, explanation, planning, and general-conversation labels. The selected intent adds useful instructions to the generation prompt. Low model scores fall back to general conversation. Intent handling does not execute code or take actions in external apps.

### How themes work

`web/theme.js` restores the saved theme before styles render and updates the `data-theme` attribute on the HTML element. `web/themes.css` defines the four palettes using CSS variables and applies them consistently to the sidebar, chat, composer, insights, settings dialog, and error messages. The preference is browser-specific; it does not require a database update or server restart.

## 4. Folder structure and where to make changes

```text
D:\LLM\
├── app/
│   ├── main.py                 FastAPI entry point
│   ├── api/routes.py           API endpoints and validation
│   ├── core/config.py          Application configuration
│   ├── core/database.py        SQLite storage
│   └── services/
│       ├── nlp.py              Language and intent detection
│       └── chat.py             Demo, local, and hosted generation
├── web/
│   ├── index.html              Interface markup
│   ├── styles.css              Layout, spacing, and responsive rules
│   ├── app.js                  Chat interactions and API calls
│   ├── theme.js                Theme selection and persistence
│   └── themes.css              Theme palettes and themed components
├── scripts/                    Start commands and model downloader
├── tests/                      Automated backend tests
├── docs/                       Architecture and validation notes
├── data/lingua.db              Saved conversations (created automatically)
├── models/                     Optional custom model files
├── .venv/                      Python virtual environment
├── .env                        Private local configuration
├── .env.example                Shareable demo configuration template
├── requirements.txt            Core app dependencies
├── requirements-ml.txt         Core dependencies plus ML libraries
├── requirements-lock.txt       Exact installed dependency versions
├── requirement.text            Alias for full dependency installation
└── PROJECT_NOTES.md            This document
```

Model downloads normally live in the Hugging Face cache, not the empty `models/` folder. The `.env`, virtual environment, database, and downloaded models should not be committed to source control.

## 5. Run this existing project in VS Code — Windows

The current workspace already has a `.venv`, installed dependencies, downloaded model weights, and a local-AI `.env`. You do not need to reinstall everything each time.

1. Open VS Code and choose **File → Open Folder**, then open `D:\LLM`.
2. Install the **Python** extension published by Microsoft if you want Python language support and interpreter selection.
3. Open the Command Palette (`Ctrl+Shift+P`), choose **Python: Select Interpreter**, and select `D:\LLM\.venv\Scripts\python.exe`. If it is missing from the list, choose **Enter interpreter path** and browse to that file.
4. Choose **Terminal → New Terminal**. Use PowerShell and check that the terminal is in `D:\LLM`:

   ```powershell
   Set-Location D:\LLM
   ```

5. Start the app with the virtual environment's Python:

   ```powershell
   .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```

6. Open **http://127.0.0.1:8000** in your browser. API documentation is at **http://127.0.0.1:8000/docs**.
7. Keep the terminal running while using the app. Press `Ctrl+C` in that terminal to stop it.

Calling `.venv\Scripts\python.exe` directly avoids virtual-environment activation and PowerShell execution-policy problems. Do not use VS Code Live Server to run this app; the chat needs the FastAPI backend.

For development, add `--reload` to the Uvicorn command. Backend changes will restart the server and reload models on the next request. Refresh your browser after editing HTML, CSS, or JavaScript. Use a hard refresh (`Ctrl+Shift+R`) if old styling is cached.

## 6. First setup on another computer

Install Python 3.11 or 3.12. Open the project folder in VS Code, then run these commands in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-ml.txt
```

Create the configuration only if `.env` does not exist:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Download the models:

```powershell
.\.venv\Scripts\python.exe scripts/download_models.py
```

Set these values in `.env` and save it:

```dotenv
CHAT_MODE=local
INTENT_MODE=transformer
```

Then run the Uvicorn command from section 5. Do not copy another computer's `.venv`; recreate it. Installation and model downloads require internet access and sufficient free disk space.

For a lightweight interface demo, install `requirements.txt` instead and keep both mode settings at `demo`. Demo mode does not generate arbitrary AI answers.

## 7. Useful commands and configuration

```powershell
# Backend tests
.\.venv\Scripts\python.exe -m pytest -q

# Check installed dependency compatibility
.\.venv\Scripts\python.exe -m pip check

# Optional JavaScript syntax checks, if Node.js is installed
node --check web/app.js
node --check web/theme.js
```

Node.js is not required to run the chatbot itself.

Important `.env` settings:

- `CHAT_MODE`: `local`, `huggingface`, or `demo`.
- `INTENT_MODE`: `transformer` or `demo`.
- `LOCAL_CHAT_MODEL`: local generation model ID or directory.
- `INTENT_MODEL`: intent model ID or directory.
- `CONTEXT_MESSAGES`: maximum number of earlier messages included.
- `MAX_NEW_TOKENS`: response-generation limit.
- `HF_TOKEN` and `HF_CHAT_MODEL`: used for optional hosted generation; keep tokens private.

Restart the server after changing `.env`. See `README.md` for hosted Hugging Face configuration.

## 8. Troubleshooting and current limits

| Problem | What to do |
| --- | --- |
| Port 8000 is already in use | Use the app already running there, stop its server, or start this one with `--port 8001` and open port 8001. |
| `python` is not recognized | For this existing setup use `.\.venv\Scripts\python.exe`. On another computer install Python and reopen the terminal. |
| `No module named ...` | Install the requirements using the same `.venv` Python used to run Uvicorn. |
| First reply is slow | Model weights load on the first request. CPU generation is slower than GPU inference. |
| Model is unavailable | Check the terminal log, model settings, installed ML dependencies, and downloaded weights. For hosted mode also check the token and provider availability. |
| Theme looks unchanged | Select a theme in the top bar and hard-refresh. Restricted browser storage may prevent saving the choice between visits. |
| VS Code selected the wrong Python | Select `.venv\Scripts\python.exe`; continue using the explicit terminal command above. |

The small default models can misclassify intents, misdetect short text, or give imperfect answers in some languages. Choosing an explicit reply language helps control output language. Larger models may improve quality but need more memory and processing power. This project uses existing pretrained models; it does not train a new model from scratch.
