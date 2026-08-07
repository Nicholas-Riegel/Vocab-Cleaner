# German Vocab Cleaner

A workflow for cleaning, checking, and organizing German vocabulary entries into a SQLite database.

---

## Key Principles

⚠️ **IMPORTANT — Pre-fill ALL data before database insertion:**

This workflow requires that `input.tsv` is **completely filled out** with all required data BEFORE running `input_to_db.py`:

- ✅ **Nouns** — Must include article (der/die/das) AND plural form
  - Example: `das Bedürfnis, Bedürfnisse`
- ✅ **Verbs** — Must include infinitive AND conjugations (Präteritum, Partizip II)
  - Example: `verwalten, verwaltete, verwaltet`
- ✅ **Adjectives/Adverbs** — Must include word_type in column 5
  - Example: `riesig\thuge\t\t\tadjective`
- ✅ **Translations** — Must be provided in column 2 for all entries

**Why?** The `input_to_db.py` script does NOT fetch missing data from Wiktionary. This approach is more reliable and avoids network/rate-limiting issues. Use Copilot or manual enrichment to prepare complete entries before insertion.

---

## Setup

```bash
cd "/Users/nicholas/Dev/Projects/Deutsch/Vocab Cleaner"
python3 -m venv vocab_env
source vocab_env/bin/activate
pip install httpx
```

**Always activate the virtual environment before running any script:**
```bash
source vocab_env/bin/activate
```

---

## Reference Information

- **Database location** — `/Users/nicholas/Dev/Projects/Deutsch/Vocab DB/vocab_master.db`

### Database Schema

#### `vocab` table
Contains German vocabulary entries with metadata and learning information.

- **id** — INTEGER, PRIMARY KEY
- **word** — TEXT, NOT NULL — German word or phrase
- **article** — TEXT, nullable — Article (der/die/das)
- **english** — TEXT, nullable — English translation
- **word_type** — TEXT, nullable — Word type (Noun, Verb, Adjective, etc.)
- **plural** — TEXT, nullable, DEFAULT '' — Plural form
- **forms** — TEXT, nullable, DEFAULT '' — Verb conjugations (Präteritum, Partizip II)
- **notes** — TEXT, nullable, DEFAULT '' — Additional notes
- **example** — TEXT, nullable — Example sentence
- **source** — TEXT, nullable — Source (e.g., "A1", book name)
- **chapter** — INTEGER, nullable — Chapter number
- **level** — TEXT, nullable — Language level (A1, A2, B1, etc.)
- **realm_ids** — TEXT, nullable, DEFAULT '' — Comma-separated realm IDs
- **frequency_rank** — INTEGER, nullable — Word frequency rank
- **flagged** — INTEGER, NOT NULL, DEFAULT 0 — Quality flag for verbs
- **noun_flagged** — INTEGER, NOT NULL, DEFAULT 0 — Quality flag for nouns
- **created_at** — TEXT, nullable — Timestamp
- **updated_at** — TEXT, nullable — Timestamp

#### `realms` table
Contains learning realm/topic categories for organizing words.

- **id** — INTEGER, PRIMARY KEY
- **name** — TEXT, NOT NULL — Realm name (e.g., "Home", "Work", "Food")
- **created_at** — TEXT, nullable
- **updated_at** — TEXT, nullable

### Input format

Tab-separated values in `input.tsv`:

**Format:** `German\tEnglish\tExample\tNotes`

The German column (column 1) can include:
- **Nouns with article:** `die Bedingungen`
- **Nouns with article and plural:** `die Stimmung, -en` or `das Bedürfnis, Bedürfnisse`
- **Verbs with conjugations:** `verwalten, verwaltete, verwaltet`
- **Bare words:** `riesig`

**Examples:**
```
das Bedürfnis, Bedürfnisse	need, requirement
verwalten, verwaltete, verwaltet	to manage, to administer
die Drehscheibe, Drehscheiben	turntable, hub
riesig	huge, enormous
```

