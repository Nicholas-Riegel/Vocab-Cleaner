#!/usr/bin/env python3
"""
db_check.py — Flag and interactively fix suspicious entries in vocab_master.db.

Checks:
  1. Verbs whose English doesn't start with "to " (likely an adjective/other)
  2. Nouns missing an article
  3. Any word with a [TODO] translation
  4. Verbs whose German doesn't look like an infinitive (doesn't end in -en/-eln/-ern)

Run with: python db_check.py
"""

import os
import re
import sqlite3
import time

DB_FILE = 'vocab_master.db'


# ── Wiktionary helpers ─────────────────────────────────────────────────────────

def get_wikitext(word):
    import httpx
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
                time.sleep(retry_after)
            else:
                print(f' [error: {type(e).__name__}: {e}]', end='')
        except Exception as e:
            if attempt == 0:
                time.sleep(5.0)
            else:
                print(f' [error: {type(e).__name__}: {e}]', end='')
    return ''


def clean_wiki(text):
    text = re.sub(r'\[\[(?:[^\]|]+\|)?([^\]|]+)\]\]', r'\1', text)
    text = re.sub(r"'{2,3}", '', text)
    text = re.sub(r'<[^>]+>', '', text)
    return text.strip()


def fetch_verb_forms(infinitive):
    """Return 'Präteritum, Partizip II' from Wiktionary, or '' if not found."""
    lookup = infinitive.replace('sich ', '').strip()
    wikitext = get_wikitext(lookup)
    if not wikitext:
        return ''
    pm = re.search(r'\|Präteritum_ich\s*=\s*(.+?)(?:\n|\||})', wikitext)
    pp = re.search(r'\|Partizip II\s*=\s*(.+?)(?:\n|\||})', wikitext)
    if not pm or not pp:
        return ''
    prateritum = clean_wiki(pm.group(1))
    partizip   = clean_wiki(pp.group(1))
    if not prateritum or not partizip:
        return ''
    return f"{prateritum}, {partizip}"


def fetch_noun_plural(word):
    """Return the Nominativ Plural form from Wiktionary, or '' if not found / no plural."""
    wikitext = get_wikitext(word)
    if not wikitext:
        return ''
    m = re.search(r'\|Nominativ Plural\s*(?:\d+\s*)?=\s*(.+?)(?:\n|\||})', wikitext)
    if not m:
        return ''
    plural = clean_wiki(m.group(1))
    for art in ('die ', 'der ', 'das '):
        if plural.lower().startswith(art):
            plural = plural[len(art):]
    if plural in ('kein Plural', '—', '-', ''):
        return 'kein Plural'
    return plural.strip()

def get_sources(conn):
    return conn.execute(
        'SELECT DISTINCT source, COUNT(*) FROM vocab GROUP BY source ORDER BY source'
    ).fetchall()


def prompt_source_chapter(conn):
    sources = get_sources(conn)
    source = None
    chapter = None

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

    if source:
        raw = input('Chapter (number, blank for all chapters): ').strip()
        if raw.isdigit():
            chapter = int(raw)

    return source, chapter

EDITABLE_FIELDS = ['english', 'word_type', 'article', 'notes', 'plural', 'forms']


# ── Checks ─────────────────────────────────────────────────────────────────────

def run_checks(conn, source=None, chapter=None):
    """Return list of (row_dict, reason) for all suspicious entries."""
    flagged = []

    query = 'SELECT id, word, article, english, word_type, plural, forms, notes, source, chapter FROM vocab'
    params = []
    conditions = []
    if source:
        conditions.append('source = ?')
        params.append(source)
    if chapter is not None:
        conditions.append('chapter = ?')
        params.append(chapter)
    if conditions:
        query += ' WHERE ' + ' AND '.join(conditions)
    query += ' ORDER BY id'

    rows = conn.execute(query, params).fetchall()

    for row in rows:
        id_, word, article, english, word_type, plural, forms, notes, source, chapter = row
        d = dict(id=id_, word=word, article=article or '', english=english or '',
                 word_type=word_type or '', plural=plural or '', forms=forms or '',
                 notes=notes or '', source=source or '', chapter=chapter)

        reasons = []

        if english == '[TODO]':
            reasons.append('missing translation ([TODO])')

        if word_type == 'verb':
            if english and not english.lower().startswith('to '):
                reasons.append(f'verb but English doesn\'t start with "to": "{english}"')
            base = (word or '').replace('sich ', '', 1).strip().split()[0]
            if base and not (base.endswith('en') or base.endswith('eln') or base.endswith('ern')):
                reasons.append(f'verb but German doesn\'t look like an infinitive: "{word}"')
            if base and base.lower().startswith('ge') and base.endswith('t'):
                reasons.append(f'verb but German starts with "ge-" and ends in "-t" — likely a past participle: "{word}"')

        if word_type == 'verb' and not (forms or '').strip():
            reasons.append('verb missing forms')

        if word_type == 'noun' and not (plural or '').strip():
            reasons.append('noun missing plural')

        if word_type == 'noun' and not (article or '').strip():
            reasons.append('noun missing article — add article or use "Word (das)" form for grammatical-gender-only')

        KNOWN_IRREGULAR_VERBS = {'sein', 'tun'}
        if word_type != 'verb' and word_type != 'past participle':
            base = word.split()[0] if word else ''
            if base.lower() in KNOWN_IRREGULAR_VERBS:
                reasons.append(f'looks like a verb but word_type is "{word_type}": "{word}"')

        for reason in reasons:
            flagged.append((d, reason))

    # Deduplicate: one entry per word id (first reason wins)
    seen = set()
    unique = []
    for d, reason in flagged:
        if d['id'] not in seen:
            seen.add(d['id'])
            unique.append((d, reason))

    return unique


