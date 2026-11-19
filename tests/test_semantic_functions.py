"""Tests for section 4 of the semantic analyzer: rules S6, S7 and S8 (CONTRATO.md, section 9).

The programs go through the three stages with analyze(), so they read as real C++.
Every function returns a value so these programs stay valid once S7 is checked.
"""

from minicpp import analyze


def check(source: str):
    """Return the semantic errors of a program."""
    _, errors = analyze(source)
    return errors


def messages(source: str) -> list[str]:
    return [str(e) for e in check(source)]


def lines(source: str) -> list[int]:
    return [e.line for e in check(source)]


# ---------- S8: break and continue in valid places ----------
def test_s8_break_inside_while():
    assert check("int main() {\n while (true) {\n break;\n }\n return 0;\n}") == []


def test_s8_break_inside_do_while():
    assert check("int main() {\n do {\n break;\n } while (true);\n return 0;\n}") == []


def test_s8_break_inside_for():
    assert check("int main() {\n for (int i = 0; i < 3; i++) break;\n return 0;\n}") == []


def test_s8_break_inside_switch():
    source = "int main() {\n int x = 1;\n switch (x) {\n case 1: break;\n }\n return 0;\n}"
    assert check(source) == []


def test_s8_continue_inside_while_for_and_do_while():
    source = (
        "int main() {\n"
        " while (true) { continue; }\n"
        " for (int i = 0; i < 3; i++) { continue; }\n"
        " do { continue; } while (true);\n"
        " return 0;\n"
        "}"
    )
    assert check(source) == []


def test_s8_continue_in_a_switch_inside_a_loop():
    source = (
        "int main() {\n int x = 1;\n"
        " while (true) {\n switch (x) {\n case 1: continue;\n }\n }\n"
        " return 0;\n}"
    )
    assert check(source) == []


def test_s8_break_inside_an_if_inside_a_loop():
    assert check("int main() {\n while (true) {\n if (true) break;\n }\n return 0;\n}") == []


# ---------- S8: break and continue outside a loop ----------
def test_s8_break_outside_a_loop():
    assert messages("int main() {\n break;\n return 0;\n}") == [
        "Error semántico en línea 2, columna 2: "
        "break solo puede ir dentro de un ciclo o de un switch"
    ]


def test_s8_continue_outside_a_loop():
    assert messages("int main() {\n continue;\n return 0;\n}") == [
        "Error semántico en línea 2, columna 2: continue solo puede ir dentro de un ciclo"
    ]


def test_s8_continue_inside_a_switch_without_a_loop():
    source = "int main() {\n int x = 1;\n switch (x) {\n case 1: continue;\n }\n return 0;\n}"
    assert lines(source) == [4]


def test_s8_break_after_the_loop_closed():
    assert lines("int main() {\n while (true) { }\n break;\n return 0;\n}") == [3]


def test_s8_break_inside_an_if_without_a_loop():
    assert lines("int main() {\n if (true) break;\n return 0;\n}") == [2]


def test_s8_break_in_a_function_called_from_a_loop():
    source = "int f() {\n break;\n return 0;\n}\nint main() {\n while (true) f();\n return 0;\n}"
    assert lines(source) == [2]


def test_s8_every_misplaced_jump_is_reported_in_order():
    assert lines("int main() {\n break;\n continue;\n return 0;\n}") == [2, 3]
