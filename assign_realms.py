#!/usr/bin/env python3
"""
assign_realms.py — Interactively assign realms (learning topics) to A1 words.

This script will:
1. Show all A1 words without a realm assigned
2. Let you assign a realm to each word
3. Save the changes to the database

Run with: python assign_realms.py
"""

import os
import sqlite3
from datetime import datetime, timezone

DB_FILE = os.path.expanduser('~/Dev/Projects/Deutsch/Vocab DB/vocab_master.db')

def now():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S')

def get_realms(conn):
    """Fetch all available realms."""
    rows = conn.execute('SELECT id, name FROM realms ORDER BY id').fetchall()
    return rows

def get_a1_words_without_realm(conn):
    """Fetch A1 words that don't have a realm assigned yet."""
    rows = conn.execute('''
        SELECT id, word, article, english, word_type
        FROM vocab
        WHERE source LIKE '%A1%' 
          AND (realm IS NULL OR realm = '' OR realm = '[]')
        ORDER BY id
    ''').fetchall()
    return rows

def assign_realm(conn, word_id, realm_id):
    """Assign a realm to a word."""
    conn.execute(
        'UPDATE vocab SET realm = ?, updated_at = ? WHERE id = ?',
        (realm_id, now(), word_id)
    )
    conn.commit()

def format_word(word, article, word_type, english):
    """Format a word for display."""
    display = f"{article} {word}".strip() if article else word
    return f"{display} ({word_type}) — {english}"

def main():
    try:
        conn = sqlite3.connect(DB_FILE)
    except sqlite3.OperationalError as e:
        print(f"❌  Could not open database: {e}")
        return

    # Get available realms
    realms = get_realms(conn)
    if not realms:
        print("❌  No realms found in database.")
        conn.close()
        return

    # Get A1 words without realm
    words = get_a1_words_without_realm(conn)
    if not words:
        print("✅  All A1 words have a realm assigned!")
        conn.close()
        return

    print(f"Found {len(words)} A1 word(s) without a realm.\n")

    assigned = 0
    skipped = 0

    for i, (word_id, word, article, english, word_type) in enumerate(words, 1):
        print(f"─── {i}/{len(words)} ───────────────────────────────────────")
        
        # Show realms first
        print("📚  Realms:")
        for j, (realm_id, name) in enumerate(realms, 1):
            print(f"  {j}. {name}")
        print()
        
        # Then show the word
        print(f"  {format_word(word, article, word_type, english)}")
        print()

        while True:
            prompt = "Enter realm number (1-15) | Enter/s = skip | q = quit: "
            user_input = input(prompt).strip().lower()

            if user_input == 'q':
                print("\n✋  Quitting early.")
                conn.close()
                return

            if user_input in ('', 's'):
                print("  ⏭️  Skipped.\n")
                skipped += 1
                break

            if user_input.isdigit():
                realm_num = int(user_input)
                if 1 <= realm_num <= len(realms):
                    realm_id, realm_name = realms[realm_num - 1]
                    assign_realm(conn, word_id, realm_id)
                    print(f"  ✅  Assigned to '{realm_name}'.\n")
                    assigned += 1
                    break
                else:
                    print(f"  ❌  Please enter a number between 1 and {len(realms)}.")
            else:
                print(f"  ❌  Invalid input.")

    print(f"\n{'─' * 40}")
    print(f"✅  Done.")
    print(f"    Assigned: {assigned}  |  Skipped: {skipped}")

    conn.close()

if __name__ == '__main__':
    main()