# ── Display ────────────────────────────────────────────────────────────────────

def print_entry(d):
    print(f"\n  {'ID':<12} {d['id']}")
    print(f"  {'German':<12} {d['word']}")
    print(f"  {'Article':<12} {d['article'] or '—'}")
    print(f"  {'English':<12} {d['english']}")
    print(f"  {'Word type':<12} {d['word_type']}")
    print(f"  {'Plural':<12} {d['plural'] or '—'}")
    print(f"  {'Verb forms':<12} {d['forms'] or '—'}")
    print(f"  {'Notes':<12} {d['notes'] or '—'}")
    print(f"  {'Source':<12} {d['source']}  ch.{d['chapter']}")


# ── Interactive fix ────────────────────────────────────────────────────────────

def prompt_fix(conn, d):
    """Let the user edit any number of fields. Returns True if at least one change was saved."""
    any_fixed = False

    while True:
        print()
        for i, f in enumerate(EDITABLE_FIELDS, 1):
            print(f"  {i}. {f:<12} {d.get(f, '') or '—'}")
        print(f"\n  Field to edit (number or name, Enter to finish): ", end='')
        raw = input().strip().lower()

        if not raw:
            if any_fixed:
                print('\n  Final state:')
                print_entry(d)
                print('\n  Looks good? [Enter] confirm  |  e  keep editing: ', end='')
                confirm = input().strip().lower()
                if confirm == 'e':
                    continue
            break

        if raw.isdigit() and 1 <= int(raw) <= len(EDITABLE_FIELDS):
            field = EDITABLE_FIELDS[int(raw) - 1]
        elif raw in EDITABLE_FIELDS:
            field = raw
        else:
            print(f"  Unknown field '{raw}', try again.")
            continue

        current = d.get(field, '')
        print(f"  Current: {current!r}")
        print(f"  New value (Enter to cancel): ", end='')
        new_val = input().strip()

        if new_val == '':
            print('  No change.')
            continue

        conn.execute(f"UPDATE vocab SET {field} = ? WHERE id = ?", (new_val, d['id']))
        conn.commit()
        d[field] = new_val  # update local copy so display reflects change
        print(f"  ✅  Updated {field} to {new_val!r}")
        any_fixed = True

    return any_fixed


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    if not os.path.exists(DB_FILE):
        print(f'❌  {DB_FILE} not found.')
        return

    conn = sqlite3.connect(DB_FILE)
    source, chapter = prompt_source_chapter(conn)
    flagged = run_checks(conn, source=source, chapter=chapter)

    if not flagged:
        print('✅  No suspicious entries found.')
        conn.close()
        return

    print(f'Found {len(flagged)} suspicious entries.\n')
    print('Commands: [Enter] skip  |  e  edit  |  q  quit\n')

    fixed = 0
    skipped = 0

    for i, (d, reason) in enumerate(flagged, 1):
        print(f'─── {i}/{len(flagged)} ───────────────────────────────────────')
        print(f'  ⚠️  {reason}')
        print_entry(d)

        if reason in ('verb missing forms', 'noun missing plural'):
            is_verb = reason == 'verb missing forms'
            field   = 'forms' if is_verb else 'plural'
            print('  Fetching from Wiktionary...', end='', flush=True)
            found = fetch_verb_forms(d['word']) if is_verb else fetch_noun_plural(d['word'])
            time.sleep(2.0)
            if found:
                print(f'  {found}')
                print(f'\n  [Enter] save "{found}"  |  e  edit manually  |  s  skip  |  q  quit: ', end='')
                cmd = input().strip().lower()
                if cmd == 'q':
                    print('\nStopped early.')
                    break
                elif cmd == 's':
                    skipped += 1
                elif cmd == 'e':
                    changed = prompt_fix(conn, d)
                    if changed:
                        fixed += 1
                    else:
                        skipped += 1
                else:
                    conn.execute(f'UPDATE vocab SET {field} = ? WHERE id = ?', (found, d['id']))
                    conn.commit()
                    print(f'  ✅  Saved.')
                    fixed += 1
            else:
                print('  not found on Wiktionary.')
                print('\n  [Enter] skip  |  e  edit manually  |  q  quit: ', end='')
                cmd = input().strip().lower()
                if cmd == 'q':
                    print('\nStopped early.')
                    break
                elif cmd == 'e':
                    changed = prompt_fix(conn, d)
                    if changed:
                        fixed += 1
                    else:
                        skipped += 1
                else:
                    skipped += 1
            continue

        print('\n  [Enter] skip  |  e  edit  |  q  quit: ', end='')
        cmd = input().strip().lower()

        if cmd == 'q':
            print('\nStopped early.')
            break
        elif cmd == 'e':
            changed = prompt_fix(conn, d)
            if changed:
                fixed += 1
            else:
                skipped += 1
        else:
            skipped += 1

    conn.close()
    print(f'\n── Done: {fixed} fixed, {skipped} skipped ──')


if __name__ == '__main__':
    main()
