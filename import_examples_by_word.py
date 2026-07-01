#!/usr/bin/env python3
"""
import_examples_by_word.py — Import example sentences by looking up the German word.

Reads input.tsv with format:
  word  |  english  |  example  |  [optional notes]

Looks up each word in the database and updates the example column.
"""

import sqlite3
from datetime import datetime, timezone

DB_FILE  = '../../Vocab DB/vocab_master.db'
IN_FILE  = 'input.tsv'


def now():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S')


def main():
    try:
        with open(IN_FILE, encoding='utf-8') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f'❌  {IN_FILE} not found.')
        return

    conn = sqlite3.connect(DB_FILE)

    updated = 0
    skipped_no_example = 0
    skipped_already_set = 0
    not_found = 0

    for line_num, line in enumerate(lines, 1):
        line = line.rstrip('\n')
        if not line:
            continue

        parts = line.split('\t')
        if len(parts) < 3:
            skipped_no_example += 1
            continue

        german_word = parts[0].strip()
        example = parts[2].strip()

        if not example:
            skipped_no_example += 1
            continue

        # Extract article and word if present (e.g., "die Neugier" -> article="die", word="Neugier")
        article = None
        word = german_word
        
        for art in ('der ', 'die ', 'das ', 'sich '):
            if german_word.startswith(art):
                article = art.strip()
                word = german_word[len(art):].strip()
                break

        # Try to find the word in the database
        if article:
            row = conn.execute(
                'SELECT id, example FROM vocab WHERE word = ? AND article = ?',
                (word, article)
            ).fetchone()
        else:
            row = conn.execute(
                'SELECT id, example FROM vocab WHERE word = ?',
                (word,)
            ).fetchone()

        if not row:
            print(f'  ⚠️  Line {line_num}: Word not found: {german_word!r}')
            not_found += 1
            continue

        word_id, existing_example = row

        # Don't overwrite an existing example
        if existing_example and existing_example.strip():
            skipped_already_set += 1
            continue

        conn.execute(
            "UPDATE vocab SET example = ?, updated_at = ? WHERE id = ?",
            (example, now(), word_id)
        )
        updated += 1

    conn.commit()
    conn.close()

    print(f'Done.')
    print(f'  Updated:               {updated}')
    print(f'  Skipped (no example):  {skipped_no_example}')
    print(f'  Skipped (already set): {skipped_already_set}')
    print(f'  Not found in DB:       {not_found}')


if __name__ == '__main__':
    main()
