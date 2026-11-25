import re
from pathlib import Path

import pytest

from minicpp.errors import SyntacticError
from minicpp.node import EPSILON, Node
from minicpp.tokens import Token
from spanish.lexer import tokenize
from spanish.parser import SpanishParser
from verifier.grammar import read_grammar

GRAMMAR = read_grammar(Path(__file__).parent.parent / "grammars" / "es.gram")
PRODUCTIONS = {(p.lhs, p.rhs) for p in GRAMMAR.productions}


def method_name(nonterminal: str) -> str:
    """NpMS -> np_ms, AdjListMS -> adj_list_ms (the copies keep MS, FS, MP and FP together)."""
    return re.sub(r"(?<=[a-z])(?=[A-Z])", "_", nonterminal).lower()


def parse(sentence: str) -> Node:
    return SpanishParser(tokenize(sentence)).parse()


def parse_with(method: str, sentence: str) -> Node:
    """Run one parser method on the sentence and check that it consumed everything."""
    parser = SpanishParser(tokenize(sentence))
    tree = getattr(parser, method)()
    assert parser.current().type == "EOF"
    return tree


def syntax_error(sentence: str) -> SyntacticError:
    """Parse a sentence that must fail and return the error."""
    with pytest.raises(SyntacticError) as info:
        parse(sentence)
    return info.value


def text(node: Node) -> str:
    """Rebuild the words covered by a node from its leaves."""
    return " ".join(token.lexeme for token in node.leaves())


def labels(node: Node) -> list[str]:
    """Return the labels of the children of a node."""
    return [child.label for child in node.children]


def find_all(node: Node, label: str) -> list[Node]:
    """Return every node with the label, in preorder."""
    found = [node] if node.label == label else []
    for child in node.children:
        found.extend(find_all(child, label))
    return found


def productions_used(node: Node) -> list[tuple[str, tuple[str, ...]]]:
    """Return the production applied at each nonterminal node of the tree."""
    if node.token is not None or node.is_epsilon():
        return []
    rhs = tuple(child.label for child in node.children if not child.is_epsilon())
    used = [(node.label, rhs)]
    for child in node.children:
        used.extend(productions_used(child))
    return used


VALID = [
    "el perro duerme",
    "el perro duerme.",
    "la niña lee una carta",
    "los niños comieron unas manzanas rojas.",
    "las maestras escriben unas cartas nuevas",
    "el gato pequeño blanco corre rápidamente",
    "la niña vio el árbol alto ayer.",
    "el maestro lee la carta en la casa",
    "el maestro lee la carta hoy en la casa",
    "el perro duerme en la casa con el gato",
    "unos perros viejos buscaron el libro de la niña en el parque temprano",
    "la maestra escribió una carta sobre la mesa de la escuela siempre en la casa.",
    "UN NIÑO DUERME",
]

INVALID = [
    # (sentence, column, expected, found)
    ("el niño comen", 9, ["VERB_S"], "VERB_P"),
    ("los niños come", 11, ["VERB_P"], "VERB_S"),
    ("el niña come", 4, ["NOUN_MS"], "NOUN_FS"),
    ("los niño come", 5, ["NOUN_MP"], "NOUN_MS"),
    ("unas manzana duerme", 6, ["NOUN_FP"], "NOUN_FS"),
    ("la casa rojo duerme", 9, ["VERB_S"], "ADJ_MS"),
    ("el niño come rápidamente una manzana", 26, ["PERIOD", "EOF"], "DET_FS"),
    ("el niño come hoy temprano", 18, ["PERIOD", "EOF"], "ADV"),
    ("el perro duerme. el gato duerme", 18, ["EOF"], "DET_MS"),
    ("el perro duerme..", 17, ["EOF"], "PERIOD"),
    ("come el niño", 1, ["DET_MS", "DET_FS", "DET_MP", "DET_FP"], "VERB_S"),
    ("niño come", 1, ["DET_MS", "DET_FS", "DET_MP", "DET_FP"], "NOUN_MS"),
    ("el come", 4, ["NOUN_MS"], "VERB_S"),
    ("el perro", 9, ["VERB_S"], "EOF"),
    ("el perro duerme en", 19, ["DET_MS", "DET_FS", "DET_MP", "DET_FP"], "EOF"),
    ("el perro duerme en casa", 20, ["DET_MS", "DET_FS", "DET_MP", "DET_FP"], "NOUN_FS"),
    ("", 1, ["DET_MS", "DET_FS", "DET_MP", "DET_FP"], "EOF"),
    (".", 1, ["DET_MS", "DET_FS", "DET_MP", "DET_FP"], "PERIOD"),
]


# ---------- Helpers ----------

def test_consume_returns_leaf_and_advances():
    parser = SpanishParser(tokenize("el perro"))
    leaf = parser.consume("DET_MS")
    assert leaf.label == "DET_MS"
    assert leaf.token.lexeme == "el"
    assert parser.current().type == "NOUN_MS"


def test_consume_wrong_type_raises_error():
    parser = SpanishParser(tokenize("la casa"))
    with pytest.raises(SyntacticError) as info:
        parser.consume("DET_MS")
    assert info.value.expected == ["DET_MS"]
    assert info.value.found == Token("DET_FS", "la", 1, 1)


