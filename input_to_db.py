#!/usr/bin/env python3
"""
input_to_db.py — German Vocabulary → Database

Reads input.txt and inserts words into vocab_master.db.

Input file format (one entry per line, tab-separated):
  aufwachsen\tto grow up, to be raised
  die Stimmung, -en\tmood, atmosphere
  schüchtern\tshy

Lines without a tab-separated translation are inserted with [TODO].
A summary of [TODO] entries is printed at the end of each run.

Run with: python input_to_db.py
"""

import os
import re
import sqlite3
import time
from datetime import datetime, timezone

INPUT_FILE = 'input.tsv'
DB_FILE    = 'vocab_master.db'


def now():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S')


# ── Database ───────────────────────────────────────────────────────────────────

def get_connection():
    return sqlite3.connect(DB_FILE)


def init_db(conn):
    conn.execute('''
        CREATE TABLE IF NOT EXISTS vocab (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            word      TEXT    NOT NULL,
            article   TEXT,
            english   TEXT,
            word_type  TEXT,
            plural     TEXT    DEFAULT '',
            forms      TEXT    DEFAULT '',
            notes      TEXT    DEFAULT '',
            source     TEXT,
            chapter    INTEGER,
            created_at TEXT,
            updated_at TEXT
        )
    ''')
    conn.commit()


def ensure_extra_columns(conn):
    for col, default in [('forms', ''), ('plural', ''), ('notes', '')]:
        try:
            conn.execute(f"ALTER TABLE vocab ADD COLUMN {col} TEXT DEFAULT '{default}'")
            conn.commit()
        except sqlite3.OperationalError:
            pass  # Column already exists


def count_words(conn):
    return conn.execute('SELECT COUNT(*) FROM vocab').fetchone()[0]


def word_exists(conn, base_word, article):
    """
    Checks for a duplicate using the base word, ignoring plural notation.
    e.g. 'Stimmung' matches an existing 'Stimmung, -en' row.
    """
    if article:
        row = conn.execute(
            "SELECT 1 FROM vocab WHERE (word = ? OR word LIKE ?) AND article = ?",
            (base_word, base_word + ', %', article)
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT 1 FROM vocab WHERE (word = ? OR word LIKE ?) AND article IS NULL",
            (base_word, base_word + ', %')
        ).fetchone()
    return row is not None


def word_is_todo(conn, base_word, article):
    """Returns True if the word exists in the DB with a [TODO] translation."""
    if article:
        row = conn.execute(
            "SELECT 1 FROM vocab WHERE (word = ? OR word LIKE ?) AND article = ? AND english = '[TODO]'",
            (base_word, base_word + ', %', article)
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT 1 FROM vocab WHERE (word = ? OR word LIKE ?) AND article IS NULL AND english = '[TODO]'",
            (base_word, base_word + ', %')
        ).fetchone()
    return row is not None


def update_translation(conn, base_word, article, english, notes):
    ts = now()
    if article:
        conn.execute(
            "UPDATE vocab SET english = ?, notes = CASE WHEN notes = '' THEN ? ELSE notes END, updated_at = ? WHERE (word = ? OR word LIKE ?) AND article = ? AND english = '[TODO]'",
            (english, notes, ts, base_word, base_word + ', %', article)
        )
    else:
        conn.execute(
            "UPDATE vocab SET english = ?, notes = CASE WHEN notes = '' THEN ? ELSE notes END, updated_at = ? WHERE (word = ? OR word LIKE ?) AND article IS NULL AND english = '[TODO]'",
            (english, notes, ts, base_word, base_word + ', %')
        )
    conn.commit()


