import importlib
import json
from pathlib import Path
import pytest
import os
import uuid
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

@pytest.fixture
def api(tmp_path,monkeypatch):
 monkeypatch.setenv('FOCO_DB',str(tmp_path/'test.db'))
 admin = None
 if os.environ.get('TEST_DATABASE_URL'):
  url = make_url(os.environ['TEST_DATABASE_URL'])
  schema = 'test_' + uuid.uuid4().hex
  admin = create_engine(url)
  with admin.begin() as conn:
   conn.execute(text('CREATE SCHEMA ' + schema))
  monkeypatch.setenv('DATABASE_URL', str(url.update_query_dict({'options': '-csearch_path=' + schema}).render_as_string(hide_password=False)))
 else:
  monkeypatch.delenv('DATABASE_URL', raising=False)
 import server_v4
 s=importlib.reload(server_v4);s.app.config.update(TESTING=True,SECRET_KEY='test-only')
 monkeypatch.setattr(s, 'ROOT', tmp_path)
 (tmp_path/'private_materials').mkdir()
 (tmp_path/'private_materials'/'guia.pdf').write_bytes(b'%PDF-1.4\n%%EOF')
 yield s,s.app.test_client()
 s.engine.dispose()
 if admin:
  with admin.begin() as conn:
   conn.execute(text('DROP SCHEMA ' + schema + ' CASCADE'))
  admin.dispose()

def register(client,email='one@example.test'):
 response=client.post('/api/register',json={'email':email,'password':'testing-only-123','name':'Teste'})
 assert response.status_code==201
 return response.json['user']

def state():
 return {'profile':dict(name='Teste',age=None,height=None,weight=None,goal='manter',place='casa',experience='iniciante',availability=3,diet='todos',allergies=[],otherRestrictions='',meals=['almoco']),
 'plan':[{'almoco':'marmita-base'} for _ in range(21)],'checks':{'1':[True,False,False]},'mealChecks':{'1:almoco:marmita-base':True},'shoppingChecks':{},'day':1,'track':'casa'}

def test_session_required_and_private_files_blocked(api):
 s,c=api
 for path in ['/api/state','/api/profile','/api/progress','/api/admin/users']:
  assert c.get(path).status_code==401
 for path in ['/instance/foco.db','/.git/config','/server_v4.py','/server.py']:
  assert c.get(path).status_code==404

def test_accounts_are_isolated_and_persist(api):
 s,a=api;user=register(a);data=state()
 assert a.put('/api/state',json=data).status_code==200
 b=s.app.test_client();register(b,'two@example.test')
 assert b.get('/api/state').json['state'] is None
 assert b.get('/api/progress?user_id='+str(user['id'])).status_code==403
 assert b.get('/api/admin/users').status_code==403
 assert a.post('/api/logout',json={}).status_code==200
 assert a.get('/api/state').status_code==401
 assert a.post('/api/login',json={'email':'one@example.test','password':'testing-only-123'}).status_code==200
 saved=a.get('/api/state').json['state']
 assert saved['profileV4']['weight'] is None
 assert saved['foodPlan']==data['plan']
 assert saved['mealChecks']==data['mealChecks']

def test_allergy_and_diet_tampering_rejected(api):
 s,c=api;register(c);data=state();data['profile']['allergies']=['soja'];data['plan'][0]['almoco']='marmita-vegetal'
 assert c.put('/api/state',json=data).status_code==400
 data=state();data['profile']['diet']='vegan'
 assert c.put('/api/state',json=data).status_code==400
 data=state();data['profile']['otherRestrictions']='Frango'
 assert c.put('/api/state',json=data).status_code==400

def test_invalid_data_and_cross_origin_rejected(api):
 s,c=api;register(c)
 assert c.put('/api/state',json=state(),headers={'Origin':'https://other.test'}).status_code==403
 for key,value in [('day',22),('plan',[]),('checks',{'1':[True]})]:
  data=state();data[key]=value;assert c.put('/api/state',json=data).status_code==400
 data=state();data['profile']['weight']=float('nan');assert c.put('/api/state',json=data).status_code==400
 assert c.put('/api/state',json=state()).status_code==200

def test_login_does_not_fake_payment_or_identity(api):
 s,c=api;register(c);c.post('/api/logout',json={})
 assert c.post('/api/login',json={'email':'one@example.test','password':'wrong-password'}).status_code==401
 assert c.get('/api/session').json['user'] is None
 assert c.post('/api/login',json={'email':'one@example.test','password':'testing-only-123'}).status_code==200
 cookie=c.get('/api/session').headers
 assert cookie['Cache-Control']=='no-store'

def test_legacy_progress_post_works_only_for_current_user(api):
 s,c=api;user=register(c)
 assert c.post('/api/progress',json={'day':1,'checks':[True,True,False]}).status_code==200
 assert c.get('/api/progress').json['checks']=={'1':[True,True,False]}
 assert c.post('/api/progress',json={'user_id':user['id']+1,'day':1,'checks':[True]*3}).status_code==403
