import re

from minicpp.parser import Parser
from minicpp.semantic import SemanticAnalyzer
from minicpp.tokens import Token
from verifier.class_notation import TOKEN_LEXEMES

_TYPE_OF_LEXEME = {lexeme: type_ for type_, lexeme in TOKEN_LEXEMES.items()}
_OPERATORS = sorted((l for l in _TYPE_OF_LEXEME if not l.isalpha()), key=len, reverse=True)
_PATTERN = re.compile(
    r"(?P<space>\s+)"
    r"|(?P<include>#include\s*<\w+>)"
    r"|(?P<float>\d+\.\d+)"
    r"|(?P<int>\d+)"
    r"|(?P<string>\"[^\"\n]*\")"
    r"|(?P<char>'[^'\n]')"
    r"|(?P<word>[A-Za-z_]\w*)"
    r"|(?P<op>" + "|".join(re.escape(o) for o in _OPERATORS) + ")"
)


def toks(source: str) -> list[Token]:
    tokens, line, column, pos = [], 1, 1, 0
    while pos < len(source):
        match = _PATTERN.match(source, pos)
        assert match, f"unexpected character {source[pos]!r}"
        text, kind = match.group(), match.lastgroup
        if kind != "space":
            if kind == "word":
                type_ = _TYPE_OF_LEXEME.get(text, "ID")
            elif kind == "op":
                type_ = _TYPE_OF_LEXEME[text]
            else:
                type_ = {"include": "INCLUDE", "float": "FLOAT_LITERAL", "int": "INT_LITERAL",
                         "string": "STRING_LITERAL", "char": "CHAR_LITERAL"}[kind]
            tokens.append(Token(type_, text, line, column))
        newlines = text.count("\n")
        if newlines:
            line += newlines
            column = len(text) - text.rfind("\n")
        else:
            column += len(text)
        pos = match.end()
    tokens.append(Token("EOF", "", line, column))
    return tokens


def check(source: str):
    tree = Parser(toks(source)).parse()
    return SemanticAnalyzer().check(tree)


def messages(source: str) -> list[str]:
    return [str(e) for e in check(source)]


def lines(source: str) -> list[int]:
    return [e.line for e in check(source)]


# ---------- Valid programs ----------
def test_program_with_declared_variables_is_valid():
    assert check("int main() {\n int x = 1;\n int y = x + 2;\n return y;\n}") == []


def test_global_variable_is_visible_inside_functions():
    assert check("int total = 0;\nint main() {\n total = 1;\n return 0;\n}") == []


def test_parameters_are_visible_in_the_body():
    assert check("int suma(int a, int b) {\n return a + b;\n}") == []


def test_function_can_be_called_after_its_definition():
    assert check("int f() { return 1; }\nint main() {\n int x = f();\n return 0;\n}") == []


def test_function_can_call_itself():
    assert check("int fact(int n) {\n if (n <= 1) return 1;\n return n * fact(n - 1);\n}") == []


def test_cin_and_cout_with_declared_variables():
    assert check("int main() {\n int x;\n cin >> x;\n cout << x << endl;\n return 0;\n}") == []


def test_several_declarators_in_one_declaration():
    assert check("int main() {\n int a = 1, b = a, c;\n c = b;\n return 0;\n}") == []


# ---------- S1: use before declaration ----------
def test_s1_undeclared_variable():
    assert messages("int main() {\n x = 1;\n return 0;\n}") == [
        "Error semántico en línea 2, columna 2: la variable 'x' no está declarada"
    ]


def test_s1_variable_used_before_its_declaration():
    assert lines("int main() {\n int y = x;\n int x = 1;\n return 0;\n}") == [2]


def test_s1_variable_in_its_own_initializer():
    assert lines("int main() {\n int x = x + 1;\n return 0;\n}") == [2]


def test_s1_undeclared_function():
    assert messages("int main() {\n int x = f(1);\n return 0;\n}") == [
        "Error semántico en línea 2, columna 10: la función 'f' no está declarada"
    ]


def test_s1_function_defined_below_cannot_be_called():
    source = "int main() {\n return f();\n}\nint f() { return 1; }"
    assert messages(source) == [
        "Error semántico en línea 2, columna 9: la función 'f' no está declarada"
    ]


def test_s1_undeclared_variable_in_a_call_argument():
    source = "int f(int a) { return a; }\nint main() {\n return f(z);\n}"
    assert lines(source) == [3]


def test_s1_undeclared_variable_in_condition():
    assert lines("int main() {\n while (n < 3) { }\n return 0;\n}") == [2]


def test_s1_undeclared_variable_in_cin():
    assert lines("int main() {\n cin >> x;\n return 0;\n}") == [2]


