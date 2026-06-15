#!/usr/bin/env python3
"""
fetch_leipzig.py — Download a Leipzig Corpora word frequency file and
write frequency_list.tsv (rank, lemma).

Source: https://wortschatz.uni-leipzig.de (CC BY-4.0)
The archive contains a *_words.txt file with pre-computed word frequencies.

Run with: python fetch_leipzig.py
Output:   frequency_list.tsv
"""

import io
import re
import tarfile
import httpx

OUT_FILE  = 'frequency_list.tsv'
# 10K sentence sample — small download (~2MB), good enough for top ~5000 words
CORPUS_URL = 'https://downloads.wortschatz-leipzig.de/corpora/deu-de_web_2021_10K.tar.gz'


# ── Skip list — grammatical words not useful as flashcards ────────────────────

SKIP_LEMMAS = {
    # sein
    'sein', 'ist', 'bin', 'bist', 'sind', 'seid',
    'war', 'warst', 'waren', 'wart',
    'wäre', 'wärst', 'wären', 'sei', 'gewesen',
    # haben
    'haben', 'habe', 'hast', 'hat', 'habt',
    'hatte', 'hattest', 'hatten', 'hattet',
    'hätte', 'hättest', 'hätten', 'gehabt',
    # werden
    'werden', 'werde', 'wirst', 'wird', 'werdet',
    'wurde', 'wurdest', 'wurden', 'wurdet',
    'würde', 'würdest', 'würden', 'geworden', 'worden',
    # modals
    'können', 'kann', 'kannst', 'könnt', 'konnte', 'könnte',
    'müssen', 'muss', 'musst', 'müsst', 'musste', 'müsste',
    'wollen', 'will', 'willst', 'wollt', 'wollte',
    'sollen', 'soll', 'sollst', 'sollt', 'sollte',
    'dürfen', 'darf', 'darfst', 'dürft', 'durfte',
    'mögen', 'mag', 'magst', 'mögt', 'mochte', 'möchte', 'möchtest',
    # articles
    'der', 'die', 'das', 'des', 'dem', 'den',
    'ein', 'eine', 'eines', 'einer', 'einem', 'einen',
    'kein', 'keine', 'keines', 'keiner', 'keinem', 'keinen',
    # pronouns
    'ich', 'mich', 'mir',
    'du', 'dich', 'dir',
    'er', 'ihn', 'ihm',
    'sie', 'es', 'wir', 'uns', 'ihr', 'euch', 'ihnen',
    # possessives
    'mein', 'meine', 'meinen', 'meinem', 'meines', 'meiner',
    'dein', 'deine', 'deinen', 'deinem', 'deines', 'deiner',
    'sein', 'seine', 'seinen', 'seinem', 'seines', 'seiner',
    'ihr', 'ihre', 'ihren', 'ihrem', 'ihres', 'ihrer',
    'unser', 'unsere', 'unseren', 'unserem', 'unseres', 'unserer',
    'euer', 'eure', 'euren', 'eurem', 'eures', 'eurer',
    # formal Sie
    'Sie', 'Ihnen', 'Ihr', 'Ihre', 'Ihren', 'Ihrem', 'Ihres', 'Ihrer',
    # demonstratives
    'dieser', 'diese', 'diesen', 'diesem', 'dieses',
    'jeder', 'jede', 'jeden', 'jedem', 'jedes',
    'alle', 'allen', 'allem', 'aller', 'alles',
    # prepositions + contractions
    'in', 'an', 'auf', 'bei', 'mit', 'nach', 'seit', 'von',
    'vor', 'zu', 'aus', 'durch', 'für', 'gegen', 'ohne',
    'um', 'über', 'unter', 'zwischen', 'hinter', 'neben',
    'im', 'ins', 'am', 'ans', 'beim', 'zum', 'zur', 'vom', 'aufs',
    # conjunctions
    'und', 'oder', 'aber', 'denn', 'wenn', 'dass', 'weil', 'daß',
    'ob', 'als', 'damit', 'obwohl', 'während', 'sondern',
    'bevor', 'nachdem', 'bis', 'falls',
    # common particles/adverbs learned at A1
    'nicht', 'ja', 'nein', 'auch', 'noch', 'schon', 'nur',
    'so', 'dann', 'da', 'hier', 'jetzt', 'heute', 'immer',
    'nie', 'mehr', 'sehr', 'mal', 'doch', 'nun', 'eben',
    # numbers
    'null', 'ein', 'zwei', 'drei', 'vier', 'fünf', 'sechs',
    'sieben', 'acht', 'neun', 'zehn', 'elf', 'zwölf',
    # noise
    'der', 'die', 'das',
}


