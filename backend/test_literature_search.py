"""Offline regression tests: real provider contracts, no paid API calls."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from literature_search import PubMedSearch, prepare_query
from paper_search import SearchUnavailable

XML=b'''<PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>123</PMID><Article><ArticleTitle>Gut microbiome and type 2 diabetes</ArticleTitle><Journal><ISSN>1234-5679</ISSN><Title>Test Journal</Title><JournalIssue><PubDate><Year>2025</Year><Month>10</Month><Day>01</Day></PubDate></JournalIssue></Journal><Abstract><AbstractText>Test evidence, not a real paper.</AbstractText></Abstract></Article><MedlineJournalInfo><ISSNLinking>1234-5679</ISSNLinking></MedlineJournalInfo></MedlineCitation><PubmedData><ArticleIdList><ArticleId IdType="doi">10.0000/test</ArticleId></ArticleIdList></PubmedData></PubmedArticle></PubmedArticleSet>'''


class RetrievalTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.post=MagicMock()
        self.now=1000.
        self.client=PubMedSearch(Path(self.tmp.name)/'test.db',post=self.post,clock=lambda:self.now)
        self.sleep=patch('literature_search.time.sleep');self.sleep.start()

    def tearDown(self):
        self.sleep.stop();self.tmp.cleanup()

    def responses(self):
        search=MagicMock(status_code=200);search.json.return_value={'esearchresult':{'count':'1','idlist':['123']}}
        fetch=MagicMock(status_code=200,content=XML)
        self.post.side_effect=[search,fetch]

    def test_records_journal_filter_cache_and_no_model_credentials(self):
        self.responses()
        result=self.client.search('gut microbiome AND diabetes','2025-01-01','2026-10-19',8,['1234-5679'])
        paper=result['papers'][0]
        self.assertEqual(paper['id'],'pubmed:123')
        self.assertEqual(paper['source'],'PubMed')
        self.assertEqual(paper['issns'],['1234-5679'])
        self.assertNotIn('cited_by_count',paper)
        params=self.post.call_args_list[0].kwargs['data']
        self.assertIn('"1234-5679"[ISSN]',params['term'])
        self.assertEqual(params['datetype'],'pdat')
        self.assertNotIn('api_key',params)
        cached=self.client.search('gut microbiome AND diabetes','2025-01-01','2026-10-19',8,['1234-5679'])
        self.assertEqual(cached['mode'],'cache');self.assertEqual(self.post.call_count,2)

    def test_rate_limit_cooldown_no_retry_and_stale_cache(self):
        self.responses();self.client.search('diabetes','2025-01-01','2026-10-19',8)
        self.now+=901
        self.post.side_effect=None;self.post.return_value=MagicMock(status_code=429,headers={'Retry-After':'120'})
        result=self.client.search('diabetes','2025-01-01','2026-10-19',8)
        self.assertEqual(result['mode'],'stale')
        calls=self.post.call_count
        with self.assertRaises(SearchUnavailable):self.client.search('different','2025-01-01','2026-10-19',8)
        self.assertEqual(self.post.call_count,calls)

    def test_chinese_without_key_and_untranslatable_topic(self):
        query,_=prepare_query('肠道微生物与2型糖尿病',optimize=False)
        self.assertIn('gut microbiota',query);self.assertIn('type 2 diabetes',query)
        with self.assertRaises(SearchUnavailable):prepare_query('未收录的新中文主题',optimize=False)

    def test_model_query_is_only_used_for_retrieval(self):
        client=MagicMock();client.chat.completions.create.return_value.choices[0].message.content='{"query":"gut microbiome AND type 2 diabetes"}'
        with patch('openai.OpenAI',return_value=client) as model:
            query,_=prepare_query('肠道微生物与糖尿病','test-key-for-unit-test','test-model','https://example.invalid/v1')
            self.assertEqual(query,'gut microbiome AND type 2 diabetes')
            self.assertEqual(model.call_args.kwargs['api_key'],'test-key-for-unit-test')
        self.assertEqual(self.post.call_count,0)

    def test_future_dates_not_returned(self):
        search=MagicMock(status_code=200);search.json.return_value={'esearchresult':{'count':'1','idlist':['123']}}
        self.post.side_effect=[search,MagicMock(status_code=200,content=XML.replace(b'<Year>2025</Year>',b'<Year>2030</Year>'))]
        self.assertEqual(self.client.search('diabetes','2025-01-01','2026-10-19',8)['papers'],[])

    def test_empty_error_fields_are_not_errors(self):
        search=MagicMock(status_code=200)
        search.json.return_value={'esearchresult':{'count':'1','idlist':['123'],
            'errorlist':{'phrasesnotfound':[],'fieldsnotfound':[]},
            'warninglist':{'quotedphrasesnotfound':['"not-indexed-issn"']}}}
        self.post.side_effect=[search,MagicMock(status_code=200,content=XML)]
        result=self.client.search('diabetes','2025-01-01','2026-10-19',8)
        self.assertEqual(len(result['papers']),1)
        self.assertIn('ISSN',result['notice'])

    def test_populated_error_fields_are_reported(self):
        response=MagicMock(status_code=200)
        response.json.return_value={'esearchresult':{'idlist':[], 'errorlist':{'fieldsnotfound':['badfield']}}}
        self.post.return_value=response
        with self.assertRaisesRegex(SearchUnavailable,'未接受检索式'):
            self.client.search('diabetes[badfield]','2025-01-01','2026-10-19',8)


if __name__=='__main__':unittest.main()
