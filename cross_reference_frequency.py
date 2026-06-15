#!/usr/bin/env python3
"""
cross_reference_frequency.py — Match the frequency list against vocab_master.db.

For each lemma in frequency_list.tsv:
  - If it matches a DB word, update its frequency_rank
  - If not, add it to the gaps list

Outputs:
  - frequency_gaps.tsv  — words in the frequency list you don't have yet,
                          sorted by rank (most important first)
  - A summary of how many of your words got tagged

Run with: python cross_reference_frequency.py

After reviewing frequency_gaps.tsv, work through it in batches:
  1. Copy a batch of words into input.tsv
  2. Ask Copilot to add translations and example sentences
  3. Run input_to_db.py to import
"""

import sqlite3

DB_FILE       = '../../Vocab DB/vocab_master.db'
FREQ_FILE     = 'frequency_list.tsv'
GAPS_FILE     = 'frequency_gaps.tsv'


def load_frequency_list() -> list[tuple[int, str]]:
    """Returns list of (rank, lemma) sorted by rank."""
    entries = []
    with open(FREQ_FILE, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('rank'):
                continue
            parts = line.split('\t')
            if len(parts) == 2:
                try:
                    entries.append((int(parts[0]), parts[1]))
                except ValueError:
                    pass
    return sorted(entries, key=lambda x: x[0])


def load_db_words(conn) -> dict[str, int]:
    """
    Returns dict of normalised_lemma -> db_id for all words in the DB.
    Normalisation: lowercase, strip leading article if present.
    """
    rows = conn.execute('SELECT id, word, article FROM vocab').fetchall()
    lookup: dict[str, int] = {}
    for word_id, word, article in rows:
        # Primary key: the word as stored (no article)
        lookup[word.lower()] = word_id
        # Also index "article word" form in case frequency list includes article
        if article:
            lookup[f'{article.lower()} {word.lower()}'] = word_id
    return lookup


def main():
    # Load frequency list
    try:
        freq_list = load_frequency_list()
    except FileNotFoundError:
        print(f'❌  {FREQ_FILE} not found. Run fetch_frequency_list.py first.')
        return

    print(f'Loaded {len(freq_list)} lemmas from frequency list.')

    conn = sqlite3.connect(DB_FILE)
    db_lookup = load_db_words(conn)
    print(f'Loaded {len(db_lookup)} entries from DB.')
    print()

    matched = 0
    gaps = []

    for rank, lemma in freq_list:
        key = lemma.lower()
        if key in db_lookup:
            word_id = db_lookup[key]
            conn.execute(
                'UPDATE vocab SET frequency_rank = ? WHERE id = ? AND (frequency_rank IS NULL OR frequency_rank > ?)',
                (rank, word_id, rank)
            )
            matched += 1
        else:
            gaps.append((rank, lemma))

    conn.commit()
    conn.close()

    # Write gaps file
    with open(GAPS_FILE, 'w', encoding='utf-8') as f:
        f.write('rank\tlemma\n')
        for rank, lemma in gaps:
            f.write(f'{rank}\t{lemma}\n')

    print('─' * 50)
    print(f'Frequency list:   {len(freq_list)} lemmas')
    print(f'Matched in DB:    {matched}')
    print(f'Gaps (missing):   {len(gaps)}')
    print()
    print(f'✅  DB updated with frequency ranks.')
    print(f'📄  Gaps written to: {GAPS_FILE}')
    print()
    print('Top 20 words you are missing:')
    print()
    for rank, lemma in gaps[:20]:
        print(f'  #{rank:4d}  {lemma}')


if __name__ == '__main__':
    main()
