"""Private daily PubMed subscriptions; background delivery while this app runs."""
import hashlib
import json
import sqlite3
import threading
import time
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta
from urllib.parse import urlencode
from uuid import uuid4
from zoneinfo import ZoneInfo
import requests
import streamlit as st

TZ=ZoneInfo('Asia/Shanghai')

def connect(db):
    con=sqlite3.connect(str(db),timeout=20);con.row_factory=sqlite3.Row
    return con

def init_db(db):
    with connect(db) as con:
        con.executescript('''
        CREATE TABLE IF NOT EXISTS subscriptions(id TEXT PRIMARY KEY,user_id TEXT NOT NULL,
            label TEXT NOT NULL,query TEXT NOT NULL,active INTEGER NOT NULL,created REAL NOT NULL,
            next_run REAL NOT NULL,last_end TEXT,lease_until REAL NOT NULL DEFAULT 0,
            UNIQUE(user_id,query));
        CREATE TABLE IF NOT EXISTS digest_runs(id TEXT PRIMARY KEY,subscription_id TEXT NOT NULL,
            edition TEXT NOT NULL,status TEXT NOT NULL,message TEXT NOT NULL,new_count INTEGER NOT NULL,
            total_count INTEGER NOT NULL,created REAL NOT NULL,UNIQUE(subscription_id,edition));
        CREATE TABLE IF NOT EXISTS digest_items(id TEXT PRIMARY KEY,subscription_id TEXT NOT NULL,
            paper_id TEXT NOT NULL,paper TEXT NOT NULL,edition TEXT NOT NULL,read INTEGER NOT NULL DEFAULT 0,
            UNIQUE(subscription_id,paper_id));
        CREATE TABLE IF NOT EXISTS digest_fetch_cache(query_id TEXT PRIMARY KEY,payload TEXT NOT NULL,fetched REAL NOT NULL);
        ''')

class Subscriptions:
    def __init__(self,db,user_id):
        self.db,self.user_id=str(db),user_id
        init_db(db)
        with connect(db) as con:
            if not user_id or not con.execute('SELECT 1 FROM users WHERE id=?',(user_id,)).fetchone():raise PermissionError('请先登录。')
    def add(self,label,query):
        label,query=label.strip(), ' '.join(query.split())
        if not label or not query:raise ValueError('请填写方向名称和检索词。')
        if len(label)>100 or len(query)>300:raise ValueError('方向名称最多100字符，检索词最多300字符。')
        with connect(self.db) as con:
            con.execute('BEGIN IMMEDIATE')
            if con.execute('SELECT COUNT(*) FROM subscriptions WHERE user_id=?',(self.user_id,)).fetchone()[0]>=5:raise ValueError('每个账号最多订阅5个方向，可编辑现有方向。')
            try:
                con.execute('INSERT INTO subscriptions(id,user_id,label,query,active,created,next_run) VALUES (?,?,?,?,1,?,?)',
                            (uuid4().hex,self.user_id,label,query,time.time(),time.time()))
            except sqlite3.IntegrityError:raise ValueError('已订阅相同检索词。') from None
    def subscriptions(self):
        with connect(self.db) as con:return [dict(r) for r in con.execute('SELECT * FROM subscriptions WHERE user_id=? ORDER BY created',(self.user_id,))]
    def set_active(self,sid,active):
        with connect(self.db) as con:
            cursor=con.execute('UPDATE subscriptions SET active=? WHERE id=? AND user_id=?',(int(active),sid,self.user_id))
            if cursor.rowcount!=1:raise PermissionError('无权访问此订阅。')
    def rename_query(self,sid,label,query):
        # Topic changes create a new subscription rather than mixing unrelated history.
        self.add(label,query)
        self.set_active(sid,False)
    def runs(self):
        with connect(self.db) as con:
            return [dict(r) for r in con.execute('SELECT r.*,s.label FROM digest_runs r JOIN subscriptions s ON s.id=r.subscription_id WHERE s.user_id=? ORDER BY r.edition DESC,r.created DESC LIMIT 100',(self.user_id,))]
    def items(self,edition=None):
        sql='SELECT i.*,s.label FROM digest_items i JOIN subscriptions s ON s.id=i.subscription_id WHERE s.user_id=?'
        args=[self.user_id]
        if edition:sql+=' AND i.edition=?';args.append(edition)
        with connect(self.db) as con:return [dict(r) for r in con.execute(sql+' ORDER BY i.edition DESC,i.rowid DESC',args)]
    def mark_read(self,iid,read=True):
        with connect(self.db) as con:
            cur=con.execute('UPDATE digest_items SET read=? WHERE id=? AND subscription_id IN (SELECT id FROM subscriptions WHERE user_id=?)',(int(read),iid,self.user_id))
            if cur.rowcount!=1:raise PermissionError('无权访问此日报。')

