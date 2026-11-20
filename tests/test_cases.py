import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minicpp import analyze
from minicpp.errors import LexicalError, SemanticError, SyntacticError

CASES = ROOT / "cases"
VALID_CASES = CASES / "valid"
INVALID_CASES = CASES / "invalid"
ERROR_MARKER = re.compile(r"^// ERROR:\s*(lexical|syntactic|semantic)\s+([0-9,\s]+)\s*$")
CASE_NAME = re.compile(r"^\d{2}_(valid|lexical|syntactic|semantic)_[a-z0-9_]+\.cpp$")


def invalid_cases():
    return sorted(INVALID_CASES.glob("*.cpp"))


def read_marker(case):
    code = case.read_text(encoding="utf-8")
    lines = code.splitlines()
    assert lines, f"El caso {case.name} está vacío"
    marker = ERROR_MARKER.fullmatch(lines[0])
    assert marker, f"El caso {case.name} no tiene la primera línea // ERROR:"
    stage, lines_text = marker.groups()
    expected_lines = [int(line.strip()) for line in lines_text.split(",") if line.strip()]
    assert expected_lines, f"El caso {case.name} no indica líneas de error"
    return code, stage, expected_lines


@pytest.mark.parametrize("case", sorted(VALID_CASES.glob("*.cpp")))
def test_valid_case(case):
    code = case.read_text(encoding="utf-8")
    tree, errors = analyze(code)
    assert tree.label == "Program", f"{case.name} no produjo la raíz Program"
    assert errors == [], f"{case.name} produjo errores semánticos: {errors}"


@pytest.mark.parametrize("case", invalid_cases())
def test_invalid_case(case):
    code, stage, expected_lines = read_marker(case)
    assert case.name.split("_", 2)[1] == stage

    if stage == "lexical":
        with pytest.raises(LexicalError) as caught:
            analyze(code)
        assert len(expected_lines) == 1
        assert caught.value.line == expected_lines[0]
    elif stage == "syntactic":
        with pytest.raises(SyntacticError) as caught:
            analyze(code)
        assert len(expected_lines) == 1
        assert caught.value.line == expected_lines[0]
    else:
        tree, errors = analyze(code)
        assert tree.label == "Program"
        assert all(isinstance(error, SemanticError) for error in errors)
        actual_lines = [error.line for error in errors]
        assert actual_lines == sorted(actual_lines), "Los errores semánticos deben ordenarse por línea"
        assert set(actual_lines) == set(expected_lines)


def test_case_directories_exist_and_have_examples():
    assert VALID_CASES.is_dir()
    assert INVALID_CASES.is_dir()
    assert list(VALID_CASES.glob("*.cpp"))
    assert invalid_cases()


def test_case_filenames_follow_the_contract():
    cases = sorted(VALID_CASES.glob("*.cpp")) + invalid_cases()
    for case in cases:
        assert CASE_NAME.fullmatch(case.name), (
            f"{case.name} debe seguir el formato NN_stage_description.cpp"
        )


def test_invalid_cases_cover_all_stages_and_semantic_rules():
    cases = invalid_cases()
    parsed = [(case.name, read_marker(case)[1]) for case in cases]
    names = [name for name, _ in parsed]
    stages = {stage for _, stage in parsed}
    assert {"lexical", "syntactic", "semantic"} <= stages
    rules = {
        int(match.group(1))
        for name in names
        if (match := re.match(r"^\d{2}_semantic_s([1-9])_", name))
    }
    assert rules == set(range(1, 10)), f"Cobertura semántica incompleta: faltan {set(range(1, 10)) - rules}"


@pytest.mark.parametrize(
    "name",
    [
        "lexical_unrecognized_character",
        "lexical_unterminated_string",
        "lexical_unterminated_comment",
        "lexical_empty_character",
        "lexical_invalid_include",
        "lexical_malformed_include",
        "lexical_invalid_escape",
        "lexical_unclosed_character",
        "lexical_multichar_character",
        "lexical_malformed_number",
        "lexical_unsupported_directive",
        "lexical_float_suffix",
        "lexical_leading_decimal",
        "lexical_trailing_decimal",
    ],
)
def test_lexical_error_inventory(name):
    assert any(case.stem.endswith(name) for case in invalid_cases()), f"Falta el caso {name}"


@pytest.mark.parametrize(
    "name",
    [
        "syntactic_missing_semicolon",
        "syntactic_missing_brace",
        "syntactic_missing_parenthesis",
        "syntactic_invalid_assignment_target",
    ],
)
def test_common_syntactic_error_inventory(name):
    assert any(case.stem.endswith(name) for case in invalid_cases()), f"Falta el caso {name}"
