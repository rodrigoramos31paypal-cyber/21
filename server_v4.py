"""API Flask do projeto: sessões, SQLite e estado individual V4."""
from flask import Flask, request, jsonify, send_from_directory, session
from werkzeug.security import generate_password_hash, check_password_hash
from pathlib import Path
from functools import wraps
from datetime import datetime, timezone
from urllib.parse import urlsplit
from collections import defaultdict, deque
import sqlite3, os, json, secrets, re, time
ROOT = Path(__file__).resolve().parent
app = Flask(__name__, static_folder=None)
app.config.update(SECRET_KEY=os.environ.get('SECRET_KEY') or secrets.token_hex(32), SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax', SESSION_COOKIE_SECURE=os.environ.get('COOKIE_SECURE') == '1', MAX_CONTENT_LENGTH=128 * 1024)
DB = os.environ.get('FOCO_DB', str(ROOT / 'instance' / 'foco.db'))
Path(DB).parent.mkdir(parents=True, exist_ok=True)
MEALS = {'pequeno', 'almoco', 'lanche', 'jantar'}
ALLERGIES = {'leite', 'gluten', 'ovos', 'amendoim', 'frutos-casca', 'soja', 'sesamo', 'aipo', 'peixe', 'crustaceos', 'moluscos', 'mostarda', 'tremoco', 'sulfitos'}
RECIPES = {r['id']: r for r in json.loads((ROOT / 'receitas.js').read_text().removeprefix('window.FOCO_RECIPES = ').strip().removesuffix(';'))}
attempts = defaultdict(deque)

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys=ON')
    return conn

def init_db():
    with get_db() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT,email TEXT UNIQUE NOT NULL,password TEXT NOT NULL,name TEXT,track TEXT DEFAULT 'geral',gender TEXT,age INTEGER,height REAL,weight REAL,goal TEXT,restrictions TEXT,calories INTEGER,created_at TEXT)")
        conn.execute('CREATE TABLE IF NOT EXISTS progress(user_id INTEGER,day INTEGER,checks TEXT,PRIMARY KEY(user_id,day),FOREIGN KEY(user_id) REFERENCES users(id))')
        conn.execute('CREATE TABLE IF NOT EXISTS account_state(user_id INTEGER PRIMARY KEY REFERENCES users(id),data TEXT NOT NULL,updated_at TEXT NOT NULL)')
init_db()

@app.before_request
def protect_api():
    if request.path.startswith('/api/') and request.method in {'POST', 'PUT', 'DELETE'}:
        if not request.is_json:
            return (jsonify(error='É necessário enviar dados JSON.'), 415)
        origin = request.headers.get('Origin')
        if origin and urlsplit(origin).netloc != request.host or request.headers.get('Sec-Fetch-Site') == 'cross-site':
            return (jsonify(error='Origem não autorizada.'), 403)

@app.after_request
def headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'same-origin'
    response.headers['X-Frame-Options'] = 'DENY'
    if request.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'no-store'
    return response

def authenticated(fn):

    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not session.get('user_id'):
            return (jsonify(error='Inicia sessão para aceder à tua conta.'), 401)
        return fn(*args, **kwargs)
    return wrapped

def current_user():
    with get_db() as conn:
        row = conn.execute('SELECT id,email,name,track FROM users WHERE id=?', (session.get('user_id'),)).fetchone()
    return dict(row) if row else None

def rate_limit():
    q = attempts[request.remote_addr or 'local']
    now = time.monotonic()
    while q and q[0] < now - 60:
        q.popleft()
    if len(q) >= 20:
        return True
    q.append(now)
    return False

def credentials(registering=False):
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValueError('Dados inválidos.')
    email, password = (data.get('email', ''), data.get('password', ''))
    if not isinstance(email, str) or not isinstance(password, str):
        raise ValueError('Credenciais inválidas.')
    email = email.strip().lower()
    if len(email) > 254 or not re.fullmatch('[^\\s@]+@[^\\s@]+\\.[^\\s@]+', email):
        raise ValueError('Indica um email válido.')
    if not (10 if registering else 1) <= len(password) <= 128:
        raise ValueError('Para criar conta, usa uma palavra-passe entre 10 e 128 caracteres.')
    return (email, password, data)

@app.route('/api/session')
def session_info():
    return jsonify(user=current_user())

