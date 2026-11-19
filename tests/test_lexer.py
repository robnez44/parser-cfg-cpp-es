from pathlib import Path

import pytest

from minicpp.errors import LexicalError
from minicpp.lexer import ERROR_RULES, IGNORED_RULES, TOKEN_RULES, tokenize
from minicpp.tokens import KEYWORDS, Token

TOKENS_DOC = Path(__file__).parent.parent / "docs" / "tokens.md"


def types(code: str) -> list[str]:
    """Return the token types of the code, without the final EOF."""
    return [token.type for token in tokenize(code)[:-1]]


def lex_error(code: str) -> LexicalError:
    """Tokenize code that must fail and return the error."""
    with pytest.raises(LexicalError) as info:
        tokenize(code)
    return info.value


# ---------- Reserved words and identifiers ----------

@pytest.mark.parametrize("word, token_type", [
    ("using", "USING"), ("namespace", "NAMESPACE"), ("std", "STD"),
    ("int", "INT"), ("float", "FLOAT"), ("double", "DOUBLE"), ("char", "CHAR"),
    ("bool", "BOOL"), ("string", "STRING"), ("void", "VOID"),
    ("if", "IF"), ("else", "ELSE"), ("while", "WHILE"), ("do", "DO"), ("for", "FOR"),
    ("switch", "SWITCH"), ("case", "CASE"), ("default", "DEFAULT"), ("break", "BREAK"),
    ("continue", "CONTINUE"), ("return", "RETURN"),
    ("cin", "CIN"), ("cout", "COUT"), ("endl", "ENDL"),
    ("true", "TRUE"), ("false", "FALSE"),
])
def test_reserved_word(word, token_type):
    assert tokenize(word)[0] == Token(token_type, word, 1, 1)


@pytest.mark.parametrize("word", ["x", "_x", "x1", "main", "contador_2", "_", "suma_Total"])
def test_identifier(word):
    assert tokenize(word)[0] == Token("ID", word, 1, 1)


@pytest.mark.parametrize("word", ["If", "INT", "Cout", "integer", "iff", "returns", "doble", "string2"])
def test_word_that_only_looks_like_a_reserved_word_is_an_id(word):
    assert types(word) == ["ID"]


# ---------- Operators and delimiters ----------

@pytest.mark.parametrize("symbol, token_type", [
    ("+", "PLUS"), ("-", "MINUS"), ("*", "STAR"), ("/", "SLASH"), ("%", "PERCENT"),
    ("++", "INCREMENT"), ("--", "DECREMENT"),
    ("=", "ASSIGN"), ("+=", "PLUS_ASSIGN"), ("-=", "MINUS_ASSIGN"), ("*=", "STAR_ASSIGN"),
    ("/=", "SLASH_ASSIGN"), ("%=", "PERCENT_ASSIGN"),
    ("==", "EQUAL"), ("!=", "NOT_EQUAL"), ("<", "LESS"), (">", "GREATER"),
    ("<=", "LESS_EQUAL"), (">=", "GREATER_EQUAL"),
    ("&&", "AND"), ("||", "OR"), ("!", "NOT"),
    ("<<", "SHIFT_LEFT"), (">>", "SHIFT_RIGHT"),
    ("(", "LPAREN"), (")", "RPAREN"), ("{", "LBRACE"), ("}", "RBRACE"),
    (";", "SEMICOLON"), (",", "COMMA"), (":", "COLON"),
])
def test_symbol(symbol, token_type):
    assert tokenize(symbol)[0] == Token(token_type, symbol, 1, 1)


# ---------- Longest match ----------

