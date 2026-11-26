import unicodedata

import pytest
from nltk import Tree

from experiments.llm_validator import (
    GRAMMAR,
    ResponseError,
    attachment,
    check_tree,
    matches,
    parse_response,
    split_words,
    validate,
)
from verifier.grammar import nullable_set

NULLABLE = nullable_set(GRAMMAR)

# Trees written by spanish/parser.py and printed with nltk.Tree, so they are
# derivations of es.gram by construction. The compact ones leave out the ε branches.
PERRO_FULL = (
    "(Sentence (Clause (NpSing (NpMS (DET_MS el) (NOUN_MS perro) (AdjListMS ε) (NpTail ε))) "
    "(VpSing (VERB_S duerme) (VpTail (Object ε) (AdvOpt ε) (PpList ε)))) (EndMark ε))"
)
PERRO_COMPACT = "(Sentence (Clause (NpSing (NpMS (DET_MS el) (NOUN_MS perro))) (VpSing (VERB_S duerme))))"

NINA_PERIOD = (
    "(Sentence (Clause (NpSing (NpFS (DET_FS la) (NOUN_FS niña) (AdjListFS ε) (NpTail ε))) "
    "(VpSing (VERB_S lee) (VpTail (Object (NounPhrase (NpSing (NpMS (DET_MS un) (NOUN_MS libro) "
    "(AdjListMS ε) (NpTail ε))))) (AdvOpt ε) (PpList ε)))) (EndMark (PERIOD .)))"
)

# "el maestro lee la carta en la casa", the ambiguous sentence of the contract
CARTA_NOUN = (
    "(Sentence (Clause (NpSing (NpMS (DET_MS el) (NOUN_MS maestro))) (VpSing (VERB_S lee) "
    "(VpTail (Object (NounPhrase (NpSing (NpFS (DET_FS la) (NOUN_FS carta) (NpTail (PrepPhrase "
    "(PREP en) (NounPhrase (NpSing (NpFS (DET_FS la) (NOUN_FS casa))))))))))))))"
)
CARTA_VERB = (
    "(Sentence (Clause (NpSing (NpMS (DET_MS el) (NOUN_MS maestro))) (VpSing (VERB_S lee) "
    "(VpTail (Object (NounPhrase (NpSing (NpFS (DET_FS la) (NOUN_FS carta))))) (PpList (PrepPhrase "
    "(PREP en) (NounPhrase (NpSing (NpFS (DET_FS la) (NOUN_FS casa))))))))))"
)

PERROS_ADV_PP = (
    "(Sentence (Clause (NpPlur (NpMP (DET_MP los) (NOUN_MP perros) (AdjListMP (ADJ_MP pequeños)))) "
    "(VpPlur (VERB_P corrieron) (VpTail (AdvOpt (ADV rápidamente)) (PpList (PrepPhrase (PREP en) "
    "(NounPhrase (NpSing (NpMS (DET_MS el) (NOUN_MS parque))))))))))"
)

GATO_SUBJECT_PP = (
    "(Sentence (Clause (NpSing (NpMS (DET_MS el) (NOUN_MS gato) (NpTail (PrepPhrase (PREP de) "
    "(NounPhrase (NpSing (NpFS (DET_FS la) (NOUN_FS niña)))))))) (VpSing (VERB_S duerme))))"
)


def answer(accepted: bool, tree: str | None = None) -> dict:
    return {"accepted": accepted, "tree": tree, "upos": None, "violated_rule": None}


def errors_of(tree: str, sentence: str) -> list[str]:
    return check_tree(Tree.fromstring(tree), sentence)


# ---------- parse_response ----------

def test_parse_response_plain_json():
    raw = '{"accepted": true, "tree": "(Sentence)", "upos": ["DET"], "violated_rule": null}'
    assert parse_response(raw) == {
        "accepted": True, "tree": "(Sentence)", "upos": ["DET"], "violated_rule": None,
    }


def test_parse_response_json_inside_a_code_block():
    raw = 'Aquí está:\n```json\n{"accepted": false, "tree": null, "upos": [], "violated_rule": "x"}\n```'
    assert parse_response(raw)["violated_rule"] == "x"


def test_parse_response_text_around_the_object():
    raw = 'Respuesta: {"accepted": false} Fin.'
    assert parse_response(raw)["accepted"] is False