@app.route('/api/register', methods=['POST'])
def register():
    if rate_limit():
        return (jsonify(error='Demasiadas tentativas. Aguarda um minuto.'), 429)
    try:
        email, password, data = credentials(registering=True)
        name = data.get('name', '')
        if not isinstance(name, str) or len(name) > 60:
            raise ValueError('Nome inválido.')
        with get_db() as conn:
            cur = conn.execute('INSERT INTO users(email,password,name,created_at) VALUES(?,?,?,?)', (email, generate_password_hash(password), name, datetime.now(timezone.utc).isoformat()))
            uid = cur.lastrowid
        session.clear()
        session['user_id'] = uid
        return (jsonify(ok=True, user=current_user()), 201)
    except ValueError as error:
        return (jsonify(error=str(error)), 400)
    except sqlite3.IntegrityError:
        return (jsonify(error='Este email já está registado.'), 409)

@app.route('/api/login', methods=['POST'])
def login():
    if rate_limit():
        return (jsonify(error='Demasiadas tentativas. Aguarda um minuto.'), 429)
    try:
        email, password, _ = credentials()
    except ValueError as error:
        return (jsonify(error=str(error)), 400)
    with get_db() as conn:
        user = conn.execute('SELECT * FROM users WHERE email=?', (email,)).fetchone()
    if not user or not check_password_hash(user['password'], password):
        return (jsonify(error='Credenciais inválidas.'), 401)
    session.clear()
    session['user_id'] = user['id']
    return jsonify(ok=True, user=current_user())

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify(ok=True)

def validate_profile(p):
    if not isinstance(p, dict):
        raise ValueError('Perfil inválido.')
    if not isinstance(p.get('name'), str) or not 1 <= len(p['name'].strip()) <= 60:
        raise ValueError('Indica um nome até 60 caracteres.')
    for key, lo, hi in [('age', 16, 110), ('height', 100, 250), ('weight', 25, 350)]:
        value = p.get(key)
        if value is not None and (type(value) not in (int, float) or not lo <= value <= hi):
            raise ValueError('Dados físicos inválidos.')
    for key, values in [('goal', {'perder', 'manter', 'ganhar'}), ('place', {'casa', 'ginasio'}), ('diet', {'todos', 'vegetariano', 'vegan'}), ('experience', {'iniciante', 'intermedio', 'avancado'})]:
        if not isinstance(p.get(key), str) or p[key] not in values:
            raise ValueError('Preferência inválida.')
    if type(p.get('availability')) is not int or p['availability'] not in {2, 3, 4, 5}:
        raise ValueError('Disponibilidade inválida.')
    for key, allowed in [('meals', MEALS), ('allergies', ALLERGIES)]:
        values = p.get(key)
        if not isinstance(values, list) or any((not isinstance(v, str) or v not in allowed for v in values)) or len(values) != len(set(values)):
            raise ValueError('Seleção inválida.')
    if not p['meals']:
        raise ValueError('Escolhe pelo menos uma refeição.')
    if not isinstance(p.get('otherRestrictions', ''), str) or len(p.get('otherRestrictions', '')) > 300:
        raise ValueError('Outras restrições inválidas.')
    return {k: p.get(k) for k in ['name', 'age', 'height', 'weight', 'goal', 'place', 'diet', 'experience', 'availability', 'meals', 'allergies', 'otherRestrictions']}

def validate_state(data):
    if not isinstance(data, dict):
        raise ValueError('Estado inválido.')
    p = validate_profile(data.get('profile'))
    plan = data.get('plan')
    if not isinstance(plan, list) or len(plan) != 21:
        raise ValueError('O plano deve ter exatamente 21 dias.')
    for day in plan:
        if not isinstance(day, dict) or set(day) != set(p['meals']):
            raise ValueError('Refeições inválidas.')
        for meal, rid in day.items():
            if rid is None:
                continue
            if not isinstance(rid, str) or rid not in RECIPES:
                raise ValueError('Receita desconhecida.')
            r = RECIPES[rid]
            if meal not in r['meals'] or set(p['allergies']) & set(r['allergens']) or p.get('otherRestrictions', '').strip():
                raise ValueError('Receita incompatível com as preferências.')
            if p['diet'] == 'vegan' and r['diet'] != 'vegan' or (p['diet'] == 'vegetariano' and r['diet'] == 'todos'):
                raise ValueError('Receita incompatível com a preferência alimentar.')
    checks = data.get('checks', {})
    if not isinstance(checks, dict) or any((not re.fullmatch('(?:[1-9]|1[0-9]|2[01])', str(k)) or not isinstance(v, list) or len(v) != 3 or any((type(x) is not bool for x in v)) for k, v in checks.items())):
        raise ValueError('Progresso inválido.')
    for key in ['mealChecks', 'shoppingChecks']:
        v = data.get(key, {})
        if not isinstance(v, dict) or len(v) > 1000 or any((not isinstance(k, str) or len(k) > 500 or type(x) is not bool for k, x in v.items())):
            raise ValueError('Marcações inválidas.')
    if type(data.get('day')) is not int or not 1 <= data['day'] <= 21 or data.get('track') not in {'geral', 'casa', 'gluteos'}:
        raise ValueError('Dia ou percurso inválido.')
    return dict(profileV4=p, foodPlan=plan, checks=checks, mealChecks=data.get('mealChecks', {}), shoppingChecks=data.get('shoppingChecks', {}), day=data['day'], track=data['track'], name=p['name'])

