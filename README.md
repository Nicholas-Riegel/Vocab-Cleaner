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

### 1. Clean the raw wordlist with `input_cleaner.py`

Paste the raw book wordlist into `input.txt`, then run:
```bash
python input_cleaner.py
```
This strips the `_____` fill-in lines from the book, leaving one word/phrase per line.

---

### 2. Ask Copilot to add translations

Open a conversation and ask Copilot to add tab-separated English translations to every line in `input.txt`. Copilot should follow this checklist:

**Translation phase checklist:**
- Output format is `German\tEnglish` or `German\tEnglish\tnotes` (tab-separated)
- Split `der/die Word` gendered pairs into two separate lines with gendered translations:
  `der Deutsche\tthe German (male)` and `die Deutsche\tthe German (female)`
- Reformat `Word (der/die/das)` — move the article to the front: `Herr (der)` → `der Herr`
- Strip `(Pl. X)` entirely — Wiktionary looks up plurals automatically
- Move `(nur Sg.)` / `(nur Pl.)` to the third tab column as a note
- Any other parenthetical annotation goes in the third column as a note
- Fix any typos noticed in the German while translating

**Example output:**
```
der Name	the name
das Alter	the age	nur Sg.
der Deutsche	the German (male)
die Deutsche	the German (female)
heißen	to be called
Wie heißen Sie?	What is your name?
```

---

### 3. Run `input_to_db.py`

```bash
python input_to_db.py
```

Lines without a translation are still accepted — they will be inserted into the database with `[TODO]` and flagged at the end of the run.

You will be prompted for:
- **Source** — e.g. `Deutsch Intensiv A1`
- **Chapter number**

The script will:
- Skip words already in the database (duplicates)
- Merge new translation terms into the existing entry if a better translation is provided
- Look up noun plurals and irregular verb forms via Wiktionary
- Insert new words into `vocab_master.db`
- Print a summary of any `[TODO]` words that still need translations

---

### 3. Check for data issues with `db_check.py`

Before exporting, run this to flag and fix suspicious entries (misclassified word types, bad translations, nouns missing articles, etc.):

```bash
python db_check.py
```

You'll be prompted to select a source and chapter. For each flagged entry you can skip, edit one or more fields, or quit early.

---

### 4. Export with `export.py`

Run to export all vocabulary (or filtered by source/chapter) to a tab-separated file for Google Sheets:

```bash
python export.py
```

You'll be prompted to select a source and chapter. Output: `output.txt` — columns: **German** / **Article** / **Plural** / **Verb Forms** / **English** / **Notes** / **Word Type** / **Source** / **Chapter**

**Importing into Google Sheets:**
1. Go to **File → Import**
2. Click **Upload** and select `output.txt`
3. Under **Separator type**, choose **Tab**
4. Click **Import data**



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