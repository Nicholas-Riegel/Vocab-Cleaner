#!/usr/bin/env python3
"""
export.py — Export vocabulary from vocab_master.db to a tab-separated file.

Columns: German | Article | Plural | Verb Forms | English | Notes | Word Type | Source | Chapter

Usage:
  python export.py                                   # all words
  python export.py --source "Deutsch Intensiv A1"   # one source, all chapters
  python export.py --source "Deutsch Intensiv A1" --chapter 3
  python export.py --list-sources                   # show available sources
"""

import argparse
import os
import sqlite3

DB_FILE  = 'vocab_master.db'
OUT_FILE = 'output.txt'


def get_sources(conn):
    rows = conn.execute(
        'SELECT DISTINCT source, COUNT(*) FROM vocab GROUP BY source ORDER BY source'
    ).fetchall()
    return rows


def fetch_words(conn, source=None, chapter=None):
    query  = '''SELECT word, article, plural, forms, english, word_type, notes, source, chapter
                FROM vocab'''
    params = []
    conditions = []

    if source is not None:
        conditions.append('source = ?')
        params.append(source)
    if chapter is not None:
        conditions.append('chapter = ?')
        params.append(chapter)

    if conditions:
        query += ' WHERE ' + ' AND '.join(conditions)

    query += ' ORDER BY id'
    return conn.execute(query, params).fetchall()


def write_output(rows, out_file):
    header = 'German\tArticle\tPlural\tVerb Forms\tEnglish\tNotes\tWord Type\tSource\tChapter\n'
    lines  = [header]

    for word, article, plural, forms, english, word_type, notes, source, chapter in rows:
        row_chapter = str(chapter) if chapter is not None else ''
        lines.append(
            f"{word or ''}\t"
            f"{article or ''}\t"
            f"{plural or ''}\t"
            f"{forms or ''}\t"
            f"{english or ''}\t"
            f"{notes or ''}\t"
            f"{word_type or ''}\t"
            f"{source or ''}\t"
            f"{row_chapter}\n"
        )

    with open(out_file, 'w', encoding='utf-8') as f:
        f.writelines(lines)

    return len(rows)


def main():
    parser = argparse.ArgumentParser(description='Export vocab_master.db to tab-separated file.')
    parser.add_argument('--source',       help='Filter by source (exact match)')
    parser.add_argument('--chapter',      type=int, help='Filter by chapter number (requires --source)')
    parser.add_argument('--list-sources', action='store_true', help='List available sources and exit')
    parser.add_argument('--out',          default=OUT_FILE, help=f'Output file (default: {OUT_FILE})')
    args = parser.parse_args()

    if not os.path.exists(DB_FILE):
        print(f'❌  {DB_FILE} not found.')
        return

    conn = sqlite3.connect(DB_FILE)

    if args.list_sources:
        sources = get_sources(conn)
        if not sources:
            print('No sources found in database.')
        else:
            print('Available sources:')
            for src, count in sources:
                print(f'  {src!r}  ({count} words)')
        conn.close()
        return

    if args.chapter and not args.source:
        parser.error('--chapter requires --source')

    source  = args.source
    chapter = args.chapter

    # Interactive prompts when no flags were given
    if source is None:
        sources = get_sources(conn)
        if sources:
            print('Available sources:')
            for i, (src, count) in enumerate(sources, 1):
                print(f'  {i}. {src}  ({count} words)')
            raw = input('Source (number or exact name, blank for all): ').strip()
            if raw:
                if raw.isdigit() and 1 <= int(raw) <= len(sources):
                    source = sources[int(raw) - 1][0]
                else:
                    source = raw

    if source and chapter is None:
        raw = input('Chapter (number, blank for all chapters): ').strip()
        if raw.isdigit():
            chapter = int(raw)

    rows = fetch_words(conn, source=source, chapter=chapter)
    conn.close()

    if not rows:
        print('No words matched the given filters.')
        return

    count = write_output(rows, args.out)

    desc = ''
    if source:
        desc += f' | source: {source!r}'
    if chapter:
        desc += f' | chapter: {chapter}'

    print(f'✅  Written to {args.out}')
    print(f'    {count} words{desc}')


if __name__ == '__main__':
    main()
