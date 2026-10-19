"""Local accounts and server-side sessions; no plaintext passwords on disk."""
import hashlib
import hmac
import json
import re
import secrets
import sqlite3
import time
from pathlib import Path
from uuid import uuid4
import streamlit as st

class AccountError(Exception):
    pass

class Accounts:
    def __init__(self, db, clock=time.time):
        # SQLite can only create/open a database when its parent directory
        # already exists.  This matters for a fresh checkout or a deployment
        # that mounts the data directory after the app starts.
        self.db, self.clock = str(db), clock
        if self.db != ':memory:':
            db_path = Path(self.db).expanduser()
            db_path.parent.mkdir(parents=True, exist_ok=True)
            self.db = str(db_path)
        with self.connect() as con:
            con.executescript('''
            CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY, username TEXT NOT NULL UNIQUE,
                salt BLOB NOT NULL, password_hash BLOB NOT NULL, created REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS login_attempts(name TEXT PRIMARY KEY, failures INTEGER NOT NULL, locked_until REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS user_sessions(token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL, expires REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS private_papers(user_id TEXT NOT NULL, paper_id TEXT NOT NULL, raw TEXT NOT NULL,
                PRIMARY KEY(user_id,paper_id));
            ''')
    def connect(self):
        con=sqlite3.connect(self.db,timeout=20);con.row_factory=sqlite3.Row
        return con
    @staticmethod
    def normalized(username):
        name=username.strip().lower()
        if not re.fullmatch(r'[a-z0-9_]{3,32}',name):
            raise AccountError('用户名使用 3–32 位英文字母、数字或下划线。')
        return name
    @staticmethod
    def derive(password,salt):
        return hashlib.pbkdf2_hmac('sha256',password.encode(),salt,600000,dklen=32)
    def register(self,username,password,confirm):
        name=self.normalized(username)
        if not 12<=len(password)<=256:
            raise AccountError('密码长度需要 12–256 个字符。')
        if password!=confirm: raise AccountError('两次输入的密码不一致。')
        salt=secrets.token_bytes(16);digest=self.derive(password,salt)
        uid=uuid4().hex
        with self.connect() as con:
            con.execute('BEGIN IMMEDIATE')
            # Rate limit public account creation without collecting IP addresses.
            recent=con.execute('SELECT COUNT(*) FROM users WHERE created>?',(self.clock()-3600,)).fetchone()[0]
            if recent>=20:raise AccountError('当前注册次数较多，请稍后重试。')
            try:con.execute('INSERT INTO users VALUES (?,?,?,?,?)',(uid,name,salt,digest,self.clock()))
            except sqlite3.IntegrityError:raise AccountError('该用户名已存在，请换一个或登录。') from None
        return uid
    def login(self,username,password):
        name=self.normalized(username)
        if len(password)>256:raise AccountError('用户名或密码不正确。')
        with self.connect() as con:
            con.execute('BEGIN IMMEDIATE')
            attempt=con.execute('SELECT * FROM login_attempts WHERE name=?',(name,)).fetchone()
            if attempt and attempt['locked_until']>self.clock():
                raise AccountError('登录尝试过多，请 15 分钟后再试。')
            row=con.execute('SELECT * FROM users WHERE username=?',(name,)).fetchone()
            valid=hmac.compare_digest(self.derive(password,row['salt'] if row else bytes(16)),row['password_hash'] if row else bytes(32))
            if not row or not valid:
                failures=(attempt['failures'] if attempt and attempt['locked_until']==0 else 0)+1
                con.execute('INSERT OR REPLACE INTO login_attempts VALUES (?,?,?)',
                            (name,failures,self.clock()+900 if failures>=5 else 0))
                error=True
            else:
                con.execute('DELETE FROM login_attempts WHERE name=?',(name,))
                token=secrets.token_urlsafe(32)
                con.execute('INSERT INTO user_sessions VALUES (?,?,?)',
                            (hashlib.sha256(token.encode()).hexdigest(),row['id'],self.clock()+8*3600))
                error=False
        if error:raise AccountError('用户名或密码不正确。')
        return token
    def user(self,token):
        if not token or not isinstance(token,str):return None
        with self.connect() as con:
            row=con.execute('SELECT u.id,u.username FROM user_sessions s JOIN users u ON u.id=s.user_id WHERE s.token_hash=? AND s.expires>?',
                            (hashlib.sha256(token.encode()).hexdigest(),self.clock())).fetchone()
        return dict(row) if row else None
    def logout(self,token):
        with self.connect() as con:
            con.execute('DELETE FROM user_sessions WHERE token_hash=?',(hashlib.sha256(token.encode()).hexdigest(),))
    def save_paper(self,uid,paper):
        with self.connect() as con:
            if not con.execute('SELECT 1 FROM users WHERE id=?',(uid,)).fetchone():raise PermissionError('请先登录。')
            con.execute('INSERT OR REPLACE INTO private_papers VALUES (?,?,?)',(uid,paper['id'],json.dumps(paper,ensure_ascii=False)))
    def papers(self,uid):
        with self.connect() as con:
            return [json.loads(r[0]) for r in con.execute('SELECT raw FROM private_papers WHERE user_id=?',(uid,))]

def require_user(db):
    accounts=Accounts(db)
    token=st.session_state.get('auth_token')
    user=accounts.user(token)
    if user:
        # Clear private widgets/results if the authenticated principal changes.
        if st.session_state.get('principal')!=user['id']:
            st.session_state.clear();st.session_state.auth_token=token;st.session_state.principal=user['id']
        with st.sidebar:
            st.caption('已登录：'+user['username'])
            if st.button('退出登录',key='logout'):
                accounts.logout(token);st.session_state.clear();st.rerun()
        return user
    if token:
        st.session_state.clear()
    st.title('🔬 ResearchLens')
    st.write('登录后继续：个人文献库、科研项目与订阅日报仅对自己的账号可见。')
    st.caption('同一浏览器会话内保持登录，最长 8 小时；关闭页面或会话失效后请重新登录。')
    login,register=st.tabs(['登录','注册'])
    with login:
        with st.form('login_form'):
            name=st.text_input('用户名',key='login_name',max_chars=32)
            password=st.text_input('密码',type='password',key='login_password',max_chars=256)
            if st.form_submit_button('登录',type='primary'):
                try:
                    token=accounts.login(name,password)
                    st.session_state.clear();st.session_state.auth_token=token;st.rerun()
                except AccountError as e:st.error(str(e))
    with register:
        st.caption('请使用本网站专用密码。目前没有邮箱验证与自助密码找回。')
        with st.form('register_form',clear_on_submit=True):
            name=st.text_input('注册用户名',max_chars=32)
            password=st.text_input('设置密码（至少12个字符）',type='password',max_chars=256)
            confirm=st.text_input('再次输入密码',type='password',max_chars=256)
            if st.form_submit_button('创建账号'):
                try:
                    accounts.register(name,password,confirm)
                    st.success('账号已创建，请切换登录页签登录。')
                except AccountError as e:st.error(str(e))
    st.info('旧共享档案已保留，但不会自动归属任何新账号；如需迁移，由网站维护者在确认归属后处理。')
    st.stop()
