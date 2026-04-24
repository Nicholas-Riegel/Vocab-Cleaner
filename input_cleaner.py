# Read input.tsv, strip the tab and everything after it, write back to input.tsv

with open("input.tsv", "r", encoding="utf-8") as f:
    lines = f.readlines()

cleaned = []
for line in lines:
    # Split on the tab character and keep only the first part (the word/phrase)
    word = line.split("\t")[0].strip()
    if word:  # skip blank lines
        cleaned.append(word)

with open("input.tsv", "w", encoding="utf-8") as f:
    f.write("\n".join(cleaned) + "\n")

print(f"Done. {len(cleaned)} entries written to input.tsv.")
