"""Eksperimen yang dapat diulang; tidak mengasumsikan label relevansi tersedia."""
import json
import platform
import statistics
import time
from pathlib import Path
from sklearn.metrics.pairwise import cosine_similarity
from ir_system.engine import Engine
from ir_system.preprocessing import preprocess

ROOT = Path(__file__).resolve().parent
QUERIES = [
    ('Q1', 'pembelajaran matematika'),
    ('Q2', 'serangan drone Afghanistan'),
    ('Q3', 'Xiaomi kacamata pintar'),
    ('Q4', 'United Airlines kelinci pesawat'),
    ('Q5', 'lagu anime Naruto'),
    ('Q6', 'pendidikan ekonomi Indonesia'),
    ('Q7', 'zzzxxyynotinvocab'),
    ('Q8', 'dan yang di'),
    ('Q9', ''),
]

def run():
    output = ROOT/'results'
    output.mkdir(exist_ok=True)
    engine = Engine(ROOT/'datasets', ROOT/'cache')
    status = engine.load_or_build(progress=print)
    results = []
    for code, text in QUERIES:
        row = engine.search(text)
        timings = [engine.search(text)['seconds'] for _ in range(5)]
        row.update(code=code, median_search_seconds=statistics.median(timings))
        # Bandingkan top-5 terhadap cosine seluruh korpus; tidak ada cutoff BM25.
        if row['results']:
            scores = cosine_similarity(engine.vectorizer.transform([preprocess(text)]),engine.matrix).ravel()
            with engine.ix.searcher() as searcher:
                fields = list(searcher.all_stored_fields())
            exhaustive = sorted(((d['doc_id'],float(scores[d['row_index']])) for d in fields
                                 if scores[d['row_index']] > 0),key=lambda p:(-p[1],p[0]))[:5]
            assert [d['doc_id'] for d in row['results']] == [d[0] for d in exhaustive]
            assert all(abs(d['score']-e[1]) < 1e-12 for d,e in zip(row['results'],exhaustive))
            row['matches_exhaustive_cosine'] = True
        else:
            row['matches_exhaustive_cosine'] = None
        print(code, row['candidates'], row['results'][0]['score'] if row['results'] else 0)
        results.append(row)
    cache_times = []
    for _ in range(3):
        warm = Engine(ROOT/'datasets',ROOT/'cache')
        cache_times.append(warm.load_or_build(progress=lambda _:None)['seconds'])
    payload = dict(environment=dict(platform=platform.platform(),python=platform.python_version()),
                   metadata=engine.metadata, initial_load=status,
                   warm_load_seconds=cache_times,
                   cache_median_seconds=statistics.median(cache_times), queries=results)
    (output/'evaluation.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Hasil disimpan ke results/evaluation.json')

if __name__ == '__main__':
    run()