@app.route('/api/state', methods=['GET', 'PUT'])
@authenticated
def account_state():
    uid = session['user_id']
    if request.method == 'GET':
        with get_db() as conn:
            row = conn.execute('SELECT data FROM account_state WHERE user_id=?', (uid,)).fetchone()
        return jsonify(state=json.loads(row['data']) if row else None)
    try:
        data = validate_state(request.get_json(silent=True))
    except (ValueError, TypeError, KeyError) as error:
        return (jsonify(error=str(error)), 400)
    with get_db() as conn:
        conn.execute('INSERT OR REPLACE INTO account_state(user_id,data,updated_at) VALUES(?,?,?)', (uid, json.dumps(data), datetime.now(timezone.utc).isoformat()))
        conn.execute('UPDATE users SET name=?,track=? WHERE id=?', (data['name'], data['track'], uid))
    return jsonify(ok=True)

@app.route('/api/profile', methods=['GET', 'POST'])
@authenticated
def profile():
    if request.method == 'POST':
        return (jsonify(error='Guarda o perfil e o plano conjuntamente em /api/state.'), 400)
    with get_db() as conn:
        row = conn.execute('SELECT data FROM account_state WHERE user_id=?', (session['user_id'],)).fetchone()
    return jsonify(profile=json.loads(row['data']).get('profileV4') if row else None)

@app.route('/api/progress', methods=['GET', 'POST'])
@authenticated
def progress():
    data = request.get_json(silent=True) if request.method == 'POST' else request.args
    if not isinstance(data, (dict, type(request.args))):
        return (jsonify(error='Dados inválidos.'), 400)
    supplied = data.get('user_id')
    if supplied is not None and str(supplied) != str(session['user_id']):
        return (jsonify(error='Acesso negado.'), 403)
    with get_db() as conn:
        if request.method == 'POST':
            day, checks = (data.get('day'), data.get('checks'))
            if type(day) is not int or not 1 <= day <= 21 or (not isinstance(checks, list)) or (len(checks) != 3) or any((type(x) is not bool for x in checks)):
                return (jsonify(error='Progresso inválido.'), 400)
            conn.execute('INSERT OR REPLACE INTO progress(user_id,day,checks) VALUES(?,?,?)', (session['user_id'], day, json.dumps(checks)))
            return jsonify(ok=True)
        rows = conn.execute('SELECT day,checks FROM progress WHERE user_id=?', (session['user_id'],)).fetchall()
    return jsonify(checks={str(r['day']): json.loads(r['checks']) for r in rows})

def is_admin():
    user = current_user()
    return user and bool(os.environ.get('FOCO_ADMIN_EMAIL')) and (user['email'] == os.environ['FOCO_ADMIN_EMAIL'].strip().lower())

@app.route('/api/admin/users')
@authenticated
def admin_users():
    if not is_admin():
        return (jsonify(error='Acesso reservado à administração.'), 403)
    with get_db() as conn:
        rows = conn.execute('SELECT id,email,name,track,created_at FROM users ORDER BY id DESC').fetchall()
    return jsonify(users=[dict(r) for r in rows])

@app.route('/api/admin/stats')
@authenticated
def admin_stats():
    if not is_admin():
        return (jsonify(error='Acesso reservado à administração.'), 403)
    with get_db() as conn:
        total = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
        progress = conn.execute('SELECT COUNT(*) FROM account_state').fetchone()[0]
    return jsonify(total_users=total, users_with_progress=progress)

@app.route('/')
def index():
    return send_from_directory(ROOT, 'index.html')

@app.route('/<path:path>')
def static_files(path):
    if path in {'index.html', 'estilos.css', 'app.js', 'conteudos.js', 'v4.js', 'alimentacao.js', 'receitas.js', 'manifest.webmanifest'} or path.startswith('assets/'):
        return send_from_directory(ROOT, path)
    return ('Não encontrado', 404)
