#!/usr/bin/env python3
"""
fetch_frequency_list.py — Download the German frequency list from HermitDave's
GitHub repo and write frequency_list.tsv (rank, lemma).

Source: https://github.com/hermitdave/FrequencyWords (CC BY-SA 4.0)
Based on OpenSubtitles — reflects everyday spoken German.

Run with: python fetch_frequency_list.py
Output:   frequency_list.tsv
"""

import re
import httpx

OUT_FILE = 'frequency_list.tsv'
FREQ_URL = 'https://raw.githubusercontent.com/hermitdave/FrequencyWords/master/content/2018/de/de_50k.txt'

# Lemmas and inflected forms to skip — grammatical words not useful as flashcards.
SKIP_LEMMAS = {
    # sein — all forms
    'sein', 'ist', 'bin', 'bist', 'sind', 'seid',
    'war', 'warst', 'waren', 'wart',
    'wäre', 'wärst', 'wären', 'wäret',
    'sei', 'seien', 'seist', 'seid',
    'gewesen',
    # haben — all forms
    'haben', 'habe', 'hast', 'hat', 'habt',
    'hatte', 'hattest', 'hatten', 'hattet',
    'hätte', 'hättest', 'hätten', 'hättet',
    'gehabt',
    # werden — all forms
    'werden', 'werde', 'wirst', 'wird', 'werdet',
    'wurde', 'wurdest', 'wurden', 'wurdet',
    'würde', 'würdest', 'würden', 'würdet',
    'geworden', 'worden',
    # können
    'können', 'kann', 'kannst', 'könnt',
    'konnte', 'konntest', 'konnten', 'konntet',
    'könnte', 'könntest', 'könnten', 'könntet',
    # müssen
    'müssen', 'muss', 'musst', 'müsst',
    'musste', 'musstest', 'mussten', 'musstet',
    'müsste', 'müsstest', 'müssten', 'müsstet',
    # wollen
    'wollen', 'will', 'willst', 'wollt',
    'wollte', 'wolltest', 'wollten', 'wolltet',
    # sollen
    'sollen', 'soll', 'sollst', 'sollt',
    'sollte', 'solltest', 'sollten', 'solltet',
    # dürfen
    'dürfen', 'darf', 'darfst', 'dürft',
    'durfte', 'durftest', 'durften', 'durftet',
    # mögen / möchten
    'mögen', 'mag', 'magst', 'mögt',
    'mochte', 'mochtest', 'mochten', 'mochtet',
    'möchte', 'möchtest', 'möchten', 'möchtet',
    # Articles — all case forms
    'der', 'die', 'das', 'des', 'dem', 'den',
    'ein', 'eine', 'eines', 'einer', 'einem', 'einen',
    'kein', 'keine', 'keines', 'keiner', 'keinem', 'keinen',
    # Personal pronouns — all case forms
    'ich', 'mich', 'mir',
    'du', 'dich', 'dir',
    'er', 'ihn', 'ihm',
    'sie', 'es',
    'wir', 'uns',
    'ihr', 'euch',
    'ihnen',
    # Possessive pronouns — all forms
    'mein', 'meine', 'meinen', 'meinem', 'meines', 'meiner',
    'dein', 'deine', 'deinen', 'deinem', 'deines', 'deiner',
    'sein', 'seine', 'seinen', 'seinem', 'seines', 'seiner',
    'ihr', 'ihre', 'ihren', 'ihrem', 'ihres', 'ihrer',
    'unser', 'unsere', 'unseren', 'unserem', 'unseres', 'unserer',
    'euer', 'eure', 'euren', 'eurem', 'eures', 'eurer',
    # Formal Sie forms
    'Sie', 'Ihnen', 'Ihr', 'Ihre', 'Ihren', 'Ihrem', 'Ihres', 'Ihrer',
    # Demonstrative / relative pronouns
    'dieser', 'diese', 'diesen', 'diesem', 'dieses',
    'jener', 'jene', 'jenen', 'jenem', 'jenes',
    'welcher', 'welche', 'welchen', 'welchem', 'welches',
    'jeder', 'jede', 'jeden', 'jedem', 'jedes',
    'alle', 'allen', 'allem', 'aller', 'alles',
    'beide', 'beiden', 'beides',
    # Prepositions (inc. contractions)
    'in', 'an', 'auf', 'bei', 'mit', 'nach', 'seit', 'von',
    'vor', 'zu', 'aus', 'durch', 'für', 'gegen', 'ohne',
    'um', 'über', 'unter', 'zwischen', 'hinter', 'neben',
    'im', 'ins', 'am', 'ans', 'beim', 'zum', 'zur', 'vom', 'aufs',
    # Conjunctions
    'und', 'oder', 'aber', 'denn', 'wenn', 'dass', 'weil',
    'ob', 'als', 'damit', 'obwohl', 'während', 'sondern',
    'bevor', 'nachdem', 'seitdem', 'bis', 'falls', 'sodass',
    # Common adverbs/particles learned at A1
    'nicht', 'ja', 'nein', 'auch', 'noch', 'schon', 'nur',
    'so', 'dann', 'da', 'hier', 'jetzt', 'heute', 'immer',
    'nie', 'mehr', 'sehr', 'mal', 'doch', 'nun', 'eben',
    'noch', 'schon', 'gleich', 'gern', 'gerne',
    # Numbers
    'null', 'ein', 'zwei', 'drei', 'vier', 'fünf', 'sechs',
    'sieben', 'acht', 'neun', 'zehn', 'elf', 'zwölf',
    # Interjections / filler
    'oh', 'ah', 'na', 'he', 'hey', 'hi', 'ok', 'okay',
    'tja', 'äh', 'ach', 'wow', 'pff',
    # Titles / English loanwords used in subtitles
    'Mr', 'Mrs', 'Dr', 'Mr.', 'Mrs.', 'Dr.', 'Sir',
    'Dad', 'Mom', 'Mama', 'Papa', 'Baby', 'Boss',
    'Yeah', 'yeah', 'Ok', 'Okay',
}


