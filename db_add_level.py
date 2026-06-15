#!/usr/bin/env python3
"""
db_add_level.py — One-time migration: add level column and populate from source.

Level mapping:
  'Deutsch Intensiv A1' → 'A1'
  'Deutsch Intensiv A2' → 'A2'
  'Deutsch Intensiv B1' → 'B1'
  'Deutsch Intensiv B2' → 'B2'
  'C1'                  → 'C1'
  anything else         → NULL

Run with: python db_add_level.py
"""

import sqlite3

DB_FILE = '../../Vocab DB/vocab_master.db'

LEVEL_MAP = {
    'Deutsch Intensiv A1': 'A1',
    'Deutsch Intensiv A2': 'A2',
    'Deutsch Intensiv B1': 'B1',
    'Deutsch Intensiv B2': 'B2',
    'C1': 'C1',
}


def main():
    conn = sqlite3.connect(DB_FILE)

    # Add column if not already present
    try:
        conn.execute("ALTER TABLE vocab ADD COLUMN level TEXT")
        conn.commit()
        print('✅  Added level column.')
    except sqlite3.OperationalError as e:
        if 'duplicate column' in str(e).lower():
            print('ℹ️   level column already exists.')
        else:
            raise

    # Populate from source
    updated = 0
    for source, level in LEVEL_MAP.items():
        cursor = conn.execute(
            "UPDATE vocab SET level = ? WHERE source = ? AND (level IS NULL OR level != ?)",
            (level, source, level)
        )
        updated += cursor.rowcount

    conn.commit()

    # Summary
    rows = conn.execute(
        "SELECT level, COUNT(*) FROM vocab GROUP BY level ORDER BY level"
    ).fetchall()
    conn.close()

    print(f'Updated {updated} rows.')
    print()
    print('Level distribution:')
    for level, count in rows:
        print(f'  {level or "(none)":8s}  {count}')


if __name__ == '__main__':
    main()
