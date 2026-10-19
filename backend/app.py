import os, json, sqlite3
from pathlib import Path
from datetime import date, datetime
from zoneinfo import ZoneInfo
import requests, streamlit as st
import pymupdf as fitz
from dotenv import load_dotenv
load_dotenv(Path(__file__).with_name('.env'))
st.set_page_config(page_title='ResearchLens 科研解读',page_icon='🔬',layout='wide')
st.markdown('''
<style>
  :root {
    --rl-ink: #17233f;
    --rl-muted: #64748b;
    --rl-primary: #3657d6;
    --rl-primary-dark: #273c9d;
    --rl-teal: #16a7a0;
    --rl-border: #e5eaf4;
    --rl-card: rgba(255,255,255,.86);
  }
  html, body, [class*="css"] {
    font-family: Inter, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
  }
  [data-testid="stAppViewContainer"] {
    background:
      radial-gradient(circle at 8% 0%, rgba(111, 134, 246, .12), transparent 27rem),
      linear-gradient(180deg, #f7f9fe 0%, #ffffff 42%, #f8fafc 100%);
  }
  [data-testid="stHeader"] { background: transparent; }
  .block-container { max-width: 1420px; padding-top: 2.2rem; padding-bottom: 4rem; }
  [data-testid="stSidebar"] {
    background: linear-gradient(180deg, #f4f6ff 0%, #ffffff 55%, #f7fbff 100%);
    border-right: 1px solid #e3e8f4;
  }
  [data-testid="stSidebar"] > div:first-child { padding-top: 1.5rem; }
  [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color: var(--rl-muted); }
  .rl-side-brand { display:flex; align-items:center; gap:.7rem; margin: 0 0 1.6rem .15rem; }
  .rl-side-brand-mark {
    width: 2.2rem; height: 2.2rem; display:grid; place-items:center; border-radius: .75rem;
    color: white; font-size: 1.2rem; background: linear-gradient(135deg, #526fe5, #19b8aa);
    box-shadow: 0 8px 18px rgba(54,87,214,.22);
  }
  .rl-side-brand strong { display:block; color: var(--rl-ink); font-size: 1rem; letter-spacing:.01em; }
  .rl-side-brand small { display:block; color: #8995ae; font-size:.72rem; margin-top:.1rem; }
  .rl-side-title { color:var(--rl-ink); font-size:1.05rem; font-weight:750; margin:0 0 .75rem; }
  .rl-hero {
    position: relative; overflow: hidden; color: white; border-radius: 1.5rem; padding: 2.3rem 2.6rem;
    margin-bottom: 1.7rem; background: linear-gradient(116deg, #1c2d68 0%, #3657d6 55%, #12a89f 125%);
    box-shadow: 0 18px 50px rgba(38, 61, 145, .22);
  }
  .rl-hero:after {
    content:""; position:absolute; width:22rem; height:22rem; right:-7rem; top:-9rem; border-radius:50%;
    border: 1px solid rgba(255,255,255,.22); box-shadow: 0 0 0 2.2rem rgba(255,255,255,.035), 0 0 0 4.4rem rgba(255,255,255,.025);
  }
  .rl-kicker { position:relative; z-index:1; font-size:.73rem; letter-spacing:.18em; font-weight:750; opacity:.72; }
  .rl-hero h1 { position:relative; z-index:1; max-width: 42rem; margin:.55rem 0 .55rem; color:#fff; font-size:clamp(1.8rem, 3.4vw, 3rem); line-height:1.16; letter-spacing:-.035em; }
  .rl-hero p { position:relative; z-index:1; max-width: 41rem; margin:0; color:rgba(255,255,255,.82); font-size:1rem; line-height:1.75; }
  .rl-hero-chips { position:relative; z-index:1; display:flex; flex-wrap:wrap; gap:.55rem; margin-top:1.35rem; }
  .rl-hero-chip { border:1px solid rgba(255,255,255,.22); border-radius:999px; padding:.36rem .72rem; color:rgba(255,255,255,.9); background:rgba(255,255,255,.1); font-size:.78rem; }
  [data-baseweb="tab-list"], [role="tablist"] { gap:.4rem; padding:.35rem; border:1px solid var(--rl-border); border-radius:1rem; background:#eef2fb; }
  [data-baseweb="tab"], [role="tab"] { border-radius:.72rem; color:#64748b; font-weight:650; padding:.7rem 1.1rem; }
  [aria-selected="true"][data-baseweb="tab"], [role="tab"][aria-selected="true"] { color:var(--rl-primary-dark); background:#fff; box-shadow:0 4px 14px rgba(42,64,143,.1); }
  [data-baseweb="tab-highlight"] { background:var(--rl-primary) !important; }
  [data-testid="stForm"], [data-testid="stExpander"] {
    border:1px solid var(--rl-border); border-radius:1.05rem; background:var(--rl-card); box-shadow:0 8px 24px rgba(32,54,105,.045);
  }
  [data-testid="stForm"] { padding: .9rem 1.15rem .2rem; }
  [data-testid="stVerticalBlockBorderWrapper"] { border-color:var(--rl-border); border-radius:1rem; background:rgba(255,255,255,.72); }
  div.stButton > button, div.stDownloadButton > button, button[kind="secondary"], button[kind="primary"], [data-testid="stBaseButton-primary"] {
    border-radius:.72rem; min-height:2.55rem; font-weight:700; transition:all .18s ease;
  }
  div.stButton > button:hover, div.stDownloadButton > button:hover { transform:translateY(-1px); box-shadow:0 7px 16px rgba(54,87,214,.14); }
  button[kind="primary"], [data-testid="stBaseButton-primary"], [data-testid="stFormSubmitButton"] button { border:0 !important; color:#fff !important; background-color:var(--rl-primary) !important; background-image:linear-gradient(135deg, var(--rl-primary), #5a72e6) !important; }
  button[kind="primary"]:hover, [data-testid="stBaseButton-primary"]:hover, [data-testid="stFormSubmitButton"] button:hover { background-color:var(--rl-primary-dark) !important; background-image:linear-gradient(135deg, var(--rl-primary-dark), #4d67d5) !important; }
  [data-baseweb="input"], [data-baseweb="textarea"], [data-baseweb="select"] > div,
  [data-testid="stTextInput"] input, [data-testid="stNumberInput"] input, [data-testid="stDateInput"] input {
    border-radius:.7rem; border-color:#dfe5f1; background:#fff;
  }
  [data-baseweb="input"]:focus-within, [data-baseweb="textarea"]:focus-within, [data-baseweb="select"] > div:focus-within,
  [data-testid="stTextInput"] input:focus, [data-testid="stNumberInput"] input:focus, [data-testid="stDateInput"] input:focus {
    border-color:#7186df; box-shadow:0 0 0 3px rgba(81,106,218,.12);
  }
  [data-testid="stAlert"] { border-radius:.85rem; border:1px solid #e0e7f5; }
  h2, h3 { color:var(--rl-ink); letter-spacing:-.02em; }
  [data-testid="stCaptionContainer"] { color:var(--rl-muted); }
  hr { border-color:#e8edf6; }
  @media (max-width: 760px) {
    .block-container { padding-left:1rem; padding-right:1rem; padding-top:1rem; }
    .rl-hero { padding:1.55rem 1.25rem; border-radius:1.15rem; }
    .rl-hero h1 { font-size:1.85rem; }
    .rl-hero p { font-size:.92rem; line-height:1.6; }
    [data-baseweb="tab"], [role="tab"] { padding:.6rem .55rem; font-size:.82rem; }
  }
</style>
''', unsafe_allow_html=True)

