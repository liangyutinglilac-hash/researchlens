"""Public paper cache and process-wide OpenAlex request coordination. No keys on disk."""
import hashlib
import json
import math
import re
import sqlite3
import threading
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import requests
import streamlit as st

class SearchUnavailable(Exception):
    pass

def decode_works(payload):
    papers = []
    for w in payload.get('results', []):
        inv = w.get('abstract_inverted_index') or {}
        venue=(w.get('primary_location') or {}).get('source') or {}
        abstract = ' '.join(word for _, word in sorted((i, word) for word, positions in inv.items() for i in positions))
        papers.append({'id':w['id'], 'title':w.get('display_name') or '无标题',
                       'date':w.get('publication_date') or '', 'doi':w.get('doi') or '',
                       'abstract':abstract, 'authors':[a.get('author',{}).get('display_name','') for a in w.get('authorships',[])][:5],
                       'url':w['id'], 'full_text':'', 'type':w.get('type','unknown'),
                       'venue':venue.get('display_name',''),'venue_type':venue.get('type',''),
                       'issns':sorted(set((venue.get('issn') or [])+([venue['issn_l']] if venue.get('issn_l') else []))),
                       'cited_by_count':w.get('cited_by_count',0)})
    return papers

class SearchClient:
    TTL = 15 * 60
    STALE_TTL = 7 * 24 * 3600
    INTERVAL = 3
    def __init__(self, db, clock=time.time, get=None):
        self.db, self.clock, self.get = str(db), clock, get
        self.lock = threading.RLock()
        self.last_request = float('-inf')
        self.cooldowns, self.failures = {}, {}
        with sqlite3.connect(self.db) as con:
            con.execute('CREATE TABLE IF NOT EXISTS paper_search_cache (query_id TEXT PRIMARY KEY, papers TEXT NOT NULL, fetched REAL NOT NULL)')
    @staticmethod
    def query_id(query, start, end, count, issns=(), sort='publication_date:desc'):
        # Only public query parameters contribute; credentials are never persisted.
        parts=[' '.join(query.split()),str(start),str(end),int(count),str(sort)]
        if issns:parts.append(sorted(set(issns)))
        return hashlib.sha256(json.dumps(parts,ensure_ascii=False).encode()).hexdigest()
    def remember(self, query, start, end, count, papers, fetched=None, issns=(), sort='publication_date:desc'):
        qid = self.query_id(query, start, end, count, issns, sort)
        with sqlite3.connect(self.db) as con:
            con.execute('INSERT OR REPLACE INTO paper_search_cache VALUES (?,?,?)',
                        (qid, json.dumps(papers, ensure_ascii=False), self.clock() if fetched is None else fetched))
    def cached(self, qid):
        with sqlite3.connect(self.db) as con:
            row = con.execute('SELECT papers,fetched FROM paper_search_cache WHERE query_id=?', (qid,)).fetchone()
        return (json.loads(row[0]), row[1]) if row else None
    def outcome(self, papers, fetched, mode, notice=''):
        return {'papers':papers, 'fetched':fetched, 'mode':mode, 'notice':notice}
    def fallback(self, cache, message):
        if cache and self.clock() - cache[1] <= self.STALE_TTL:
            return self.outcome(*cache, 'stale', message + ' 现显示相同条件的历史缓存，并非实时结果。')
        raise SearchUnavailable(message)
    def retry_delay(self, headers, scope):
        delay = min(900, 60 * 2 ** min(self.failures.get(scope, 0), 4))
        retry = headers.get('Retry-After', '')
        try:
            delay = max(delay, float(retry))
        except (TypeError, ValueError):
            try:
                delay = max(delay, parsedate_to_datetime(retry).timestamp() - self.clock())
            except (TypeError, ValueError, OverflowError):
                pass
        if str(headers.get('X-RateLimit-Remaining', '')) == '0':
            try:
                delay = max(delay, float(headers.get('X-RateLimit-Reset', 0)))
            except (TypeError, ValueError):
                pass
        return max(1, delay)
    def search(self, query, start, end, count, key='', issns=(), sort='publication_date:desc'):
        if len(issns)>100:raise SearchUnavailable('每批最多100个ISSN。')
        query = ' '.join(query.split())
        if not query:
            raise SearchUnavailable('请输入研究主题。')
        if str(start) > str(end):
            raise SearchUnavailable('最早发表日期不能晚于今天。')
        qid = self.query_id(query, start, end, count, issns, sort)
        scope = hashlib.sha256(key.encode()).hexdigest() if key else 'anonymous'
        # Serializes cache misses across sessions, preventing duplicate requests.
        with self.lock:
            cache, now = self.cached(qid), self.clock()
            if cache and now - cache[1] < self.TTL:
                return self.outcome(*cache, 'cache')
            wait = self.cooldowns.get(scope, 0) - now
            if wait > 0:
                return self.fallback(cache, f'OpenAlex 正在冷却，请至少 {math.ceil(wait)} 秒后再试。冷却结束不代表配额一定恢复；也可配置自己的 OpenAlex Key。')
            wait = self.INTERVAL - (now - self.last_request)
            if wait > 0:
                return self.fallback(cache, f'检索操作过快，请 {math.ceil(wait)} 秒后重试。')
            params = {'search':query,'per_page':int(count),'sort':sort,
                      'filter':f'from_publication_date:{start},to_publication_date:{end}'}
            doi = re.fullmatch(r'(?:https?://doi\.org/)?(10\.\d{4,9}/[-._;()/:A-Z0-9]+)', query, re.I)
            if doi:
                params.pop('search')
                params['filter'] += ',doi:https://doi.org/' + doi.group(1)
            if issns:
                from journal_metrics import normalize_issn
                ids=sorted({normalize_issn(v) for v in issns})
                params['filter']+=',primary_location.source.issn:'+'|'.join(ids)
            if key:
                params['api_key'] = key
            self.last_request = now
            try:
                r = (self.get or requests.get)('https://api.openalex.org/works', params=params, timeout=30)
                if r.status_code == 429:
                    delay = self.retry_delay(r.headers, scope)
                    self.cooldowns[scope] = self.clock() + delay
                    self.failures[scope] = self.failures.get(scope, 0) + 1
                    return self.fallback(cache, f'OpenAlex 限流或配额不足，已暂停请求至少 {math.ceil(delay)} 秒。请等待后再试，或配置自己的 OpenAlex Key。')
                if r.status_code in (401, 403):
                    return self.fallback(cache, 'OpenAlex 身份验证未通过，请检查侧边栏中的 OpenAlex Key。')
                if r.status_code >= 400:
                    return self.fallback(cache, f'OpenAlex 返回 HTTP {r.status_code}，请稍后重试。')
                papers = decode_works(r.json())
                papers = [p for p in papers if p['date'] and str(start) <= p['date'] <= str(end)]
            except requests.RequestException:
                return self.fallback(cache, 'OpenAlex 网络连接失败或超时，请稍后重试。')
            except (ValueError, KeyError, TypeError):
                return self.fallback(cache, 'OpenAlex 返回的数据暂时无法解析，请稍后重试。')
            fetched = self.clock()
            self.remember(query, start, end, count, papers, fetched, issns, sort)
            self.cooldowns.pop(scope, None)
            self.failures.pop(scope, None)
            return self.outcome(papers, fetched, 'live')

    def search_journals(self,query,start,end,count,key,issns):
        from journal_metrics import normalize_issn
        ids=sorted({normalize_issn(v) for v in issns})
        if not ids:raise SearchUnavailable('所选年份和区间没有匹配期刊，请调整条件或导入指标表。')
        batches=[ids[i:i+100] for i in range(0,len(ids),100)]
        outcomes=[]
        for batch in batches:
            try:
                with self.lock:
                    cache=self.cached(self.query_id(query,start,end,count,batch))
                    if not cache or self.clock()-cache[1]>=self.TTL:
                        if self.cooldowns.get(hashlib.sha256(key.encode()).hexdigest() if key else 'anonymous',0)<=self.clock():
                            wait=self.INTERVAL-(self.clock()-self.last_request)
                            if wait>0:time.sleep(wait)
                    outcome=self.search(query,start,end,count,key,issns=batch)
                outcomes.append(outcome)
                if outcome['mode']=='stale':break
            except SearchUnavailable as e:
                if not outcomes:raise
                return self.combine(outcomes,count,len(batches),str(e))
        return self.combine(outcomes,count,len(batches))
    def combine(self,outcomes,count,total,warning=''):
        papers={p['id']:p for o in outcomes for p in o['papers']}
        ordered=sorted(papers.values(),key=lambda p:(p['date'],p['id']),reverse=True)[:count]
        partial=len(outcomes)<total
        notices=[o['notice'] for o in outcomes if o.get('notice')]
        if warning:notices.append(warning)
        if partial:notices.append(f'仅完成{len(outcomes)}/{total}组期刊检索，结果不完整。')
        mode='partial' if partial else ('stale' if any(o['mode']=='stale' for o in outcomes) else ('cache' if all(o['mode']=='cache' for o in outcomes) else 'live'))
        return self.outcome(ordered,min(o['fetched'] for o in outcomes),mode,' '.join(dict.fromkeys(notices)))

@st.cache_resource(show_spinner=False)
def get_search_client(db):
    return SearchClient(db)
