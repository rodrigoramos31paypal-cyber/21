"""Persistência comum a SQLite local e PostgreSQL de produção."""
import os
from pathlib import Path
from sqlalchemy import create_engine, text, event
from sqlalchemy.pool import NullPool
from sqlalchemy.exc import IntegrityError

def create_database(root):
    url = os.environ.get('DATABASE_URL')
    if url:
        if url.startswith(('postgres://', 'postgresql://')):
            url = 'postgresql+psycopg://' + url.split('://', 1)[1]
        if not url.startswith('postgresql+psycopg://'):
            raise RuntimeError('DATABASE_URL deve apontar para PostgreSQL.')
        engine = create_engine(url, poolclass=NullPool, connect_args={'connect_timeout': 10})
    else:
        if os.environ.get('VERCEL') or os.environ.get('FOCO_ENV') == 'production':
            raise RuntimeError('Configura DATABASE_URL persistente; SQLite não é permitido neste alojamento.')
        path = Path(os.environ.get('FOCO_DB', str(root / 'instance' / 'foco.db')))
        path.parent.mkdir(parents=True, exist_ok=True)
        engine = create_engine('sqlite:///' + str(path))
        @event.listens_for(engine, 'connect')
        def foreign_keys(connection, _):
            connection.execute('PRAGMA foreign_keys=ON')
    return engine

class Connection:
    def __init__(self, engine):
        self.context = engine.begin()
    def __enter__(self):
        self.conn = self.context.__enter__()
        return self
    def __exit__(self, *args):
        return self.context.__exit__(*args)
    def execute(self, sql, values=()):
        parts = sql.split('?')
        query = parts[0] + ''.join(f':p{i}' + part for i, part in enumerate(parts[1:]))
        return self.conn.execute(text(query), {f'p{i}': value for i, value in enumerate(values)}).mappings()

def migrate(engine):
    identity = 'INTEGER PRIMARY KEY AUTOINCREMENT' if engine.dialect.name == 'sqlite' else 'SERIAL PRIMARY KEY'
    statements = [
        f"CREATE TABLE IF NOT EXISTS users(id {identity},email TEXT UNIQUE NOT NULL,password TEXT NOT NULL,name TEXT,track TEXT DEFAULT 'geral',gender TEXT,age INTEGER,height REAL,weight REAL,goal TEXT,restrictions TEXT,calories INTEGER,created_at TEXT)",
        'CREATE TABLE IF NOT EXISTS progress(user_id INTEGER REFERENCES users(id),day INTEGER,checks TEXT,PRIMARY KEY(user_id,day))',
        'CREATE TABLE IF NOT EXISTS account_state(user_id INTEGER PRIMARY KEY REFERENCES users(id),data TEXT NOT NULL,updated_at TEXT NOT NULL)',
        'CREATE TABLE IF NOT EXISTS auth_sessions(token TEXT PRIMARY KEY,user_id INTEGER REFERENCES users(id),expires BIGINT NOT NULL)',
        'CREATE TABLE IF NOT EXISTS auth_limits(bucket TEXT PRIMARY KEY,"window" BIGINT NOT NULL,hits INTEGER NOT NULL)',
        'CREATE TABLE IF NOT EXISTS access_grants(user_id INTEGER PRIMARY KEY REFERENCES users(id),source TEXT NOT NULL)',
        'CREATE TABLE IF NOT EXISTS administrators(user_id INTEGER PRIMARY KEY REFERENCES users(id))',
        'CREATE TABLE IF NOT EXISTS content_settings(key TEXT PRIMARY KEY,value TEXT NOT NULL)',
        'CREATE TABLE IF NOT EXISTS checkout_sessions(id TEXT PRIMARY KEY,user_id INTEGER REFERENCES users(id),status TEXT NOT NULL)',
        'CREATE TABLE IF NOT EXISTS stripe_events(id TEXT PRIMARY KEY)',
        'CREATE TABLE IF NOT EXISTS email_tokens(token TEXT PRIMARY KEY,user_id INTEGER REFERENCES users(id),purpose TEXT NOT NULL,expires BIGINT NOT NULL)',
        'CREATE TABLE IF NOT EXISTS verified_emails(user_id INTEGER PRIMARY KEY REFERENCES users(id))',
    ]
    with Connection(engine) as conn:
        for sql in statements:
            conn.execute(sql)
