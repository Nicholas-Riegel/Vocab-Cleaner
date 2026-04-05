#!/usr/bin/env python3
"""
Process german_vocab_raw.txt (words encountered in reading) into vocab_master.db.
Looks up plural forms for nouns and irregular conjugations for verbs via Wiktionary.
Run with: python process_reading.py
"""

import os
import re
import sqlite3
import time

DB_FILE  = 'vocab_master.db'
RAW_FILE = 'german_vocab_raw.txt'
SOURCE   = 'reading'
CHAPTER  = 0

# ── Corrections ────────────────────────────────────────────────────────────────
# Maps the raw squished line from the file → corrected form (before any other processing)
CORRECTIONS = {
    'derBekante':         'der Bekannte',
    'derKunde/Kundin':    'der Kunde',
    'derVermeiter/terin': 'der Vermieter',
    'überweissen':        'überweisen',
    'dasPacket':          'das Paket',
    'überalle':           'überall',
}

# ── Database ───────────────────────────────────────────────────────────────────

def get_connection():
    return sqlite3.connect(DB_FILE)


def ensure_forms_column(conn):
    """Add the forms column if it doesn't exist yet."""
    try:
        conn.execute("ALTER TABLE vocab ADD COLUMN forms TEXT DEFAULT ''")
        conn.commit()
        print("  + Added 'forms' column to database")
    except sqlite3.OperationalError:
        pass  # Column already exists


