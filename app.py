import os, sqlite3, secrets, subprocess, shutil, threading, time, base64, json, uuid
from datetime import datetime, timezone
from functools import wraps
from flask import Flask, render_template, request, redirect, session, url_for, send_file, Response, flash, jsonify
from werkzeug.security import check_password_hash
import qrcode
from io import BytesIO

APP_PORT=int(os.getenv('PORT','5000')); ADMIN_USERNAME=os.getenv('ADMIN_USERNAME','admin'); ADMIN_PASSWORD=os.getenv('ADMIN_PASSWORD','admin123')
SECRET_KEY=os.getenv('SECRET_KEY') or secrets.token_hex(32); DATA_DIR=os.getenv('DATA_DIR','/data'); os.makedirs(DATA_DIR,exist_ok=True)
DB_PATH=os.path.join(DATA_DIR,'v2panel.db'); XRAY_BIN=os.getenv('XRAY_BIN','/usr/local/bin/xray'); XRAY_CONF=os.getenv('XRAY_CONF','/data/xray.json')
app=Flask(__name__,template_folder=os.path.dirname(os.path.abspath(__file__))); app.secret_key=SECRET_KEY

def db():
 c=sqlite3.connect(DB_PATH); c.row_factory=sqlite3.Row; return c

def init_db():
 c=db(); c.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY,value TEXT)')
 c.execute('''CREATE TABLE IF NOT EXISTS clients (id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,uuid TEXT NOT NULL UNIQUE,created_at TEXT NOT NULL,enabled INTEGER NOT NULL DEFAULT 1,quota_gb INTEGER NOT NULL DEFAULT 0,expires_at TEXT,token TEXT NOT NULL UNIQUE)''')
 d={'server_name':os.getenv('SERVER_NAME','V2Ray Panel'),'host':os.getenv('PUBLIC_HOST',''),'port':os.getenv('XRAY_PORT','443'),'path':os.getenv('VLESS_PATH','/vless'),'security':os.getenv('VLESS_SECURITY','none')}
 for k,v in d.items(): c.execute('INSERT OR IGNORE INTO settings VALUES(?,?)',(k,v))
 c.commit(); c.close()
def setting(k):
 c=db(); r=c.execute('SELECT value FROM settings WHERE key=?',(k,)).fetchone(); c.close(); return r['value'] if r else ''
