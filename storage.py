"""Local, parameterized SQLite persistence. No API keys in the storage schema."""
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4
from datetime import datetime, timezone

DEFAULT_DB = Path(__file__).resolve().parent / 'data' / 'interviews.sqlite3'

@contextmanager
def connect(path=DEFAULT_DB):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    try:
        with db:
            db.execute('CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, title TEXT NOT NULL, updated TEXT NOT NULL, payload TEXT NOT NULL)')
            yield db
    finally:
        db.close()

def save(session, path=DEFAULT_DB):
    # Deliberate whitelist prevents accidental inclusion of UI key fields.
    clean = {k: session[k] for k in ('id', 'request', 'model', 'pack', 'answers', 'feedback')}
    with connect(path) as db:
        db.execute('INSERT INTO sessions VALUES (?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET title=excluded.title, updated=excluded.updated, payload=excluded.payload',
                   (clean['id'], clean['pack']['title'], datetime.now(timezone.utc).isoformat(), json.dumps(clean)))

def list_sessions(path=DEFAULT_DB):
    with connect(path) as db:
        return db.execute('SELECT id,title,updated FROM sessions ORDER BY updated DESC LIMIT 100').fetchall()

def load(session_id, path=DEFAULT_DB):
    with connect(path) as db:
        row = db.execute('SELECT payload FROM sessions WHERE id=?', (session_id,)).fetchone()
    return json.loads(row[0]) if row else None

def delete(session_id, path=DEFAULT_DB):
    with connect(path) as db:
        db.execute('DELETE FROM sessions WHERE id=?', (session_id,))

def new_session(request, model, pack):
    return {'id': uuid4().hex, 'request': request.model_dump(), 'model': model,
            'pack': pack.model_dump(), 'answers': {}, 'feedback': {}}
