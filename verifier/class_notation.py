"""Convert a .gram grammar to the notation used in class (BNF with <angle brackets>).

  AdditiveExprTail -> AdditiveOp MultExpr AdditiveExprTail | ε

becomes

  <additive_expr_tail> ::= <additive_op> <mult_expr> <additive_expr_tail>
                         | ε

Terminals are shown with their lexeme (``SEMICOLON`` becomes ``";"``). Terminals that stand for a
whole lexical category (``ID``, ``INT_LITERAL``, ...) become ``<identifier>``, ``<int_literal>``,
and are defined in a final "Lexical level" section, because the lexer recognizes them, not the parser.
"""

from __future__ import annotations

import re

from .grammar import EPSILON, Grammar
from .ll1 import Analysis

# Token type -> lexeme (CONTRATO.md, section 4).
TOKEN_LEXEMES: dict[str, str] = {
    "USING": "using", "NAMESPACE": "namespace", "STD": "std",
    "INT": "int", "FLOAT": "float", "DOUBLE": "double", "CHAR": "char", "BOOL": "bool",
    "STRING": "string", "VOID": "void",
    "IF": "if", "ELSE": "else", "WHILE": "while", "DO": "do", "FOR": "for", "SWITCH": "switch",
    "CASE": "case", "DEFAULT": "default", "BREAK": "break", "CONTINUE": "continue", "RETURN": "return",
    "CIN": "cin", "COUT": "cout", "ENDL": "endl",
    "TRUE": "true", "FALSE": "false",
    "PLUS": "+", "MINUS": "-", "STAR": "*", "SLASH": "/", "PERCENT": "%",
    "INCREMENT": "++", "DECREMENT": "--",
    "ASSIGN": "=", "PLUS_ASSIGN": "+=", "MINUS_ASSIGN": "-=", "STAR_ASSIGN": "*=",
    "SLASH_ASSIGN": "/=", "PERCENT_ASSIGN": "%=",
    "EQUAL": "==", "NOT_EQUAL": "!=", "LESS": "<", "GREATER": ">",
    "LESS_EQUAL": "<=", "GREATER_EQUAL": ">=",
    "AND": "&&", "OR": "||", "NOT": "!",
    "SHIFT_LEFT": "<<", "SHIFT_RIGHT": ">>",
    "LPAREN": "(", "RPAREN": ")", "LBRACE": "{", "RBRACE": "}",
    "SEMICOLON": ";", "COMMA": ",", "COLON": ":",
}

# Token types that stand for a lexical category, shown as <name> and defined at the end.
LEXICAL_CATEGORIES: dict[str, str] = {
    "INCLUDE": "include_directive",
    "ID": "identifier",
    "INT_LITERAL": "int_literal",
    "FLOAT_LITERAL": "float_literal",
    "STRING_LITERAL": "string_literal",
    "CHAR_LITERAL": "char_literal",
}

# Definition of each lexical category: (alternatives, continuation lines).
_LEXICAL_DEFINITIONS: dict[str, list[str]] = {
    "include_directive": ['"#include <iostream>"', '"#include <string>"'],
    "identifier": ['a letter or "_", followed by letters, digits or "_"', '(must not be a reserved word)'],
    "int_literal": ["one or more digits"],
    "float_literal": ['one or more digits "." one or more digits'],
    "string_literal": ["'\"' characters without a newline '\"'", "(accepted escapes: \\n \\t \\\\ \\\" \\')"],
    "char_literal": ['"\'" one character or one escape "\'"'],
}
# For these, every entry is an alternative (joined with "|"); for the rest, entries are continuation lines.
_LEXICAL_ALTERNATIVES = {"include_directive"}


def to_snake_case(name: str) -> str:
    """``AdditiveExprTail`` -> ``additive_expr_tail``."""
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def _terminal(symbol: str) -> str:
    if symbol in LEXICAL_CATEGORIES:
        return f"<{LEXICAL_CATEGORIES[symbol]}>"
    return f'"{TOKEN_LEXEMES.get(symbol, symbol)}"'


