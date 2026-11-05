import json
import time
import hashlib
import hmac
import pytest
from test_accounts import api, register
from test_accounts import state

def grant(s, uid, admin=False):
    with s.get_db() as conn:
        table = 'administrators' if admin else 'access_grants'
        sql = f'INSERT INTO {table}(user_id) VALUES(?)' if admin else f'INSERT INTO {table}(user_id,source) VALUES(?,?)'
        conn.execute(sql, (uid,) if admin else (uid, 'test'))

def test_pdf_permission_and_no_static_bypass(api):
    s, c = api
    assert c.get('/assets/guia.pdf').status_code == 401
    uid = register(c)['id']
    assert c.get('/assets/guia.pdf').status_code == 403
    for path in ['/private_materials/guia.pdf', '/database.py', '/.env', '/assets/../private_materials/guia.pdf', '/assets/GUIA.PDF']:
        assert c.get(path).status_code == 404
    grant(s, uid)
    result = c.get('/assets/guia.pdf')
    assert result.status_code == 200 and result.data.startswith(b'%PDF')
    assert result.headers['Cache-Control'] == 'private, no-store'

def test_stale_tab_cannot_write_previous_account_data(api):
    s, c = api
    uid = register(c)['id']
    data = state()
    data['accountId'] = uid + 1
    assert c.put('/api/state', json=data).status_code == 409
    assert c.get('/api/state').json['state'] is None
    data['accountId'] = uid
    assert c.put('/api/state', json=data).status_code == 200

def test_production_refuses_ephemeral_database(monkeypatch, tmp_path):
    from database import create_database
    monkeypatch.delenv('DATABASE_URL', raising=False)
    monkeypatch.setenv('VERCEL', '1')
    with pytest.raises(RuntimeError, match='persistente'):
        create_database(tmp_path)
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///:memory:')
    with pytest.raises(RuntimeError, match='PostgreSQL'):
        create_database(tmp_path)

def test_cookie_security_and_invalid_origin(api):
    s,c=api
    result=c.post('/api/register',json={'email':'one@example.test','password':'testing-only-123'})
    assert 'HttpOnly' in result.headers['Set-Cookie']
    assert 'SameSite=Lax' in result.headers['Set-Cookie']
    assert c.post('/api/logout',json={},headers={'Origin':'https://localhost'}).status_code==403
    assert c.post('/api/logout',data='{}',content_type='text/plain').status_code==415

def test_private_storage_only_signs_after_authorization(api, monkeypatch):
    from types import SimpleNamespace
    import materials
    s,c=api
    monkeypatch.setenv('FOCO_MATERIALS_BUCKET','private-test-bucket')
    captured=[]
    def sign(operation, **kwargs):
        captured.append((operation, kwargs))
        return 'https://private-test-bucket.s3.amazonaws.com/foco/guia.pdf?test-signature'
    monkeypatch.setattr(materials.boto3,'client',lambda *args,**kwargs: SimpleNamespace(generate_presigned_url=sign))
    assert c.get('/assets/guia.pdf').status_code==401
    uid=register(c)['id']
    assert c.get('/assets/guia.pdf').status_code==403
    assert captured==[]
    grant(s,uid)
    result=c.get('/assets/guia.pdf')
    assert result.status_code==302
    assert captured[0][1]['ExpiresIn']==60
    assert captured[0][1]['Params']['Key']=='foco/guia.pdf'
    assert result.headers['Cache-Control']=='private, no-store'
    monkeypatch.delenv('FOCO_MATERIALS_BUCKET')
    monkeypatch.setattr(s,'production',True)
    assert c.get('/assets/guia.pdf').status_code==503

def test_vercel_all_routes_pass_through_authorization():
    from pathlib import Path
    config=json.loads((Path(__file__).parents[1]/'vercel.json').read_text())
    assert config['routes']==[{'src':'/(.*)','dest':'/api/index.py'}]
    assert not any('private_materials' in item for item in config['builds'][0]['config']['includeFiles'])

def test_logout_revokes_copied_cookie(api):
    s, c = api
    register(c)
    value = c.get_cookie('session').value
    thief = s.app.test_client()
    thief.set_cookie('session', value)
    assert thief.get('/api/state').status_code == 200
    c.post('/api/logout', json={})
    assert thief.get('/api/state').status_code == 401

def test_expired_session_and_shared_rate_limit(api):
    s, c = api
    register(c)
    with s.get_db() as conn:
        conn.execute('UPDATE auth_sessions SET expires=0')
    assert c.get('/api/state').status_code == 401
    # Novos clientes/funções partilham a mesma base de dados de limites.
    for _ in range(19):
        assert s.app.test_client().post('/api/login', json={'email':'one@example.test','password':'wrong'}).status_code == 401
    assert s.app.test_client().post('/api/login', json={'email':'one@example.test','password':'wrong'}).status_code == 429

