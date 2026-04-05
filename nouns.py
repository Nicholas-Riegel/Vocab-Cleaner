#!/usr/bin/env python3
"""
Extracts all nouns from vocab_master.db, grouped by gender.
Run with: python nouns.py
Output:   nouns_by_gender.txt
"""

import os
import sqlite3

DB_FILE  = 'vocab_master.db'
OUT_FILE = 'nouns_by_gender.txt'

LABELS = {
    'der': 'DER  (masculine)',
    'die': 'DIE  (feminine)',
    'das': 'DAS  (neuter)',
}


def fetch_nouns(conn):
    rows = conn.execute(
        '''SELECT article, word, english
           FROM vocab
           WHERE word_type = 'noun'
           ORDER BY article, word COLLATE NOCASE'''
    ).fetchall()

    groups = {'der': [], 'die': [], 'das': []}
    for article, word, english in rows:
        if article in groups:
            groups[article].append((word, english or ''))
    return groups


def write_output(groups):
    total = sum(len(v) for v in groups.values())

    lines = [
        'German Nouns by Gender',
        f'{total} nouns total',
        '',
    ]

    for article in ('der', 'die', 'das'):
        nouns = groups[article]
        lines.append('=' * 55)
        lines.append(f"  {LABELS[article]}  ({len(nouns)} nouns)")
        lines.append('=' * 55)
        lines.append('')
        for word, english in nouns:
            full = f"{article} {word}"
            lines.append(f"  {full:<35}  {english}")
        lines.append('')

    with open(OUT_FILE, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    print(f"✅  Written to {OUT_FILE}")
    print(f"    {total} nouns total")
    for article in ('der', 'die', 'das'):
        print(f"    {LABELS[article]}: {len(groups[article])}")


def main():
    if not os.path.exists(DB_FILE):
        print(f"❌  {DB_FILE} not found. Run migrate.py first.")
        return

    conn = sqlite3.connect(DB_FILE)
    groups = fetch_nouns(conn)
    conn.close()
    write_output(groups)


if __name__ == '__main__':
    main()
