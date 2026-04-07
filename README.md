# German Vocab Cleaner

## Setup

```bash
cd "/Users/nicholas/Deutsch/Vocab Cleaner"
python3 -m venv vocab_env
source vocab_env/bin/activate
pip install httpx
```

Always activate the virtual environment before running any script:
```bash
source vocab_env/bin/activate
```

---

## Workflow

### 1. Prepare `input.txt`

Add one word per line. Translations are **required** — provide them as a tab-separated value on the same line:

```
aufwachsen	to grow up, to be raised
die Stimmung, -en	mood, atmosphere
schüchtern	shy
```

You can copy the German words from your textbook and ask Copilot to add the translations before running the script.

Nouns with a known plural can include it inline (the script will also look it up via Wiktionary if omitted):
```
der Zahn, Zähne	tooth
```

Lines without a translation are still accepted — they will be inserted into the database with `[TODO]` and flagged at the end of the run.

---

### 2. Run `input_to_db.py`

```bash
python input_to_db.py
```

You will be prompted for:
- **Source** — e.g. `Deutsch Intensiv B1`
- **Chapter number**

The script will:
- Skip words already in the database (duplicates)
- Merge new translation terms into the existing entry if a better translation is provided
- Look up noun plurals and irregular verb forms via Wiktionary
- Insert new words into `vocab_master.db`
- Print a summary of any `[TODO]` words that still need translations

---

### 3. Export nouns with `get_nouns.py`

Run any time you want a tab-separated export of all nouns, ready to paste into a spreadsheet:

```bash
python get_nouns.py
```

Output: `output.txt` — three columns: **Article** / **German** / **English**

---

## Files

| File | Purpose |
|------|---------|
| `input.txt` | Words to add — edit this before each run |
| `input_to_db.py` | Processes `input.txt` into the database |
| `get_nouns.py` | Exports all nouns to `output.txt` |
| `vocab_master.db` | The database — all vocabulary lives here |
| `output.txt` | Tab-separated noun export for spreadsheets |

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