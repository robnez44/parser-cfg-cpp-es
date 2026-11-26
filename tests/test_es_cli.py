import subprocess
import sys
from pathlib import Path

import pytest

from minicpp.errors import LexicalError, SyntacticError
from spanish import analyze
from spanish.__main__ import main

ROOT = Path(__file__).parent.parent
VALID = "el maestro lee la carta en la casa."


# ---------- analyze() ----------

def test_analyze_returns_the_tree():
    tree = analyze(VALID)
    assert tree.label == "Sentence"
    assert [t.lexeme for t in tree.leaves()] == VALID[:-1].split() + ["."]


def test_analyze_raises_lexical_error():
    with pytest.raises(LexicalError):
        analyze("las gatas comen")


def test_analyze_raises_syntactic_error():
    with pytest.raises(SyntacticError):
        analyze("el niño comen")


def test_analyze_rejects_words_after_the_sentence():
    with pytest.raises(SyntacticError) as info:
        analyze("el perro duerme. el gato duerme")
    assert info.value.expected == ["EOF"]


# ---------- Command line ----------

def test_valid_sentence(capsys):
    assert main([VALID]) == 0
    assert capsys.readouterr().out == "Oración válida\n"


def test_words_without_quotes(capsys):
    assert main(["El", "perro", "duerme."]) == 0
    assert capsys.readouterr().out == "Oración válida\n"


def test_tokens_option(capsys):
    assert main(["el niño come.", "--tokens"]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[0].split() == ["Col", "Tipo", "UPOS", "Palabra"]
    assert lines[1].split() == ["1", "DET_MS", "DET", "el"]
    assert lines[4].split() == ["13", "PERIOD", "PUNCT", "."]
    assert lines[5].split() == ["14", "EOF"]
    assert lines[-1] == "Oración válida"


def test_tree_option_console(capsys):
    assert main([VALID, "--tree", "--compact"]) == 0
    output = capsys.readouterr().out
    assert "Sentence" in output and "PrepPhrase" in output and "casa" in output
    assert "ε" not in output
    assert output.endswith("Oración válida\n")


def test_tree_option_outline(capsys):
    assert main(["el perro duerme", "--tree", "--view", "outline"]) == 0
    output = capsys.readouterr().out
    assert output.startswith("Sentence\n├── Clause")
    assert "VERB_S 'duerme'" in output
    assert "ε" in output


def test_lexical_error(capsys):
    assert main(["las gatas comen"]) == 1
    captured = capsys.readouterr()
    assert captured.err == "Error léxico en línea 1, columna 5: palabra fuera del vocabulario 'gatas'\n"
    assert "Oración válida" not in captured.out


def test_tokens_option_with_lexical_error(capsys):
    assert main(["el arbol", "--tokens"]) == 1
    assert capsys.readouterr().err.startswith("Error léxico en línea 1, columna 4")


def test_syntactic_error(capsys):
    assert main(["el niño comen", "--tree"]) == 1
    captured = capsys.readouterr()
    assert captured.err == (
        "Error sintáctico en línea 1, columna 9: se esperaba VERB_S y se encontró VERB_P ('comen')\n"
    )
    assert captured.out == ""


def test_unknown_view_is_rejected():
    with pytest.raises(SystemExit):
        main(["el perro duerme", "--view", "svg"])


def test_run_as_module():
    result = subprocess.run(
        [sys.executable, "-m", "spanish", "el niño come una manzana"],
        cwd=ROOT, capture_output=True, encoding="utf-8",
    )
    assert result.returncode == 0
    assert result.stdout == "Oración válida\n"