def download_and_extract_words(url: str) -> str | None:
    """Download the tar.gz, find the *_words.txt file, return its contents."""
    print(f'Downloading {url} ...')
    headers = {'User-Agent': 'GermanVocabLearner/1.0 (personal study tool)'}
    try:
        r = httpx.get(url, headers=headers, timeout=60.0, follow_redirects=True)
        r.raise_for_status()
    except Exception as e:
        print(f'❌  Download failed: {e}')
        return None

    print(f'  Downloaded {len(r.content) / 1024:.0f} KB. Extracting...')
    try:
        with tarfile.open(fileobj=io.BytesIO(r.content), mode='r:gz') as tar:
            for member in tar.getmembers():
                if member.name.endswith('-words.txt') or member.name.endswith('_words.txt'):
                    print(f'  Found: {member.name}')
                    f = tar.extractfile(member)
                    if f:
                        return f.read().decode('utf-8')
    except Exception as e:
        print(f'❌  Extraction failed: {e}')
    return None


def parse_leipzig_words(text: str) -> list[tuple[int, str]]:
    """
    Leipzig *_words.txt format (tab-separated):
      rank  word  frequency  [other fields...]
    Returns list of (rank, word).
    """
    results = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split('\t')
        if len(parts) >= 2:
            try:
                rank = int(parts[0])
                word = parts[1].strip()
                if word:
                    results.append((rank, word))
            except ValueError:
                pass
    return results


def build_lemma_rank(entries: list[tuple[int, str]]) -> dict[str, int]:
    """Deduplicate by lowercase key, keep lowest rank."""
    seen: dict[str, tuple[int, str]] = {}
    for rank, word in entries:
        key = word.lower()
        if key not in seen or rank < seen[key][0]:
            seen[key] = (rank, word)
    return {data[1]: data[0] for data in seen.values()}


def main():
    text = download_and_extract_words(CORPUS_URL)
    if not text:
        return

    entries = parse_leipzig_words(text)
    print(f'  Parsed {len(entries)} word entries.')

    lemma_rank = build_lemma_rank(entries)

    skip_lower = {s.lower() for s in SKIP_LEMMAS}
    before = len(lemma_rank)
    lemma_rank = {
        w: r for w, r in lemma_rank.items()
        if w.lower() not in skip_lower
        and re.match(r'^[a-zA-ZäöüÄÖÜß][a-zA-ZäöüÄÖÜß\-]*$', w)  # letters only
        and len(w) >= 2
    }
    skipped = before - len(lemma_rank)

    sorted_words = sorted(lemma_rank.items(), key=lambda x: x[1])

    with open(OUT_FILE, 'w', encoding='utf-8') as f:
        f.write('rank\tlemma\n')
        for word, rank in sorted_words:
            f.write(f'{rank}\t{word}\n')

    print()
    print(f'✅  Done.')
    print(f'    Total unique words: {len(sorted_words)}')
    print(f'    Function words skipped: {skipped}')
    print(f'    Written to: {OUT_FILE}')
    print()
    print('Top 30 (after skipping function words):')
    for word, rank in sorted_words[:30]:
        print(f'  #{rank:5d}  {word}')


if __name__ == '__main__':
    main()