def set_setting(k,v):
 c=db(); c.execute('INSERT INTO settings VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(k,str(v))); c.commit(); c.close()
def login_required(fn):
 @wraps(fn)
 def w(*a,**kw):
  if not session.get('logged_in'): return redirect(url_for('login'))
  return fn(*a,**kw)
 return w
def expired(v):
 if not v:return False
 try:return datetime.fromisoformat(v.replace('Z','+00:00'))<=datetime.now(timezone.utc)
 except:return True

def xray_available(): return os.path.exists(XRAY_BIN) and os.access(XRAY_BIN,os.X_OK)
def vless_uri(c):
 host=setting('host') or request.host.split(':')[0]; port=setting('port'); path=setting('path') or '/vless'; name=c['name']
 return f"vless://{c['uuid']}@{host}:{port}?type=ws&encryption=none&security={setting('security')}&path={path}#{name}"
def xray_config():
 port=int(setting('port') or 443); path=setting('path') or '/vless'
 c=db(); rows=c.execute('SELECT * FROM clients WHERE enabled=1').fetchall(); c.close()
 clients=[{'id':r['uuid'],'email':f"client-{r['id']}"} for r in rows if not expired(r['expires_at'])]
 return {'log':{'loglevel':'warning'},'inbounds':[{'listen':'0.0.0.0','port':port,'protocol':'vless','settings':{'clients':clients,'decryption':'none'},'streamSettings':{'network':'ws','security':'none','wsSettings':{'path':path}}}], 'outbounds':[{'protocol':'freedom','tag':'direct'},{'protocol':'blackhole','tag':'block'}]}
def apply_xray():
 try:
  with open(XRAY_CONF,'w') as f: json.dump(xray_config(),f,indent=2)
  if not xray_available(): return False,'Xray نصب نشده است. نصب خودکار در Dockerfile انجام می‌شود.'
  r=subprocess.run([XRAY_BIN,'run','-test','-config',XRAY_CONF],capture_output=True,text=True,timeout=20)
  if r.returncode:return False,(r.stderr or r.stdout).strip()
  subprocess.run(['pkill','-f',f'{XRAY_BIN} run -config {XRAY_CONF}'],capture_output=True)
  subprocess.Popen([XRAY_BIN,'run','-config',XRAY_CONF],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
  return True,'Xray با پیکربندی جدید اجرا شد.'
 except Exception as e:return False,str(e)
def worker():
 while True:
  try:
   c=db(); c.execute('UPDATE clients SET enabled=0 WHERE expires_at IS NOT NULL AND enabled=1 AND expires_at<=?',(datetime.now(timezone.utc).isoformat(),)); c.commit(); c.close(); apply_xray()
  except: pass
  time.sleep(60)

init_db(); threading.Thread(target=worker,daemon=True).start()
@app.route('/login',methods=['GET','POST'])
def login():
 if request.method=='POST':
  u=request.form.get('username',''); p=request.form.get('password',''); ok=False
  if u==ADMIN_USERNAME:
   try: ok=check_password_hash(ADMIN_PASSWORD,p) if ADMIN_PASSWORD.startswith(('pbkdf2:','scrypt:')) else secrets.compare_digest(ADMIN_PASSWORD,p)
   except: ok=False
  if ok: session['logged_in']=True; return redirect(url_for('dashboard'))
  flash('نام کاربری یا رمز عبور اشتباه است')
 return render_template('login.html')
@app.route('/logout')
def logout(): session.clear(); return redirect(url_for('login'))
@app.route('/')
@login_required
def dashboard():
 c=db(); clients=c.execute('SELECT * FROM clients ORDER BY id DESC').fetchall(); c.close()
 return render_template('dashboard.html',clients=clients,settings={k:setting(k) for k in ['server_name','host','port','path','security']},xray=xray_available())
@app.route('/settings',methods=['POST'])
@login_required
def settings_save():
 for k in ['server_name','host','port','path','security']:
  v=request.form.get(k,'').strip()
  if v:set_setting(k,v)
 ok,msg=apply_xray(); flash(msg); return redirect(url_for('dashboard'))
@app.route('/server/install',methods=['POST'])
@login_required
def server_install():
 ok,msg=apply_xray(); flash(msg); return redirect(url_for('dashboard'))
@app.route('/clients/add',methods=['POST'])
@login_required
def add_client():
 try:
  name=request.form.get('name','').strip() or 'client-'+secrets.token_hex(3); quota=int(request.form.get('quota_gb') or 0); exp=request.form.get('expires_at','').strip() or None
  if exp:
   dt=datetime.fromisoformat(exp); exp=dt.replace(tzinfo=timezone.utc).isoformat() if dt.tzinfo is None else dt.astimezone(timezone.utc).isoformat()
  c=db(); c.execute('INSERT INTO clients(name,uuid,created_at,quota_gb,expires_at,token) VALUES(?,?,?,?,?,?)',(name,str(uuid.uuid4()),datetime.now(timezone.utc).isoformat(),quota,exp,secrets.token_urlsafe(18))); c.commit(); c.close(); ok,msg=apply_xray(); flash('کاربر VLESS ساخته شد. '+msg)
 except Exception as e:flash('خطا: '+str(e))
 return redirect(url_for('dashboard'))
def get_client(i):
 c=db(); r=c.execute('SELECT * FROM clients WHERE id=?',(i,)).fetchone(); c.close(); return r
@app.route('/clients/<int:i>/toggle',methods=['POST'])
@login_required
def toggle(i):
 c=db(); c.execute('UPDATE clients SET enabled=1-enabled WHERE id=?',(i,)); c.commit(); c.close(); apply_xray(); return redirect(url_for('dashboard'))
@app.route('/clients/<int:i>/delete',methods=['POST'])
@login_required
def delete(i):
 c=db(); c.execute('DELETE FROM clients WHERE id=?',(i,)); c.commit(); c.close(); apply_xray(); flash('کاربر حذف شد'); return redirect(url_for('dashboard'))
@app.route('/clients/<int:i>/renew',methods=['POST'])
@login_required
def renew(i):
 try:
  dt=datetime.fromisoformat(request.form.get('expires_at')); exp=dt.replace(tzinfo=timezone.utc).isoformat() if dt.tzinfo is None else dt.astimezone(timezone.utc).isoformat(); c=db(); c.execute('UPDATE clients SET expires_at=?,enabled=1 WHERE id=?',(exp,i)); c.commit(); c.close(); apply_xray(); flash('تمدید شد')
 except:flash('تاریخ نامعتبر است')
 return redirect(url_for('dashboard'))
@app.route('/clients/<int:i>/link')
@login_required
def link(i):
 c=get_client(i); return Response(vless_uri(c),mimetype='text/plain') if c else ('not found',404)
@app.route('/clients/<int:i>/qr.png')
@login_required
def qr(i):
 c=get_client(i)
 if not c:return 'not found',404
 b=BytesIO(); qrcode.make(vless_uri(c)).save(b,'PNG'); b.seek(0); return send_file(b,mimetype='image/png')
@app.route('/sub/<token>')
def sub(token):
 c=db(); rows=c.execute('SELECT * FROM clients WHERE token=? AND enabled=1',(token,)).fetchall(); c.close()
 if not rows:return 'not found',404
 links='\n'.join(vless_uri(r) for r in rows if not expired(r['expires_at']))
 return Response(base64.b64encode(links.encode()).decode(),mimetype='text/plain',headers={'Subscription-Userinfo':'upload=0; download=0; total=0; expire=0'})
@app.route('/api/status')
@login_required
def status():return jsonify({'xray_available':xray_available(),'config':XRAY_CONF,'host':setting('host'),'port':setting('port')})
if __name__=='__main__': app.run(host='0.0.0.0',port=APP_PORT)
