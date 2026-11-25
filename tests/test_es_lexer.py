import csv
import unicodedata
from pathlib import Path

import pytest

from minicpp.errors import LexicalError
from minicpp.tokens import Token
from spanish.lexer import LEXICON, LEXICON_PATH, load_lexicon, tokenize
from verifier.grammar import read_grammar

ES_GRAM = Path(__file__).parent.parent / "grammars" / "es.gram"

UPOS_BY_TYPE = {
    "DET_MS": "DET", "DET_FS": "DET", "DET_MP": "DET", "DET_FP": "DET",
    "NOUN_MS": "NOUN", "NOUN_FS": "NOUN", "NOUN_MP": "NOUN", "NOUN_FP": "NOUN",
    "ADJ_MS": "ADJ", "ADJ_FS": "ADJ", "ADJ_MP": "ADJ", "ADJ_FP": "ADJ",
    "VERB_S": "VERB", "VERB_P": "VERB",
    "ADV": "ADV", "PREP": "ADP", "PERIOD": "PUNCT",
}


def types(sentence: str) -> list[str]:
    """Return the token types of the sentence, without the final EOF."""
    return [token.type for token in tokenize(sentence)[:-1]]


def lex_error(sentence: str) -> LexicalError:
    """Tokenize a sentence that must fail and return the error."""
    with pytest.raises(LexicalError) as info:
        tokenize(sentence)
    return info.value


def lexicon_rows() -> list[dict[str, str]]:
    """Return every row of the lexicon, even repeated words."""
    with open(LEXICON_PATH, encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file, delimiter="\t", quoting=csv.QUOTE_NONE))


# ---------- Lexicon ----------

def test_lexicon_has_98_words_and_the_period():
    words = [row["word"] for row in lexicon_rows()]
    assert len(words) == 99
    assert "." in words


def test_lexicon_words_are_unique():
    words = [row["word"] for row in lexicon_rows()]
    assert len(words) == len(set(words)) == len(LEXICON)


def test_lexicon_words_are_lowercase_and_nfc():
    for word in LEXICON:
        assert word == word.lower()
        assert word == unicodedata.normalize("NFC", word)


def test_lexicon_types_are_the_terminals_of_es_gram():
    grammar = read_grammar(ES_GRAM)
    assert {row["type"] for row in LEXICON.values()} == set(grammar.terminals)


def test_lexicon_upos_matches_the_type():
    for word, row in LEXICON.items():
        assert row["upos"] == UPOS_BY_TYPE[row["type"]], word


def test_lexicon_gender_and_number_match_the_type():
    for word, row in LEXICON.items():
        suffix = row["type"].rsplit("_", 1)[-1]
        if suffix in ("MS", "FS", "MP", "FP"):
            assert (row["gender"], row["number"]) == (suffix[0], suffix[1]), word
        elif suffix in ("S", "P"):
            assert (row["gender"], row["number"]) == ("", suffix), word


def test_lexicon_tense_only_on_verbs():
    for word, row in LEXICON.items():
        if row["upos"] == "VERB":
            assert row["tense"] in ("presente", "preterito"), word
        else:
            assert row["tense"] == "", word


def test_lexicon_rows_have_no_carriage_return():
    # with autocrlf the file has CRLF on Windows, and the \r must not stay in the last column
    for row in LEXICON.values():
        assert all("\r" not in value for value in row.values())


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_lexicon_loads_with_lf_and_crlf(tmp_path, newline):
    path = tmp_path / "lexicon.tsv"
    lines = ["word\ttype\tupos\tlemma\tgender\tnumber\ttense", "come\tVERB_S\tVERB\tcomer\t\tS\tpresente"]
    path.write_bytes(newline.join(lines).encode("utf-8") + newline.encode())
    assert load_lexicon(path) == {
        "come": {"word": "come", "type": "VERB_S", "upos": "VERB", "lemma": "comer",
                 "gender": "", "number": "S", "tense": "presente"},
    }


@pytest.mark.parametrize("word", sorted(LEXICON))
def test_every_lexicon_word_gives_its_type(word):
    assert tokenize(word) == [
        Token(LEXICON[word]["type"], word, 1, 1),
        Token("EOF", "", 1, len(word) + 1),
    ]


# ---------- Sentences ----------

def test_simple_sentence():
    tokens = tokenize("El niño come una manzana.")
    assert [(t.type, t.lexeme, t.column) for t in tokens] == [
        ("DET_MS", "el", 1), ("NOUN_MS", "niño", 4), ("VERB_S", "come", 9),
        ("DET_FS", "una", 14), ("NOUN_FS", "manzana", 18), ("PERIOD", ".", 25),
        ("EOF", "", 26),
    ]