def word_exists(conn, base_word, article):
    """
    Check for duplicates using the base noun (without plural notation).
    Handles both 'Stimmung' and 'Stimmung, -en' already in the DB.
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


def insert_word(conn, word, article, english, word_type, forms, source, chapter):
    conn.execute(
        '''INSERT INTO vocab (word, article, english, word_type, forms, source, chapter)
           VALUES (?, ?, ?, ?, ?, ?, ?)''',
        (word, article, english, word_type, forms, source, chapter)
    )
    conn.commit()


# ── Entry parsing ──────────────────────────────────────────────────────────────

def unsquish(text):
    """
    'derVerwandte'     → 'der Verwandte'
    'dieKette'         → 'die Kette'
    'derZahn, Zähne'   → 'der Zahn, Zähne'
    'der Bekannte'     → 'der Bekannte'  (already has space, unchanged)
    """
    for article in ('der', 'die', 'das'):
        if text.startswith(article) and len(text) > len(article):
            rest = text[len(article):]
            if rest and rest[0].isupper():  # squished: next char is uppercase
                return f"{article} {rest}"
    return text


def parse_entry(text):
    """
    Returns (article, word, inline_forms, word_type).

    'der Zahn, Zähne'     → ('der', 'Zahn',     'Zähne',    'noun')
    'die Kette'           → ('die', 'Kette',     '',         'noun')
    'bewerben, beworben'  → (None,  'bewerben',  'beworben', 'verb')
    'sich verspäten'      → (None,  'sich verspäten', '',    'verb')
    'aufwachsen'          → (None,  'aufwachsen', '',        'verb')
    'Bescheid sagen'      → (None,  'Bescheid sagen', '',   'phrase')
    'erlaubt'             → (None,  'erlaubt',   '',        'other')
    """
    # Noun: starts with article + space
    for article in ('der', 'die', 'das'):
        if text.lower().startswith(article + ' '):
            rest = text[len(article) + 1:]
            if ', ' in rest:
                noun, inline = rest.split(', ', 1)
                return article, noun.strip(), inline.strip(), 'noun'
            return article, rest.strip(), '', 'noun'

    # Verb with inline forms: 'bewerben, beworben' (no space in first part)
    if ', ' in text:
        first = text.split(',')[0].strip()
        if ' ' not in first and re.search(r'(en|ern|ieren)$', first):
            parts = [p.strip() for p in text.split(', ')]
            return None, parts[0], ', '.join(parts[1:]), 'verb'

    if text.startswith('sich '):
        return None, text, '', 'verb'
    if ' ' in text:
        return None, text, '', 'phrase'
    if re.search(r'(en|ern|ieren)$', text):
        return None, text, '', 'verb'
    return None, text, '', 'other'


# ── Wiktionary ─────────────────────────────────────────────────────────────────

def get_wikitext(word):
    """Fetch German wikitext for a word from de.wiktionary.org."""
    try:
        import httpx
        r = httpx.get(
            'https://de.wiktionary.org/w/api.php',
            params={
                'action': 'parse',
                'page': word,
                'prop': 'wikitext',
                'format': 'json',
                'redirects': '1',
            },
            headers={'User-Agent': 'GermanVocabLearner/1.0 (personal study tool)'},
            timeout=10.0
        )
        data = r.json()
        return data.get('parse', {}).get('wikitext', {}).get('*', '')
    except Exception:
        return ''


def clean_wiki(text):
    """Strip basic wiki markup from a field value."""
    text = re.sub(r'\[\[(?:[^\]|]+\|)?([^\]|]+)\]\]', r'\1', text)
    text = re.sub(r"'{2,3}", '', text)
    text = re.sub(r'<[^>]+>', '', text)
    return text.strip()


def get_noun_plural(word):
    """
    Look up the Nominativ Plural for a German noun on de.wiktionary.org.
    Returns the bare plural (e.g. 'Zähne'), or '' if not found.
    """
    wikitext = get_wikitext(word)
    if not wikitext:
        return ''

    m = re.search(r'\|Nominativ Plural\s*(?:\d+\s*)?=\s*(.+?)(?:\n|\||})', wikitext)
    if not m:
        return ''

    plural = clean_wiki(m.group(1))

    # Strip article prefix that Wiktionary includes
    for art in ('die ', 'der ', 'das '):
        if plural.lower().startswith(art):
            plural = plural[len(art):]

    # No plural form
    if plural in ('kein Plural', '—', '-', ''):
        return ''

    return plural.strip()


def get_verb_forms(infinitive):
    """
    Returns 'Präteritum, Partizip II' if the verb is irregular, else ''.
    Strips 'sich ' prefix before looking up.
    """
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

    # Regular weak verbs: Präteritum = stem + -te or stem + -ete
    stem = re.sub(r'(en|ern|eln)$', '', lookup)
    is_regular = prateritum in (stem + 'te', stem + 'ete')
    if is_regular:
        return ''

    return f"{prateritum}, {partizip}"


# ── Translation ────────────────────────────────────────────────────────────────

def get_translation(german_text):
    try:
        from googletrans import Translator
        translator = Translator()
        result = translator.translate(german_text, src='de', dest='en')
        return result.text
    except ImportError:
        print("❌  googletrans not installed: pip install googletrans==4.0.0rc1")
        return "[INSTALL GOOGLETRANS]"
    except Exception as e:
        print(f"⚠️   Translation error for '{german_text}': {e}")
        return "[TRANSLATION ERROR]"


# ── Main ───────────────────────────────────────────────────────────────────────

def process():
    if not os.path.exists(DB_FILE):
        print(f"❌  {DB_FILE} not found. Run migrate.py first.")
        return
    if not os.path.exists(RAW_FILE):
        print(f"❌  {RAW_FILE} not found.")
        return

    conn = get_connection()
    ensure_forms_column(conn)

    with open(RAW_FILE, 'r', encoding='utf-8') as f:
        lines = [l.strip() for l in f if l.strip()]

    added   = 0
    skipped = 0

    print(f"\n🔄  Processing {len(lines)} lines from {RAW_FILE}...\n")

    for raw_line in lines:
        # 1. Apply manual corrections (on the raw squished form)
        line = CORRECTIONS.get(raw_line, raw_line)

        # 2. Unsquish article+noun
        line = unsquish(line)

        # 3. Strip trailing underscores (copy-paste artifact)
        if '_' in line:
            line = line.split('_')[0].strip()
        if not line:
            continue

        article, word, inline_forms, word_type = parse_entry(line)

        # 4. Duplicate check (using base word without plural notation)
        if word_exists(conn, word, article):
            display = f"{article} {word}" if article else word
            print(f"   ⏭️   Skipping duplicate: {display}")
            skipped += 1
            continue

        display = f"{article} {word}" if article else word
        print(f"   {display}", end='')

        # 5. Look up grammatical forms
        forms       = ''

        if word_type == 'noun':
            if inline_forms:
                forms = inline_forms
                print(f"  {forms}", end='')
            else:
                forms = get_noun_plural(word)
                time.sleep(0.3)
                if forms:
                    print(f"  {forms}", end='')
                else:
                    print('  -', end='')

        elif word_type == 'verb':
            forms = get_verb_forms(word)
            time.sleep(0.3)
            # Fall back to inline forms if Wiktionary lookup fails
            if not forms and inline_forms:
                forms = inline_forms
            if forms:
                print(f"  {forms}", end='')
            else:
                print('  -', end='')

        # 6. Translate
        translate_text = f"{article} {word}" if article else word
        english = get_translation(translate_text)
        print(f"  →  {english}")

        insert_word(conn, word, article, english, word_type, forms, SOURCE, CHAPTER)
        added += 1

    conn.close()
    print(f"\n✅  Done.  {added} words added,  {skipped} duplicates skipped.")


if __name__ == '__main__':
    process()
