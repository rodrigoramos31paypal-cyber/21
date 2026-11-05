"""Conteúdos, recuperação de conta e checkout exclusivamente de teste."""
import os
import secrets
import smtplib
import time
from email.message import EmailMessage
from urllib.parse import urlsplit
import stripe
from flask import request, jsonify

def install_features(app, get_db, authenticated, current_user, is_admin, rate_limit, digest, recipes):
    def unavailable():
        return jsonify(error='Serviço ainda não configurado.'), 503

    @app.get('/api/health')
    def health():
        with get_db() as conn:
            conn.execute('SELECT COUNT(*) FROM users').fetchone()
        return jsonify(ok=True, checkout='test-only')

    @app.get('/api/content')
    def content():
        with get_db() as conn:
            rows = conn.execute('SELECT key,value FROM content_settings').fetchall()
        return jsonify(videos={r['key']: r['value'] for r in rows if not r['key'].startswith('text:')},
                       texts={r['key'][5:]: r['value'] for r in rows if r['key'].startswith('text:')})

    @app.put('/api/admin/text')
    @authenticated
    def update_text():
        if not is_admin():
            return jsonify(error='Acesso reservado à administração.'), 403
        data = request.get_json(silent=True)
        if not isinstance(data, dict) or set(data) != {'key', 'text'}:
            return jsonify(error='Dados inválidos.'), 400
        key, value = data['key'], data['text']
        allowed = {'recipe:' + rid for rid in recipes} | {'day:' + str(day) for day in range(1, 22)}
        if not isinstance(key, str) or key not in allowed or not isinstance(value, str) or len(value) > 1000:
            return jsonify(error='Texto inválido; máximo de 1000 caracteres.'), 400
        with get_db() as conn:
            if value.strip():
                conn.execute('INSERT INTO content_settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value', ('text:' + key, value.strip()))
            else:
                conn.execute('DELETE FROM content_settings WHERE key=?', ('text:' + key,))
        return jsonify(ok=True)

    @app.put('/api/admin/content')
    @authenticated
    def update_content():
        if not is_admin():
            return jsonify(error='Acesso reservado à administração.'), 403
        data = request.get_json(silent=True)
        if not isinstance(data, dict) or set(data) != {'key', 'url'}:
            return jsonify(error='Dados inválidos.'), 400
        key, url = data['key'], data['url']
        allowed = {'recipe:' + rid for rid in recipes} | {'day:' + str(day) for day in range(1, 22)}
        if not isinstance(key, str) or key not in allowed or not isinstance(url, str) or len(url) > 2048:
            return jsonify(error='Conteúdo inválido.'), 400
        parsed = urlsplit(url)
        if url and (parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password):
            return jsonify(error='Usa uma ligação HTTPS confirmada.'), 400
        with get_db() as conn:
            if url:
                conn.execute('INSERT INTO content_settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value', (key, url))
            else:
                conn.execute('DELETE FROM content_settings WHERE key=?', (key,))
        return jsonify(ok=True)

    @app.post('/api/email/request')
    def email_request():
        if rate_limit():
            return jsonify(error='Demasiadas tentativas. Aguarda um minuto.'), 429
        data = request.get_json(silent=True)
        if not isinstance(data, dict) or data.get('purpose') not in {'reset', 'verify'} or not isinstance(data.get('email'), str):
            return jsonify(error='Pedido inválido.'), 400
        origin = os.environ.get('APP_ORIGIN', '')
        if not all(os.environ.get(k) for k in ['SMTP_HOST', 'SMTP_USER', 'SMTP_PASSWORD', 'SMTP_FROM']) or not origin.startswith('https://'):
            return unavailable()
        with get_db() as conn:
            user = conn.execute('SELECT id,email FROM users WHERE email=?', (data['email'].strip().lower(),)).fetchone()
        if user:
            token = secrets.token_urlsafe(32)
            with get_db() as conn:
                conn.execute('DELETE FROM email_tokens WHERE expires<?', (int(time.time()),))
                conn.execute('INSERT INTO email_tokens(token,user_id,purpose,expires) VALUES(?,?,?,?)',
                             (digest(token), user['id'], data['purpose'], int(time.time()) + 1800))
            message = EmailMessage()
            message['Subject'] = '21 Dias de Foco — confirmar pedido'
            message['From'] = os.environ['SMTP_FROM']
            message['To'] = user['email']
            message.set_content('Abre esta ligação nos próximos 30 minutos:\n' + origin.rstrip('/') + '/#account/' + data['purpose'] + '/' + token)
            try:
                with smtplib.SMTP(os.environ['SMTP_HOST'], int(os.environ.get('SMTP_PORT', '587')), timeout=10) as smtp:
                    smtp.starttls()
                    smtp.login(os.environ['SMTP_USER'], os.environ['SMTP_PASSWORD'])
                    smtp.send_message(message)
            except (OSError, smtplib.SMTPException):
                app.logger.error('Falha na entrega de email de conta.')
                # Mesma resposta pública para evitar revelar contas existentes.
        return jsonify(ok=True, message='Se existir uma conta, receberás uma ligação por email.')

    @app.post('/api/email/confirm')
    def email_confirm():
        from werkzeug.security import generate_password_hash
        if rate_limit():
            return jsonify(error='Demasiadas tentativas.'), 429
        data = request.get_json(silent=True)
        if not isinstance(data, dict) or not isinstance(data.get('token'), str):
            return jsonify(error='Pedido inválido.'), 400
        purpose = data.get('purpose')
        password = data.get('password')
        if purpose not in {'reset', 'verify'} or (purpose == 'reset' and (not isinstance(password, str) or not 10 <= len(password) <= 128)):
            return jsonify(error='Usa uma palavra-passe entre 10 e 128 caracteres.'), 400
        with get_db() as conn:
            row = conn.execute('DELETE FROM email_tokens WHERE token=? AND purpose=? AND expires>? RETURNING user_id',
                               (digest(data['token']), purpose, int(time.time()))).fetchone()
            if not row:
                return jsonify(error='Ligação inválida ou expirada.'), 400
            uid = row['user_id']
            if purpose == 'reset':
                conn.execute('UPDATE users SET password=? WHERE id=?', (generate_password_hash(password), uid))
                conn.execute('DELETE FROM auth_sessions WHERE user_id=?', (uid,))
                conn.execute('DELETE FROM email_tokens WHERE user_id=? AND purpose=?', (uid, 'reset'))
            else:
                conn.execute('INSERT INTO verified_emails(user_id) VALUES(?) ON CONFLICT(user_id) DO NOTHING', (uid,))
        return jsonify(ok=True)

    def test_stripe():
        key = os.environ.get('STRIPE_SECRET_KEY', '')
        # Não existe opção para ativar live nesta entrega.
        return key if key.startswith('sk_test_') else None

    @app.post('/api/checkout')
    @authenticated
    def checkout():
        key = test_stripe()
        origin = os.environ.get('APP_ORIGIN', '')
        if not key or os.environ.get('STRIPE_TEST_CHECKOUT') != '1' or not origin.startswith('https://'):
            return unavailable()
        user = current_user()
        if user['has_access']:
            return jsonify(error='Esta conta já tem acesso.'), 409
        if not user['email_verified']:
            return jsonify(error='Confirma primeiro o teu email.'), 403
        if rate_limit():
            return jsonify(error='Demasiadas tentativas.'), 429
        try:
            checkout = stripe.checkout.Session.create(api_key=key, mode='payment',
                customer_email=user['email'], client_reference_id=str(user['id']),
                metadata={'foco_user_id': str(user['id'])},
                line_items=[{'price_data': {'currency': 'eur', 'unit_amount': 2490,
                    'product_data': {'name': '21 Dias de Foco — pagamento único (TESTE)'}}, 'quantity': 1}],
                success_url=origin.rstrip('/') + '/?checkout=success#inicio',
                cancel_url=origin.rstrip('/') + '/?checkout=cancel#inicio')
        except stripe.StripeError:
            return jsonify(error='Não foi possível abrir o checkout de teste.'), 502
        with get_db() as conn:
            conn.execute('INSERT INTO checkout_sessions(id,user_id,status) VALUES(?,?,?)', (checkout.id, user['id'], 'pending'))
        return jsonify(url=checkout.url, mode='test')

    @app.post('/api/stripe/webhook')
    def webhook():
        secret = os.environ.get('STRIPE_WEBHOOK_SECRET', '')
        if not test_stripe() or not secret:
            return unavailable()
        try:
            event = stripe.Webhook.construct_event(request.get_data(), request.headers.get('Stripe-Signature', ''), secret)
        except (ValueError, stripe.SignatureVerificationError):
            return jsonify(error='Assinatura inválida.'), 400
        if event.get('livemode') is not False:
            return jsonify(error='Eventos live não são aceites.'), 400
        if event['type'] not in {'checkout.session.completed', 'checkout.session.async_payment_succeeded'}:
            return jsonify(ok=True)
        obj = event['data']['object']
        if obj.get('payment_status') != 'paid':
            return jsonify(ok=True)
        with get_db() as conn:
            row = conn.execute('SELECT user_id FROM checkout_sessions WHERE id=?', (obj['id'],)).fetchone()
            if not row:
                return jsonify(error='Checkout desconhecido; repetir após registo.'), 409
            uid = row['user_id']
            if obj.get('amount_total') != 2490 or obj.get('currency') != 'eur' or obj.get('mode') != 'payment' or obj.get('client_reference_id') != str(uid) or obj.get('metadata', {}).get('foco_user_id') != str(uid):
                return jsonify(error='Pagamento incompatível.'), 400
            seen = conn.execute('INSERT INTO stripe_events(id) VALUES(?) ON CONFLICT(id) DO NOTHING RETURNING id', (event['id'],)).fetchone()
            if seen:
                conn.execute('UPDATE checkout_sessions SET status=? WHERE id=?', ('paid', obj['id']))
                conn.execute('INSERT INTO access_grants(user_id,source) VALUES(?,?) ON CONFLICT(user_id) DO NOTHING', (uid, 'stripe-test'))
        return jsonify(ok=True)
