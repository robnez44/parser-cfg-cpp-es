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


# ---------- S6: valid calls ----------
FUNCTIONS = (
    "int suma(int a, int b) {\n return a + b;\n}\n"
    "int doble(int x) {\n return x * 2;\n}\n"
    "int cero() {\n return 0;\n}\n"
)


def test_s6_calls_with_the_right_number_of_arguments():
    source = FUNCTIONS + "int main() {\n return suma(1, 2) + doble(3) + cero();\n}"
    assert check(source) == []


def test_s6_call_as_an_argument_of_another_call():
    assert check(FUNCTIONS + "int main() {\n return suma(doble(1), cero());\n}") == []


def test_s6_recursive_call_with_the_right_number_of_arguments():
    assert check("int fact(int n) {\n if (n <= 1) return 1;\n return n * fact(n - 1);\n}") == []


# ---------- S6: wrong number of arguments ----------
def test_s6_too_many_arguments():
    assert messages(FUNCTIONS + "int main() {\n return suma(1, 2, 3);\n}") == [
        "Error semántico en línea 11, columna 9: 'suma' espera 2 argumentos y recibió 3"
    ]


def test_s6_too_few_arguments():
    assert lines(FUNCTIONS + "int main() {\n return suma(1);\n}") == [11]


def test_s6_message_uses_singular_for_one_parameter():
    assert messages(FUNCTIONS + "int main() {\n return doble();\n}") == [
        "Error semántico en línea 11, columna 9: 'doble' espera 1 argumento y recibió 0"
    ]


def test_s6_arguments_to_a_function_without_parameters():
    assert lines(FUNCTIONS + "int main() {\n return cero(5);\n}") == [11]


def test_s6_recursive_call_with_the_wrong_number_of_arguments():
    assert lines("int f(int n) {\n return f(n, 1);\n}") == [2]


def test_s6_wrong_call_inside_the_arguments_of_another_call():
    assert lines(FUNCTIONS + "int main() {\n return suma(doble(1, 2), 3);\n}") == [11]


# ---------- S6: the called name is not a function ----------
def test_s6_calling_a_variable():
    assert messages("int main() {\n int x = 1;\n x();\n return 0;\n}") == [
        "Error semántico en línea 3, columna 2: 'x' no es una función"
    ]


def test_s6_calling_a_parameter():
    assert lines("int f(int a) {\n return a(1);\n}") == [2]


def test_s6_local_variable_hides_a_function_with_the_same_name():
    assert lines(FUNCTIONS + "int main() {\n int suma = 1;\n return suma(1, 2);\n}") == [12]


def test_s6_undeclared_function_only_reports_s1():
    assert messages("int main() {\n g(1);\n return 0;\n}") == [
        "Error semántico en línea 2, columna 2: la función 'g' no está declarada"
    ]


# ---------- S6: a function used as a variable ----------
def test_s6_function_name_without_parentheses():
    assert messages(FUNCTIONS + "int main() {\n int y = cero;\n return y;\n}") == [
        "Error semántico en línea 11, columna 10: 'cero' es una función, no una variable"
    ]


def test_s6_assigning_to_a_function_name():
    assert lines(FUNCTIONS + "int main() {\n cero = 1;\n return 0;\n}") == [11]
