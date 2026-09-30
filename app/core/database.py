import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from uuid import uuid4
from app.core.config import ROOT, settings

def now():
    return datetime.now(timezone.utc).isoformat()

@contextmanager
def connection():
    path = ROOT / settings.database_path
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=20)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys = ON')
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def initialize():
    with connection() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS conversations (
          id TEXT PRIMARY KEY, title TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS messages (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
          role TEXT NOT NULL, content TEXT NOT NULL, metadata TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id, id);
        ''')

def create():
    item = dict(id=str(uuid4()), title='New conversation', created_at=now(), updated_at=now())
    with connection() as db:
        db.execute('INSERT INTO conversations VALUES (:id,:title,:created_at,:updated_at)', item)
    return item

def list_all():
    with connection() as db:
        return [dict(r) for r in db.execute('SELECT * FROM conversations ORDER BY updated_at DESC LIMIT 100')]

def get(cid):
    with connection() as db:
        row = db.execute('SELECT * FROM conversations WHERE id=?', (cid,)).fetchone()
        if not row:
            return None
        messages = [dict(r) for r in db.execute('SELECT * FROM messages WHERE conversation_id=? ORDER BY id', (cid,))]
        for message in messages:
            message['metadata'] = json.loads(message['metadata'])
        return dict(row) | {'messages': messages}

def save_turn(cid, user, assistant, metadata):
    with connection() as db:
        # Save the complete exchange together; provider failures cannot leave half a turn.
        stamp = now()
        db.executemany('INSERT INTO messages (conversation_id,role,content,metadata,created_at) VALUES (?,?,?,?,?)',
            [(cid, 'user', user, '{}', stamp), (cid, 'assistant', assistant, json.dumps(metadata), stamp)])
        db.execute("UPDATE conversations SET title=CASE WHEN title='New conversation' THEN ? ELSE title END, updated_at=? WHERE id=?", (user[:60], stamp, cid))

def delete(cid):
    with connection() as db:
        return db.execute('DELETE FROM conversations WHERE id=?', (cid,)).rowcount > 0