def parse_pasted_table(text: str) -> list[tuple[int, str]]:
    """
    Parse the HermitDave plain-text format: one "word count" per line,
    already sorted by frequency descending.
    Returns list of (rank, word).
    """
    results = []
    rank = 0
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) >= 1:
            rank += 1
            word = parts[0]
            results.append((rank, word))
    return results


def deduplicate(entries: list[tuple[int, str]]) -> dict[str, int]:
    """
    Given (rank, lemma) pairs, return dict of lemma -> best_rank.
    Normalise: lowercase for lookup key, but preserve original case as value key.
    """
    seen: dict[str, tuple[int, str]] = {}  # lowercase -> (rank, original_lemma)
    for rank, lemma in entries:
        key = lemma.lower()
        if key not in seen or rank < seen[key][0]:
            seen[key] = (rank, lemma)
    return {original: rank for rank, original in seen.values() for _ in [None]
            if original == seen[original.lower()][1]}


def build_lemma_rank(entries: list[tuple[int, str]]) -> dict[str, int]:
    """lemma (original case) -> best rank, deduplicated."""
    seen: dict[str, tuple[int, str]] = {}
    for rank, lemma in entries:
        key = lemma.lower()
        if key not in seen or rank < seen[key][0]:
            seen[key] = (rank, lemma)
    return {data[1]: data[0] for data in seen.values()}


def main():
    print('Fetching frequency list from HermitDave/FrequencyWords...')
    headers = {'User-Agent': 'GermanVocabLearner/1.0 (personal study tool)'}
    try:
        r = httpx.get(FREQ_URL, headers=headers, timeout=30.0, follow_redirects=True)
        r.raise_for_status()
        raw = r.text
    except Exception as e:
        print(f'❌  Failed to fetch: {e}')
        return

    all_entries = parse_pasted_table(raw)
    print(f'Parsed {len(all_entries)} entries.')

    if not all_entries:
        print('❌  No entries found. Aborting.')
        return

    # Deduplicate: lemma -> best rank (keeps lowest rank = most frequent)
    lemma_rank = build_lemma_rank(all_entries)

    # Filter skip list
    before = len(lemma_rank)
    skip_lower = {s.lower() for s in SKIP_LEMMAS}
    lemma_rank = {
        lemma: rank for lemma, rank in lemma_rank.items()
        if lemma.lower() not in skip_lower
    }
    skipped = before - len(lemma_rank)

    # Sort by rank
    sorted_lemmas = sorted(lemma_rank.items(), key=lambda x: x[1])

    # Write output
    with open(OUT_FILE, 'w', encoding='utf-8') as f:
        f.write('rank\tlemma\n')
        for lemma, rank in sorted_lemmas:
            f.write(f'{rank}\t{lemma}\n')

    print()
    print(f'✅  Done.')
    print(f'    Total unique lemmas: {len(sorted_lemmas)}')
    print(f'    Function words skipped: {skipped}')
    print(f'    Written to: {OUT_FILE}')


if __name__ == '__main__':
    main()
