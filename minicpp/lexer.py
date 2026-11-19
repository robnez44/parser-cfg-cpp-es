"""Lexer for the C++ subset: turns source code into a list of tokens.

Every token is described by a regular expression (same tables as docs/tokens.md).
At each position the lexer keeps the longest match, and on a tie the first
rule wins, so a valid token beats an error pattern of the same length.
"""

import re
from typing import NoReturn

from minicpp.errors import LexicalError
from minicpp.tokens import KEYWORDS, Token

# Valid tokens. The order only matters for ties.
TOKEN_RULES = [
    ("INCLUDE", r"#[ \t]*include[ \t]*<(iostream|string)>"),
    ("FLOAT_LITERAL", r"[0-9]+\.[0-9]+"),
    ("INT_LITERAL", r"[0-9]+"),
    ("STRING_LITERAL", r'"([^"\\\n]|\\[nt\\"\'])*"'),
    ("CHAR_LITERAL", r"'([^'\\\n]|\\[nt\\\"'])'"),
    # identifiers and reserved words (see KEYWORDS)
    ("ID", r"[A-Za-z_][A-Za-z0-9_]*"),

    ("PLUS", r"\+"),
    ("MINUS", r"-"),
    ("STAR", r"\*"),
    ("SLASH", r"/"),
    ("PERCENT", r"%"),

    ("INCREMENT", r"\+\+"),
    ("DECREMENT", r"--"),

    ("ASSIGN", r"="),
    ("PLUS_ASSIGN", r"\+="),
    ("MINUS_ASSIGN", r"-="),
    ("STAR_ASSIGN", r"\*="),
    ("SLASH_ASSIGN", r"/="),
    ("PERCENT_ASSIGN", r"%="),

    ("EQUAL", r"=="),
    ("NOT_EQUAL", r"!="),
    ("LESS", r"<"),
    ("GREATER", r">"),
    ("LESS_EQUAL", r"<="),
    ("GREATER_EQUAL", r">="),

    ("AND", r"&&"),
    ("OR", r"\|\|"),
    ("NOT", r"!"),

    ("SHIFT_LEFT", r"<<"),
    ("SHIFT_RIGHT", r">>"),

    ("LPAREN", r"\("),
    ("RPAREN", r"\)"),
    ("LBRACE", r"\{"),
    ("RBRACE", r"\}"),
    ("SEMICOLON", r";"),
    ("COMMA", r","),
    ("COLON", r":"),
]

# Text that is read but does not produce a token.
IGNORED_RULES = [
    ("WHITESPACE", r"[ \t\r\n]+"),
    ("LINE_COMMENT", r"//[^\n]*"),
    ("BLOCK_COMMENT", r"/\*([^*]|\*+[^*/])*\*+/"),
]

# Error patterns. They only win when they match more text than any valid
# token, for example "3.14f" (5 characters) against "3.14" (4 characters).
ERROR_RULES = [
    ("BAD_NUMBER", r"[0-9][0-9A-Za-z_.]*"),
    ("BAD_STRING", r'"([^"\\\n]|\\.)*"?'),
    ("BAD_CHAR", r"'([^'\\\n]|\\.)*'?"),
    ("BAD_COMMENT", r"/\*([^*]|\*+[^*/])*\**\Z"),
    ("BAD_DIRECTIVE", r'#[ \t]*[A-Za-z_]*[ \t]*(<[A-Za-z_]*>?|"[^"\n]*"?)?'),
]

RULES = [
    (token_type, re.compile(pattern))
    for token_type, pattern in TOKEN_RULES + IGNORED_RULES + ERROR_RULES
]
IGNORED = {token_type for token_type, _ in IGNORED_RULES}
ERRORS = {token_type for token_type, _ in ERROR_RULES}

ESCAPES = "nt\\\"'"     # characters allowed after a backslash
DIRECTIVE = re.compile(r"#[ \t]*([A-Za-z_]*)[ \t]*(.*)")
LIBRARY = re.compile(r"<([A-Za-z_]+)>$")


def tokenize(code: str) -> list[Token]:
    """Return the tokens of the code. The list always ends with an EOF token."""
    return Lexer(code).tokenize()


class Lexer:
    """Reads the code from left to right and keeps track of line and column."""

    def __init__(self, code: str):
        self.code = code
        self.pos = 0       # index of the next character to read
        self.line = 1
        self.column = 1

    def tokenize(self) -> list[Token]:
        tokens = []

        while self.pos < len(self.code):
            token_type, text = self.longest_match()

            if token_type is None:
                self.error(f"carácter no reconocido '{self.code[self.pos]}'")
            if token_type in ERRORS:
                self.report(token_type, text)
            if token_type == "ID":
                token_type = KEYWORDS.get(text, "ID")
            if token_type not in IGNORED:
                tokens.append(Token(token_type, text, self.line, self.column))

            self.advance(text)

        tokens.append(Token("EOF", "", self.line, self.column))
        return tokens

    def longest_match(self) -> tuple[str | None, str]:
        """Return the longest match at the current position (first rule on a tie)."""
        best_type, best_text = None, ""

        for token_type, pattern in RULES:
            match = pattern.match(self.code, self.pos)
            if match and len(match.group()) > len(best_text):
                best_type, best_text = token_type, match.group()

        return best_type, best_text

    def advance(self, text: str) -> None:
        self.pos += len(text)
        newlines = text.count("\n")

        if newlines == 0:
            self.column += len(text)
        else:
            self.line += newlines
            self.column = len(text) - text.rfind("\n")

    # Lexical errors

    def error(self, detail: str, offset: int = 0) -> NoReturn:
        """Raise a LexicalError at the current position, moved offset columns."""
        raise LexicalError(self.line, self.column + offset, detail)

    def report(self, token_type: str, text: str) -> NoReturn:
        if token_type == "BAD_NUMBER":
            self.error(f"número mal formado '{text}'")
        if token_type == "BAD_COMMENT":
            self.error("comentario sin cerrar")
        if token_type == "BAD_DIRECTIVE":
            self.report_directive(text)
        if token_type == "BAD_STRING":
            self.report_string(text)
        self.report_char(text)

    def report_string(self, text: str) -> NoReturn:
        self.check_escapes(text)
        self.error("cadena sin cerrar")

    def report_char(self, text: str) -> NoReturn:
        closed = len(text) > 1 and text.endswith("'")

        if not closed:
            self.error("literal de carácter sin cerrar")
        if text == "''":
            self.error("literal de carácter vacío ''")
        self.check_escapes(text)
        self.error("literal de carácter con más de un carácter")

    def check_escapes(self, text: str) -> None:
        """Raise at the first bad escape. Literals stay on one line, so its column
        is the current column plus its index in the lexeme."""
        i = find_bad_escape(text)
        if i is not None:
            self.error(f"secuencia de escape no válida '{text[i:i + 2]}'", i)

    def report_directive(self, text: str) -> NoReturn:
        name, rest = DIRECTIVE.match(text).groups()

        if name != "include":
            self.error(f"directiva de preprocesador no soportada '#{name}'")

        library = LIBRARY.match(rest)
        if library is None:
            self.error("#include mal formado, se esperaba #include <biblioteca>")
        self.error(f"biblioteca no soportada '<{library.group(1)}>'")


def find_bad_escape(text: str) -> int | None:
    """Return the index of the first backslash not followed by n, t, \\, " or '."""
    i = 0

    while i < len(text):
        if text[i] == "\\":
            if i + 1 < len(text) and text[i + 1] in ESCAPES:
                i += 2
                continue
            return i
        i += 1

    return None
