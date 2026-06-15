#!/usr/bin/env python3
"""
import_examples.py — Write example sentences back to the DB.

Reads examples_needed.tsv (after Copilot has added a 4th column).
Expected format per line:
  id  |  word  |  english  |  example sentence

Lines without a 4th column are skipped.
Lines that already have an example in the DB are skipped (no overwrite).

Run with: python import_examples.py
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
        print(f'❌  {IN_FILE} not found. Run export_for_examples.py first.')
        return

    conn = sqlite3.connect(DB_FILE)

    updated = 0
    skipped_no_example = 0
    skipped_already_set = 0

    for line in lines:
        line = line.rstrip('\n')
        if not line or line.startswith('id\t'):
            continue

        parts = line.split('\t')
        if len(parts) < 4:
            skipped_no_example += 1
            continue

        word_id_str, _word, _english, example = parts[0], parts[1], parts[2], parts[3]
        example = example.strip()

        if not example:
            skipped_no_example += 1
            continue

        try:
            word_id = int(word_id_str)
        except ValueError:
            print(f'  ⚠️  Skipping bad id: {word_id_str!r}')
            continue

        # Don't overwrite an existing example
        existing = conn.execute('SELECT example FROM vocab WHERE id = ?', (word_id,)).fetchone()
        if existing and existing[0] and existing[0].strip():
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
    print(f'  Updated:              {updated}')
    print(f'  Skipped (no example): {skipped_no_example}')
    print(f'  Skipped (already set): {skipped_already_set}')


if __name__ == '__main__':
    main()