@pytest.mark.parametrize("code, expected", [
    (">>", ["SHIFT_RIGHT"]),
    ("> >", ["GREATER", "GREATER"]),
    ("<<", ["SHIFT_LEFT"]),
    ("< <", ["LESS", "LESS"]),
    ("<=", ["LESS_EQUAL"]),
    ("< =", ["LESS", "ASSIGN"]),
    ("++", ["INCREMENT"]),
    ("+ +", ["PLUS", "PLUS"]),
    ("==", ["EQUAL"]),
    ("= =", ["ASSIGN", "ASSIGN"]),
    ("a+++b", ["ID", "INCREMENT", "PLUS", "ID"]),
    ("a---b", ["ID", "DECREMENT", "MINUS", "ID"]),
    ("x+=1", ["ID", "PLUS_ASSIGN", "INT_LITERAL"]),
    ("<<=", ["SHIFT_LEFT", "ASSIGN"]),
    ("!==", ["NOT_EQUAL", "ASSIGN"]),
    ("i<=n", ["ID", "LESS_EQUAL", "ID"]),
    ("cin>>x>>y", ["CIN", "SHIFT_RIGHT", "ID", "SHIFT_RIGHT", "ID"]),
])
def test_longest_match(code, expected):
    assert types(code) == expected


# ---------- Literals ----------

@pytest.mark.parametrize("code, token_type", [
    ("0", "INT_LITERAL"),
    ("42", "INT_LITERAL"),
    ("007", "INT_LITERAL"),
    ("3.14", "FLOAT_LITERAL"),
    ("0.5", "FLOAT_LITERAL"),
    ("10.0", "FLOAT_LITERAL"),
])
def test_number(code, token_type):
    assert tokenize(code)[0] == Token(token_type, code, 1, 1)


@pytest.mark.parametrize("code", [
    '"Hola"',
    '""',
    '"Hola mundo, 123"',
    '"Número inválido"',
    r'"linea\n"',
    r'"a\tb"',
    r'"barra \\ invertida"',
    r'"dice \"hola\""',
    r'"apostrofe \' "',
    '"// esto no es comentario"',
    '"/* tampoco */"',
])
def test_string_literal_keeps_its_lexeme(code):
    assert tokenize(code)[0] == Token("STRING_LITERAL", code, 1, 1)


@pytest.mark.parametrize("code", ["'a'", "'0'", "' '", "'\"'", r"'\n'", r"'\t'", r"'\\'", r"'\''"])
def test_char_literal(code):
    assert tokenize(code)[0] == Token("CHAR_LITERAL", code, 1, 1)


def test_negative_number_is_minus_and_number():
    assert types("-5") == ["MINUS", "INT_LITERAL"]


# ---------- Header ----------

@pytest.mark.parametrize("code", ["#include <iostream>", "#include <string>", "#include<iostream>"])
def test_include_is_one_token(code):
    assert tokenize(code)[0] == Token("INCLUDE", code, 1, 1)


def test_using_namespace_std():
    assert types("using namespace std;") == ["USING", "NAMESPACE", "STD", "SEMICOLON"]


def test_full_header():
    code = "#include <iostream>\n#include <string>\nusing namespace std;\n"
    assert types(code) == ["INCLUDE", "INCLUDE", "USING", "NAMESPACE", "STD", "SEMICOLON"]


# ---------- Comments and whitespace ----------

@pytest.mark.parametrize("code", [
    "x // comentario",
    "x // comentario con int y ; adentro",
    "x /* comentario */",
    "/* antes */ x",
    "/**/ x",
    "x /* a /* b */",
    "x\t\t",
    "\n\n  x  \n",
    "x // sin salto de linea al final",
])
def test_comments_and_whitespace_are_ignored(code):
    assert types(code) == ["ID"]


def test_division_is_not_a_comment():
    assert types("a / b") == ["ID", "SLASH", "ID"]
    assert types("a /= b") == ["ID", "SLASH_ASSIGN", "ID"]


def test_block_comment_can_span_lines():
    tokens = tokenize("/* linea 1\nlinea 2\nlinea 3 */ x")
    assert tokens[0] == Token("ID", "x", 3, 12)


def test_empty_code_and_only_comments_give_only_eof():
    assert tokenize("") == [Token("EOF", "", 1, 1)]
    assert [t.type for t in tokenize("// nada\n/* nada */\n")] == ["EOF"]


# ---------- Line and column ----------