def text(node,path):
    found=node.find(path)
    return ''.join(found.itertext()).strip() if found is not None else ''

def parse_pubmed(xml,today):
    root=ET.fromstring(xml);papers=[]
    if root.tag!='PubmedArticleSet' or root.find('.//ERROR') is not None:raise ValueError('Invalid PubMed XML')
    for entry in root.findall('.//PubmedArticle'):
        article=entry.find('MedlineCitation/Article')
        if article is None:continue
        pmid=text(entry,'MedlineCitation/PMID')
        if not pmid:continue
        # Prefer the electronic publication date when present.
        pd=article.find('ArticleDate')
        if pd is None:pd=article.find('Journal/JournalIssue/PubDate')
        parts=[text(pd,p) if pd is not None else '' for p in ('Year','Month','Day')]
        publication='-'.join(p for p in parts if p) or (text(pd,'MedlineDate') if pd is not None else '')
        if parts[0].isdigit():
            year=int(parts[0]);month=parts[1]
            if month.isalpha():
                try:month=str(datetime.strptime(month[:3],'%b').month)
                except ValueError:month=''
            if year>today.year:continue
            if month.isdigit():
                day=int(parts[2]) if parts[2].isdigit() else 1
                try:
                    earliest=date(year,int(month),day)
                    if earliest>today:continue
                    publication=earliest.isoformat() if parts[2].isdigit() else f'{year:04d}-{int(month):02d}'
                except ValueError:pass
        authors=[]
        for author in article.findall('AuthorList/Author')[:5]:
            authors.append((text(author,'ForeName')+' '+text(author,'LastName')).strip() or text(author,'CollectiveName'))
        doi=''
        for ident in entry.findall('PubmedData/ArticleIdList/ArticleId'):
            if ident.get('IdType')=='doi':doi='https://doi.org/'+(ident.text or '')
        abstract='\n'.join(((a.get('Label','')+': ') if a.get('Label') else '')+''.join(a.itertext()).strip() for a in article.findall('Abstract/AbstractText'))
        papers.append({'id':'pubmed:'+pmid,'title':text(article,'ArticleTitle') or '无标题','date':publication,
                       'doi':doi,'abstract':abstract,'authors':authors,'url':f'https://pubmed.ncbi.nlm.nih.gov/{pmid}/',
                       'full_text':'','type':'PubMed article','venue':text(article,'Journal/Title'),'source':'PubMed',
                       'venue_type':'journal','issns':list({v for v in [text(article,'Journal/ISSN'),text(entry,'MedlineCitation/MedlineJournalInfo/ISSNLinking')] if v})})
    return papers

class PubMedClient:
    def __init__(self,db,get=None):
        self.db,self.get=str(db),get
        self.lock=threading.Lock();self.last=0
    def request(self,endpoint,params):
        # Keep all background requests below the keyless NCBI request rate.
        with self.lock:
            wait=1-(time.monotonic()-self.last)
            if wait>0:time.sleep(wait)
            self.last=time.monotonic()
            r=(self.get or requests.get)('https://eutils.ncbi.nlm.nih.gov/entrez/eutils/'+endpoint,params={**params,'tool':'ResearchLens'},timeout=25)
            r.raise_for_status();return r
    def fetch(self,query,start,end):
        qid=hashlib.sha256(json.dumps([query,str(start),str(end)]).encode()).hexdigest()
        with connect(self.db) as con:
            cached=con.execute('SELECT * FROM digest_fetch_cache WHERE query_id=?',(qid,)).fetchone()
        if cached and time.time()-cached['fetched']<3600:return json.loads(cached['payload'])
        result=self.request('esearch.fcgi',{'db':'pubmed','term':query,'datetype':'edat','mindate':str(start).replace('-','/'),
                    'maxdate':str(end).replace('-','/'),'retmax':50,'sort':'pub_date','retmode':'json'}).json()
        data=result.get('esearchresult',{})
        errors=data.get('errorlist') or {}
        has_errors=any(bool(value) for value in errors.values()) if isinstance(errors,dict) else bool(errors)
        if result.get('ERROR') or result.get('error') or has_errors or not isinstance(data.get('idlist'),list):raise ValueError('Invalid PubMed response')
        ids=data['idlist'];count=int(data.get('count',0))
        papers=[]
        if ids:
            xml=self.request('efetch.fcgi',{'db':'pubmed','id':','.join(ids),'retmode':'xml'}).content
            papers=parse_pubmed(xml,datetime.now(TZ).date())
        payload={'papers':papers,'count':count,'limit':50}
        with connect(self.db) as con:con.execute('INSERT OR REPLACE INTO digest_fetch_cache VALUES (?,?,?)',(qid,json.dumps(payload,ensure_ascii=False),time.time()))
        return payload

