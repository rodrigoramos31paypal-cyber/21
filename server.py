from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
import json
from datetime import datetime

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

DB = 'foco.db'

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            name TEXT,
            track TEXT DEFAULT 'geral',
            gender TEXT,
            age INTEGER,
            height REAL,
            weight REAL,
            goal TEXT,
            restrictions TEXT,
            calories INTEGER,
            created_at TEXT
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS progress (
            user_id INTEGER,
            day INTEGER,
            checks TEXT,
            PRIMARY KEY (user_id, day),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )''')
        conn.commit()

init_db()

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    name = data.get('name', email.split('@')[0])
    if not email or len(password) < 4:
        return jsonify({'error': 'Email e password (mín. 4) obrigatórios'}), 400
    hashed = generate_password_hash(password)
    try:
        with get_db() as conn:
            conn.execute('INSERT INTO users (email, password, name, created_at) VALUES (?, ?, ?, ?)',
                         (email, hashed, name, datetime.utcnow().isoformat()))
            conn.commit()
            user = conn.execute('SELECT id, email, name, track FROM users WHERE email = ?', (email,)).fetchone()
        return jsonify({'ok': True, 'user': dict(user)})
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Email já registado'}), 409

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    with get_db() as conn:
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
    if not user or not check_password_hash(user['password'], password):
        return jsonify({'error': 'Credenciais inválidas'}), 401
    return jsonify({'ok': True, 'user': {'id': user['id'], 'email': user['email'], 'name': user['name'], 'track': user['track']}})

@app.route('/api/progress', methods=['GET'])
def get_progress():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id necessário'}), 400
    with get_db() as conn:
        rows = conn.execute('SELECT day, checks FROM progress WHERE user_id = ?', (user_id,)).fetchall()
    checks = {str(r['day']): json.loads(r['checks']) for r in rows}
    return jsonify({'checks': checks})

@app.route('/api/profile', methods=['POST'])
def save_profile():
    data = request.json
    user_id = data.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id necessário'}), 400
    with get_db() as conn:
        conn.execute('''UPDATE users SET gender=?, age=?, height=?, weight=?, goal=?, restrictions=?, calories=? WHERE id=?''',
                     (data.get('gender'), data.get('age'), data.get('height'), data.get('weight'),
                      data.get('goal'), data.get('restrictions'), data.get('calories'), user_id))
        conn.commit()
    return jsonify({'ok': True})
def save_progress():
    data = request.json
    user_id = data.get('user_id')
    day = data.get('day')
    checks = data.get('checks')
    track = data.get('track')
    if not user_id or not day:
        return jsonify({'error': 'Dados incompletos'}), 400
    with get_db() as conn:
        conn.execute('INSERT OR REPLACE INTO progress (user_id, day, checks) VALUES (?, ?, ?)',
                     (user_id, day, json.dumps(checks)))
        if track:
            conn.execute('UPDATE users SET track = ? WHERE id = ?', (track, user_id))
        conn.commit()
    return jsonify({'ok': True})


# ---- Admin simples (protótipo) ----
@app.route('/api/admin/users')
def admin_users():
    # Em produção: verificar sessão/role de admin
    with get_db() as conn:
        rows = conn.execute('SELECT id, email, name, track, created_at FROM users ORDER BY id DESC').fetchall()
    return jsonify({'users': [dict(r) for r in rows]})

@app.route('/api/admin/stats')
def admin_stats():
    with get_db() as conn:
        total = conn.execute('SELECT COUNT(*) as c FROM users').fetchone()['c']
        progress = conn.execute('SELECT COUNT(DISTINCT user_id) as c FROM progress').fetchone()['c']
    return jsonify({'total_users': total, 'users_with_progress': progress})

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('.', path)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False)