def test_parse_response_missing_keys_are_null():
    assert parse_response('{"accepted": true}') == {
        "accepted": True, "tree": None, "upos": None, "violated_rule": None,
    }


def test_parse_response_empty_tree_is_null():
    assert parse_response('{"accepted": false, "tree": "  "}')["tree"] is None


def test_parse_response_upos_that_is_not_a_list_of_strings_is_null():
    assert parse_response('{"accepted": true, "upos": "DET NOUN"}')["upos"] is None
    assert parse_response('{"accepted": true, "upos": [1, 2]}')["upos"] is None


@pytest.mark.parametrize("raw", ["", "acepto la oración", "[true]"])
def test_parse_response_without_object_fails(raw):
    with pytest.raises(ResponseError):
        parse_response(raw)


def test_parse_response_invalid_json_fails():
    with pytest.raises(ResponseError, match="no es JSON válido"):
        parse_response('{"accepted": true,}')


@pytest.mark.parametrize("value", ['"true"', "1", "null"])
def test_parse_response_accepted_must_be_boolean(value):
    with pytest.raises(ResponseError, match="accepted"):
        parse_response(f'{{"accepted": {value}}}')


# ---------- split_words ----------

def test_split_words_separates_the_period():
    assert split_words("La niña lee un libro.") == ["la", "niña", "lee", "un", "libro", "."]


def test_split_words_normalizes_accents():
    decomposed = unicodedata.normalize("NFD", "niño")
    assert split_words(decomposed) == ["niño"]


# ---------- matches ----------

def test_matches_exact_right_side():
    assert matches(("DET_MS", "NOUN_MS", "AdjListMS", "NpTail"),
                   ("DET_MS", "NOUN_MS", "AdjListMS", "NpTail"), NULLABLE)


def test_matches_skips_nullable_symbols():
    assert matches(("DET_MS", "NOUN_MS"), ("DET_MS", "NOUN_MS", "AdjListMS", "NpTail"), NULLABLE)
    assert matches(("AdvOpt",), ("Object", "AdvOpt", "PpList"), NULLABLE)


def test_matches_never_skips_a_terminal():
    assert not matches(("NOUN_MS",), ("DET_MS", "NOUN_MS", "AdjListMS", "NpTail"), NULLABLE)


def test_matches_keeps_the_order():
    assert not matches(("PpList", "AdvOpt"), ("Object", "AdvOpt", "PpList"), NULLABLE)


def test_matches_rejects_extra_children():
    assert not matches(("VERB_S", "VpTail", "ADV"), ("VERB_S", "VpTail"), NULLABLE)


# ---------- valid trees ----------

@pytest.mark.parametrize("tree, sentence", [
    (PERRO_FULL, "el perro duerme"),
    (PERRO_COMPACT, "el perro duerme"),
    (NINA_PERIOD, "la niña lee un libro."),
    (NINA_PERIOD, "La niña lee un libro ."),
    (CARTA_NOUN, "el maestro lee la carta en la casa"),
    (CARTA_VERB, "el maestro lee la carta en la casa"),
    (PERROS_ADV_PP, "los perros pequeños corrieron rápidamente en el parque"),
    (GATO_SUBJECT_PP, "el gato de la niña duerme"),
])
def test_validate_accepts_derivations_of_es_gram(tree, sentence):
    assert validate(answer(True, tree), sentence).valid


def test_validate_empty_node_counts_as_epsilon():
    tree = PERRO_FULL.replace("(EndMark ε)", "(EndMark )")
    assert validate(answer(True, tree), "el perro duerme").valid


def test_validate_rejection_without_tree_is_valid():
    assert validate(answer(False), "el niña come").valid


# ---------- consistency between accepted and tree ----------

def test_validate_rejection_with_tree_is_invalid():
    result = validate(answer(False, PERRO_FULL), "el perro duerme")
    assert result.errors == ["rechazó la oración pero devolvió un árbol"]


def test_validate_acceptance_without_tree_is_invalid():
    result = validate(answer(True), "el perro duerme")
    assert result.errors == ["aceptó la oración pero no devolvió el árbol"]


def test_validate_malformed_brackets_is_invalid():
    result = validate(answer(True, "(Sentence (Clause"), "el perro duerme")
    assert not result.valid
    assert "no está bien formado" in result.errors[0]


# ---------- invalid trees ----------

