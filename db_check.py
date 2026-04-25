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
import sqlite3

DB_FILE = 'vocab_master.db'


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
            base = word.split()[0] if word else ''
            if base and not (base.endswith('en') or base.endswith('eln') or base.endswith('ern')):
                reasons.append(f'verb but German doesn\'t look like an infinitive: "{word}"')
            if base and base.lower().startswith('ge'):
                reasons.append(f'verb but German starts with "ge-" — likely a past participle: "{word}"')

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
