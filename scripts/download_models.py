"""Download model files ahead of the first local inference request."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from huggingface_hub import snapshot_download
from app.core.config import settings

if __name__ == '__main__':
    for model in [settings.intent_model, settings.local_chat_model]:
        print(f'Downloading {model} ...', flush=True)
        snapshot_download(model, allow_patterns=['*.json', '*.safetensors', '*.model', '*.txt', '*.tiktoken'], token=settings.hf_token or None)
    print('Models ready. Set CHAT_MODE=local and INTENT_MODE=transformer in .env, then restart.')