**Database column mapping:** The script parses column 1 and stores components in separate database columns:
- `das Bedürfnis, Bedürfnisse` → `article="das"`, `word="Bedürfnis"`, `plural="Bedürfnisse"`
- `verwalten, verwaltete, verwaltet` → `word="verwalten"`, `forms="verwaltete, verwaltet"`
- Column 2 → `english`, Column 3 → `example`, Column 4 → `notes`

---

## Scripts

### 1. `input_cleaner.py`

**Purpose** — Strips all translations and notes from `input.tsv`, keeping only the German words.

This script is used when you have a combined file (with translations/notes) and need to extract just the German words.

**Input:** `input.tsv` (any format)  
**Output:** `input.tsv` (German words only, one per line)

**Run with:**
```bash
python input_cleaner.py
```

---

### 2. `enrich_forms.py` (DEPRECATED — Use manual enrichment instead)

**Purpose** — Enriches `input.tsv` with missing verb conjugations and noun articles from Wiktionary.

⚠️ **NOTE:** This script is no longer recommended. Instead, manually prepare `input.tsv` with ALL data (articles, plurals, verb forms) BEFORE running `input_to_db.py`. This approach is more reliable and avoids network/rate-limiting issues.

**Legacy functionality:**
- **Verbs** — Fetches Präteritum and Partizip II (e.g., `lehnen` → `lehnen, lehnte, gelehnt`)
- **Nouns** — Fetches articles (der/die/das) when missing
- **Nouns** — Fetches plural forms (optional, can store as `pl: Pluralform` in notes)

**Input:** `input.tsv`  
**Output:** `input.tsv` (enriched with verb forms and articles)

**Run with:**
```bash
python enrich_forms.py
```

**Limitations:** Uses Wiktionary API with rate limiting (0.5 sec between requests). Often rate-limited or blocked. Network sandbox restrictions may prevent execution.

---

### 3. `check_new_words.py`

**Purpose** — Checks which words in `input.tsv` are already in the database and which are new.

Compares each German word against the vocab database. Displays which words exist (✅) and which are new (⭕). Writes only the new/unrecognized words to `output.txt` for further processing.

**Input:** `input.tsv` (one entry per line, tab-separated or German-only)  
**Output:** `output.txt` (words NOT in the database)

**Run with:**
```bash
python check_new_words.py
```

**Output:**
```
Summary:
  Total words:     99
  Already in DB:   26
  NOT in DB:       73
```

---

### 4. `input_to_db.py`

**Purpose** — Reads `input.tsv` and inserts all words into the database.

⚠️ **IMPORTANT:** This script does NOT fetch missing data from Wiktionary. All data must be complete in `input.tsv` BEFORE running this script:
- **Nouns** — Must include article (der/die/das) and plural form: `das Bedürfnis, Bedürfnisse`
- **Verbs** — Must include base infinitive and conjugations: `verwalten, verwaltete, verwaltet`
- **Other words** — Must include word_type in column 5 if not a noun/verb: `riesig\thuge\t\t\tadjective`

**Input format examples:**
- Nouns: `das Bedürfnis, Bedürfnisse\tneed, requirement` → Stores: `word="Bedürfnis"`, `article="das"`, `plural="Bedürfnisse"`
- Verbs: `verwalten, verwaltete, verwaltet\tto manage` → Stores: `word="verwalten"`, `forms="verwaltete, verwaltet"`
- Adjectives: `riesig\thuge\t\t\tadjective` → Stores: `word="riesig"`, `word_type="adjective"` (column 5 prevents verb lookup)

**Database column mapping:**
- Column 1 (German) → parsed into `word`, `article`, `plural` (nouns), or `forms` (verbs) columns
- Column 2 (English) → `english` column
- Column 3 (Example) → `example` column
- Column 4 (Notes) → `notes` column
- Column 5 (word_type) → `word_type` column (optional, overrides auto-detection)
- Plus prompts for: `source`, `level`, `chapter`

**Input:** `input.tsv` (tab-separated: `German\tEnglish\tExample\tNotes\tword_type`)  
**Output:** Inserts into database; prints summary of entries added and duplicates skipped

