"""Per-account, attributed JIF data. No fabricated or substitute impact factors."""
import json
from pathlib import Path
from functools import lru_cache
import csv
import io
import math
import re
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo
import streamlit as st

def normalize_issn(value):
    value=re.sub(r'[-\s]','',str(value)).upper()
    if not re.fullmatch(r'\d{7}[\dX]',value):raise ValueError('ISSN格式应为1234-567X。')
    total=sum(int(c)*weight for c,weight in zip(value[:7],range(8,1,-1)))+(10 if value[-1]=='X' else int(value[-1]))
    if total%11:raise ValueError('ISSN校验位不正确。')
    return value[:4]+'-'+value[4:]

def parse_metrics(data):
    if len(data)>5_000_000:raise ValueError('文件请控制在5MB以内。')
    try:reader=csv.DictReader(io.StringIO(data.decode('utf-8-sig')))
    except UnicodeDecodeError:raise ValueError('请使用UTF-8编码的CSV文件。') from None
    required={'issn','journal','jif','year','source'}
    if not reader.fieldnames or not required.issubset(reader.fieldnames):raise ValueError('CSV需要包含：issn,journal,jif,year,source。')
    rows={};current=datetime.now(ZoneInfo('Asia/Shanghai')).year
    for index,row in enumerate(reader,2):
        if index>30002:raise ValueError('每次最多导入30000行。')
        try:
            year=int(row['year']);jif=float(row['jif'])
            if not 1990<=year<=current or not math.isfinite(jif) or jif<0:raise ValueError()
            journal=(row['journal'] or '').strip();source=(row['source'] or '').strip()
            if not journal or not source or len(source)>500 or len(journal)>250:raise ValueError()
            ids=[normalize_issn(v) for v in re.split(r'[;,|]',row['issn']) if v.strip()]
            if not ids:raise ValueError()
        except (ValueError,TypeError,KeyError):raise ValueError(f'第{index}行存在无效ISSN、指标年、数值或来源；未导入任何数据。') from None
        for issn in ids:
            key=(issn,year)
            if key in rows and rows[key]['jif']!=jif:raise ValueError(f'第{index}行与同一ISSN、年份的指标冲突。')
            rows[key]={'issn':issn,'year':year,'jif':jif,'journal':journal,'source':source}
    if not rows:raise ValueError('文件中没有可导入的指标。')
    return list(rows.values())

@lru_cache(maxsize=1)
def builtin_dataset():
    path = Path(__file__).parent/'data'/'jcr_2026.json'
    if not path.exists():
        return {'records': []}
    return json.loads(path.read_text(encoding='utf-8'))

def builtin_rows():
    result={}
    for r in builtin_dataset()['records']:
        if r['issn'] and r['jif'] is not None and not r['conflict']:
            result[(r['issn'],r['year'])]={k:r[k] for k in ('issn','year','jif','journal','release_year')}
            result[(r['issn'],r['year'])].update(source='用户提供的2026年度JCR名单（2025影响因子列）',status='内置名单，未独立核验')
    return result

