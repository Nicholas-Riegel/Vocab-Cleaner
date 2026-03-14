# German Vocab Cleaner Setup

## Automatic Translation

Install googletrans for automatic German-English translation:

```bash
# Create virtual environment
cd "/Users/nicholas/Deutsch/Vocab Cleaner"
python3 -m venv vocab_env
source vocab_env/bin/activate

# Install googletrans
pip install googletrans==4.0.0rc1
```

## How to Use

1. **Activate virtual environment**: `source vocab_env/bin/activate`
2. **Paste your raw German vocab** into `german_vocab_raw.txt`
3. **Run the script**: `python3 clean_vocab.py`
4. **Copy from Excel file**: Open `german_vocab_excel.txt`, copy all content, paste into Excel

## What It Does

✅ Removes underscore clutter  
✅ Joins articles with nouns (die Trauer → dieTrauer)  
✅ Auto-translates to English  
✅ Creates Excel-ready format  

## Example Output

```
German	English
aufwachsen	to grow up
dieBeziehung, -en	relationship
mutig	brave
```

## Files Created:

- `german_vocab_excel.txt` - Excel-ready format with translations  

Perfect! Just one file to copy into Excel and you're ready to study! 🇩🇪📚