import logging
import time
from threading import Lock
from uuid import UUID
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator
from app.core.config import settings
from app.core import database as db
from app.services.nlp import nlp, LANGUAGES
from app.services.chat import chat

router = APIRouter(prefix='/api')
# Bound lock pool serializes turns of a conversation without growing with history.
locks = [Lock() for _ in range(64)]

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    language: str = 'auto'

    @field_validator('message')
    @classmethod
    def nonempty(cls, value):
        if not value.strip():
            raise ValueError('Message cannot be blank')
        return value.strip()

    @field_validator('language')
    @classmethod
    def known_language(cls, value):
        if value not in LANGUAGES:
            raise ValueError('Unsupported language selection')
        return value

@router.get('/health')
def health():
    return {'status':'ok','chat_mode':settings.chat_mode,'intent_mode':settings.intent_mode,'context_window':settings.context_messages,'languages':LANGUAGES}

@router.get('/conversations')
def conversations():
    return db.list_all()

@router.post('/conversations', status_code=201)
def create_conversation():
    return db.create()

@router.get('/conversations/{cid}')
def conversation(cid: UUID):
    result = db.get(str(cid))
    if result is None:
        raise HTTPException(404, 'Conversation not found')
    return result

@router.delete('/conversations/{cid}', status_code=204)
def delete_conversation(cid: UUID):
    with locks[hash(str(cid)) % len(locks)]:
        if not db.delete(str(cid)):
            raise HTTPException(404, 'Conversation not found')

@router.post('/conversations/{cid}/messages')
def send(cid: UUID, body: ChatRequest):
    with locks[hash(str(cid)) % len(locks)]:
        current = conversation(cid)
        started = time.monotonic()
        history = current['messages'][-settings.context_messages:]
        detected = nlp.language(body.message)
        try:
            intent = nlp.classify(body.message, history)
            reply = chat.reply(body.message, history, detected if body.language=='auto' and detected!='und' else body.language, intent)
        except Exception:
            logging.exception('Inference failed')
            raise HTTPException(503, 'The model is unavailable. Check model settings, installed ML dependencies, and your Hugging Face token. Your message was not saved; please retry.') from None
        metadata = {'intent':intent, 'language':detected, 'reply_language':body.language, 'context_messages':len(history), 'latency_ms':round((time.monotonic()-started)*1000), 'mode':settings.chat_mode}
        db.save_turn(str(cid), body.message, reply, metadata)
        return db.get(str(cid))