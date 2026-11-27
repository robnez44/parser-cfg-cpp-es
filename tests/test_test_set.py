import json
import re
from pathlib import Path

import pytest

from minicpp.errors import LexicalError, SyntacticError
from spanish import analyze

ROOT = Path(__file__).resolve().parents[1]
TEST_SET_PATH = ROOT / "data" / "test_set.jsonl"
REQUIRED_FIELDS = {
    "id",
    "level",
    "sentence",
    "spanish_ok",
    "in_grammar",
    "upos",
    "ambiguous",
    "attachment",
    "phenomena",
    "note",
}
ALLOWED_PHENOMENA = {
    "svo",
    "intransitiva",
    "adj",
    "adv",
    "pp",
    "preterito",
    "plural",
    "concordancia_numero",
    "concordancia_genero",
    "orden",
    "ambigua",
    "subordinada",
    "coordinacion",
    "respectivamente",
    "clitico",
    "contraccion",
    "fuera_de_vocabulario",
}
ALLOWED_UPOS = {
    "ADJ",
    "ADP",
    "ADV",
    "AUX",
    "CCONJ",
    "DET",
    "NOUN",
    "PRON",
    "SCONJ",
    "VERB",
}
WORD = re.compile(r"[^\s.]+")
IDENTIFIER = re.compile(r"^L([1-3])-(\d{2})$")


def load_test_set(path=TEST_SET_PATH):
    with path.open(encoding="utf-8") as file:
        return [json.loads(line) for line in file if line.strip()]


@pytest.fixture(scope="module")
def test_set():
    return load_test_set()


def test_test_set_has_at_least_twenty_sentences_per_level(test_set):
    assert len(test_set) >= 60
    for level in (1, 2, 3):
        assert sum(item["level"] == level for item in test_set) >= 20


def test_test_set_has_unique_ids_and_complete_fields(test_set):
    ids = set()
    for item in test_set:
        assert set(item) == REQUIRED_FIELDS
        assert item["id"] not in ids
        ids.add(item["id"])
        match = IDENTIFIER.fullmatch(item["id"])
        assert match
        assert int(match.group(1)) == item["level"]


def test_test_set_values_and_upos_align_with_words(test_set):
    for item in test_set:
        assert item["level"] in (1, 2, 3)
        assert isinstance(item["sentence"], str) and item["sentence"]
        assert item["sentence"] == item["sentence"].lower()
        assert item["sentence"] == item["sentence"].strip()
        assert isinstance(item["spanish_ok"], bool)
        assert isinstance(item["in_grammar"], bool)
        assert isinstance(item["ambiguous"], bool)
        assert isinstance(item["phenomena"], list) and item["phenomena"]
        assert set(item["phenomena"]) <= ALLOWED_PHENOMENA
        assert isinstance(item["note"], str)

        if item["spanish_ok"]:
            assert isinstance(item["upos"], list)
            assert len(item["upos"]) == len(WORD.findall(item["sentence"]))
            assert set(item["upos"]) <= ALLOWED_UPOS
        else:
            assert item["upos"] is None

        if item["ambiguous"]:
            assert item["attachment"] in {"noun", "verb"}
            assert {"pp", "ambigua"} <= set(item["phenomena"])
        else:
            assert item["attachment"] is None


def test_level_one_contains_only_simple_grammatical_sentences(test_set):
    level_one = [item for item in test_set if item["level"] == 1]
    assert len(level_one) >= 20
    assert all(item["spanish_ok"] and item["in_grammar"] for item in level_one)


def test_set_has_required_negative_and_ambiguous_examples(test_set):
    assert sum(not item["spanish_ok"] for item in test_set) >= 15
    assert sum(item["ambiguous"] for item in test_set) >= 6


def test_level_two_covers_required_modifiers_and_variations(test_set):
    level_two = [item for item in test_set if item["level"] == 2]
    phenomena = {phenomenon for item in level_two for phenomenon in item["phenomena"]}
    assert {"adj", "adv", "pp", "preterito", "plural"} <= phenomena
    assert {"concordancia_numero", "concordancia_genero"} <= phenomena


def test_level_three_covers_out_of_grammar_phenomena(test_set):
    level_three = [item for item in test_set if item["level"] == 3]
    phenomena = {phenomenon for item in level_three for phenomenon in item["phenomena"]}
    assert {
        "subordinada",
        "coordinacion",
        "respectivamente",
        "clitico",
        "contraccion",
        "orden",
    } <= phenomena
    assert any(item["spanish_ok"] and not item["in_grammar"] for item in level_three)


@pytest.mark.parametrize("item", load_test_set(), ids=lambda item: item["id"])
def test_in_grammar_label_matches_parser(item):
    try:
        analyze(item["sentence"])
        accepted = True
    except (LexicalError, SyntacticError):
        accepted = False

    assert item["in_grammar"] is accepted
