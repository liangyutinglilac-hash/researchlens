"""Regression coverage for public builds without the optional JCR dataset."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from accounts import Accounts
from journal_metrics import MetricStore, builtin_dataset


class OptionalDatasetTests(unittest.TestCase):
    def tearDown(self):
        builtin_dataset.cache_clear()

    def test_missing_dataset_has_complete_empty_contract(self):
        builtin_dataset.cache_clear()
        with patch('journal_metrics.Path.exists', return_value=False):
            self.assertEqual(builtin_dataset(), {'records': [], 'metadata': {}})

    def test_records_do_not_require_metadata(self):
        builtin_dataset.cache_clear()
        with patch('journal_metrics.Path.exists', return_value=True), patch(
            'journal_metrics.Path.read_text', return_value='{"records": []}'
        ):
            self.assertEqual(builtin_dataset(), {'records': [], 'metadata': {}})

    def test_switch_research_modes_and_import_personal_metrics(self):
        builtin_dataset.cache_clear()
        with tempfile.TemporaryDirectory(prefix='researchlens-metrics-') as tmp, patch.dict(
            os.environ,
            {'RESEARCHLENS_DB_PATH': str(Path(tmp)/'test.db'),
             'RESEARCHLENS_EXTERNAL_DIGEST_WORKER': '1'},
        ), patch('journal_metrics.builtin_dataset', return_value={'records': [], 'metadata': {}}):
            accounts=Accounts(os.environ['RESEARCHLENS_DB_PATH'])
            accounts.register('metrics_test', 'test-password-2026', 'test-password-2026')
            app=AppTest.from_file(str(Path(__file__).with_name('app.py')))
            app.session_state.auth_token=accounts.login('metrics_test', 'test-password-2026')
            app.run(timeout=20)
            self.assertFalse(app.exception, list(app.exception))
            for audience in ('科研入门', '专业科研', '大众科普', '科研入门'):
                next(s for s in app.selectbox if s.label=='解读对象').select(audience).run(timeout=20)
                self.assertFalse(app.exception, list(app.exception))
                if audience!='大众科普':
                    self.assertTrue(any('公开版未附带' in i.value for i in app.info))
                    self.assertIsNone(next(s for s in app.selectbox if s.label=='JIF指标年').value)
            user=accounts.user(app.session_state.auth_token)
            store=MetricStore(os.environ['RESEARCHLENS_DB_PATH'], user['id'])
            store.import_rows([{'issn':'1234-5679', 'journal':'Regression test journal',
                                'jif':2.5, 'year':2025, 'source':'Synthetic test fixture'}])
            app.run(timeout=20)
            self.assertFalse(app.exception, list(app.exception))
            self.assertEqual(next(s for s in app.selectbox if s.label=='JIF指标年').value, 2025)
            self.assertEqual(store.eligible(2025, 2, 3), ['1234-5679'])


if __name__=='__main__':
    unittest.main()
