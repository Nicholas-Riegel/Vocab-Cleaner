#!/usr/bin/env python3
"""
check_new_words.py — Find words in input.tsv that are NOT in the database.

Reads input.tsv, checks each German word against vocab_master.db,
and outputs only the words that are not yet in the database to output.txt.

Run with: python check_new_words.py
"""

import os
import re
import sqlite3

INPUT_FILE = 'input.tsv'
OUTPUT_FILE = 'output.txt'

# Resolve database path - Vocab DB folder is a sibling of Vocab Cleaner
DB_FILE = '/Users/nicholas/Dev/Projects/Deutsch/Vocab DB/vocab_master.db'


def get_connection():
    """Open connection to the database."""
    if not os.path.exists(DB_FILE):
        print(f"❌  Database file not found: {DB_FILE}")
        exit(1)
    return sqlite3.connect(DB_FILE)


def extract_base_word(raw_entry):
    """
    Extract the base German word from an entry.
    Handles formats like:
      - "riesig" → "riesig"
      - "die Größe" → "Größe"
      - "die Stimmung, -en" → "Stimmung"
      - "verzichten, verzichtete, verzichtet" → "verzichten"
    """
    # Remove article prefix (der, die, das)
    entry = re.sub(r'^(der|die|das)\s+', '', raw_entry.strip())
    
    # Extract base word (everything before comma or parenthesis)
    base = entry.split(',')[0].split('(')[0].strip()
    
    return base


def word_exists_in_db(conn, base_word, article=None):
    """
    Check if a word exists in the database.
    Matches by base_word and optionally by article.
    """
    # Try exact match on word field
    row = conn.execute(
        "SELECT 1 FROM vocab WHERE word = ?",
        (base_word,)
    ).fetchone()
    
    if row:
        return True
    
    # Try matching base word before comma (for plural notation like "Stimmung, -en")
    base_pattern = base_word + ', %'
    row = conn.execute(
        "SELECT 1 FROM vocab WHERE word LIKE ?",
        (base_pattern,)
    ).fetchone()
    
    if row:
        return True
    
    return False


def main():
    conn = get_connection()
    
    # Read input.tsv
    if not os.path.exists(INPUT_FILE):
        print(f"❌  Input file not found: {INPUT_FILE}")
        conn.close()
        exit(1)
    
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        lines = f.read().strip().split('\n')
    
    if not lines:
        print("❌  Input file is empty")
        conn.close()
        exit(1)
    
    print(f"📖  Reading {len(lines)} word(s) from {INPUT_FILE}...\n")
    
    new_words = []
    existing_words = []
    
    for i, line in enumerate(lines, 1):
        line = line.strip()
        if not line:
            continue
        
        # Extract the German word (first column, before tab)
        raw_german = line.split('\t')[0] if '\t' in line else line
        base_word = extract_base_word(raw_german)
        
        # Check if it exists
        if word_exists_in_db(conn, base_word):
            existing_words.append(line)
            print(f"  ✅  {base_word}")
        else:
            new_words.append(line)
            print(f"  ⭕  {base_word}  (NEW)")
    
    conn.close()
    
    print(f"\n{'─' * 60}")
    print(f"Summary:")
    print(f"  Total words:     {len(lines)}")
    print(f"  Already in DB:   {len(existing_words)}")
    print(f"  NOT in DB:       {len(new_words)}")
    print(f"{'─' * 60}\n")
    
    # Write new words to output.txt
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        for word in new_words:
            f.write(word + '\n')
    
    print(f"📝  Wrote {len(new_words)} new word(s) to {OUTPUT_FILE}")


if __name__ == '__main__':
    main()