# Resolve the default relative to this file so the app is independent of the
# shell's current directory.  A custom location is useful for protected
# folders (for example macOS Documents/Downloads) and persistent deployments.
_configured_db = os.getenv('RESEARCHLENS_DB_PATH', '').strip()
DB=(Path(_configured_db).expanduser() if _configured_db else Path(__file__).resolve().parent/'papers.db').resolve()
DB.parent.mkdir(parents=True, exist_ok=True)
from accounts import Accounts, require_user
from daily_digest import start_digest_worker, render_digest
accounts=Accounts(DB)
if os.getenv('RESEARCHLENS_EXTERNAL_DIGEST_WORKER')!='1': start_digest_worker(str(DB))
user=require_user(DB)
def save(p):
 accounts.save_paper(user['id'],p)
def saved():
 return accounts.papers(user['id'])
def abstract(inv):
 return ' '.join(w for _,w in sorted((i,w) for w,positions in (inv or {}).items() for i in positions))
def safe_error(e):
 from paper_search import SearchUnavailable
 if isinstance(e, SearchUnavailable): return str(e)
 if isinstance(e, requests.HTTPError):
  if e.response is not None and e.response.status_code == 429:
   return 'OpenAlex 暂时限流，请稍后重试，或在侧边栏配置自己的 API Key。'
  return f'服务返回 HTTP {e.response.status_code}，请检查网络、配额和 API Key。'
 if isinstance(e, (requests.Timeout, requests.ConnectionError)):
  return '网络连接失败或超时，请稍后重试。'
 if type(e).__name__ in ('AuthenticationError','PermissionDeniedError'):
  return '模型服务认证失败：请确认 API Key、模型服务商和接口地址匹配。OpenAI NextCREDITS 请选对应服务商并使用 https://api.openai-next.com/v1。'
 return f'操作失败（{type(e).__name__}），请检查文件或服务配置。'
