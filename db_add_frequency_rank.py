#!/usr/bin/env python3
"""
db_add_frequency_rank.py — One-time migration: add frequency_rank column to vocab table.

Run with: python db_add_frequency_rank.py
"""

import sqlite3

DB_FILE = '../../Vocab DB/vocab_master.db'


def main():
    conn = sqlite3.connect(DB_FILE)

    try:
        conn.execute('ALTER TABLE vocab ADD COLUMN frequency_rank INTEGER')
        conn.commit()
        print('✅  Added frequency_rank column to vocab table.')
    except sqlite3.OperationalError as e:
        if 'duplicate column' in str(e).lower():
            print('ℹ️   frequency_rank column already exists — nothing to do.')
        else:
            raise

    # Quick confirmation
    count = conn.execute('SELECT COUNT(*) FROM vocab WHERE frequency_rank IS NOT NULL').fetchone()[0]
    total = conn.execute('SELECT COUNT(*) FROM vocab').fetchone()[0]
    print(f'    {count}/{total} words currently have a frequency rank.')

    conn.close()


if __name__ == '__main__':
    main()