class MetricStore:
    def __init__(self,db,user_id):
        self.db,self.user_id=str(db),user_id
        with self.connect() as con:
            if not user_id or not con.execute('SELECT 1 FROM users WHERE id=?',(user_id,)).fetchone():raise PermissionError('请先登录。')
            con.execute('CREATE TABLE IF NOT EXISTS journal_metrics(user_id TEXT NOT NULL,issn TEXT NOT NULL,year INTEGER NOT NULL,jif REAL NOT NULL,journal TEXT NOT NULL,source TEXT NOT NULL,PRIMARY KEY(user_id,issn,year))')
    def connect(self):
        con=sqlite3.connect(self.db,timeout=20);con.row_factory=sqlite3.Row;return con
    def import_rows(self,rows):
        # Public method also validates input; UI validation is not an access boundary.
        raw=io.StringIO();writer=csv.DictWriter(raw,fieldnames=['issn','journal','jif','year','source']);writer.writeheader();writer.writerows(rows)
        checked=parse_metrics(raw.getvalue().encode())
        with self.connect() as con:
            con.executemany('INSERT INTO journal_metrics VALUES (?,?,?,?,?,?) ON CONFLICT(user_id,issn,year) DO UPDATE SET jif=excluded.jif,journal=excluded.journal,source=excluded.source',
                [(self.user_id,r['issn'],r['year'],r['jif'],r['journal'],r['source']) for r in checked])
    def rows(self):
        with self.connect() as con:personal=[dict(r) for r in con.execute('SELECT issn,year,jif,journal,source FROM journal_metrics WHERE user_id=? ORDER BY year DESC,jif DESC',(self.user_id,))]
        merged=builtin_rows()
        for r in personal:merged[(r['issn'],r['year'])]={**r,'status':'用户导入，未自动核验'}
        return sorted(merged.values(),key=lambda r:(r['year'],r['jif']),reverse=True)
    def eligible(self,year,minimum,maximum,term=''):
        return sorted({r['issn'] for r in self.rows() if r['year']==year and minimum<=r['jif']<=maximum and term.lower() in r['journal'].lower()})
    def annotate(self,papers,year):
        lookup={r['issn']:r for r in self.rows() if r['year']==year}
        result=[]
        for paper in papers:
            p=dict(paper);p.pop('journal_metric',None);p.pop('journal_metric_conflict',None);matches=[]
            if p.get('venue_type') in (None,'','journal'):
                for value in p.get('issns',[]):
                    try:row=lookup.get(normalize_issn(value))
                    except ValueError:continue
                    if row:matches.append(row)
            if matches:
                values={r['jif'] for r in matches}
                if len(values)==1:p['journal_metric']=dict(matches[0])
                else:p['journal_metric_conflict']=True
            result.append(p)
        return result

def render_metric_import(store):
    with st.expander('期刊影响因子数据与导入',expanded=False):
        st.write('JIF是期刊年度指标。已内置用户提供的2026年发布名单，表内为2025影响因子。个人CSV可补充或覆盖同一ISSN及指标年。不同年份不混用，未匹配不记为0。')
        st.caption('CSV列：issn、journal、jif、year、source。来源填数据出处或授权导出说明；多个ISSN用分号分隔。按账号保存，其他访客看不到你的指标表。')
        file=st.file_uploader('导入个人期刊指标表（UTF-8 CSV）',type='csv',key='metric_csv')
        if st.button('保存指标表',disabled=file is None):
            try:
                rows=parse_metrics(file.getvalue());store.import_rows(rows)
                st.success(f'已保存{len(rows)}条ISSN年度记录；同一ISSN年份更新，其他记录保留。')
            except ValueError as e:st.error(str(e))
        st.download_button('下载空白CSV模板','issn,journal,jif,year,source\n',file_name='journal_metrics_template.csv',mime='text/csv')
        meta=builtin_dataset()['metadata']
        st.caption(f"内置完整名单：{meta['records']}行；2026发布年，2025指标年。仅有效ISSN及明确数值参与区间检索。<0.1、N/A和无效ISSN保留原值，不换算为0。数据来自提供的文件，未独立核验。")
        term=st.text_input('查询内置期刊名单',placeholder='输入期刊名或ISSN，查看学科与分区')
        if term.strip():
            found=[r for r in builtin_dataset()['records'] if term.casefold() in str(r['journal']).casefold() or term.casefold() in str(r['raw_issn']).casefold()]
            st.caption(f'匹配{len(found)}行，最多展示前100行。分区按各学科分别保留。')
            st.dataframe([{'期刊':r['journal'],'ISSN':r['raw_issn'],'学科':r['category'],'2025 JIF':str(r['jif_raw']),'分区':r['quartile']} for r in found[:100]],hide_index=True)