def test_consume_one_of_accepts_any_of_the_types():
    parser = SpanishParser(tokenize("los perros"))
    assert parser.consume_one_of(("DET_MS", "DET_MP")).label == "DET_MP"
    with pytest.raises(SyntacticError) as info:
        parser.consume_one_of(("DET_MS", "DET_MP"))
    assert info.value.expected == ["DET_MS", "DET_MP"]


def test_check_accepts_several_types():
    parser = SpanishParser(tokenize("hoy"))
    assert parser.check("ADV", "PREP")
    assert not parser.check("PREP")


def test_epsilon_returns_epsilon_leaf():
    assert SpanishParser(tokenize("")).epsilon().is_epsilon()


# ---------- Methods and grammar ----------

def test_one_method_per_nonterminal():
    for nonterminal in GRAMMAR.nonterminals:
        assert callable(getattr(SpanishParser, method_name(nonterminal), None)), nonterminal


def test_docstring_first_line_is_the_production():
    for nonterminal in GRAMMAR.nonterminals:
        method = getattr(SpanishParser, method_name(nonterminal))
        alternatives = [" ".join(p.rhs) or EPSILON for p in GRAMMAR.productions_of(nonterminal)]
        expected = f"{nonterminal} -> {' | '.join(alternatives)}"
        assert method.__doc__.splitlines()[0] == expected


@pytest.mark.parametrize("sentence", VALID)
def test_tree_only_uses_productions_of_es_gram(sentence):
    for production in productions_used(parse(sentence)):
        assert production in PRODUCTIONS, production


@pytest.mark.parametrize("sentence", VALID)
def test_leaves_read_the_sentence(sentence):
    assert [t.lexeme for t in parse(sentence).leaves()] == [t.lexeme for t in tokenize(sentence)[:-1]]


# ---------- Sentence and EndMark ----------

def test_sentence_has_clause_and_end_mark():
    tree = parse("el perro duerme.")
    assert tree.label == "Sentence"
    assert labels(tree) == ["Clause", "EndMark"]


def test_end_mark_with_period():
    assert labels(parse("el perro duerme.").children[1]) == ["PERIOD"]


def test_end_mark_without_period_is_epsilon():
    assert parse("el perro duerme").children[1].children[0].is_epsilon()


def test_parse_after_period_expects_only_eof():
    error = syntax_error("el perro duerme. el gato duerme")
    assert error.expected == ["EOF"]


def test_parse_without_period_also_expects_period():
    error = syntax_error("el perro duerme rápidamente el gato")
    assert error.expected == ["PERIOD", "EOF"]


# ---------- Clause and number agreement ----------

def test_clause_singular():
    assert labels(parse("el perro duerme").children[0]) == ["NpSing", "VpSing"]


def test_clause_plural():
    assert labels(parse("los perros duermen").children[0]) == ["NpPlur", "VpPlur"]


@pytest.mark.parametrize("sentence", [
    "el niño comen", "la niña duermen", "los niños come", "las niñas leyó",
])
def test_clause_subject_and_verb_must_agree_in_number(sentence):
    error = syntax_error(sentence)
    assert error.found.type in ("VERB_S", "VERB_P")


def test_clause_error_message():
    assert str(syntax_error("el niño comen")) == (
        "Error sintáctico en línea 1, columna 9: se esperaba VERB_S y se encontró VERB_P ('comen')"
    )


# ---------- Noun phrases and gender agreement ----------

@pytest.mark.parametrize("phrase, number, copy", [
    ("el niño", "NpSing", "NpMS"),
    ("la niña", "NpSing", "NpFS"),
    ("los niños", "NpPlur", "NpMP"),
    ("las niñas", "NpPlur", "NpFP"),
])
def test_noun_phrase_picks_the_copy(phrase, number, copy):
    tree = parse_with("noun_phrase", phrase)
    assert labels(tree) == [number]
    assert labels(tree.children[0]) == [copy]


@pytest.mark.parametrize("phrase, method", [
    ("un árbol rojo", "np_ms"),
    ("una mesa roja", "np_fs"),
    ("unos árboles rojos", "np_mp"),
    ("unas mesas rojas", "np_fp"),
])
def test_np_copies_with_one_adjective(phrase, method):
    tree = parse_with(method, phrase)
    assert text(tree) == phrase
    assert tree.children[2].children[0].token.lexeme == phrase.split()[2]


@pytest.mark.parametrize("phrase", [
    "el niña", "la niño", "los niñas", "las niños", "un manzana", "unas libros",
])
def test_noun_phrase_determiner_and_noun_must_agree(phrase):
    with pytest.raises(SyntacticError) as info:
        parse_with("noun_phrase", phrase)
    assert info.value.found.type.startswith("NOUN_")


def test_noun_phrase_needs_a_determiner():
    with pytest.raises(SyntacticError) as info:
        parse_with("noun_phrase", "niño")
    assert info.value.expected == ["DET_MS", "DET_FS", "DET_MP", "DET_FP"]


