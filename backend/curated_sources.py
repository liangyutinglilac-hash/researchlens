"""Import user-supplied editorial science articles without claiming primary evidence."""
import hashlib
import re
from urllib.parse import urlsplit
from html.parser import HTMLParser
from html import unescape


def _check_wechat_url(url):
    parsed = urlsplit(url.strip())
    if parsed.scheme != 'https' or parsed.hostname != 'mp.weixin.qq.com' or parsed.username or parsed.password or parsed.port:
        raise ValueError('来源链接请填写 https://mp.weixin.qq.com/ 开头的公众号文章链接，或留空。')
    return parsed


class _WeChatParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title, self.body, self._title_depth, self._body_depth = [], [], 0, 0

    def handle_starttag(self, tag, attrs):
        if tag in ('br', 'img', 'hr', 'input', 'meta', 'link', 'source', 'wbr', 'area', 'base', 'embed', 'param', 'track', 'col'):
            return
        attrs = dict(attrs)
        ident = attrs.get('id', '')
        if ident == 'activity-name':
            self._title_depth = 1
        elif self._title_depth:
            self._title_depth += 1
        if ident == 'js_content':
            self._body_depth = 1
        elif self._body_depth:
            self._body_depth += 1

    def handle_endtag(self, tag):
        if self._title_depth:
            self._title_depth -= 1
        if self._body_depth:
            self._body_depth -= 1

    def handle_data(self, data):
        if self._title_depth:
            self.title.append(data)
        if self._body_depth:
            self.body.append(data)


def fetch_article(url):
    """Best-effort fetch of one public WeChat article; paste fallback is explicit."""
    _check_wechat_url(url)
    import requests
    response = requests.get(url.strip(), headers={'User-Agent': 'ResearchLens/1.0'}, timeout=15, allow_redirects=False)
    if response.status_code in (301, 302, 303, 307, 308):
        raise ValueError('公众号链接发生跳转，出于安全原因请直接粘贴文章正文。')
    if response.status_code >= 400:
        raise ValueError(f'公众号文章暂时无法读取（HTTP {response.status_code}），请直接粘贴正文。')
    parser = _WeChatParser()
    parser.feed(response.text)
    title = ' '.join(unescape(' '.join(parser.title)).split())
    body = ' '.join(unescape(' '.join(parser.body)).split())
    if len(body) < 150:
        raise ValueError('公众号页面未返回完整正文，可能需要登录或被平台拦截；请直接粘贴文章正文。')
    return title, body


def extract_dois(text):
    return list(dict.fromkeys(value.rstrip('.,;:，。；：)）]】') for value in
                             re.findall(r'10\.\d{4,9}/[-._;()/:A-Z0-9]+', text, re.I)))


def make_article(title, body, url=''):
    title, body, url = title.strip(), body.strip(), url.strip()
    if not title or len(title) > 300:
        raise ValueError('请填写公众号文章标题（300字以内）。')
    if len(body) < 150:
        raise ValueError('请粘贴包含研究要点的文章正文（至少150字）；只有标题和进群广告无法作为科普证据。')
    if len(body) > 45000:
        raise ValueError('正文最多45000字，请只保留本篇研究相关内容。')
    if url:
        _check_wechat_url(url)
    ident = hashlib.sha256((title + '\n' + body + '\n' + url).encode()).hexdigest()
    return {'id': 'curated:' + ident, 'title': title, 'abstract': '', 'full_text': body,
            'url': url, 'date': '', 'source': '用户导入公众号解读',
            'material_source': '公众号解读（二级资料，未核对原论文）',
            'source_kind': 'editorial', 'doi_hints': extract_dois(body),
            'venue': '', 'cited_by_count': None}


def resolve_doi(db, value, key='', provider='OpenAlex'):
    from datetime import datetime
    from zoneinfo import ZoneInfo
    from paper_search import get_search_client
    dois = extract_dois(value.strip())
    if len(dois) != 1:
        raise ValueError('请一次填写一个完整 DOI，例如 10.xxxx/xxxxx。')
    doi = dois[0]
    if provider=='PubMed':
        from literature_search import get_pubmed_search
        result=get_pubmed_search(str(db)).search('"'+doi+'"[AID]', '1800-01-01',
            datetime.now(ZoneInfo('Asia/Shanghai')).date().isoformat(), 5)
    else:
        result = get_search_client(str(db)).search(doi, '1800-01-01',
            datetime.now(ZoneInfo('Asia/Shanghai')).date().isoformat(), 1, key)
    expected = doi.lower()
    result['papers'] = [p for p in result['papers'] if
                        str(p.get('doi', '')).lower().removeprefix('https://doi.org/').removeprefix('http://doi.org/') == expected]
    return result


