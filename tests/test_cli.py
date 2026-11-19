import pytest

# The command line runs the three stages through analyze() (P1). These tests
# are skipped until minicpp/semantic.py is in the branch.
pytest.importorskip("minicpp.semantic", reason="la línea de comandos necesita el analizador semántico")

from minicpp.__main__ import main  # noqa: E402

VALID = "int main() {\n    int x = 2 + 3 * 4;\n    return x;\n}\n"


@pytest.fixture
def program(tmp_path):
    def write(code: str) -> str:
        path = tmp_path / "programa.cpp"
        path.write_text(code, encoding="utf-8")
        return str(path)
    return write


def test_valid_program(program, capsys):
    assert main([program(VALID)]) == 0
    assert capsys.readouterr().out == "Programa válido\n"


def test_tokens_option(program, capsys):
    assert main([program("int main() { return 0; }"), "--tokens"]) == 0
    output = capsys.readouterr().out
    assert "RETURN" in output and "SEMICOLON" in output and "EOF" in output
    assert output.endswith("Programa válido\n")


def test_tree_option(program, capsys):
    assert main([program(VALID), "--tree", "--view", "outline", "--compact"]) == 0
    output = capsys.readouterr().out
    assert output.startswith("Program\n└── GlobalList")
    assert "STAR '*'" in output


def test_lexical_error_stops_before_the_parser(program, capsys):
    assert main([program("int main() {\n    int x = 5 @ 3;\n}")]) == 1
    captured = capsys.readouterr()
    assert captured.err == "Error léxico en línea 2, columna 15: carácter no reconocido '@'\n"
    assert "Programa válido" not in captured.out


def test_tokens_option_with_lexical_error(program, capsys):
    assert main([program('cout << "Hola;'), "--tokens"]) == 1
    assert capsys.readouterr().err.startswith("Error léxico en línea 1, columna 9: cadena sin cerrar")


def test_syntactic_error(program, capsys):
    assert main([program("int main() {\n    int x = 5\n}")]) == 1
    assert capsys.readouterr().err.startswith("Error sintáctico en línea 3, columna 1")


def test_semantic_errors(program, capsys):
    assert main([program("int main() {\n    total = 5;\n    return 0;\n}")]) == 1
    captured = capsys.readouterr()
    assert captured.err.startswith("Error semántico en línea 2")
    assert "Programa válido" not in captured.out


def test_missing_file(tmp_path, capsys):
    assert main([str(tmp_path / "no_existe.cpp")]) == 2
    assert "No se encontró el archivo" in capsys.readouterr().err


def test_utf8_bom_is_ignored(tmp_path):
    path = tmp_path / "con_bom.cpp"
    path.write_text(VALID, encoding="utf-8-sig")
    assert main([str(path)]) == 0
