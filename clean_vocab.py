#!/usr/bin/env python3
"""
German Vocabulary Cleaner
Reads german_vocab_raw.txt, translates new words, saves to vocab_master.db
Creates an Excel-ready text file for copying into spreadsheets.
"""

import os
import re
import sqlite3

DB_FILE = 'vocab_master.db'


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
            word_type TEXT,
            source    TEXT,
            chapter   INTEGER
        )
    ''')
    conn.commit()


def word_exists(conn, word, article):
    if article:
        row = conn.execute(
            'SELECT 1 FROM vocab WHERE word = ? AND article = ?',
            (word, article)
        ).fetchone()
    else:
        row = conn.execute(
            'SELECT 1 FROM vocab WHERE word = ? AND article IS NULL',
            (word,)
        ).fetchone()
    return row is not None


def insert_word(conn, word, article, english, word_type, source, chapter):
    conn.execute(
        '''INSERT INTO vocab (word, article, english, word_type, source, chapter)
           VALUES (?, ?, ?, ?, ?, ?)''',
        (word, article, english, word_type, source, chapter)
    )
    conn.commit()


def count_words(conn):
    return conn.execute('SELECT COUNT(*) FROM vocab').fetchone()[0]


# ── Entry parsing ──────────────────────────────────────────────────────────────

def parse_entry(text):
    """
    Split a raw vocab line into (article, word, word_type).

    Examples:
      'die Stimmung, -en'  → ('die', 'Stimmung, -en', 'noun')
      'sich leisten'       → (None, 'sich leisten', 'verb')
      'aufwachsen'         → (None, 'aufwachsen', 'verb')
      'ehrlich'            → (None, 'ehrlich', 'other')
      'gar nicht'          → (None, 'gar nicht', 'phrase')
    """
    for article in ('der', 'die', 'das'):
        if text.lower().startswith(article + ' '):
            word = text[len(article) + 1:]
            return article, word, 'noun'
    if text.startswith('sich '):
        return None, text, 'verb'
    if ' ' in text:
        return None, text, 'phrase'
    if re.search(r'(en|ern|ieren)$', text):
        return None, text, 'verb'
    return None, text, 'other'


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


def normalize_translation(english, word_type):
    if word_type == 'noun':
        if english.lower().startswith('the '):
            return english[4:]
    elif word_type == 'verb':
        if not english.lower().startswith('to '):
            return 'to ' + english
    return english


# ── Processing ─────────────────────────────────────────────────────────────────

def process_raw_file(input_file, output_file, conn, source, chapter):
    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    excel_lines = ["German\tEnglish\n"]
    processed = 0
    skipped   = 0

    print("🔄  Processing and translating vocabulary...")

    for line in lines:
        raw = line.strip()
        if not raw:
            continue

        # Strip trailing underscores (artifact of copying from some sources)
        if '_' in raw:
            raw = raw.split('_')[0].strip()
        if not raw:
            continue

        article, word, word_type = parse_entry(raw)

        if word_exists(conn, word, article):
            display = f"{article} {word}" if article else word
            print(f"   ⏭️   Skipping duplicate: {display}")
            skipped += 1
            continue

        # Translate with article included so the API has full context
        translate_text = f"{article} {word}" if article else word
        english = normalize_translation(get_translation(translate_text), word_type)

        insert_word(conn, word, article, english, word_type, source, chapter)

        display = f"{article} {word}" if article else word
        excel_lines.append(f"{display}\t{english}\n")
        processed += 1

    with open(output_file, 'w', encoding='utf-8') as f:
        f.writelines(excel_lines)

    print(f"✅  Done. {processed} new words added, {skipped} duplicates skipped.")
    return processed


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    input_file  = 'german_vocab_raw.txt'
    output_file = 'german_vocab_excel.txt'

    if not os.path.exists(DB_FILE):
        print(f"❌  {DB_FILE} not found. Run migrate.py first.")
        return

    print("🧹  German Vocabulary Cleaner")
    print("─" * 40)

    conn = get_connection()
    init_db(conn)

    print(f"📚  {count_words(conn)} words currently in database\n")

    source = input("Source book (e.g. Deutsch Intensiv B1): ").strip()
    if not source:
        source = 'Deutsch Intensiv B1'

    chapter_raw = input("Chapter number: ").strip()
    try:
        chapter = int(chapter_raw)
    except ValueError:
        print("❌  Chapter must be a number.")
        conn.close()
        return

    print()

    try:
        new_count = process_raw_file(input_file, output_file, conn, source, chapter)
        print(f"\n✅  All done!")
        print(f"    New words added:   {new_count}")
        print(f"    Total in database: {count_words(conn)}")
        print(f"    Source: {source}, Chapter {chapter}")
        print(f"    💡 Copy {output_file} into Excel!")
    except FileNotFoundError:
        print(f"❌  Could not find {input_file}")
    except Exception as e:
        print(f"❌  Error: {e}")
    finally:
        conn.close()


if __name__ == '__main__':
    main()