**Run with:**
```bash
python input_to_db.py
```

---

### 5. `db_check.py`

**Purpose** — Validates and flags suspicious entries in the database.

Performs interactive quality checks on existing database entries:
- Verbs whose English doesn't start with "to " (likely incorrect)
- Nouns missing an article (should be `der/die/das Word`)
- Entries with [TODO] translations (incomplete)
- Verbs whose German doesn't end in -en/-eln/-ern (invalid infinitive)

For verbs, can fetch correct forms and plural from Wiktionary.

**Input:** Database (`vocab_master.db`)  
**Output:** Interactive prompts for fixes; updates database with corrections

**Run with:**
```bash
python db_check.py
```

**Wiktionary features** — Automatically fetches:
- Präteritum and Partizip II for verbs
- Nominativ Plural for nouns

---

### 5. `assign_realms.py`

**Purpose** — Interactively assign learning realms (topics) to A1-level words.

Shows all A1-level words from the database that don't yet have a realm assigned. Lets you categorize each word into one of 15 learning realms.

**Input:** Database (`vocab_master.db`) — specifically A1 words without a realm  
**Output:** Updates database with realm assignments

**Run with:**
```bash
python assign_realms.py
```

---

## Workflow

### Full workflow for a new wordlist:

1. **Paste raw book wordlist** into `input.tsv`

2. **Clean the raw input** (if it has fill-in lines):
   ```bash
   python input_cleaner.py
   ```

3. **Ask Copilot to add translations AND all required data** — Open a conversation and request:
   - **Format:** `German\tEnglish\tExample\tNotes\tword_type`
   - **Nouns:** Must include article AND plural form: `das Bedürfnis, Bedürfnisse\tneed, requirement`
   - **Verbs:** Must include infinitive AND conjugations: `verwalten, verwaltete, verwaltet\tto manage`
   - **Adjectives/Adverbs:** Include word_type in column 5: `riesig\thuge\t\t\tadjective`
   - **Additional rules:**
     - Split gendered pairs: `der Deutsche\tthe German (male)` and `die Deutsche\tthe German (female)`
     - Reformat `Word (der/die/das)` → `der Word`
     - Strip `(Pl. X)` entirely — include plural after comma instead
     - Move `(nur Sg.)` / `(nur Pl.)` to notes column

4. **Check for new words**:
   ```bash
   python check_new_words.py
   ```
   Review the new words in `output.txt` and verify all entries in `input.tsv` are complete.

5. **Verify all entries are complete** — Before insertion, ensure:
   - ✅ All nouns have articles (der/die/das) AND plurals
   - ✅ All verbs have conjugations (Präteritum, Partizip II)
   - ✅ All non-noun/non-verb words have word_type in column 5
   - ✅ All translations are provided in column 2

6. **Insert into database**:
   ```bash
   python input_to_db.py
   ```
   Prints summary of added entries and duplicates skipped. Script will NOT fetch missing data — all data must be pre-filled.

7. **Validate entries** (optional quality check):
   ```bash
   python db_check.py
   ```
   Fix any flagged entries interactively (Wiktionary lookups available for verbs/nouns).

8. **Assign realms** (optional, for A1 words):
   ```bash
   python assign_realms.py
   ```
   Categorize words into learning topics.

---

## File Overview

- **`input.tsv`** — Input file for processing (one entry per line, tab-separated)
- **`output.txt`** — Output file with words not in the database (generated by `check_new_words.py`)
- **`frequency_list.tsv`** — Optional file with German word frequencies (used by `input_to_db.py` to rank common words)
- **`vocab_env/`** — Python virtual environment (created by setup)

---

## Notes

- All scripts read from the database at `/Users/nicholas/Dev/Projects/Deutsch/Vocab DB/vocab_master.db`
- Scripts expect to run from the `Vocab Cleaner` directory (where this README is)
- Tab-separated format must use actual tab characters, not spaces
- Wiktionary lookups in `db_check.py` require internet connection
