#!/usr/bin/env python3
"""
check_duplicates.py — Filter input.tsv to only words not already in the DB.

Reads input.tsv (one German word per line, optionally with tab-separated columns).
Checks each word against vocab_master.db and removes duplicates.
Overwrites input.tsv with only the new words.

Run with: python check_duplicates.py
"""

import sqlite3

DB_FILE  = '../../Vocab DB/vocab_master.db'
IN_FILE  = 'input.tsv'


def load_db_words(conn) -> set[str]:
    """Return a set of lowercase (article+word) and word-only keys."""
    rows = conn.execute('SELECT word, article FROM vocab').fetchall()
    keys = set()
    for word, article in rows:
        keys.add(word.lower())
        if article:
            keys.add(f'{article.lower()} {word.lower()}')
    return keys


def main():
    with open(IN_FILE, encoding='utf-8') as f:
        lines = [l.rstrip('\n') for l in f if l.strip()]

    conn = sqlite3.connect(DB_FILE)
    db_words = load_db_words(conn)
    conn.close()

    new_lines = []
    dupes = []

    for line in lines:
        # Extract the German part (first tab-separated column, or whole line)
        german = line.split('\t')[0].strip()
        # Normalise: strip article for lookup
        lookup = german.lower()
        for art in ('der ', 'die ', 'das '):
            if lookup.startswith(art):
                bare = lookup[len(art):]
                if bare in db_words:
                    dupes.append(german)
                    break
        else:
            if lookup in db_words:
                dupes.append(german)
            else:
                new_lines.append(line)

    with open(IN_FILE, 'w', encoding='utf-8') as f:
        f.write('\n'.join(new_lines) + '\n')

    print(f'Total input:    {len(lines)}')
    print(f'Already in DB:  {len(dupes)}')
    print(f'New words kept: {len(new_lines)}')
    if dupes:
        print('\nRemoved (duplicates):')
        for d in dupes:
            print(f'  {d}')


if __name__ == '__main__':
    main()
