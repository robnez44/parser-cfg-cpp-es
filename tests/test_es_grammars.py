"""Tests of the Spanish grammars and of the formal analysis of P1 (CONTRATO_FASE2.md, sections 5 and 12).

The expected numbers (35, 22, 17, ...) are the ones written in the contract. The parser of the
Spanish subset is not needed here: the sentences are checked with nltk.ChartParser over the same
.gram files, so these tests only depend on the grammars and on the lexicon.
"""

import csv
import itertools
import re
from pathlib import Path

import pytest

from experiments.ambiguity_trees import (
    AMBIGUOUS_SENTENCE,
    attachment,
    by_type,
    by_upos,
    draw_svg,
    parse_all,
    to_nltk_cfg,
)
from experiments.grammar_growth import build_agreement_grammar, expected_productions, growth_table
from verifier import class_notation
from verifier.grammar import left_recursion_cycles, parse_grammar, read_grammar
from verifier.ll1 import analyze

ROOT = Path(__file__).resolve().parents[1]
GRAMMARS = ROOT / "grammars"
LEXICON = ROOT / "spanish" / "lexicon.tsv"


@pytest.fixture(scope="module")
def es():
    return read_grammar(GRAMMARS / "es.gram")


@pytest.fixture(scope="module")
def es_base():
    return read_grammar(GRAMMARS / "es_base.gram")


@pytest.fixture(scope="module")
def es_natural():
    return read_grammar(GRAMMARS / "es_natural.gram")


@pytest.fixture(scope="module")
def cfgs(es, es_base, es_natural):
    return {
        "es": to_nltk_cfg(es, by_type),
        "es_base": to_nltk_cfg(es_base, by_upos),
        "es_natural": to_nltk_cfg(es_natural, by_upos),
    }


def sizes(grammar):
    return len(grammar.productions), len(grammar.nonterminals), len(grammar.terminals)


# ---------- Sizes ----------
def test_es_gram_has_35_productions_22_nonterminals_and_17_terminals(es):
    assert sizes(es) == (35, 22, 17)


def test_es_base_gram_has_18_productions_12_nonterminals_and_7_terminals(es_base):
    assert sizes(es_base) == (18, 12, 7)


def test_es_natural_gram_has_9_productions(es_natural):
    assert len(es_natural.productions) == 9


# ---------- LL(1) ----------
@pytest.mark.parametrize("name", ["es", "es_base"])
def test_es_grammars_only_have_the_accepted_conflict(name):
    analysis = analyze(read_grammar(GRAMMARS / f"{name}.gram"))
    assert [(c.nonterminal, c.terminal) for c in analysis.conflicts] == [("NpTail", "PREP")]
    assert analysis.is_ll1()


def test_es_gram_conflict_is_first_follow(es):
    (conflict,) = analyze(es).conflicts
    assert conflict.kind == "FIRST/FOLLOW"
    assert {str(p) for p in conflict.productions} == {"NpTail -> PrepPhrase NpTail", "NpTail -> ε"}


def test_es_natural_gram_has_two_conflicts_without_accepting(es_natural):
    analysis = analyze(es_natural)
    assert not analysis.is_ll1()
    assert {(c.nonterminal, c.terminal) for c in analysis.unaccepted_conflicts()} == {
        ("NounPhrase", "DET"),
        ("VerbPhrase", "VERB"),
    }


def test_es_natural_gram_has_left_recursion_in_noun_phrase_and_verb_phrase(es_natural):
    recursive = {production.lhs for _, production in left_recursion_cycles(es_natural)}
    assert recursive == {"NounPhrase", "VerbPhrase"}


@pytest.mark.parametrize("name", ["es", "es_base"])
def test_es_grammars_have_no_left_recursion(name):
    assert left_recursion_cycles(read_grammar(GRAMMARS / f"{name}.gram")) == []


# ---------- Class notation ----------
def test_es_bnf_is_the_class_notation_of_es_gram(es):
    text = class_notation.convert(es, analyze(es), "grammars/es.gram")
    assert (GRAMMARS / "es.bnf").read_text(encoding="utf-8") == text


# ---------- Lexicon ----------
def lexicon_types():
    with open(LEXICON, encoding="utf-8", newline="") as file:
        return {row["type"] for row in csv.DictReader(file, delimiter="\t")}


def test_terminals_of_es_gram_are_the_token_types_of_the_lexicon(es):
    assert set(es.terminals) == lexicon_types()


def test_terminals_of_es_natural_gram_are_categories_of_the_lexicon(es_natural):
    assert set(es_natural.terminals) == {"DET", "NOUN", "ADJ", "VERB", "ADV", "PREP"}