def today():
 return datetime.now(ZoneInfo('Asia/Shanghai')).date()
def search(q,dt,n,key,journal_issns=None):
 from paper_search import get_search_client
 client=get_search_client(str(DB))
 result=client.search(q,dt,today().isoformat(),n,key) if journal_issns is None else client.search_journals(q,dt,today().isoformat(),n,key,journal_issns)
 st.session_state.search_meta={k:v for k,v in result.items() if k != 'papers'}
 return result['papers']
def content_of(p):
 return (p.get('material_source','上传 PDF 全文'),p['full_text']) if p.get('full_text') else (p.get('source','OpenAlex')+' 摘要',p.get('abstract',''))
def find_passages(p, question):
 import re
 source, content=content_of(p)
 groups=[('研究问题 目的 目标 背景', 'objective aim purpose background hypothesis'),
         ('方法 设计 实验 对照 随机', 'method design experiment control random'),
         ('样本 人数 数量 多少', 'sample participants subjects patients enrolled n='),
         ('局限 限制 不足 缺点', 'limitation limited bias uncertainty'),
         ('结果 发现 结论', 'result finding conclusion outcome')]
 terms=set(re.findall(r'[a-zA-Z]{3,}',question.lower()))
 for chinese, english in groups:
  if any(word in question for word in chinese.split()): terms.update(english.split())
 terms.update(re.findall(r'[\u4e00-\u9fff]{2,}',question))
 chunks=[c.strip() for c in re.split(r'\n+|(?<=[.!?。！？])\s+',content) if c.strip()]
 ranked=sorted(((sum(term in chunk.lower() for term in terms),i,chunk) for i,chunk in enumerate(chunks)),key=lambda x:(-x[0],x[1]))
 selected=[chunk for score,_,chunk in ranked if score][:3]
 header=f'**相关原文查找（非 AI 回答）** · 材料：{source}\n\n'
 if not selected: return header+'未找到与问题直接匹配的原文。不能据此判断论文没有相关内容；可换用原文术语，或配置 OpenAI API Key 后提问。'
 return header+'以下为关键词匹配片段，不代表已经回答问题或核实结论：\n\n'+'\n\n'.join('> '+chunk[:1800].replace('\n','\n> ') for chunk in selected)