def test_np_sing_rejects_plural_determiner():
    with pytest.raises(SyntacticError) as info:
        SpanishParser(tokenize("los niños")).np_sing()
    assert info.value.expected == ["DET_MS", "DET_FS"]


def test_np_plur_rejects_singular_determiner():
    with pytest.raises(SyntacticError) as info:
        SpanishParser(tokenize("el niño")).np_plur()
    assert info.value.expected == ["DET_MP", "DET_FP"]


def test_adj_list_with_several_adjectives():
    tree = parse_with("adj_list_ms", "pequeño blanco viejo")
    assert labels(tree) == ["ADJ_MS", "AdjListMS"]
    assert text(tree) == "pequeño blanco viejo"
    last = tree.children[1].children[1].children[1]
    assert last.children[0].is_epsilon()


def test_adj_list_empty():
    assert parse_with("adj_list_fp", "").children[0].is_epsilon()


def test_adj_list_stops_at_an_adjective_of_another_gender():
    # "rojo" is not ADJ_FS, so AdjListFS ends and the parser expects the verb
    error = syntax_error("la casa roja rojo duerme")
    assert (error.column, error.expected, error.found.type) == (14, ["VERB_S"], "ADJ_MS")


# ---------- Prepositional phrases and the accepted conflict ----------

def test_prep_phrase():
    tree = parse_with("prep_phrase", "de la niña")
    assert labels(tree) == ["PREP", "NounPhrase"]


def test_np_tail_takes_the_prep_phrase():
    tree = parse_with("np_tail", "de la niña")
    assert labels(tree) == ["PrepPhrase", "NpTail"]


def test_np_tail_attaches_to_the_object_and_not_to_the_verb():
    tree = parse("el maestro lee la carta en la casa")
    vp_tail = find_all(tree, "VpTail")[0]
    obj, adv, pp_list = vp_tail.children
    assert text(obj) == "la carta en la casa"
    assert adv.children[0].is_epsilon()
    assert pp_list.children[0].is_epsilon()


def test_np_tail_attaches_to_the_nearest_noun():
    # "en el parque" goes with "niña", the noun right before it, not with "libro"
    tree = parse("el niño busca el libro de la niña en el parque")
    phrases = find_all(tree, "PrepPhrase")
    assert [text(p) for p in phrases] == ["de la niña en el parque", "en el parque"]
    outer_tail = find_all(tree, "NpTail")[1]
    assert text(outer_tail) == "de la niña en el parque"
    assert outer_tail.children[1].children[0].is_epsilon()


def test_pp_list_after_an_intransitive_verb():
    tree = parse("el perro duerme en la casa")
    pp_list = find_all(tree, "PpList")[0]
    assert text(pp_list) == "en la casa"


def test_pp_list_after_the_adverb():
    tree = parse("el maestro lee la carta hoy en la casa")
    vp_tail = find_all(tree, "VpTail")[0]
    assert [text(child) for child in vp_tail.children] == ["la carta", "hoy", "en la casa"]


def test_pp_list_second_phrase_goes_to_the_noun():
    tree = parse("el perro duerme en la casa con el gato")
    pp_list = find_all(tree, "PpList")[0]
    assert text(pp_list.children[0]) == "en la casa con el gato"
    assert pp_list.children[1].children[0].is_epsilon()


def test_prep_phrase_needs_a_noun_phrase():
    error = syntax_error("el perro duerme en casa")
    assert error.found == Token("NOUN_FS", "casa", 1, 20)


# ---------- Verb phrases ----------

def test_vp_tail_intransitive_has_three_epsilons():
    vp_tail = find_all(parse("el perro duerme"), "VpTail")[0]
    assert labels(vp_tail) == ["Object", "AdvOpt", "PpList"]
    assert all(child.children[0].is_epsilon() for child in vp_tail.children)


def test_object_and_adverb():
    vp_tail = find_all(parse("los niños comieron unas manzanas ayer"), "VpTail")[0]
    assert text(vp_tail.children[0]) == "unas manzanas"
    assert text(vp_tail.children[1]) == "ayer"


def test_adverb_without_object():
    vp_tail = find_all(parse("el gato corre rápidamente"), "VpTail")[0]
    assert vp_tail.children[0].children[0].is_epsilon()
    assert labels(vp_tail.children[1]) == ["ADV"]


def test_object_can_be_plural_with_a_singular_subject():
    # agreement in number is only between subject and verb
    assert labels(parse("el niño come unas manzanas").children[0]) == ["NpSing", "VpSing"]


def test_adverb_before_the_object_is_rejected():
    error = syntax_error("el niño come rápidamente una manzana")
    assert error.found == Token("DET_FS", "una", 1, 26)


# ---------- Whole sentences ----------

@pytest.mark.parametrize("sentence", VALID)
def test_valid_sentence(sentence):
    assert parse(sentence).label == "Sentence"


@pytest.mark.parametrize("sentence, column, expected, found", INVALID)
def test_invalid_sentence(sentence, column, expected, found):
    error = syntax_error(sentence)
    assert (error.line, error.column) == (1, column)
    assert error.expected == expected
    assert error.found.type == found