# ---------- Ambiguity ----------
def test_ambiguous_sentence_has_two_trees_in_es_natural_gram(cfgs):
    assert len(parse_all(cfgs["es_natural"], AMBIGUOUS_SENTENCE)) == 2


def test_two_trees_attach_the_prepositional_phrase_to_noun_and_to_verb(cfgs):
    trees = parse_all(cfgs["es_natural"], AMBIGUOUS_SENTENCE)
    assert sorted(attachment(tree) for tree in trees) == ["noun", "verb"]


def test_both_trees_have_the_same_words_in_the_same_order(cfgs):
    trees = parse_all(cfgs["es_natural"], AMBIGUOUS_SENTENCE)
    assert trees[0].leaves() == trees[1].leaves() == AMBIGUOUS_SENTENCE.split()


def test_two_trees_are_different(cfgs):
    first, second = parse_all(cfgs["es_natural"], AMBIGUOUS_SENTENCE)
    assert first != second


@pytest.mark.parametrize("name", ["es", "es_base"])
def test_es_grammars_read_as_plain_cfgs_are_still_ambiguous(cfgs, name):
    # The conflict M[NpTail, PREP] is exactly this ambiguity. The parser gets one tree because
    # NpTail always takes the prepositional phrase, not because the CFG forbids the other reading.
    trees = parse_all(cfgs[name], AMBIGUOUS_SENTENCE)
    assert sorted(attachment(tree) for tree in trees) == ["noun", "verb"]


def test_sentence_without_prepositional_phrase_has_one_tree(cfgs):
    assert len(parse_all(cfgs["es_natural"], "el maestro lee la carta")) == 1


def test_prepositional_phrase_before_the_verb_has_only_one_attachment(cfgs):
    # "en la casa" comes before the verb, so it can only modify the subject.
    assert len(parse_all(cfgs["es"], "el niño en la casa duerme")) == 1


def test_word_outside_the_lexicon_has_no_tree(cfgs):
    assert parse_all(cfgs["es_natural"], "el elefante lee") == []


def test_drawing_of_a_tree_is_a_svg_with_its_words(cfgs):
    tree = parse_all(cfgs["es_natural"], AMBIGUOUS_SENTENCE)[0]
    svg = draw_svg(tree, "Lectura")
    assert svg.startswith("<svg") and svg.rstrip().endswith("</svg>")
    assert all(word in svg for word in ("maestro", "carta", "casa", "PrepPhrase"))


# ---------- Agreement ----------
ACCEPTED_BY_BOTH = [
    "el niño come",
    "la niña pequeña lee un libro",
    "los gatos rojos duermen",
    "el niño come una manzana rápidamente",
    "el maestro lee la carta en la casa.",
]

AGREEMENT_ERRORS = [
    "los niño come",          # determiner and noun in number
    "el niña come",           # determiner and noun in gender
    "el niño pequeña come",   # adjective and noun in gender
    "los niños pequeño comen",  # adjective and noun in number
    "los niños come",         # subject and verb in number
    "el niño comen",          # subject and verb in number, the other way
    "el niño lee las cartas rojo",  # adjective of the object
]


@pytest.mark.parametrize("sentence", ACCEPTED_BY_BOTH)
def test_correct_sentences_are_accepted_with_and_without_agreement(cfgs, sentence):
    assert parse_all(cfgs["es"], sentence)
    assert parse_all(cfgs["es_base"], sentence)


@pytest.mark.parametrize("sentence", AGREEMENT_ERRORS)
def test_es_base_accepts_agreement_errors_and_es_rejects_them(cfgs, sentence):
    assert parse_all(cfgs["es_base"], sentence)
    assert parse_all(cfgs["es"], sentence) == []


# ---------- Growth by agreement ----------
def test_generated_grammar_with_gender_and_number_has_the_size_of_es_gram(es):
    generated = parse_grammar(build_agreement_grammar(2))
    assert sizes(generated) == sizes(es)


@pytest.mark.parametrize("features", [1, 2, 3, 4, 5])
def test_generated_grammars_follow_the_formula_4k_plus_3n_plus_13(features):
    generated = parse_grammar(build_agreement_grammar(features))
    assert len(generated.productions) == expected_productions(2**features)


@pytest.mark.parametrize("features", [1, 2, 3, 4, 5])
def test_generated_grammars_keep_only_the_accepted_conflict(features):
    analysis = analyze(parse_grammar(build_agreement_grammar(features)))
    assert [(c.nonterminal, c.terminal) for c in analysis.conflicts] == [("NpTail", "PREP")]
    assert analysis.is_ll1()


