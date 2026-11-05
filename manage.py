"""Operações explícitas: migrar, atribuir administrador ou acesso manual."""
import argparse
from pathlib import Path
from database import create_database, migrate, Connection

parser = argparse.ArgumentParser()
parser.add_argument('action', choices=['migrate', 'admin', 'grant', 'revoke'])
parser.add_argument('--email')
args = parser.parse_args()
engine = create_database(Path(__file__).resolve().parent)
if args.action == 'migrate':
    migrate(engine)
    print('Esquema atualizado; tabelas e contas existentes conservadas.')
else:
    if not args.email:
        parser.error('--email é obrigatório')
    with Connection(engine) as conn:
        user = conn.execute('SELECT id FROM users WHERE email=?', (args.email.strip().lower(),)).fetchone()
        if not user:
            parser.error('Conta inexistente; criar primeiro na aplicação.')
        uid = user['id']
        if args.action == 'admin':
            conn.execute('INSERT INTO administrators(user_id) VALUES(?) ON CONFLICT(user_id) DO NOTHING', (uid,))
        elif args.action == 'grant':
            conn.execute('INSERT INTO access_grants(user_id,source) VALUES(?,?) ON CONFLICT(user_id) DO NOTHING', (uid, 'manual'))
        else:
            conn.execute('DELETE FROM access_grants WHERE user_id=?', (uid,))
            conn.execute('DELETE FROM administrators WHERE user_id=?', (uid,))
        conn.execute('DELETE FROM auth_sessions WHERE user_id=?', (uid,))
    print('Permissão atualizada. A conta terá de voltar a iniciar sessão.')