class DigestEngine:
    def __init__(self,db,client=None,clock=time.time):
        self.db,self.clock=str(db),clock
        init_db(db);self.client=client or PubMedClient(db)
    def run_due(self,limit=20):
        now=self.clock()
        with connect(self.db) as con:
            due=[dict(r) for r in con.execute('SELECT * FROM subscriptions WHERE active=1 AND next_run<=? AND lease_until<? ORDER BY next_run LIMIT ?',(now,now,limit))]
        for sub in due:
            now=self.clock()
            with connect(self.db) as con:
                claim=con.execute('UPDATE subscriptions SET lease_until=? WHERE id=? AND active=1 AND lease_until<? AND next_run<=?',(now+180,sub['id'],now,now))
                if claim.rowcount!=1:continue
            self.deliver(sub)
    def deliver(self,sub):
        now=self.clock();local=datetime.fromtimestamp(now,TZ);edition=local.date().isoformat()
        end=local.date()-timedelta(days=1)
        # On subscription deliver the previous 7 complete days; overlap subsequent
        # windows to catch indexing changes, while item IDs prevent duplicates.
        start=date.fromisoformat(sub['last_end'])-timedelta(days=2) if sub['last_end'] else end-timedelta(days=6)
        try:
            result=self.client.fetch(sub['query'],start,end)
            next_run=(local+timedelta(days=1)).replace(hour=9,minute=0,second=0,microsecond=0).timestamp()
            with connect(self.db) as con:
                con.execute('BEGIN IMMEDIATE')
                live=con.execute('SELECT active FROM subscriptions WHERE id=?',(sub['id'],)).fetchone()
                if not live or not live['active']:
                    con.execute('UPDATE subscriptions SET lease_until=0 WHERE id=?',(sub['id'],));return
                added=0
                for p in result['papers']:
                    cursor=con.execute('INSERT OR IGNORE INTO digest_items(id,subscription_id,paper_id,paper,edition) VALUES (?,?,?,?,?)',
                                       (uuid4().hex,sub['id'],p['id'],json.dumps(p,ensure_ascii=False),edition))
                    added+=cursor.rowcount
                message=f'PubMed 收录日期范围 {start} 至 {end}；按订阅关键词检索。'
                if result['count']>result['limit']:message+=f" 本期匹配 {result['count']} 条，仅展示最新 {result['limit']} 条；请细化订阅词。"
                con.execute('INSERT INTO digest_runs VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(subscription_id,edition) DO UPDATE SET status=excluded.status,message=excluded.message,new_count=digest_runs.new_count+excluded.new_count,total_count=excluded.total_count,created=excluded.created',
                            (uuid4().hex,sub['id'],edition,'success',message,added,result['count'],now))
                con.execute('UPDATE subscriptions SET next_run=?,last_end=?,lease_until=0 WHERE id=?',(next_run,str(end),sub['id']))
        except Exception:
            # Do not put URLs, tokens, raw HTTP messages or query text in errors.
            with connect(self.db) as con:
                con.execute('INSERT INTO digest_runs VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(subscription_id,edition) DO UPDATE SET status=excluded.status,message=excluded.message,created=excluded.created',
                            (uuid4().hex,sub['id'],edition,'error','PubMed 暂不可用，本期未完成；约1小时后重试，不代表没有新文献。',0,0,now))
                con.execute('UPDATE subscriptions SET next_run=?,lease_until=0 WHERE id=?',(now+3600,sub['id']))