def test_growth_table_starts_with_the_real_files():
    rows = growth_table()
    assert (rows[0].productions, rows[0].nonterminals, rows[0].terminals) == (18, 12, 7)
    assert (rows[2].productions, rows[2].nonterminals, rows[2].terminals) == (35, 22, 17)


def test_each_new_feature_doubles_the_added_productions():
    productions = [row.productions for row in growth_table()][1:]
    increments = [b - a for a, b in zip(productions, productions[1:])]
    assert increments == [8, 16, 32, 64]


def test_growth_has_no_unaccepted_conflicts():
    assert all(row.conflicts == 0 for row in growth_table())


# ---------- "respectivamente" is not context-free ----------
# Model: a, b are subjects (masculine, feminine) and A, B the adjectives that agree with them.
# L = { w h(w) | w in {a,b}+ } with h(a) = A, h(b) = B. Intersected with a+b+A+B+ it is
# L2 = { a^i b^j A^i B^j | i, j >= 1 }, which the pumping lemma rules out.


def h(word: str) -> str:
    return word.replace("a", "A").replace("b", "B")


def in_l(s: str) -> bool:
    half, odd = divmod(len(s), 2)
    return not odd and half > 0 and set(s[:half]) <= {"a", "b"} and s[half:] == h(s[:half])


def in_l2(s: str) -> bool:
    match = re.fullmatch(r"(a+)(b+)(A+)(B+)", s)
    return bool(match) and len(match[1]) == len(match[3]) and len(match[2]) == len(match[4])


def words(max_length: int):
    for length in range(1, max_length + 1):
        for letters in itertools.product("ab", repeat=length):
            yield "".join(letters)


def test_pumping_intersection_with_the_regular_language_is_l2():
    for w in words(8):
        candidate = w + h(w)
        assert in_l(candidate)
        assert bool(re.fullmatch(r"a+b+A+B+", candidate)) == bool(re.fullmatch(r"a+b+", w))
        if re.fullmatch(r"a+b+A+B+", candidate):
            assert in_l2(candidate)


def test_pumping_l2_has_the_expected_members_and_non_members():
    assert in_l2("abAB") and in_l2("aabAAB") and in_l2("abbABB")
    assert not in_l2("aabAB") and not in_l2("abAAB") and not in_l2("baBA") and not in_l2("")


@pytest.mark.parametrize("p", [1, 2, 3, 4, 5])
def test_pumping_no_decomposition_of_the_chosen_word_survives(p):
    # z = a^p b^p A^p B^p. For every z = u v w x y with |vwx| <= p and |vx| >= 1,
    # pumping with i = 2 leaves L2. This is the case analysis of the report, checked by brute force.
    z = "a" * p + "b" * p + "A" * p + "B" * p
    n = len(z)
    checked = 0
    for i in range(n + 1):
        for j in range(i, min(i + p, n) + 1):
            for k in range(j, min(i + p, n) + 1):
                for l in range(k, min(i + p, n) + 1):
                    if (j - i) + (l - k) == 0:
                        continue
                    u, v, w, x, y = z[:i], z[i:j], z[j:k], z[k:l], z[l:]
                    checked += 1
                    assert not in_l2(u + v * 2 + w + x * 2 + y), (u, v, w, x, y)
    assert checked > 0


@pytest.mark.parametrize("p", [1, 2, 3, 4])
def test_pumping_word_chosen_is_in_l2_and_is_long_enough(p):
    z = "a" * p + "b" * p + "A" * p + "B" * p
    assert in_l2(z) and len(z) >= p


def test_pumping_control_nested_dependencies_survive_pumping():
    # Control: { a^i b^j B^j A^i } (nested dependencies) IS context free, and a decomposition
    # in its middle does survive pumping. It shows that the check above is not rejecting everything.
    def nested(s: str) -> bool:
        match = re.fullmatch(r"(a+)(b+)(B+)(A+)", s)
        return bool(match) and len(match[1]) == len(match[4]) and len(match[2]) == len(match[3])

    p = 3
    z = "a" * p + "b" * p + "B" * p + "A" * p
    # v = "b", x = "B" in the middle: pumping keeps the nesting.
    u, v, w, x, y = "a" * p + "b" * (p - 1), "b", "", "B", "B" * (p - 1) + "A" * p
    assert u + v + w + x + y == z
    assert all(nested(u + v * i + w + x * i + y) for i in range(0, 5))
