import json

from nltk import Tree

from experiments.llm_validator import check_tree
from experiments.run_parser import in_grammar_differences, main, result_line

FIELDS = ["id", "tool", "accepted", "upos", "attachment", "tree", "error"]


def item(sentence: str, in_grammar: bool = True, item_id: str = "L1-01") -> dict:
    return {"id": item_id, "sentence": sentence, "in_grammar": in_grammar}


def write_set(path, items: list[dict]) -> None:
    path.write_text("".join(json.dumps(i, ensure_ascii=False) + "\n" for i in items), encoding="utf-8")


# ---------- One sentence ----------

def test_result_line_has_the_fields_of_section_8():
    assert list(result_line(item("el perro duerme"))) == FIELDS


def test_accepted_sentence():
    line = result_line(item("los niños comieron unas manzanas rojas"))
    assert line["tool"] == "parser"
    assert line["accepted"] is True
    assert line["upos"] == ["DET", "NOUN", "VERB", "DET", "NOUN", "ADJ"]
    assert line["error"] is None


def test_upos_leaves_out_the_period():
    assert result_line(item("el perro duerme."))["upos"] == ["DET", "NOUN", "VERB"]


def test_tree_is_one_line_in_brackets():
    line = result_line(item("el maestro lee la carta en la casa"))
    assert "\n" not in line["tree"]
    tree = Tree.fromstring(line["tree"])
    assert tree.label() == "Sentence"


def test_tree_is_the_full_derivation_with_epsilon():
    assert "(EndMark ε)" in result_line(item("el perro duerme"))["tree"]


def test_tree_passes_the_llm_validator():
    # the parser and the LLM are checked with the same rules
    for sentence in ["el maestro lee la carta en la casa", "el gato blanco corre rápidamente.",
                     "las niñas leyeron unas cartas hoy en la escuela"]:
        tree = Tree.fromstring(result_line(item(sentence))["tree"])
        assert check_tree(tree, sentence) == []


def test_attachment_noun_after_the_object():
    assert result_line(item("el maestro lee la carta en la casa"))["attachment"] == "noun"


def test_attachment_verb_without_object():
    assert result_line(item("el perro duerme en la casa"))["attachment"] == "verb"


def test_attachment_verb_after_the_adverb():
    assert result_line(item("el maestro lee la carta hoy en la casa"))["attachment"] == "verb"


def test_attachment_none_without_prep_phrase_after_the_verb():
    assert result_line(item("el niño come una manzana"))["attachment"] is None
    # a phrase inside the subject does not count
    assert result_line(item("el libro de la niña ve el gato"))["attachment"] is None


def test_lexical_error_is_rejected():
    line = result_line(item("las gatas comen"))
    assert line == {
        "id": "L1-01", "tool": "parser", "accepted": False, "upos": None, "attachment": None,
        "tree": None, "error": "Error léxico en línea 1, columna 5: palabra fuera del vocabulario 'gatas'",
    }


def test_syntactic_error_is_rejected():
    line = result_line(item("el niño comen"))
    assert line["accepted"] is False
    assert line["upos"] is None and line["tree"] is None
    assert line["error"].startswith("Error sintáctico en línea 1, columna 9")


# ---------- Whole set ----------

def test_main_writes_one_line_per_sentence(tmp_path, capsys):
    test_set, output = tmp_path / "test_set.jsonl", tmp_path / "results" / "parser.jsonl"
    write_set(test_set, [
        item("el perro duerme", True, "L1-01"),
        item("el niño comen", False, "L2-16"),
        item("el niño que corre duerme", False, "L3-01"),
    ])
    assert main(["--test-set", str(test_set), "--output", str(output)]) == 0

    lines = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    assert [line["id"] for line in lines] == ["L1-01", "L2-16", "L3-01"]
    assert [line["accepted"] for line in lines] == [True, False, False]
    assert capsys.readouterr().out == (
        "parser: 3 oraciones, aceptadas 1, rechazadas 2 (1 léxicas y 1 sintácticas)\n"
    )


def test_main_keeps_accents_readable(tmp_path):
    test_set, output = tmp_path / "test_set.jsonl", tmp_path / "parser.jsonl"
    write_set(test_set, [item("la niña duerme")])
    main(["--test-set", str(test_set), "--output", str(output)])
    assert "niña" in output.read_text(encoding="utf-8")


def test_main_reports_in_grammar_differences(tmp_path, capsys):
    test_set, output = tmp_path / "test_set.jsonl", tmp_path / "parser.jsonl"
    write_set(test_set, [item("el perro duerme", False, "L1-01"), item("el niño comen", True, "L2-16")])
    main(["--test-set", str(test_set), "--output", str(output)])
    assert capsys.readouterr().out.splitlines()[-1] == "No coinciden con in_grammar: L1-01, L2-16"


def test_in_grammar_differences_empty_when_all_agree():
    test_set = [item("el perro duerme", True), item("el niño comen", False)]
    results = [result_line(i) for i in test_set]
    assert in_grammar_differences(test_set, results) == []


def test_main_without_test_set(tmp_path, capsys):
    assert main(["--test-set", str(tmp_path / "no_existe.jsonl")]) == 1
    assert "hace falta el set de prueba" in capsys.readouterr().out
