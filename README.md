# German Vocab Cleaner

## Setup

```bash
cd "/Users/nicholas/Deutsch/Vocab Cleaner"
python3 -m venv vocab_env
source vocab_env/bin/activate
pip install googletrans==4.0.0rc1
```

Always activate the virtual environment before running any script:
```bash
source vocab_env/bin/activate
```

---

## Scripts

### `clean_vocab.py` — Add textbook words
Use this when adding vocabulary from a structured source (textbook, course).

1. Paste new words into `german_vocab_raw.txt`, one per line, e.g. `die Stimmung, -en`
2. Run: `python clean_vocab.py`
3. You'll be prompted for the source book and chapter number
4. Translates new words, skips duplicates, saves to `vocab_master.db`
5. Also writes `german_vocab_excel.txt` for pasting into Excel

---

### `process_reading.py` — Add words from reading
Use this when you've noted down words encountered while reading (not from a textbook).

1. Paste new words into `german_vocab_raw.txt`, one per line
2. Run: `python process_reading.py`
3. Automatically looks up noun plurals and irregular verb forms via Wiktionary
4. Translates and saves to `vocab_master.db` with source `reading`, chapter `0`

---

### `nouns.py` — Export noun list to spreadsheet
Run any time you want a tab-separated export of all nouns in insertion order.

```bash
python nouns.py
```

Output: `nouns_excel.txt` — three columns: **Article**, **German**, **English**

**Importing into Google Sheets:**
1. Go to **File → Import**
2. Click **Upload** and select `nouns_excel.txt`
3. Under **Separator type**, choose **Tab**
4. Click **Import data**

---

## Files

| File | Purpose |
|---|---|
| `german_vocab_raw.txt` | Paste new raw vocab here before each run |
| `german_vocab_excel.txt` | Output from `clean_vocab.py` — paste into Excel |
| `vocab_master.db` | SQLite database — all words, articles, forms, source, chapter |
| `nouns_excel.txt` | Tab-separated noun export — regenerate any time with `nouns.py` |

---

## Database structure

Each word is stored with:
- `word` — the base word (e.g. `Stimmung`)
- `article` — `der`, `die`, `das`, or empty for non-nouns
- `english` — translation
- `word_type` — `noun`, `verb`, `phrase`, or `other`
- `forms` — plural for nouns (e.g. `Stimmungen`), irregular conjugation for verbs (e.g. `fuhr, gefahren`)
- `source` — e.g. `Deutsch Intensiv B1` or `reading`
- `chapter` — chapter number, or `0` for reading words

---

## Querying the database directly

```bash
sqlite3 vocab_master.db
```

```sql
.headers on
.mode column
SELECT * FROM vocab;
SELECT * FROM vocab WHERE word_type = 'noun';
SELECT * FROM vocab WHERE source = 'reading';
SELECT * FROM vocab WHERE source = 'Deutsch Intensiv B1' AND chapter = 1;
SELECT COUNT(*) FROM vocab;
.quit
```