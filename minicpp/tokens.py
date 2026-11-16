from dataclasses import dataclass

@dataclass
class Token:
    """A lexical unit produced by the lexer."""

    type: str      # token type name, e.g. "ID" or "SEMICOLON"
    lexeme: str    # text as it appears in the source code
    line: int      # starts at 1
    column: int    # starts at 1