def test_sentence_with_every_kind_of_word():
    sentence = "los niños pequeños leyeron unas cartas viejas ayer en la escuela"
    assert types(sentence) == [
        "DET_MP", "NOUN_MP", "ADJ_MP", "VERB_P", "DET_FP", "NOUN_FP", "ADJ_FP",
        "ADV", "PREP", "DET_FS", "NOUN_FS",
    ]


def test_tokens_always_end_with_eof():
    assert tokenize("el perro duerme")[-1] == Token("EOF", "", 1, 16)


def test_empty_sentence_gives_only_eof():
    assert tokenize("") == [Token("EOF", "", 1, 1)]


def test_blank_sentence_gives_only_eof():
    assert tokenize("   ") == [Token("EOF", "", 1, 4)]


# ---------- Uppercase and accents ----------

@pytest.mark.parametrize("sentence", ["EL PERRO DUERME", "El Perro Duerme", "eL pErRo DuErMe"])
def test_uppercase_is_lowered(sentence):
    assert [t.lexeme for t in tokenize(sentence)[:-1]] == ["el", "perro", "duerme"]


def test_uppercase_with_accent():
    assert tokenize("ÁRBOL")[0] == Token("NOUN_MS", "árbol", 1, 1)


def test_accents_are_kept():
    assert types("el árbol") == ["DET_MS", "NOUN_MS"]


def test_decomposed_accent_is_accepted():
    # "niño" written as "n" plus a combining tilde, which looks the same on screen
    decomposed = unicodedata.normalize("NFD", "niño")
    assert decomposed != "niño"
    assert tokenize(decomposed)[0] == Token("NOUN_MS", "niño", 1, 1)


# ---------- Period ----------

def test_period_stuck_to_a_word_is_split():
    assert types("el perro duerme.") == ["DET_MS", "NOUN_MS", "VERB_S", "PERIOD"]


def test_period_after_a_space():
    tokens = tokenize("el perro duerme .")
    assert tokens[3] == Token("PERIOD", ".", 1, 17)


def test_period_between_two_words():
    assert types("perro.gato") == ["NOUN_MS", "PERIOD", "NOUN_MS"]


def test_several_periods_are_several_tokens():
    # the lexer gives three PERIOD tokens and the parser rejects the sentence
    assert types("el perro duerme...") == ["DET_MS", "NOUN_MS", "VERB_S", "PERIOD", "PERIOD", "PERIOD"]


def test_period_alone():
    assert tokenize(".") == [Token("PERIOD", ".", 1, 1), Token("EOF", "", 1, 2)]


# ---------- Whitespace ----------

def test_extra_spaces_move_the_columns():
    tokens = tokenize("  el   perro")
    assert [(t.lexeme, t.column) for t in tokens] == [("el", 3), ("perro", 8), ("", 13)]


def test_tabs_separate_words():
    assert types("el\tperro\tduerme") == ["DET_MS", "NOUN_MS", "VERB_S"]


def test_line_is_always_one():
    tokens = tokenize("el perro\nduerme")
    assert all(t.line == 1 for t in tokens)
    assert tokens[2] == Token("VERB_S", "duerme", 1, 10)


# ---------- Out of vocabulary ----------

def test_out_of_vocabulary_message():
    error = lex_error("las gatas comen")
    assert (error.line, error.column) == (1, 5)
    assert error.detail == "palabra fuera del vocabulario 'gatas'"
    assert str(error) == "Error léxico en línea 1, columna 5: palabra fuera del vocabulario 'gatas'"


def test_out_of_vocabulary_without_accent():
    error = lex_error("el arbol")
    assert error.column == 4
    assert error.detail == "palabra fuera del vocabulario 'arbol'"


def test_out_of_vocabulary_word_is_shown_in_lowercase():
    assert lex_error("el Gato Negro").detail == "palabra fuera del vocabulario 'negro'"


@pytest.mark.parametrize("word", ["del", "al", "él", "ella", "lo", "grande", "y", "que", "juan", "comía"])
def test_out_of_vocabulary_words_left_out_of_the_lexicon(word):
    assert lex_error(f"el niño {word}").detail == f"palabra fuera del vocabulario '{word}'"


def test_out_of_vocabulary_comma_stays_in_the_word():
    error = lex_error("el niño, come")
    assert error.column == 4
    assert error.detail == "palabra fuera del vocabulario 'niño,'"


@pytest.mark.parametrize("sign", [",", ";", ":", "!", "?", "¿", "¡", "3", "-"])
def test_out_of_vocabulary_sign_alone(sign):
    assert lex_error(f"el perro {sign}").detail == f"palabra fuera del vocabulario '{sign}'"


def test_out_of_vocabulary_reports_the_first_unknown_word():
    error = lex_error("el gatito come la galleta")
    assert error.column == 4
    assert "'gatito'" in error.detail


def test_out_of_vocabulary_before_a_period():
    error = lex_error("el perro ladra.")
    assert error.column == 10
    assert error.detail == "palabra fuera del vocabulario 'ladra'"