def test_line_and_column():
    code = "int main() {\n    int x = 10;\n    return x;\n}"
    positions = [(t.lexeme, t.line, t.column) for t in tokenize(code)]
    assert positions == [
        ("int", 1, 1), ("main", 1, 5), ("(", 1, 9), (")", 1, 10), ("{", 1, 12),
        ("int", 2, 5), ("x", 2, 9), ("=", 2, 11), ("10", 2, 13), (";", 2, 15),
        ("return", 3, 5), ("x", 3, 12), (";", 3, 13),
        ("}", 4, 1),
        ("", 4, 2),
    ]


def test_windows_line_breaks():
    tokens = tokenize("int x;\r\nx = 1;\r\n")
    assert [(t.lexeme, t.line, t.column) for t in tokens[3:5]] == [("x", 2, 1), ("=", 2, 3)]


def test_tab_counts_as_one_column():
    assert tokenize("\tx")[0].column == 2


def test_eof_is_always_last():
    tokens = tokenize("int x = 5;")
    assert tokens[-1] == Token("EOF", "", 1, 11)
    assert [t.type for t in tokens].count("EOF") == 1


# ---------- Lexical errors ----------

@pytest.mark.parametrize("char", ["@", "$", "`", "~", "?", "&", "|", "^", "[", "]", ".", "\\"])
def test_unrecognized_character(char):
    error = lex_error(f"x = {char};")
    assert (error.line, error.column) == (1, 5)
    assert error.detail == f"carácter no reconocido '{char}'"


@pytest.mark.parametrize("char", ["ñ", "á", "²"])
def test_non_ascii_character_outside_strings(char):
    assert lex_error(f"int a{char} = 1;").detail == f"carácter no reconocido '{char}'"


def test_error_message_format():
    error = lex_error("int x;\nint y = 5 @ 3;")
    assert str(error) == "Error léxico en línea 2, columna 11: carácter no reconocido '@'"


@pytest.mark.parametrize("code", ['"Hola', 'cout << "Hola;', '"Hola\nmundo"', '"termina en \\'])
def test_unclosed_string(code):
    error = lex_error(code)
    assert error.detail == "cadena sin cerrar"


def test_unclosed_string_points_to_its_start():
    error = lex_error('int x;\ncout << "Hola;\n')
    assert (error.line, error.column) == (2, 9)


def test_invalid_escape():
    error = lex_error(r'"a\qb"')
    assert (error.column, error.detail) == (3, r"secuencia de escape no válida '\q'")


def test_unclosed_block_comment_points_to_its_start():
    error = lex_error("int x;\n  /* sin cerrar\nint y;")
    assert (error.line, error.column, error.detail) == (2, 3, "comentario sin cerrar")


def test_empty_char():
    assert lex_error("char c = '';").detail == "literal de carácter vacío ''"


def test_char_with_more_than_one_character():
    assert lex_error("char c = 'ab';").detail == "literal de carácter con más de un carácter"


@pytest.mark.parametrize("code", ["char c = 'a", "char c = 'a;\n", "'"])
def test_unclosed_char(code):
    assert lex_error(code).detail == "literal de carácter sin cerrar"


@pytest.mark.parametrize("code", ["3.14f", "5.", "1.2.3", "3x", "123abc", "0x1F", "2_000"])
def test_malformed_number(code):
    assert lex_error(code).detail == f"número mal formado '{code}'"


def test_number_without_integer_part():
    assert lex_error(".5").detail == "carácter no reconocido '.'"


def test_include_of_other_library():
    assert lex_error("#include <vector>").detail == "biblioteca no soportada '<vector>'"


@pytest.mark.parametrize("code, detail", [
    ("#define N 10", "directiva de preprocesador no soportada '#define'"),
    ("#pragma once", "directiva de preprocesador no soportada '#pragma'"),
    ('#include "iostream"', "#include mal formado, se esperaba #include <biblioteca>"),
    ("#include <iostream", "#include mal formado, se esperaba #include <biblioteca>"),
])
def test_unsupported_directive(code, detail):
    assert lex_error(code).detail == detail


def test_std_qualified_name_is_not_one_token():
    # std::cout is out of the subset: the lexer gives STD COLON COLON COUT
    # and the parser rejects it.
    assert types("std::cout") == ["STD", "COLON", "COLON", "COUT"]


# ---------- Complete program ----------

