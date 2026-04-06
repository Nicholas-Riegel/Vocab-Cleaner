#!/usr/bin/env python3
"""
Extracts all nouns from vocab_master.db in insertion order.
Run with: python nouns.py
Output:   nouns_excel.txt  (tab-separated: Article / German / English)
"""

import os
import sqlite3

DB_FILE  = 'vocab_master.db'
OUT_FILE = 'nouns_excel.txt'


def fetch_nouns(conn):
    return conn.execute(
        '''SELECT article, word, forms, english
           FROM vocab
           WHERE word_type = 'noun'
           ORDER BY id'''
    ).fetchall()


def build_german(word, forms):
    """Return the German display string, normalising plural info.

    Old-style rows:  word = 'Stimmung, -en',  forms = ''   → 'Stimmung, -en'
    New-style rows:  word = 'Vorschlag',       forms = 'Vorschläge' → 'Vorschlag, Vorschläge'
    No plural info:  word = 'Verwandte',       forms = ''   → 'Verwandte'
    """
    if ',' in word:
        return word          # plural already embedded
    if forms and forms.strip():
        return f"{word}, {forms.strip()}"
    return word


def write_output(rows):
    lines = ['Article\tGerman\tEnglish\n']
    for article, word, forms, english in rows:
        german  = build_german(word, forms or '')
        article = article or ''
        english = english or ''
        lines.append(f"{article}\t{german}\t{english}\n")

    with open(OUT_FILE, 'w', encoding='utf-8') as f:
        f.writelines(lines)

    total = len(rows)
    print(f"✅  Written to {OUT_FILE}")
    print(f"    {total} nouns total")


def main():
    if not os.path.exists(DB_FILE):
        print(f"❌  {DB_FILE} not found. Run migrate.py first.")
        return

    conn = sqlite3.connect(DB_FILE)
    rows = fetch_nouns(conn)
    conn.close()
    write_output(rows)


if __name__ == '__main__':
    main()
