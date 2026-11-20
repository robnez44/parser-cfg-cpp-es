"""Tests for section 3 of the semantic analyzer: rules S3, S4 and S9 (CONTRATO.md, section 9).

The programs go through the three stages with analyze(), so they read as real C++.
Each invalid program has exactly one type error, so the tests also check that
an error does not produce a cascade of messages.
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


def in_main(*statements: str) -> str:
    """Wrap statements in main, one per line starting at line 2."""
    body = "\n".join(" " + s for s in statements)
    return f"int main() {{\n{body}\n return 0;\n}}"


# ---------- Valid programs ----------
def test_valid_numeric_types_mix():
    source = in_main(
        "int i = 1;",
        "double d = i * 2.5;",
        "float f = d;",
        "char c = 'a';",
        "bool b = c;",
        "i = c + 1;",
        "d = i / 2 + f - b;",
    )
    assert check(source) == []


def test_valid_string_operations():
    source = in_main(
        'string s = "Hola";',
        's = s + " mundo";',
        's += "!";',
        'bool same = s == "Hola";',
        "bool less = s < s;",
    )
    assert check(source) == []


def test_valid_logical_and_comparison():
    source = in_main(
        "int a = 1;",
        "double d = 2.5;",
        "bool b = a < d && !(a == 2) || d >= 1;",
        "if (a) { }",
        "while (b) { b = false; }",
    )
    assert check(source) == []


def test_valid_increment_and_compound_assignment():
    source = in_main(
        "int i = 0;",
        "char c = 'a';",
        "double d = 1.0;",
        "i++;", "--i;", "c++;", "d--;",
        "i += 2;", "i -= 1;", "i *= 3;", "i /= 2;", "i %= 2;",
        "d += i;",
    )
    assert check(source) == []


def test_valid_function_call_types():
    source = (
        "double half(int x) { return x / 2.0; }\n"
        "void show() { }\n"
        "int main() {\n"
        " double d = half(3) + 1;\n"
        " show();\n"
        " cout << half(4) << endl;\n"
        " return 0;\n"
        "}"
    )
    assert check(source) == []


def test_valid_conditions_of_every_statement():
    source = in_main(
        "int n = 3;",
        "if (n > 0) { }",
        "while (n) { n--; }",
        "do { n++; } while (n < 3);",
        "for (int i = 0; i < n; i++) { }",
        "for (;;) { break; }",
    )
    assert check(source) == []


# ---------- S3: assignments ----------
def test_s3_assign_string_to_int():
    source = in_main("int x = 0;", 'x = "hola";')
    assert messages(source) == ["Error semántico en línea 3, columna 4: no se puede asignar string a int"]


def test_s3_assign_number_to_string():
    source = in_main('string s = "a";', "s = 65;")
    assert messages(source) == ["Error semántico en línea 3, columna 4: no se puede asignar int a string"]


def test_s3_initializer_with_wrong_type():
    source = in_main('int x = "hola";')
    assert messages(source) == ["Error semántico en línea 2, columna 8: no se puede asignar string a int"]


def test_s3_global_initializer_with_wrong_type():
    source = 'double rate = "alta";\nint main() {\n return 0;\n}'
    assert messages(source) == ["Error semántico en línea 1, columna 13: no se puede asignar string a double"]


def test_s3_each_declarator_of_a_list():
    source = in_main('int a = 1, b = "dos", c = 3;')
    assert messages(source) == ["Error semántico en línea 2, columna 15: no se puede asignar string a int"]


def test_s3_assign_void_call():
    source = "void f() { }\nint main() {\n int x = 0;\n x = f();\n return 0;\n}"
    assert messages(source) == ["Error semántico en línea 4, columna 4: no se puede asignar void a int"]


def test_s3_compound_assignment_mixing_string_and_number():
    source = in_main('string s = "a";', "s += 1;")
    assert messages(source) == ["Error semántico en línea 3, columna 4: no se puede asignar int a string"]


def test_s3_chained_assignment():
    source = in_main("int a = 0;", 'string s = "x";', "a = s = 1;")
    assert lines(source) == [4]


# ---------- S4: operators ----------
def test_s4_modulo_with_double():
    source = in_main("double d = 2.5;", "int x = d % 2;")
    assert messages(source) == [
        "Error semántico en línea 3, columna 12: el operador % necesita operandos enteros y recibió double"
    ]


def test_s4_modulo_assignment_with_double():
    source = in_main("double d = 2.5;", "d %= 2;")
    assert messages(source) == [
        "Error semántico en línea 3, columna 4: el operador %= necesita operandos enteros y recibió double"
    ]


def test_s4_string_plus_number():
    source = in_main('string s = "a";', "s = s + 1;")
    assert messages(source) == [
        "Error semántico en línea 3, columna 8: el operador + no se puede aplicar a string y int"
    ]


def test_s4_string_minus_string():
    source = in_main('string s = "a";', 's = s - "b";')
    assert messages(source) == [
        "Error semántico en línea 3, columna 8: el operador - no se puede aplicar a string y string"
    ]


def test_s4_compound_minus_with_strings():
    source = in_main('string s = "a";', 's -= "b";')
    assert messages(source) == [
        "Error semántico en línea 3, columna 4: el operador -= no se puede aplicar a string y string"
    ]


def test_s4_compare_string_with_number():
    source = in_main('string s = "a";', "bool b = s == 1;")
    assert messages(source) == [
        "Error semántico en línea 3, columna 13: el operador == no se puede aplicar a string y int"
    ]


def test_s4_logical_and_with_string():
    source = in_main('string s = "a";', "bool b = true && s;")
    assert messages(source) == [
        "Error semántico en línea 3, columna 16: el operador && no se puede aplicar a bool y string"
    ]


def test_s4_not_of_string():
    source = in_main('string s = "a";', "bool b = !s;")
    assert messages(source) == ["Error semántico en línea 3, columna 11: el operador ! no se puede aplicar a string"]


def test_s4_unary_minus_of_string():
    source = in_main('string s = "a";', "s = -s;")
    assert messages(source) == ["Error semántico en línea 3, columna 6: el operador - no se puede aplicar a string"]


def test_s4_increment_bool():
    source = in_main("bool b = true;", "b++;")
    assert messages(source) == ["Error semántico en línea 3, columna 3: el operador ++ no se puede aplicar a bool"]


def test_s4_prefix_decrement_string():
    source = in_main('string s = "a";', "--s;")
    assert messages(source) == ["Error semántico en línea 3, columna 2: el operador -- no se puede aplicar a string"]


def test_s4_operator_with_void_call():
    source = "void f() { }\nint main() {\n int x = f() + 1;\n return 0;\n}"
    assert messages(source) == [
        "Error semántico en línea 3, columna 14: el operador + no se puede aplicar a void y int"
    ]


def test_s4_cout_void_call():
    source = "void f() { }\nint main() {\n cout << f() << endl;\n return 0;\n}"
    assert messages(source) == ["Error semántico en línea 3, columna 10: cout no puede mostrar un valor de tipo void"]


def test_s4_error_inside_cout_expression():
    source = in_main('string s = "a";', "cout << s - 1;")
    assert lines(source) == [3]


def test_s4_left_associativity_reports_the_right_operator():
    # (1 + 2) - s: the error is in the -, because 1 + 2 is computed first and gives int.
    source = in_main('string s = "a";', "int x = 1 + 2 - s;")
    assert messages(source) == [
        "Error semántico en línea 3, columna 16: el operador - no se puede aplicar a int y string"
    ]


def test_s4_error_inside_parentheses_is_reported_once():
    source = in_main('string s = "a";', "int x = (s * 2) + 1;")
    assert lines(source) == [3]


def test_s4_error_inside_call_argument_is_reported_once():
    source = 'int f(int a) { return a; }\nint main() {\n string s = "a";\n int x = f(s % 2);\n return 0;\n}'
    assert lines(source) == [4]


# ---------- S9: conditions ----------
def test_s9_if_with_string():
    source = in_main('string s = "a";', "if (s) { }")
    assert messages(source) == ["Error semántico en línea 3, columna 6: la condición del if no puede ser de tipo string"]


def test_s9_while_with_void_call():
    source = "void f() { }\nint main() {\n while (f()) { }\n return 0;\n}"
    assert messages(source) == [
        "Error semántico en línea 3, columna 9: la condición del while no puede ser de tipo void"
    ]


def test_s9_do_while_with_string():
    source = in_main('string s = "a";', "do { } while (s);")
    assert messages(source) == [
        "Error semántico en línea 3, columna 16: la condición del do-while no puede ser de tipo string"
    ]


def test_s9_for_with_string():
    source = in_main('string s = "a";', "for (int i = 0; s; i++) { }")
    assert messages(source) == [
        "Error semántico en línea 3, columna 18: la condición del for no puede ser de tipo string"
    ]


def test_s9_for_condition_sees_its_own_variable():
    source = in_main("for (int i = 0; i; i++) { }")
    assert check(source) == []


def test_s9_string_comparison_is_a_valid_condition():
    source = in_main('string s = "a";', 'if (s == "a") { }')
    assert check(source) == []


# ---------- No cascades with other rules ----------
def test_analyzer_undeclared_variable_gives_only_s1():
    source = in_main("int x = y + 1;")
    assert messages(source) == ["Error semántico en línea 2, columna 10: la variable 'y' no está declarada"]


def test_analyzer_undeclared_variable_in_condition_gives_only_s1():
    source = in_main("if (z) { }")
    assert messages(source) == ["Error semántico en línea 2, columna 6: la variable 'z' no está declarada"]


def test_analyzer_several_type_errors_sorted_by_line():
    source = in_main('string s = "a";', "int x = s;", "double d = 1.5;", "x = d % 2;", "if (s) { }")
    assert lines(source) == [3, 5, 6]