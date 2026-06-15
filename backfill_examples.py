#!/usr/bin/env python3
"""
backfill_examples.py — Fetch example sentences from Wiktionary for flagged words.

Targets rows where:
  - flagged = 1  (words you have trouble remembering)
  - example IS NULL or example = ''

Run with: python backfill_examples.py

Options (prompted interactively):
  - Dry run: preview what would be updated without touching the DB
  - Live run: write examples to the DB
"""

import re
import sqlite3
import time
import httpx

DB_FILE = '../../Vocab DB/vocab_master.db'

# Pause between Wiktionary requests (seconds) to be polite
REQUEST_DELAY = 2.5


# ── Wiktionary ─────────────────────────────────────────────────────────────────

def get_wikitext(word: str) -> str:
    params = {
        'action':    'parse',
        'page':      word,
        'prop':      'wikitext',
        'format':    'json',
        'redirects': '1',
    }
    headers = {'User-Agent': 'GermanVocabLearner/1.0 (personal study tool)'}
    for attempt in range(2):
        try:
            r = httpx.get(
                'https://de.wiktionary.org/w/api.php',
                params=params,
                headers=headers,
                timeout=10.0,
            )
            r.raise_for_status()
            data = r.json()
            return data.get('parse', {}).get('wikitext', {}).get('*', '')
        except httpx.HTTPStatusError as e:
            if attempt == 0:
                retry_after = int(e.response.headers.get('Retry-After', 10))
                print(f'    [rate limited, waiting {retry_after}s]')
                time.sleep(retry_after)
            else:
                print(f'    [HTTP error: {e}]')
        except Exception as e:
            if attempt == 0:
                time.sleep(5.0)
            else:
                print(f'    [error: {type(e).__name__}: {e}]')
    return ''


def clean_wiki(text: str) -> str:
    """Strip wiki markup, leaving plain text."""
    # [[link|label]] → label,  [[link]] → link
    text = re.sub(r'\[\[(?:[^\]|]+\|)?([^\]|]+)\]\]', r'\1', text)
    # {{template|...}} — remove entirely
    text = re.sub(r'\{\{[^}]*\}\}', '', text)
    # ''italic'' / '''bold'''
    text = re.sub(r"'{2,3}", '', text)
    # <ref>…</ref> and other tags
    text = re.sub(r'<ref[^>]*>.*?</ref>', '', text, flags=re.DOTALL)
    text = re.sub(r'<[^>]+>', '', text)
    # [en]-style optional ending markers e.g. ein[en]
    text = re.sub(r'\[[a-zäöüA-ZÄÖÜ]+\]', '', text)
    # collapse whitespace
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def get_example(word: str, word_type: str) -> str:
    """
    Return the first usable example sentence for this word from de.wiktionary.org.
    Returns '' if nothing found.
    """
    # For reflexive verbs strip 'sich '
    lookup = word.replace('sich ', '').strip()

    wikitext = get_wikitext(lookup)
    if not wikitext:
        return ''

    # Find the Beispiele section
    m = re.search(r'\{\{Beispiele\}\}(.*?)(?=\n==|\n\{\{[A-ZÜÄÖ]|\Z)', wikitext, re.DOTALL)
    if not m:
        return ''

    section = m.group(1)

    # Each example line looks like:  :[1] ''Word'' rest of sentence.
    # or                              :{{Beispiele fehlen}}
    examples = []
    for line in section.splitlines():
        line = line.strip()
        if not line.startswith(':'):
            continue
        # Skip meta lines like {{Beispiele fehlen}}
        if re.match(r':\s*\{\{', line):
            continue
        # Strip the leading  :[1]  or  :[1, 2]  marker
        cleaned = re.sub(r'^:\[[\d\s,]+\]\s*', '', line)
        cleaned = clean_wiki(cleaned)
        if cleaned:
            examples.append(cleaned)

    return examples[0] if examples else ''


# ── Database ───────────────────────────────────────────────────────────────────

def get_flagged_without_examples(conn):
    return conn.execute(
        """
        SELECT id, word, article, word_type, english
        FROM vocab
        WHERE flagged = 1
          AND (example IS NULL OR example = '')
        ORDER BY id
        """
    ).fetchall()


def update_example(conn, word_id: int, example: str):
    conn.execute(
        "UPDATE vocab SET example = ?, updated_at = datetime('now') WHERE id = ?",
        (example, word_id)
    )
    conn.commit()


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    conn = sqlite3.connect(DB_FILE)

    rows = get_flagged_without_examples(conn)
    if not rows:
        print('No flagged words are missing examples. Nothing to do.')
        conn.close()
        return

    print(f'Found {len(rows)} flagged word(s) without an example sentence.\n')

    dry = input('Dry run first? (Y/n): ').strip().lower() or 'y'
    dry_run = dry != 'n'

    if dry_run:
        print('\n[DRY RUN — no changes will be written]\n')
    else:
        print('\n[LIVE RUN — DB will be updated]\n')

    found = 0
    not_found = 0

    for word_id, word, article, word_type, english in rows:
        display = f'{article} {word}'.strip() if article else word
        print(f'  {display} ({word_type}) — {english}')
        print(f'    Fetching...', end='', flush=True)

        example = get_example(word, word_type)
        time.sleep(REQUEST_DELAY)

        if example:
            print(f'\n    ✓ {example}')
            if not dry_run:
                update_example(conn, word_id, example)
            found += 1
        else:
            print(' not found.')
            not_found += 1

    conn.close()

    print()
    print('─' * 50)
    print(f'Done.  Found: {found}   Not found: {not_found}')
    if dry_run and found > 0:
        print("\nRe-run and answer 'n' to dry run to write the results.")


if __name__ == '__main__':
    main()