class DigestWorker:
    def __init__(self,db):
        self.engine=DigestEngine(db);self.stop_event=threading.Event()
        self.thread=threading.Thread(target=self.loop,name='ResearchLensDailyDigest',daemon=True)
        self.thread.start()
    def loop(self):
        while not self.stop_event.is_set():
            try:self.engine.run_due()
            except Exception:pass
            self.stop_event.wait(30)
    def stop(self):self.stop_event.set()

@st.cache_resource(show_spinner=False)
def start_digest_worker(db):
    return DigestWorker(db)

def render_digest(db,user_id,save_paper):
    store=Subscriptions(db,user_id)
    st.divider();st.header('📰 我的文献日报')
    st.caption('生物方向 · PubMed · 每日北京时间 09:00 更新前一天及遗漏的新增收录记录。首次订阅回看近7个完整日，不代表完整文献综述。')
    st.info('日报只对自己的账号可见。网站运行时后台自动更新；Mac 关机或休眠时暂停，恢复后补查。订阅后通常约30秒开始首次更新，刷新页面查看。')
    with st.expander('订阅科研方向',expanded=not bool(store.subscriptions())):
        with st.form('subscribe_direction',clear_on_submit=True):
            label=st.text_input('方向名称',placeholder='例如：植物免疫',max_chars=100)
            query=st.text_input('PubMed 英文检索词',placeholder='例如：plant immunity 或 (CRISPR) AND (plant)',max_chars=300)
            st.caption('每个账号最多5个方向。订阅词会发送给 PubMed；请勿填写私人研究数据。当前为站内日报，不发送邮件。')
            if st.form_submit_button('订阅每日文献'):
                try:store.add(label,query);st.rerun()
                except ValueError as e:st.error(str(e))
    for sub in store.subscriptions():
        a,b=st.columns([5,1])
        a.write(f"{sub['label']} · {'订阅中' if sub['active'] else '已暂停'}")
        a.caption(sub['query'])
        if b.button('暂停' if sub['active'] else '恢复',key=f"pause_{sub['id']}"):
            store.set_active(sub['id'],not sub['active']);st.rerun()
    items,runs=store.items(),store.runs()
    st.caption(f"未读 {sum(not r['read'] for r in items)} 条 · 相同文献在同一订阅中只投递一次")
    if st.button('刷新日报',key='refresh_digest'):st.rerun()
    if not runs:
        st.info('还没有日报。订阅后等待首次更新；没有订阅时不会请求文献接口。')
        return
    dates=sorted({r['edition'] for r in runs},reverse=True)
    edition=st.selectbox('日报日期',dates,key='digest_edition')
    for run in (r for r in runs if r['edition']==edition):
        if run['status']=='error':st.warning(run['label']+'：'+run['message'])
        else:st.caption(f"{run['label']} · 本期新增 {run['new_count']} 条 · {run['message']}")
    selected=[i for i in items if i['edition']==edition]
    for item in selected:
        p=json.loads(item['paper'])
        with st.container(border=True):
            st.markdown('**'+p['title']+'**')
            st.caption(f"{item['label']} · {p.get('venue','')} · 出版日期：{p['date'] or '未提供'} · {'已读' if item['read'] else '未读'}")
            st.write(p['abstract'][:450] or '来源没有提供摘要。')
            a,b,c,d=st.columns(4)
            a.link_button('PubMed 来源',p['url'])
            if b.button('选择解读',key=f"digest_select_{item['id']}"):
                st.session_state.paper=p;st.session_state.pop('analysis',None);store.mark_read(item['id']);st.rerun()
            if c.button('保存文献',key=f"digest_save_{item['id']}"):
                save_paper(p);st.success('已保存到个人文献库。')
            if d.button('标为未读' if item['read'] else '标为已读',key=f"digest_read_{item['id']}"):
                store.mark_read(item['id'],not item['read']);st.rerun()
    if not selected:st.info('本期没有新增投递；若更新失败，请查看上方状态。')
    st.download_button('导出本期日报 JSON',json.dumps([json.loads(i['paper']) for i in selected],ensure_ascii=False,indent=2),file_name=f'literature_digest_{edition}.json',mime='application/json')
