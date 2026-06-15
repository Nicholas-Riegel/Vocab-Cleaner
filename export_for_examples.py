#!/usr/bin/env python3
"""
export_for_examples.py — Export flagged words that need example sentences.

Writes examples_needed.tsv with columns:
  id  |  word (with article)  |  english

Paste the contents into a Copilot conversation and ask for example sentences.
Copilot should add a 4th tab-separated column with the example.
Then run import_examples.py to write them to the DB.
"""

import sqlite3

DB_FILE  = '../../Vocab DB/vocab_master.db'
OUT_FILE = 'input.tsv'


def main():
    conn = sqlite3.connect(DB_FILE)

    rows = conn.execute(
        """
        SELECT id, word, article, word_type, english
        FROM vocab
        WHERE flagged = 1
          AND (example IS NULL OR TRIM(example) = '')
        ORDER BY id
        """
    ).fetchall()
    conn.close()

    if not rows:
        print('No flagged words are missing examples.')
        return

    lines = ['id\tword\tenglish\n']
    for word_id, word, article, word_type, english in rows:
        display = f'{article} {word}'.strip() if article else word
        lines.append(f'{word_id}\t{display}\t{english}\n')

    with open(OUT_FILE, 'w', encoding='utf-8') as f:
        f.writelines(lines)

    print(f'Exported {len(rows)} words to {OUT_FILE}')
    print('Paste the file contents to Copilot and ask it to add example sentences as a 4th column.')
    print('Then run: python import_examples.py')


if __name__ == '__main__':
    main()