def render_import(db, uid, openalex_key, provider='OpenAlex'):
    import streamlit as st
    from accounts import Accounts
    account = Accounts(db)
    with st.expander('导入公众号精选文章（如热心肠日报）'):
        st.caption('可粘贴文章正文，或填写公开链接尝试提取正文；不会订阅或爬取公众号列表。建议同时填写原论文 DOI，核对摘要。')
        with st.form('curated_article_import'):
            title = st.text_input('公众号文章标题', max_chars=300)
            url = st.text_input('公众号原文链接（可选）')
            body = st.text_area('文章正文／研究要点', height=180, max_chars=45000, help='请保留研究对象、方法、结果和局限；不需要粘贴进群广告。')
            imported = st.form_submit_button('保存为视频素材')
        if imported:
            try:
                if not body.strip() and url.strip():
                    title, body = fetch_article(url)
                article = make_article(title, body, url)
                account.save_paper(uid, article)
                st.success('已保存到个人文献库，下方可勾选加入视频。材料将明确标注为公众号解读。')
                if article['doi_hints']:
                    st.info('正文发现 DOI：' + '；'.join(article['doi_hints']) + '。可在下方查回原论文。')
            except ValueError as error:
                st.warning(str(error))
            except Exception:
                st.warning('公众号链接读取失败，请直接粘贴文章正文后保存。')
        with st.form('curated_doi_lookup'):
            doi = st.text_input('原论文 DOI', placeholder='从公众号文末参考文献复制 DOI 或 doi.org 链接')
            lookup = st.form_submit_button('按 DOI 精确查回原论文')
        if lookup:
            st.session_state.curated_doi_candidate = None
            try:
                result = resolve_doi(db, doi, openalex_key, provider)
                if result.get('notice'):
                    st.warning(result['notice'])
                if result['papers']:
                    st.session_state.curated_doi_candidate = result['papers'][0]
                else:
                    st.info(provider+' 没有找到该 DOI 的论文；不会用相似标题代替。可继续使用已导入的公众号材料。')
            except ValueError as error:
                st.warning(str(error))
            except Exception as error:
                from paper_search import SearchUnavailable
                st.warning(str(error) if isinstance(error, SearchUnavailable) else '原论文查询未完成，请检查 OpenAlex 配额或网络后重试。')
        candidate = st.session_state.get('curated_doi_candidate')
        if candidate:
            st.write(candidate['title'])
            st.caption(f"{candidate.get('venue', '')} · {candidate.get('date', '')} · 被引 {candidate.get('cited_by_count', 0)}")
            st.write(candidate.get('abstract') or '没有可用摘要，暂不能直接制作视频。')
            if st.button('确认并加入原论文素材', disabled=not bool(candidate.get('abstract')), key='curated_confirm_doi'):
                paper = dict(candidate, curated_original=True)
                account.save_paper(uid, paper)
                st.success('已加入原论文素材；仍只依据可获取的摘要，不表示已阅读全文。')
    selected = []
    for paper in account.papers(uid):
        if paper.get('source_kind') != 'editorial' and not paper.get('curated_original'):
            continue
        ident = hashlib.sha256(paper['id'].encode()).hexdigest()[:20]
        label = '公众号解读 · 未核对原论文' if paper.get('source_kind') == 'editorial' else '原论文摘要'
        if st.checkbox(f"加入素材：{paper['title']}（{label}）", key='curated_pick_' + ident):
            selected.append(paper)
        with st.expander('查看素材内容与来源', expanded=False):
            st.caption(label)
            st.write(paper.get('full_text') or paper.get('abstract', ''))
            if paper.get('url'):
                st.link_button('打开来源', paper['url'], key='curated_source_' + ident)
        if st.button('移除此导入素材', key='curated_remove_' + ident):
            with account.connect() as con:
                con.execute('DELETE FROM private_papers WHERE user_id=? AND paper_id=?', (uid, paper['id']))
            st.rerun()
    return selected
