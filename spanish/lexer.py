"""Lexer for the Spanish subset: turns a sentence into a list of tokens.

Each word is looked up in spanish/lexicon.tsv, and its type is the terminal
of grammars/es.gram (CONTRATO_FASE2.md, section 4). A word that is not in
the lexicon is a lexical error.
"""

import csv
import re
import unicodedata
from pathlib import Path

from minicpp.errors import LexicalError
from minicpp.tokens import Token

LEXICON_PATH = Path(__file__).with_name("lexicon.tsv")

# A word, or a period on its own even if it is stuck to a word ("manzana.").
# Any other sign stays inside the word, so "niño," is out of the vocabulary.
WORD = re.compile(r"[^\s.]+|\.")


def load_lexicon(path: Path = LEXICON_PATH) -> dict[str, dict[str, str]]:
    """Return a dictionary from each word to its row of the lexicon."""
    # utf-8-sig also removes the BOM, and newline="" lets csv read CRLF from Windows
    with open(path, encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file, delimiter="\t", quoting=csv.QUOTE_NONE)
        return {row["word"]: row for row in reader}


# Loaded once. run_parser.py takes the upos from here, since a Token only has the type.
LEXICON = load_lexicon()


def tokenize(sentence: str) -> list[Token]:
    """Return the tokens of the sentence. The list always ends with an EOF token.

    The line is always 1 and the column is where the word starts.
    """
    # NFC joins a letter and its accent, so "ñ" matches the lexicon however it was typed
    text = unicodedata.normalize("NFC", sentence).lower()
    tokens = []

    for match in WORD.finditer(text):
        word = match.group()
        column = match.start() + 1
        entry = LEXICON.get(word)

        if entry is None:
            raise LexicalError(1, column, f"palabra fuera del vocabulario '{word}'")

        tokens.append(Token(entry["type"], word, 1, column))

    tokens.append(Token("EOF", "", 1, len(text) + 1))
    return tokens
