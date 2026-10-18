import csv
import math
import tempfile
import unittest
from pathlib import Path
from ir_system.engine import Engine, SOURCES
from ir_system.preprocessing import preprocess

class RetrievalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.data = self.root/'datasets'
        for source in SOURCES:
            folder = self.data/source
            folder.mkdir(parents=True)
            with (folder/(source.replace('-', '_')+'.csv')).open('w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['judul','konten'])
                writer.writerow(['apel', 'apel jeruk'])
                writer.writerow(['jeruk', 'pisang'])
                writer.writerow(['dan', 'yang di'])
        self.engine = Engine(self.data, self.root/'cache')
        self.status = self.engine.load_or_build(progress=lambda _: None)

    def test_preprocessing(self):
        self.assertEqual(preprocess('<b>Di</b> SEKOLAH &amp; café 2026, A!'), 'sekolah café')

    def test_exact_cosine_and_deterministic_tie(self):
        found = self.engine.search('apel')
        self.assertEqual(found['candidates'], 5)
        self.assertEqual(len(found['results']), 5)
        self.assertEqual(found['results'][0]['doc_id'], 'etd-ugm:1')
        self.assertAlmostEqual(found['results'][0]['score'], 2/math.sqrt(5))

    def test_ranking_equals_entire_corpus(self):
        from sklearn.metrics.pairwise import cosine_similarity
        for query in ['apel', 'jeruk pisang', 'apel jeruk jeruk', 'apel zzzunknown']:
            all_scores = cosine_similarity(self.engine.vectorizer.transform([preprocess(query)]),
                                           self.engine.matrix).ravel()
            with self.engine.ix.searcher() as s:
                fields = list(s.all_stored_fields())
            expected = sorted([(d['doc_id'], float(all_scores[d['row_index']])) for d in fields
                               if all_scores[d['row_index']] > 0], key=lambda p: (-p[1], p[0]))
            actual = self.engine.search(query, top_k=100)['results']
            self.assertEqual([a['doc_id'] for a in actual], [a[0] for a in expected])
            for a,b in zip(actual,expected):
                self.assertAlmostEqual(a['score'],b[1])

    def test_empty_oov_stopwords(self):
        for q in ['', 'dan yang di', 'zzzxxyynotinvocab', '12345 !!!']:
            self.assertEqual(self.engine.search(q)['results'], [])

    def test_source_filter(self):
        found = self.engine.search('apel', source='tempo')
        self.assertEqual(found['candidates'], 1)
        self.assertEqual(found['results'][0]['source'], 'tempo')

    def test_cache_reuse_and_invalidation(self):
        self.assertFalse(self.status['cache_hit'])
        self.assertTrue(self.engine.load_or_build(progress=lambda _: None)['cache_hit'])
        path = self.data/'tempo'/'tempo.csv'
        with path.open('a', encoding='utf-8') as f:
            f.write('mangga,pepaya\n')
        updated = self.engine.load_or_build(progress=lambda _: None)
        self.assertFalse(updated['cache_hit'])
        self.assertEqual(updated['documents'], 11)
        self.assertEqual(self.engine.search('mangga')['results'][0]['doc_id'], 'tempo:4')

    def test_missing_and_bad_schema(self):
        file = self.data/'tempo'/'tempo.csv'
        file.unlink()
        with self.assertRaisesRegex(ValueError, 'belum lengkap'):
            self.engine.load_or_build(progress=lambda _: None)
        file.write_text('salah,kolom\na,b\n', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'kolom judul'):
            self.engine.load_or_build(progress=lambda _: None)
        self.assertFalse((self.root/'cache'/'BUILD.lock').exists())
        self.assertTrue(self.engine.generation.exists())

    def test_validation(self):
        for kwargs in [dict(top_k=0),dict(source='invalid')]:
            with self.assertRaises(ValueError):
                self.engine.search('apel',**kwargs)

    def test_skip_and_bow(self):
        self.assertEqual(self.status['documents'],10)
        self.assertEqual(sum(self.status['skipped'].values()),5)
        idx = self.engine.vectorizer.vocabulary_['apel']
        self.assertEqual(self.engine.matrix[0,idx],2)

if __name__ == '__main__':
    unittest.main()
