#!/usr/bin/env python3
"""Jalankan python main.py untuk menu interaktif."""
import argparse
import csv
import json
import sys
from pathlib import Path
from ir_system.engine import Engine, SOURCES

BASE = Path(__file__).resolve().parent

def display(result):
    print(f"\nQuery: {result['query']}\nToken: {result['normalized_query']}")
    print(f"Kandidat: {result['candidates']:,} | Waktu pencarian: {result['seconds']:.4f} s")
    if not result['results']:
        print(result.get('message', 'Tidak ada dokumen cocok.'))
    for rank, row in enumerate(result['results'], 1):
        print(f"\n{rank}. [{row['source']}] {row['title']}")
        print(f"   ID: {row['doc_id']} | Cosine: {row['score']:.6f}\n   {row['snippet']}...")

def interactive(engine):
    while True:
        print('\n=== INFORMATION RETRIEVAL SYSTEM ===\n[1] Load & Index Dataset\n[2] Search Query\n[3] Exit\n====================================')
        choice = input('Pilih menu: ').strip()
        if choice == '3':
            print('Program selesai.')
            return
        try:
            if choice == '1':
                status = engine.load_or_build()
                print(f"{'Cache dimuat' if status['cache_hit'] else 'Indeks selesai'}: "
                      f"{status['documents']:,} dokumen dalam {status['seconds']:.3f} s")
            elif choice == '2':
                if engine.ix is None:
                    print('Pilih menu 1 terlebih dahulu.')
                    continue
                display(engine.search(input('Masukkan query: ')))
            else:
                print('Pilihan tidak valid.')
        except (ValueError, OSError, csv.Error) as error:
            print(f'Gagal: {error}')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, default=BASE/'datasets')
    parser.add_argument('--cache-dir', type=Path, default=BASE/'cache')
    sub = parser.add_subparsers(dest='command')
    build = sub.add_parser('index', help='Bangun atau muat cache')
    build.add_argument('--rebuild', action='store_true')
    search = sub.add_parser('search', help='Cari dan ranking dengan cosine')
    search.add_argument('query')
    search.add_argument('--top-k', type=int, default=5)
    search.add_argument('--source', choices=SOURCES)
    search.add_argument('--json', action='store_true')
    sub.add_parser('stats', help='Statistik indeks')
    args = parser.parse_args()
    engine = Engine(args.data_dir, args.cache_dir)
    try:
        if args.command is None:
            interactive(engine)
        elif args.command == 'index':
            print(json.dumps(engine.load_or_build(force=args.rebuild), indent=2))
        elif args.command == 'stats':
            engine.load_or_build(progress=lambda _: None)
            print(json.dumps(engine.metadata, indent=2))
        else:
            if args.top_k < 1:
                parser.error('--top-k minimal 1')
            engine.load_or_build(progress=lambda msg: print(msg, file=sys.stderr))
            result = engine.search(args.query, args.top_k, args.source)
            if args.json:
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                display(result)
    except (ValueError, OSError, csv.Error) as error:
        print(f'Gagal: {error}', file=sys.stderr)
        return 1
    except (KeyboardInterrupt, EOFError):
        print('\nProgram dihentikan.')
    return 0

if __name__ == '__main__':
    sys.exit(main())