def test_admin_requires_explicit_provisioning_and_content_validation(api, monkeypatch):
    s, c = api
    monkeypatch.setenv('FOCO_ADMIN_EMAIL', 'one@example.test')
    uid = register(c)['id']
    assert c.get('/api/admin/users').status_code == 403
    assert c.put('/api/admin/content', json={'key':'day:1','url':'https://example.test/video'}).status_code == 403
    grant(s, uid, admin=True)
    assert c.get('/api/admin/users').status_code == 200
    assert c.get('/api/admin/stats').json == {'total_users':1, 'users_with_progress':0}
    for data in [{'key':'day:22','url':''}, {'key':'day:1','url':'javascript:alert(1)'}, {'key':'recipe:inventada','url':'https://example.test'}]:
        assert c.put('/api/admin/content', json=data).status_code == 400
    assert c.put('/api/admin/content', json={'key':'recipe:marmita-base','url':'https://example.test/video'}).status_code == 200
    assert c.get('/api/content').json['videos']['recipe:marmita-base'] == 'https://example.test/video'
    assert c.put('/api/admin/content', json={'key':'recipe:marmita-base','url':''}).status_code == 200
    assert c.get('/api/content').json == {'videos':{},'texts':{}}
    assert c.put('/api/admin/text',json={'key':'day:1','text':'Nota revista'}).status_code==200
    assert c.get('/api/content').json['texts']['day:1']=='Nota revista'
    assert c.put('/api/admin/text',json={'key':'day:1','text':'x'*1001}).status_code==400

def test_email_tokens_single_use_expiry_and_session_revocation(api):
    s, c = api
    uid = register(c)['id']
    assert c.post('/api/email/request', json={'purpose':'reset','email':'one@example.test'}).status_code == 503
    def token(value, purpose, expires):
        with s.get_db() as conn:
            conn.execute('INSERT INTO email_tokens(token,user_id,purpose,expires) VALUES(?,?,?,?)', (s.digest(value),uid,purpose,expires))
    token('expired', 'reset', 0)
    assert c.post('/api/email/confirm', json={'token':'expired','purpose':'reset','password':'replacement-123'}).status_code == 400
    token('valid', 'reset', int(time.time())+600)
    data = {'token':'valid','purpose':'reset','password':'replacement-123'}
    assert c.post('/api/email/confirm',json=data).status_code == 200
    assert c.get('/api/state').status_code == 401
    assert c.post('/api/email/confirm',json=data).status_code == 400
    assert c.post('/api/login',json={'email':'one@example.test','password':'replacement-123'}).status_code == 200
    token('verify', 'verify', int(time.time())+600)
    assert c.post('/api/email/confirm',json={'token':'verify','purpose':'verify'}).status_code == 200
    assert c.get('/api/session').json['user']['email_verified'] is True

def stripe_event(c, event, secret='whsec_testing', invalid=False):
    body=json.dumps(event).encode()
    timestamp=str(int(time.time()))
    signature=hmac.new(secret.encode(), timestamp.encode()+b'.'+body, hashlib.sha256).hexdigest()
    return c.post('/api/stripe/webhook',data=body,content_type='application/json',headers={'Stripe-Signature':f't={timestamp},v1={"invalid" if invalid else signature}'})

def test_checkout_only_test_keys_and_server_fixed_price(api, monkeypatch):
    import stripe
    s,c=api
    uid=register(c)['id']
    monkeypatch.setenv('STRIPE_TEST_CHECKOUT','1')
    monkeypatch.setenv('STRIPE_SECRET_KEY','sk_live_never_use')
    monkeypatch.setenv('APP_ORIGIN','https://preview.example.test')
    assert c.post('/api/checkout',json={}).status_code == 503
    monkeypatch.setenv('STRIPE_SECRET_KEY','sk_test_example')
    assert c.post('/api/checkout',json={}).status_code == 403
    with s.get_db() as conn:
        conn.execute('INSERT INTO verified_emails(user_id) VALUES(?)',(uid,))
    captured={}
    def create(**kwargs):
        captured.update(kwargs)
        return stripe.StripeObject.construct_from({'id':'cs_test_1','url':'https://checkout.stripe.com/test'},None)
    monkeypatch.setattr(stripe.checkout.Session,'create',create)
    assert c.post('/api/checkout',json={'amount':1,'user_id':999}).status_code == 200
    assert captured['line_items'][0]['price_data']['unit_amount']==2490
    assert captured['mode']=='payment' and captured['client_reference_id']==str(uid)
    assert c.get('/api/session').json['user']['has_access'] is False

def test_stripe_signature_amount_owner_live_and_idempotence(api, monkeypatch):
    s,c=api
    uid=register(c)['id']
    monkeypatch.setenv('STRIPE_SECRET_KEY','sk_test_example')
    monkeypatch.setenv('STRIPE_WEBHOOK_SECRET','whsec_testing')
    with s.get_db() as conn:
        conn.execute('INSERT INTO checkout_sessions(id,user_id,status) VALUES(?,?,?)',('cs_test_1',uid,'pending'))
    obj={'id':'cs_test_1','amount_total':2490,'currency':'eur','mode':'payment','payment_status':'paid','client_reference_id':str(uid),'metadata':{'foco_user_id':str(uid)}}
    event={'id':'evt_1','object':'event','livemode':False,'type':'checkout.session.completed','data':{'object':obj}}
    assert stripe_event(c,event,invalid=True).status_code==400
    event['livemode']=True
    assert stripe_event(c,event).status_code==400
    event['livemode']=False
    for key,wrong in [('amount_total',1),('currency','usd'),('client_reference_id','999')]:
        original=obj[key];obj[key]=wrong
        assert stripe_event(c,event).status_code==400
        obj[key]=original
    assert c.get('/api/session').json['user']['has_access'] is False
    assert stripe_event(c,event).status_code==200
    assert stripe_event(c,event).status_code==200
    assert c.get('/api/session').json['user']['has_access'] is True
    with s.get_db() as conn:
        assert conn.execute('SELECT COUNT(*) AS n FROM stripe_events').fetchone()['n']==1