def _symbol(grammar: Grammar, symbol: str) -> str:
    if grammar.is_nonterminal(symbol):
        return f"<{to_snake_case(symbol)}>"
    return _terminal(symbol)


def _rhs(grammar: Grammar, rhs: tuple[str, ...]) -> str:
    return " ".join(_symbol(grammar, s) for s in rhs) if rhs else EPSILON


def _rule_lines(grammar: Grammar, nonterminal: str) -> list[str]:
    head = f"<{to_snake_case(nonterminal)}> ::= "
    indent = " " * (len(head) - 2)  # aligns "|" under the "=" of "::="
    alternatives = [_rhs(grammar, p.rhs) for p in grammar.productions_of(nonterminal)]
    lines = [head + alternatives[0]]
    lines.extend(f"{indent}| {alternative}" for alternative in alternatives[1:])
    return lines


def _header(grammar: Grammar, analysis: Analysis, source_name: str, source_path: str) -> list[str]:
    from .grammar import left_recursion_cycles

    if grammar.title:
        title = f"# LL(1) grammar for {grammar.title}, in class notation."
    else:
        title = "# LL(1) grammar in class notation."
    clean = not left_recursion_cycles(grammar) and not any(c.kind == "FIRST/FIRST" for c in analysis.conflicts)
    if clean:
        lines = [
            title,
            f"# Same grammar as {source_name}, rule by rule: no left recursion and no alternatives",
            "# sharing a common prefix. ε is the empty string.",
        ]
    else:
        lines = [title, f"# Same grammar as {source_name}, rule by rule. ε is the empty string."]

    conflicts = analysis.conflicts
    if len(conflicts) == 1:
        conflict = conflicts[0]
        chosen = next((p for p in conflict.productions if p.rhs), conflict.productions[0])
        lines.append(
            f"# Only LL(1) conflict: <{to_snake_case(conflict.nonterminal)}>. "
            f'On {_terminal(conflict.terminal)}, the parser chooses {_rhs(grammar, chosen.rhs)}.'
        )
    elif len(conflicts) > 1:
        names = ", ".join(sorted({f"<{to_snake_case(c.nonterminal)}>" for c in conflicts}))
        lines.append(f"# LL(1) conflicts: {names}.")
    lines.append(
        f"# Generated from {source_name} (python -m verifier {source_path} --class-notation). Do not edit by hand."
    )
    return lines


def _lexical_level(used: list[str]) -> list[str]:
    lines = [
        "# Lexical level",
        "# These categories are recognized by the lexer with regular expressions (type 3 languages).",
        "# The parser receives them as tokens, so they are not defined with syntactic rules.",
    ]
    for name in used:
        head = f"<{name}> ::= "
        indent = " " * len(head)
        entries = _LEXICAL_DEFINITIONS[name]
        lines.append("")
        if name in _LEXICAL_ALTERNATIVES:
            lines.append(head + entries[0])
            lines.extend(f"{' ' * (len(head) - 2)}| {entry}" for entry in entries[1:])
        else:
            lines.append(head + entries[0])
            lines.extend(f"{indent}{entry}" for entry in entries[1:])
    return lines


def convert(grammar: Grammar, analysis: Analysis, source_path: str = "grammars/cpp.gram") -> str:
    """Return the grammar in class notation, ending with a newline."""
    source_name = source_path.replace("\\", "/").rsplit("/", 1)[-1]
    out: list[str] = _header(grammar, analysis, source_name, source_path)

    first_section = True
    for nonterminal in grammar.nonterminals:
        if nonterminal in grammar.sections:
            out.append("")
            if not first_section:
                out.append("")
            out.append(f"# {grammar.sections[nonterminal]}")
            first_section = False
        elif nonterminal != grammar.nonterminals[0]:
            out.append("")
        elif not grammar.sections:
            out.append("")
        out.extend(_rule_lines(grammar, nonterminal))

    used = [name for token, name in LEXICAL_CATEGORIES.items() if any(
        token in p.rhs for p in grammar.productions
    )]
    if used:
        out.append("")
        out.extend(_lexical_level(used))
    return "\n".join(out) + "\n"