def interpret(p,audience,question,key,model,base_url=''):
 source,content=content_of(p)
 if not content: return '无摘要或全文，不能生成有依据的解读。'
 if not key:
  return f"""### {p['title']}

**当前材料：** {source}

**原文摘录（非 AI 结论）：**

> {content[:1500]}

**阅读提示（供你自行核对）：** 研究问题是什么？研究设计和样本量是什么？结论有哪些限制？

当前未配置模型。下方仍可输入问题，查找相关原文；配置 OpenAI API Key 后可获得 AI 解读与回答。"""
 from openai import OpenAI
 system='你是严谨的跨学科论文解读Agent。只依据提供材料回答，不能编造论文事实、数据、DOI、页码。重要结论附上材料中的短句证据。区分事实、推断、未知。摘要材料必须标明仅依据摘要，不能声称审阅全文。针对受众调整术语和深度。用中文回答。'
 prompt=f'受众：{audience}\n任务：{question}\n标题：{p["title"]}\nDOI：{p.get("doi")}\n来源：{source}\n材料（最多45000字符）：\n{content[:45000]}'
 resp=OpenAI(api_key=key,base_url=base_url or None,timeout=60).chat.completions.create(model=model,temperature=0.2,messages=[{'role':'system','content':system},{'role':'user','content':prompt}])
 return resp.choices[0].message.content or '模型未返回内容'
st.markdown('''
<section class="rl-hero">
  <div class="rl-kicker">RESEARCHLENS · 学生科研伙伴</div>
  <h1>从一个问题，走到一份有证据的答案。</h1>
  <p>检索热点论文、读懂研究证据，把复杂发现讲清楚，再把灵感整理成可以继续推进的研究方向。</p>
  <div class="rl-hero-chips">
    <span class="rl-hero-chip">🔎 热点论文</span>
    <span class="rl-hero-chip">📚 PDF 阅读</span>
    <span class="rl-hero-chip">🎬 科普视频</span>
    <span class="rl-hero-chip">🧭 研究工作台</span>
  </div>
</section>
''', unsafe_allow_html=True)
with st.sidebar:
 st.markdown('<div class="rl-side-brand"><span class="rl-side-brand-mark">✦</span><div><strong>ResearchLens</strong><small>学生科研伙伴</small></div></div>', unsafe_allow_html=True)
 st.markdown('<div class="rl-side-title">工作台设置</div>', unsafe_allow_html=True)
 audience=st.selectbox('解读对象',['大众科普','科研入门','专业科研'])
 configured_base=os.getenv('OPENAI_BASE_URL','').strip().rstrip('/')
 provider_options=['OpenAI 官方','OpenAI NextCREDITS','自定义兼容接口']
 provider_default=('OpenAI NextCREDITS' if configured_base=='https://api.openai-next.com/v1' else ('自定义兼容接口' if configured_base else 'OpenAI 官方'))
 provider=st.selectbox('模型服务商',provider_options,index=provider_options.index(provider_default))
 if provider=='OpenAI NextCREDITS':
  openai_base_url='https://api.openai-next.com/v1'
  st.caption('NextCREDITS OpenAI 兼容接口：api.openai-next.com/v1')
 elif provider=='自定义兼容接口':
  openai_base_url=st.text_input('OpenAI 兼容接口地址',value=configured_base,placeholder='https://example.com/v1').strip().rstrip('/')
 else:
  openai_base_url=''
 oa_key=st.text_input('OpenAlex API Key',value=os.getenv('OPENALEX_API_KEY',''),type='password')
 st.caption('此 Key 只用于 OpenAlex 论文检索；OpenAI NextCREDITS Key 不能补充 OpenAlex 配额。')
 ai_key=st.text_input('模型服务 API Key（可选）',value=os.getenv('OPENAI_API_KEY',''),type='password')
 if provider=='OpenAI NextCREDITS':
  st.caption('请把 NextCREDITS 控制台创建的模型 API Key 填在上面；它与 OpenAlex API Key 是两把不同的 Key。')
 else:
  st.caption('这里填写所选模型服务商对应的 API Key，不要把 OpenAlex Key 填到这里。')
 model_default=os.getenv('OPENAI_MODEL','gpt-4.1-mini')
 if provider=='OpenAI NextCREDITS' and 'OPENAI_MODEL' not in os.environ:
  model_default='gpt-6.1-sol'
 model=st.text_input('模型',value=model_default)
 if ai_key:
  st.success('模型服务 Key 已填写；当前 AI 请求会发送到所选服务商。')
 else:
  st.info('无模型服务 Key 仍可检索、保存、阅读论文和管理项目。AI 解读与方案完善需配置匹配的 Key、服务商和接口地址。')
 if audience == '大众科普': st.caption('当前为科普阅读模式：理解研究发现与局限。切换科研入门或专业科研可打开项目工作台。')
 else: st.caption('科研模式已启用：下方项目工作台可持续保存研究问题、证据、方案版本和任务。')