def test_example_program_from_the_specification():
    code = """#include <iostream>
using namespace std;

int factorial(int n) {
    int r = 1;
    for (int i = 2; i <= n; i++) {
        r *= i;
    }
    return r;
}
"""
    assert types(code) == [
        "INCLUDE",
        "USING", "NAMESPACE", "STD", "SEMICOLON",
        "INT", "ID", "LPAREN", "INT", "ID", "RPAREN", "LBRACE",
        "INT", "ID", "ASSIGN", "INT_LITERAL", "SEMICOLON",
        "FOR", "LPAREN", "INT", "ID", "ASSIGN", "INT_LITERAL", "SEMICOLON",
        "ID", "LESS_EQUAL", "ID", "SEMICOLON", "ID", "INCREMENT", "RPAREN", "LBRACE",
        "ID", "STAR_ASSIGN", "ID", "SEMICOLON",
        "RBRACE",
        "RETURN", "ID", "SEMICOLON",
        "RBRACE",
    ]


# ---------- Rule tables ----------

def rules_in_doc() -> list[tuple[str, str]]:
    """Read the "NAME  pattern" lines of the plain code blocks in docs/tokens.md.

    Blocks with a language (```mermaid) are diagrams and are skipped.
    """
    rules = []
    in_block = False
    plain_block = False

    for line in TOKENS_DOC.read_text(encoding="utf-8").splitlines():
        if line.startswith("```"):
            plain_block = not in_block and line == "```"
            in_block = not in_block
        elif plain_block:
            name, pattern = line.split(None, 1)
            rules.append((name, pattern))

    return rules


def test_doc_has_the_same_regular_expressions_as_the_lexer():
    assert rules_in_doc() == TOKEN_RULES + IGNORED_RULES + ERROR_RULES


def test_every_token_type_of_the_contract_has_a_rule():
    contract_types = {
        "INCLUDE", "USING", "NAMESPACE", "STD",
        "INT", "FLOAT", "DOUBLE", "CHAR", "BOOL", "STRING", "VOID",
        "IF", "ELSE", "WHILE", "DO", "FOR", "SWITCH", "CASE", "DEFAULT", "BREAK", "CONTINUE", "RETURN",
        "CIN", "COUT", "ENDL",
        "INT_LITERAL", "FLOAT_LITERAL", "STRING_LITERAL", "CHAR_LITERAL", "TRUE", "FALSE", "ID",
        "PLUS", "MINUS", "STAR", "SLASH", "PERCENT", "INCREMENT", "DECREMENT",
        "ASSIGN", "PLUS_ASSIGN", "MINUS_ASSIGN", "STAR_ASSIGN", "SLASH_ASSIGN", "PERCENT_ASSIGN",
        "EQUAL", "NOT_EQUAL", "LESS", "GREATER", "LESS_EQUAL", "GREATER_EQUAL",
        "AND", "OR", "NOT", "SHIFT_LEFT", "SHIFT_RIGHT",
        "LPAREN", "RPAREN", "LBRACE", "RBRACE", "SEMICOLON", "COMMA", "COLON",
    }
    rule_types = {name for name, _ in TOKEN_RULES} - {"ID"}
    assert rule_types | set(KEYWORDS.values()) | {"ID"} == contract_types


@pytest.mark.parametrize("code, token_type", [
    ("3.14", "FLOAT_LITERAL"),
    ("42", "INT_LITERAL"),
    ('"Hola"', "STRING_LITERAL"),
    ("'a'", "CHAR_LITERAL"),
    ("#include <iostream>", "INCLUDE"),
])
def test_valid_token_wins_a_tie_against_an_error_pattern(code, token_type):
    # The error pattern also matches the whole lexeme, but it comes later
    # in the table, so the valid token wins.
    assert tokenize(code)[0].type == token_type


def test_error_pattern_wins_when_it_is_longer():
    # FLOAT_LITERAL matches "3.14" (4 characters), BAD_NUMBER matches "3.14f" (5)
    assert lex_error("3.14f").detail == "número mal formado '3.14f'"


def test_escape_error_points_to_the_backslash():
    error = lex_error('int x;\ncout << "ok\\n y \\q";')
    assert (error.line, error.column) == (2, 17)
