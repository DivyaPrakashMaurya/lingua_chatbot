import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.services.chat import chat

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, 'database_path', str(tmp_path / 'test.db'))
    monkeypatch.setattr(settings, 'chat_mode', 'demo')
    monkeypatch.setattr(settings, 'intent_mode', 'demo')
    with TestClient(app) as client:
        yield client

def test_chat_context_persistence_and_delete(client):
    cid = client.post('/api/conversations').json()['id']
    first = client.post(f'/api/conversations/{cid}/messages', json={'message':'Hello'})
    assert first.status_code == 200
    assert first.json()['messages'][1]['metadata']['intent']['label'] == 'greeting'
    second = client.post(f'/api/conversations/{cid}/messages', json={'message':'What did I say before?'})
    assert second.status_code == 200
    data = second.json()['messages']
    assert len(data) == 4
    assert data[-1]['metadata']['context_messages'] == 2
    assert 'Hello' in data[-1]['content']
    assert len(client.get(f'/api/conversations/{cid}').json()['messages']) == 4
    assert client.delete(f'/api/conversations/{cid}').status_code == 204
    assert client.get(f'/api/conversations/{cid}').status_code == 404

def test_validation_and_missing_conversation(client):
    cid = client.post('/api/conversations').json()['id']
    for message in ['', '   ', 'a' * 4001]:
        assert client.post(f'/api/conversations/{cid}/messages', json={'message':message}).status_code == 422
    assert client.post(f'/api/conversations/{cid}/messages', json={'message':'Hello', 'language':'invalid'}).status_code == 422
    assert client.get('/api/conversations/not-a-uuid').status_code == 422
    assert client.get('/api/conversations/00000000-0000-0000-0000-000000000000').status_code == 404

def test_multilingual_and_isolation(client):
    a = client.post('/api/conversations').json()['id']
    b = client.post('/api/conversations').json()['id']
    reply = client.post(f'/api/conversations/{a}/messages', json={'message':'नमस्ते', 'language':'hi'}).json()
    assert reply['messages'][-1]['metadata']['language'] == 'hi'
    assert 'नमस्ते' in reply['messages'][-1]['content']
    assert client.get(f'/api/conversations/{b}').json()['messages'] == []

def test_provider_failure_is_atomic_and_retryable(client, monkeypatch):
    cid = client.post('/api/conversations').json()['id']
    def broken(*args):
        raise RuntimeError('private provider details')
    monkeypatch.setattr(chat, 'reply', broken)
    result = client.post(f'/api/conversations/{cid}/messages', json={'message':'Hello'})
    assert result.status_code == 503
    assert 'private provider details' not in result.text
    assert client.get(f'/api/conversations/{cid}').json()['messages'] == []

def test_context_window_is_bounded(client, monkeypatch):
    monkeypatch.setattr(settings, 'context_messages', 2)
    cid = client.post('/api/conversations').json()['id']
    for text in ['Hello', 'Explain transformers', 'Make it shorter']:
        reply = client.post(f'/api/conversations/{cid}/messages', json={'message':text})
        assert reply.status_code == 200
    assert reply.json()['messages'][-1]['metadata']['context_messages'] == 2
    assert len(reply.json()['messages']) == 6

def test_frontend_and_health(client):
    assert client.get('/').status_code == 200
    assert 'Lingua' in client.get('/').text
    assert client.get('/static/app.js').status_code == 200
    assert client.get('/api/health').json()['chat_mode'] == 'demo'

def test_local_generator_receives_history_and_language(monkeypatch):
    monkeypatch.setattr(settings, 'chat_mode', 'local')
    class FakeTokenizer:
        def apply_chat_template(self, messages, **kwargs):
            assert 'Hindi' in messages[0]['content']
            assert messages[1]['content'] == 'My name is Mira.'
            assert messages[-1]['content'] == 'What is my name?'
            return 'rendered prompt'
    class FakeGenerator:
        tokenizer = FakeTokenizer()
        def __call__(self, prompt, **kwargs):
            assert prompt == 'rendered prompt'
            assert kwargs['return_full_text'] is False
            return [{'generated_text':'आपका नाम मीरा है।'}]
    monkeypatch.setattr(chat, 'generator', FakeGenerator())
    result = chat.reply('What is my name?', [{'role':'user','content':'My name is Mira.'}], 'hi', {'label':'general conversation'})
    assert 'मीरा' in result