t1,t2,t3=st.tabs(['🔎 搜索最新论文','📄 上传 PDF','📚 已保存论文'])
with t1:
 from journal_metrics import MetricStore,render_metric_import
 metric_store=MetricStore(DB,user['id'])
 advanced=audience != '大众科普'
 if st.session_state.get('metric_mode') != advanced:
  for state_key in ('results','search_settings','search_meta','paper_result_order'):st.session_state.pop(state_key,None)
  st.session_state.metric_mode=advanced
 if advanced:render_metric_import(metric_store)
 metric_rows=metric_store.rows();metric_years=sorted({r['year'] for r in metric_rows},reverse=True)
 with st.form('search'):
  a,b,c=st.columns([4,2,1]);q=a.text_input('研究主题',value='artificial intelligence scientific discovery');dt=b.date_input('最早发表日期',value=date(2025,1,1));n=c.number_input('数量',1,50,8)
  use_jif=False;jif_year=None;jif_min=0.;jif_max=1000.;journal_term=''
  if advanced:
   use_jif=st.checkbox('同时限定期刊影响因子（JIF）',value=False)
   y,lo,hi=st.columns(3)
   jif_year=y.selectbox('JIF指标年',metric_years or [None],format_func=lambda v:str(v) if v is not None else '尚未导入数据')
   jif_min=lo.number_input('JIF下限',min_value=0.0,value=0.0,step=1.0)
   jif_max=hi.number_input('JIF上限',min_value=0.0,value=1000.0,step=1.0)
   journal_term=st.text_input('期刊名称限定（可选）',placeholder='例如：Nature；用于缩小指标表中的期刊范围')
  go=st.form_submit_button('检索真实论文',type='primary')
 if advanced:st.caption('主题、日期和JIF区间可联合检索。已内置2026发布名单的2025指标；会议及未匹配期刊不填0。期刊指标不代表单篇论文质量。')
 st.caption('相同条件缓存15分钟；请求至少间隔3秒，限流时暂停，不会持续重试。')
 search_ok=False
 if go:
  try:
   if jif_min>jif_max:raise ValueError('JIF下限不能大于上限。')
   ids=None
   if use_jif:
    if jif_year is None:raise ValueError('请先在“期刊影响因子数据与导入”中导入指标表，再启用JIF联合检索。')
    ids=metric_store.eligible(jif_year,jif_min,jif_max,journal_term)
    if not ids:raise ValueError('该指标年份、区间和期刊名称没有匹配记录，请调整条件。')
    st.caption(f'匹配 {len(ids)} 个 ISSN，将分 {(len(ids)+99)//100} 批检索，每批最多100个；遇到限流会保留已取得的部分结果。')
   with st.spinner('正在结合研究主题与期刊条件检索…'):
    papers=search(q,str(dt),int(n),oa_key,ids)
    papers=metric_store.annotate(papers,jif_year) if jif_year is not None else papers
    if use_jif:papers=[p for p in papers if p.get('journal_metric') and jif_min<=p['journal_metric']['jif']<=jif_max]
    st.session_state.results=papers
    st.session_state.search_settings={'year':jif_year,'filtered':use_jif,'min':jif_min,'max':jif_max,'query':q}
    search_ok=True
  except ValueError as e:st.warning(str(e))
  except Exception as e:
   st.warning('检索暂不可用：'+safe_error(e))
   if st.session_state.get('results'):st.info('下方保留上次成功结果，条件可能与本次不同。')
 meta=st.session_state.get('search_meta');settings=st.session_state.get('search_settings',{})
 if meta:
  stamp=datetime.fromtimestamp(meta['fetched'],ZoneInfo('Asia/Shanghai')).strftime('%Y-%m-%d %H:%M:%S')
  mode={'live':'实时检索','cache':'命中缓存','stale':'历史缓存','partial':'部分结果'}.get(meta['mode'],'检索')
  st.caption(f"{mode} · 获取时间（北京时间）：{stamp}")
  if meta.get('notice'):st.warning(meta['notice'])
 if settings.get('query'):st.caption('当前展示主题：'+settings['query']+(f" · {settings['year']}年JIF {settings['min']:g}–{settings['max']:g}" if settings.get('filtered') else ''))
 if search_ok and not st.session_state.get('results'):st.info('当前条件没有返回记录，可放宽主题、日期'+('或JIF区间' if advanced else '')+'后再试。')
 papers=[p for p in st.session_state.get('results',[]) if p.get('date') and p['date']<=today().isoformat()]
 order=st.selectbox('本次结果排序',(['最新发表','JIF从高到低','被引次数从高到低'] if advanced else ['最新发表','被引次数从高到低']),key='paper_result_order')
 if order=='JIF从高到低':
  papers.sort(key=lambda p:p.get('journal_metric',{}).get('jif',-1),reverse=True)
  st.caption('仅重排本次已取回的结果，不代表全部匹配文献的JIF排名。未知指标放在最后。')
 elif order=='被引次数从高到低':papers.sort(key=lambda p:p.get('cited_by_count',0),reverse=True)
 for i,p in enumerate(papers):
  with st.container(border=True):
   st.markdown(f'**{i+1}. {p["title"]}**');st.caption(f'{p["date"]} · {p["type"]} · {", ".join(p["authors"][:3])}')
   metric=p.get('journal_metric')
   journal=p.get('venue') or (metric.get('journal') if metric else '') or '来源期刊未提供'
   if not advanced:st.caption(journal)
   elif metric:st.caption(f"{journal} · JIF {metric['jif']:g}（{metric['year']}指标年，{metric.get('status','未核验')}） · 来源：{metric['source']}")
   else:st.caption(journal+' · '+('JIF数据冲突，请检查指标表' if p.get('journal_metric_conflict') else 'JIF未知／未提供对应年度数据'))
   if 'cited_by_count' in p:st.caption(f"文章被引次数：{p['cited_by_count']}（OpenAlex）")
   st.write((p['abstract'][:350]+'…') if len(p['abstract'])>350 else (p['abstract'] or '无摘要'))
   import hashlib
   ident=hashlib.sha256(p['id'].encode()).hexdigest()[:16]
   x,y,z=st.columns([1,1,3])
   if x.button('选择解读',key=f's_{ident}'):st.session_state.paper=p;st.session_state.pop('analysis',None);st.success('已选择，请向下滚动')
   if y.button('保存',key=f'v_{ident}'):save(p);st.success('已保存')
   if p['url']:z.link_button('论文来源',p['url'])
