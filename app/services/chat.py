from threading import Lock
from app.core.config import settings
from app.services.nlp import LANGUAGES, GUIDANCE

class ChatService:
    def __init__(self):
        self.generator = None
        self.lock = Lock()

    def reply(self, text, history, language, intent):
        if settings.chat_mode == 'demo':
            return self.demo(text, history, language, intent)
        target = LANGUAGES.get(language, language) if language != 'auto' else "the language of the user's latest message"
        system = f'You are Lingua, a helpful multilingual assistant. Respond in {target}. Use conversation history to resolve references and remember user details. Be clear, accurate, and concise. Do not claim to perform external actions. ' + GUIDANCE.get(intent['label'], 'Answer the user helpfully.')
        messages = [{'role':'system','content':system}]
        messages += [{'role':m['role'], 'content':m['content']} for m in history[-settings.context_messages:]]
        messages += [{'role':'user','content':text}]
        if settings.chat_mode == 'huggingface':
            if not settings.hf_token:
                raise RuntimeError('HF_TOKEN is required for Hugging Face mode. Add it to .env and restart.')
            from huggingface_hub import InferenceClient
            client = InferenceClient(token=settings.hf_token, timeout=90)
            result = client.chat_completion(model=settings.hf_chat_model, messages=messages, max_tokens=settings.max_new_tokens, temperature=.6)
            content = result.choices[0].message.content
            if not content:
                raise RuntimeError('The model returned an empty response. Please try again.')
            return content
        with self.lock:
            if self.generator is None:
                from transformers import pipeline
                self.generator = pipeline('text-generation', model=settings.local_chat_model, device=-1)
            prompt = self.generator.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            result = self.generator(prompt, max_new_tokens=settings.max_new_tokens, do_sample=True, temperature=.6, return_full_text=False)
            return result[0]['generated_text'].strip()

    def demo(self, text, history, language, intent):
        intro = {'hi':'नमस्ते! मैं Lingua हूँ।', 'es':'¡Hola! Soy Lingua.', 'fr':'Bonjour ! Je suis Lingua.', 'de':'Hallo! Ich bin Lingua.', 'ar':'مرحباً! أنا Lingua.', 'ja':'こんにちは！Linguaです。', 'zh-cn':'你好！我是 Lingua。', 'pt':'Olá! Eu sou Lingua.', 'bn':'নমস্কার! আমি Lingua।', 'ta':'வணக்கம்! நான் Lingua.'}
        greeting = intro.get(language, 'Hello! I’m Lingua.')
        if intent['label'] == 'greeting':
            return greeting + '\n\nThis is demo mode. You can explore conversations and language settings here. Enable a model in .env for open-ended multilingual answers.'
        if intent['label'] == 'explanation' and any(w in text.lower() for w in ['transformer','context','nlp']):
            return 'A context-aware chatbot uses earlier messages to understand follow-up questions. A transformer processes relationships between tokens using attention.\n\nIn Lingua, a multilingual classifier identifies the intent, an intent-specific instruction guides the response, and recent conversation turns are sent to the language model.\n\nThis is a prepared demo answer. Enable local or Hugging Face mode for generated responses.'
        previous = next((m['content'] for m in reversed(history) if m['role']=='user'), None)
        context = f'\n\nYour previous message was: “{previous[:240]}”' if previous else '\n\nThis is the beginning of our conversation.'
        return f'{greeting}\n\nI identified this as {intent["label"]}. Demo mode demonstrates the workflow using simple rules; it cannot generate a full answer to this request.{context}\n\nEnable local Transformers or connect Hugging Face in .env to continue with an AI-generated answer.'

chat = ChatService()