def insert_word(conn, word, article, english, word_type, plural, forms, notes, source, chapter):
    ts = now()
    conn.execute(
        '''INSERT INTO vocab (word, article, english, word_type, plural, forms, notes, source, chapter, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (word, article, english, word_type, plural, forms, notes, source, chapter, ts, ts)
    )
    conn.commit()


# ── Translation helpers ────────────────────────────────────────────────────────

def normalize_translation(english, word_type):
    if word_type == 'noun':
        if english.lower().startswith('the '):
            return english[4:]
    elif word_type == 'verb':
        if not english.lower().startswith('to '):
            return 'to ' + english
    return english


# ── Entry parsing ──────────────────────────────────────────────────────────────

def unsquish(text):
    """
    Fix run-together article+noun copied from some sources:
      'dieStimmung'  → 'die Stimmung'
      'derZahn, Zähne' → 'der Zahn, Zähne'
    Already-spaced words are returned unchanged.
    """
    for article in ('der', 'die', 'das'):
        if text.startswith(article) and len(text) > len(article):
            rest = text[len(article):]
            if rest[0].isupper():
                return f"{article} {rest}"
    return text


def parse_entry(text):
    """
    Returns (article, word, inline_forms, word_type, provided_translation).

    The German part is separated from the English translation by a tab:
      'die Stimmung, -en\tmood, atmosphere' → ('die', 'Stimmung', '-en', 'noun', 'mood, atmosphere')
      'aufwachsen\tto grow up'              → (None, 'aufwachsen', '', 'verb', 'to grow up')
      'aufwachsen'                           → (None, 'aufwachsen', '', 'verb', None)

    Noun plural / verb forms can be included inline in the German part:
      'die Stimmung, -en'    → word='Stimmung', inline_forms='-en'
      'fahren, gefahren'     → word='fahren',   inline_forms='gefahren'
      'Deutschland (das)'    → article='(das)', word='Deutschland'  (gender known, article not used in practice)
    """
    provided_translation = None
    provided_notes = None
    if '\t' in text:
        parts = text.split('\t', 2)
        text = parts[0].strip()
        provided_translation = parts[1].strip() or None if len(parts) > 1 else None
        provided_notes = parts[2].strip() or None if len(parts) > 2 else None

    # Noun: line starts with a grammatical article
    for article in ('der', 'die', 'das'):
        if text.lower().startswith(article + ' '):
            rest = text[len(article) + 1:]
            if ', ' in rest:
                noun, inline = rest.split(', ', 1)
                return article, noun.strip(), inline.strip(), 'noun', provided_translation, provided_notes
            return article, rest.strip(), '', 'noun', provided_translation, provided_notes

    # Noun with parenthetical article: 'Deutschland (das)' — gender known but article not used in practice
    m = re.match(r'^(.+?)\s+\((der|die|das)\)$', text, re.IGNORECASE)
    if m:
        word_part = m.group(1).strip()
        paren_article = f'({m.group(2).lower()})'
        return paren_article, word_part, '', 'noun', provided_translation, provided_notes

    # Verb with inline irregular forms: 'fahren, fuhr, gefahren'
    if ', ' in text:
        first = text.split(',')[0].strip()
        if ' ' not in first and re.search(r'(en|ern|ieren)$', first):
            parts = [p.strip() for p in text.split(', ')]
            return None, parts[0], ', '.join(parts[1:]), 'verb', provided_translation, provided_notes

    if text.startswith('sich '):
        return None, text, '', 'verb', provided_translation, provided_notes
    if ' ' in text:
        return None, text, '', 'phrase', provided_translation, provided_notes
    if re.search(r'(en|eln|ern|ieren)$', text):
        return None, text, '', 'verb', provided_translation, provided_notes
    # Verbs ending in -n that don't match the pattern above (sein, tun)
    if text.lower() in ('sein', 'tun'):
        return None, text, '', 'verb', provided_translation, provided_notes
    return None, text, '', 'other', provided_translation, provided_notes


# ── Wiktionary lookups ─────────────────────────────────────────────────────────

def get_wikitext(word):
    try:
        import httpx
        r = httpx.get(
            'https://de.wiktionary.org/w/api.php',
            params={
                'action': 'parse',
                'page':   word,
                'prop':   'wikitext',
                'format': 'json',
                'redirects': '1',
            },
            headers={'User-Agent': 'GermanVocabLearner/1.0 (personal study tool)'},
            timeout=10.0,
        )
        data = r.json()
        return data.get('parse', {}).get('wikitext', {}).get('*', '')
    except Exception:
        return ''


def clean_wiki(text):
    text = re.sub(r'\[\[(?:[^\]|]+\|)?([^\]|]+)\]\]', r'\1', text)
    text = re.sub(r"'{2,3}", '', text)
    text = re.sub(r'<[^>]+>', '', text)
    return text.strip()


def get_noun_plural(word):
    """Return the Nominativ Plural form, or '' if not found / no plural."""
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
        return ''
    return plural.strip()


def get_verb_forms(infinitive):
    """
    Return 'Präteritum, Partizip II' for irregular verbs, or '' for regular ones.
    """
    lookup   = infinitive.replace('sich ', '').strip()
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
    stem       = re.sub(r'(en|ern|eln)$', '', lookup)
    is_regular = prateritum in (stem + 'te', stem + 'ete')
    if is_regular:
        return ''
    return f"{prateritum}, {partizip}"


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    if not os.path.exists(DB_FILE):
        print(f"❌  {DB_FILE} not found. Run this script once with an empty input.txt to create it, or check you are in the right directory.")
        return
    if not os.path.exists(INPUT_FILE):
        print(f"❌  {INPUT_FILE} not found.")
        return

    print("📖  German Vocabulary → Database")
    print("─" * 40)

    translations_ok = input("Are translations provided for all words? (Y/n): ").strip().lower() or "y"
    if translations_ok != 'y':
        print("Please add translations to input.txt and re-run.")
        return

    print()

    conn = get_connection()
    init_db(conn)
    ensure_extra_columns(conn)

    print(f"📚  {count_words(conn)} words currently in database\n")

    source = 'Reading'
    print(f"📗  Source: {source}")

    chapter_raw = input("Chapter number: ").strip()
    try:
        chapter = int(chapter_raw)
    except ValueError:
        print("❌  Chapter must be a number.")
        conn.close()
        return

    print()

    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        lines = [l.strip() for l in f if l.strip()]

    added   = 0
    skipped = 0
    todos   = []

    for raw_line in lines:
        # Unsquish run-together article+noun
        line = unsquish(raw_line)

        # Strip trailing underscores (copy-paste artifact from some book formats)
        if '_' in line:
            line = line.split('_')[0].strip()
        if not line:
            continue

        article, word, inline_forms, word_type, provided_translation, provided_notes = parse_entry(line)
        display = f"{article} {word}" if article else word

        # ── Duplicate ──────────────────────────────────────────────────────────
        if word_exists(conn, word, article):
            if provided_translation and word_is_todo(conn, word, article):
                english = normalize_translation(provided_translation, word_type)
                notes = provided_notes or ''
                update_translation(conn, word, article, english, notes)
                print(f"   ✏️   Updated TODO: {display}  →  {english}")
                added += 1
            else:
                print(f"   ⏭️   Duplicate (skipped): {display}")
                skipped += 1
            continue

        # ── New word ───────────────────────────────────────────────────────────
        print(f"   {display}", end='')

        # Look up grammatical forms via Wiktionary
        plural = ''
        forms = ''
        notes = provided_notes or ''
        if word_type == 'noun':
            if inline_forms:
                plural = inline_forms
            else:
                plural = get_noun_plural(word)
                time.sleep(0.3)
            print(f"  [{plural or '—'}]", end='')

        elif word_type == 'verb':
            if inline_forms:
                forms = inline_forms
            else:
                forms = get_verb_forms(word)
                time.sleep(0.3)
            if forms:
                print(f"  [{forms}]", end='')

        # Translation
        if provided_translation:
            english = normalize_translation(provided_translation, word_type)
            print(f"  →  {english}")
        else:
            english = '[TODO]'
            todos.append(display)
            print(f"  →  ⚠️  [TODO]")

        insert_word(conn, word, article, english, word_type, plural, forms, notes, source, chapter)
        added += 1

    conn.close()

    print(f"\n{'─' * 40}")
    print(f"✅  Done.")
    print(f"    Added:   {added}  |  Duplicates: {skipped}")
    print(f"    Total in database: {count_words(get_connection())}")

    if todos:
        print(f"\n⚠️   {len(todos)} word(s) need a translation:")
        for t in todos:
            print(f"       • {t}")
        print("    Add translations to input.txt and re-run.")


if __name__ == '__main__':
    main()