with t2:
 f=st.file_uploader('上传文字型 PDF（扫描版暂不支持）',type='pdf')
 if f and st.button('解析并选择 PDF'):
  try:
   with fitz.open(stream=f.getvalue(),filetype='pdf') as doc:
    page_count=len(doc)
    txt='\n'.join(page.get_text(sort=True) for page in doc)
   if not txt.strip(): st.error('未提取到文字，请上传非扫描 PDF')
   else:
    st.session_state.paper={'id':'upload:'+f.name,'title':f.name,'date':'','doi':'','abstract':'','authors':[],'url':'','full_text':txt}
    st.session_state.pop('analysis',None);st.success(f'已解析 {page_count} 页，{len(txt)} 字符')
  except Exception as e: st.error('PDF 解析失败：'+safe_error(e))
with t3:
 items=saved();st.caption(f'已保存 {len(items)} 篇')
 for i,p in enumerate(items):
  a,b=st.columns([5,1]);a.write(f'{p["title"]} · {p["date"]}')
  if b.button('选择',key=f'lib{i}'):st.session_state.paper=p;st.session_state.pop('analysis',None)
st.divider();st.subheader('🧠 分层解读与追问')
p=st.session_state.get('paper')
if p:
 context=(p['id'],audience,model)
 if st.session_state.get('analysis_context') != context:
  st.session_state.pop('analysis',None)
  st.session_state.analysis_context=context
 source,body=content_of(p);st.markdown(f'**{p["title"]}**');st.caption(f'证据材料：{source}，{len(body)} 字符；受众：{audience}')
 if p.get('url'):st.markdown(f'[查看原始论文记录]({p["url"]})')
 if not body:st.warning('此论文没有可用摘要。请上传 PDF 后解读。')
 if st.button('生成分层解读',type='primary',disabled=not bool(body)):
  try:
   with st.spinner('正在分析论文...'):
    task='用大众能理解的语言简要说明：研究在问什么、发现了什么、对日常理解有什么意义，以及哪些尚不能下结论。不引导制定科研方案，不把论文发现转成个人医疗建议。引用材料短句。' if audience == '大众科普' else '解读研究问题、研究方法、主要结果、证据限制、尚未证明什么、进一步阅读问题。必须引用材料中的短句。'
    st.session_state.analysis=interpret(p,audience,task,ai_key,model,openai_base_url)
  except Exception as e:st.error('解读失败：'+safe_error(e))
 if st.session_state.get('analysis'):
  st.markdown(st.session_state.analysis)
  st.download_button('导出 Markdown',st.session_state.analysis,file_name='paper_analysis.md')
 if not ai_key:
  st.info('未配置 OpenAI Key：提问后仅查找相关原文，不生成 AI 回答。需要解释或推理时，请在侧边栏填写自己的 OpenAI Key。')
 question=st.text_area('针对当前论文追问',placeholder='例如：研究方法有哪些局限？')
 if st.button('提问',disabled=not bool(body and question.strip())):
  try:
   with st.spinner('正在根据材料查找或回答...'):
    answer=interpret(p,audience,question,ai_key,model,openai_base_url) if ai_key else find_passages(p,question)
    st.session_state.qa={'context':context,'question':question,'answer':answer}
  except Exception as e:st.error('回答失败：'+safe_error(e))
 qa=st.session_state.get('qa')
 if qa and qa['context']==context:
  st.write('你的问题：'+qa['question'])
  st.markdown(qa['answer'])
else:st.info('请先检索并选择论文，或上传 PDF。')
from paper_video import render_video
render_video(DB,user['id'],p,ai_key,model,oa_key,openai_base_url)
if audience != '大众科普':
 from research_workspace import render_workspace
 render_workspace(DB,lambda paper,aud,question,key,selected_model: interpret(paper,aud,question,key,selected_model,openai_base_url),ai_key,model,st.session_state.get('paper'),saved(),user['id'])
render_digest(DB,user['id'],save)
st.caption('材料与模型输出均需核验。项目工作台提供研究规划草稿，不替代伦理审批、专业实验审核或临床决策。当前不含自动系统综述或多篇向量 RAG。')
