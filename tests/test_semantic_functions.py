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


# ---------- S7: valid returns ----------
def test_s7_function_with_a_type_returns_a_value():
    assert check("int f() {\n return 1;\n}") == []


def test_s7_void_function_without_return():
    assert check("void f() {\n cout << 1;\n}") == []


def test_s7_void_function_with_an_empty_return():
    assert check("void f() {\n return;\n}") == []


def test_s7_main_may_end_without_return():
    assert check("int main() {\n int x = 1;\n}") == []


def test_s7_return_inside_a_nested_block_counts():
    assert check("int f(int x) {\n while (x > 0) {\n return x;\n }\n return 0;\n}") == []


# ---------- S7: wrong returns ----------
def test_s7_void_function_returns_a_value():
    assert messages("void f() {\n return 5;\n}") == [
        "Error semántico en línea 2, columna 2: "
        "la función 'f' es void y no puede devolver un valor"
    ]


def test_s7_function_with_a_type_has_an_empty_return():
    assert messages("double f() {\n return;\n}") == [
        "Error semántico en línea 2, columna 2: "
        "la función 'f' debe devolver un valor de tipo double"
    ]


def test_s7_main_cannot_have_an_empty_return():
    assert lines("int main() {\n return;\n}") == [2]


def test_s7_function_with_a_type_without_return_points_at_its_name():
    assert messages("int suma(int a, int b) {\n int c = a + b;\n}") == [
        "Error semántico en línea 1, columna 5: "
        "la función 'suma' debe devolver un valor de tipo int"
    ]


def test_s7_empty_return_is_not_also_reported_as_missing():
    assert lines("int f() {\n return;\n}") == [2]


def test_s7_each_function_is_checked_on_its_own():
    source = "int f() {\n}\nint g() {\n return 1;\n}\nint h() {\n}"
    assert lines(source) == [1, 6]


def test_s7_undeclared_name_in_the_returned_value_is_still_reported():
    assert messages("int f() {\n return y;\n}") == [
        "Error semántico en línea 2, columna 9: la variable 'y' no está declarada"
    ]


# ---------- S7: known limitation ----------
def test_s7_does_not_check_that_every_path_returns():
    # g++ only warns here ("control reaches end of non-void function").
    # Checking every path needs control flow analysis (CONTRATO.md, section 9, S7).
    assert check("int f(int x) {\n if (x > 0) return 1;\n}") == []


# ---------- S6: types of the arguments ----------
def test_s6_argument_with_an_incompatible_type():
    assert messages(FUNCTIONS + "int main() {\n return suma(1, \"dos\");\n}") == [
        "Error semántico en línea 11, columna 17: "
        "el argumento 2 de 'suma' debe ser int y recibió string"
    ]


def test_s6_numeric_arguments_convert_as_in_an_assignment():
    assert check(FUNCTIONS + "int main() {\n return suma(1.5, 'c');\n}") == []


def test_s6_string_parameter_does_not_accept_a_number():
    source = "string eco(string s) {\n return s;\n}\nint main() {\n eco(5);\n}"
    assert lines(source) == [5]


def test_s6_call_to_a_void_function_as_an_argument():
    source = (
        "void nada() {\n}\n"
        "int doble(int x) {\n return x * 2;\n}\n"
        "int main() {\n return doble(nada());\n}"
    )
    assert messages(source) == [
        "Error semántico en línea 7, columna 15: "
        "el argumento 1 de 'doble' debe ser int y recibió void"
    ]


def test_s6_types_are_not_compared_when_the_count_is_wrong():
    assert messages(FUNCTIONS + "int main() {\n return suma(\"a\");\n}") == [
        "Error semántico en línea 11, columna 9: 'suma' espera 2 argumentos y recibió 1"
    ]


def test_s6_error_inside_an_argument_is_not_reported_twice():
    assert lines(FUNCTIONS + "int main() {\n return suma(\"a\" - 1, 2);\n}") == [11]


# ---------- S7: type of the returned value ----------
def test_s7_returned_value_with_an_incompatible_type():
    assert messages("int calcular() {\n return \"texto\";\n}") == [
        "Error semántico en línea 2, columna 9: "
        "la función 'calcular' debe devolver int y recibió string"
    ]


def test_s7_numeric_value_converts_to_the_return_type():
    assert check("int f() {\n return 2.5;\n}\nbool g() {\n return 1;\n}") == []


def test_s7_string_function_does_not_return_a_number():
    assert lines("string f() {\n return 1;\n}") == [2]


def test_s7_returning_a_call_to_a_void_function():
    assert lines("void g() {\n}\nint f() {\n return g();\n}") == [4]