def test_s1_undeclared_variable_in_cout():
    assert lines("int main() {\n cout << x;\n return 0;\n}") == [2]


def test_s1_every_undeclared_use_is_reported_in_order():
    assert lines("int main() {\n a = 1;\n b = 2;\n return 0;\n}") == [2, 3]


# ---------- S2: redeclaration ----------
def test_s2_redeclared_variable():
    assert messages("int main() {\n int x = 1;\n int x = 2;\n return 0;\n}") == [
        "Error semántico en línea 3, columna 6: 'x' ya fue declarada en este ámbito (línea 2)"
    ]


def test_s2_redeclaration_with_a_different_type_is_still_an_error():
    assert lines("int main() {\n int x;\n double x;\n return 0;\n}") == [3]


def test_s2_redeclared_in_the_same_declaration():
    assert lines("int main() {\n int a, a;\n return 0;\n}") == [2]


def test_s2_parameter_and_local_share_the_scope():
    assert lines("int f(int a) {\n int a = 1;\n return a;\n}") == [2]


def test_s2_duplicate_parameter_names():
    assert lines("int f(int a, int a) {\n return a;\n}") == [1]


def test_s2_redeclared_global_variable():
    assert lines("int x;\nint x;\nint main() { return 0; }") == [2]


def test_s2_redeclared_function():
    assert lines("int f() { return 1; }\nint f() { return 2; }") == [2]


def test_s2_function_and_global_variable_with_same_name():
    assert lines("int f;\nint f() { return 1; }") == [2]


def test_s2_same_name_in_different_functions_is_fine():
    assert check("int f() { int x; return 0; }\nint g() { int x; return 0; }") == []


# ---------- S5: scopes ----------
def test_s5_variable_of_a_block_is_not_visible_outside():
    source = "int main() {\n {\n int x = 1;\n }\n x = 2;\n return 0;\n}"
    assert messages(source) == [
        "Error semántico en línea 5, columna 2: la variable 'x' no está declarada"
    ]


def test_s5_for_variable_is_not_visible_after_the_loop():
    source = "int main() {\n for (int i = 0; i < 3; i++) { }\n i = 5;\n return 0;\n}"
    assert lines(source) == [3]


def test_s5_for_variable_is_visible_in_condition_update_and_body():
    assert check("int main() {\n int s = 0;\n for (int i = 0; i < 3; i++) { s += i; }\n return s;\n}") == []


def test_s5_two_for_loops_can_use_the_same_variable():
    source = "int main() {\n for (int i = 0; i < 2; i++) { }\n for (int i = 0; i < 2; i++) { }\n return 0;\n}"
    assert check(source) == []


def test_s5_variable_declared_in_if_block_is_not_visible_in_else():
    source = "int main() {\n if (1) { int a = 1; } else { a = 2; }\n return 0;\n}"
    assert lines(source) == [2]


def test_s5_variable_of_a_while_body_is_not_visible_after_it():
    source = "int main() {\n while (1) { int k = 0; }\n k = 1;\n return 0;\n}"
    assert lines(source) == [3]


def test_s5_switch_cases_share_one_scope_that_closes_with_the_switch():
    source = (
        "int main() {\n int op = 1;\n switch (op) {\n  case 1: int r = 1; break;\n"
        "  default: r = 2;\n }\n r = 3;\n return 0;\n}"
    )
    assert lines(source) == [7]


def test_s5_main_body_variable_is_not_visible_in_another_function():
    assert lines("int f() { int x = 1; return x; }\nint g() { return x; }") == [2]


# ---------- Shadowing ----------
def test_shadowing_a_global_in_a_function_is_fine():
    assert check("int x;\nint main() {\n int x = 1;\n return x;\n}") == []


def test_shadowing_in_an_inner_block_is_fine():
    assert check("int main() {\n int x = 1;\n {\n  int x = 2;\n  x = 3;\n }\n return x;\n}") == []


def test_shadowing_a_parameter_in_an_inner_block_is_fine():
    assert check("int f(int a) {\n {\n  int a = 2;\n }\n return a;\n}") == []


def test_for_variable_can_shadow_an_outer_one():
    assert check("int main() {\n int i = 0;\n for (int i = 0; i < 2; i++) { }\n return i;\n}") == []


# ---------- General behavior ----------
def test_analyzer_does_not_stop_at_the_first_error():
    source = "int main() {\n int x;\n int x;\n y = 1;\n return 0;\n}"
    assert lines(source) == [3, 4]


def test_analyzer_can_be_reused_on_another_program():
    analyzer = SemanticAnalyzer()
    bad = Parser(toks("int main() { y = 1; return 0; }")).parse()
    good = Parser(toks("int main() { return 0; }")).parse()
    assert len(analyzer.check(bad)) == 1
    assert analyzer.check(good) == []