def test_root_must_be_sentence():
    tree = "(Clause (NpSing (NpMS (DET_MS el) (NOUN_MS perro))) (VpSing (VERB_S duerme)))"
    assert "la raíz es 'Clause' y debía ser 'Sentence'" in errors_of(tree, "el perro duerme")


def test_number_agreement_has_no_production():
    tree = "(Sentence (Clause (NpSing (NpMS (DET_MS el) (NOUN_MS perro))) (VpPlur (VERB_P duermen))))"
    assert errors_of(tree, "el perro duermen") == [
        "no existe la producción Clause -> NpSing VpPlur",
    ]


def test_gender_agreement_has_no_production():
    tree = "(Sentence (Clause (NpSing (NpMS (DET_MS el) (NOUN_FS niña))) (VpSing (VERB_S come))))"
    assert errors_of(tree, "el niña come") == ["no existe la producción NpMS -> DET_MS NOUN_FS"]


def test_word_with_another_type_in_the_lexicon():
    tree = "(Sentence (Clause (NpSing (NpFS (DET_FS el) (NOUN_FS niña))) (VpSing (VERB_S come))))"
    assert errors_of(tree, "el niña come") == ["'el' es DET_MS en el lexicón, no DET_FS"]


def test_word_out_of_the_vocabulary():
    tree = "(Sentence (Clause (NpSing (NpMS (DET_MS el) (NOUN_MS lobo))) (VpSing (VERB_S duerme))))"
    assert errors_of(tree, "el lobo duerme") == ["palabra fuera del vocabulario 'lobo'"]


def test_leaves_must_be_the_sentence():
    errors = errors_of(PERRO_COMPACT, "el gato duerme")
    assert errors == ["las hojas del árbol (el perro duerme) no son la oración (el gato duerme)"]


def test_missing_period_in_the_tree():
    assert errors_of(PERRO_COMPACT, "el perro duerme.") == [
        "las hojas del árbol (el perro duerme) no son la oración (el perro duerme .)",
    ]


def test_unknown_symbol():
    tree = "(Sentence (Clause (Sujeto (DET_MS el) (NOUN_MS perro)) (VpSing (VERB_S duerme))))"
    errors = errors_of(tree, "el perro duerme")
    assert "'Sujeto' no es un símbolo de la gramática" in errors


def test_epsilon_only_for_nullable_nonterminals():
    tree = "(Sentence (Clause (NpSing ε) (VpSing (VERB_S duerme))))"
    assert "NpSing no puede derivar ε" in errors_of(tree, "duerme")


def test_word_hanging_from_a_nonterminal():
    tree = "(Sentence (Clause (NpSing (NpMS el perro)) (VpSing (VERB_S duerme))))"
    errors = errors_of(tree, "el perro duerme")
    assert "NpMS tiene una palabra suelta; cada palabra va dentro de su tipo de token" in errors


def test_terminal_with_two_words():
    tree = "(Sentence (Clause (NpSing (NpMS (DET_MS el) (NOUN_MS perro gato))) (VpSing (VERB_S duerme))))"
    assert "el terminal NOUN_MS debe tener exactamente una palabra" in errors_of(tree, "el perro duerme")


def test_adverb_before_the_object_has_no_production():
    tree = (
        "(Sentence (Clause (NpSing (NpMS (DET_MS el) (NOUN_MS niño))) (VpSing (VERB_S come) "
        "(VpTail (AdvOpt (ADV rápidamente)) (Object (NounPhrase (NpSing (NpFS (DET_FS una) "
        "(NOUN_FS manzana)))))))))"
    )
    errors = errors_of(tree, "el niño come rápidamente una manzana")
    assert errors == ["no existe la producción VpTail -> AdvOpt Object"]


# ---------- attachment ----------

def test_attachment_noun():
    assert attachment(Tree.fromstring(CARTA_NOUN)) == "noun"


def test_attachment_verb():
    assert attachment(Tree.fromstring(CARTA_VERB)) == "verb"


def test_attachment_after_an_adverb_is_verb():
    assert attachment(Tree.fromstring(PERROS_ADV_PP)) == "verb"


def test_attachment_ignores_the_subject():
    assert attachment(Tree.fromstring(GATO_SUBJECT_PP)) is None


def test_attachment_without_prepositional_phrase():
    assert attachment(Tree.fromstring(PERRO_FULL)) is None
