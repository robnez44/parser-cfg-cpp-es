from minicpp.tokens import Token

class LexicalError(Exception):
    """Raised by the lexer when it finds text that is not a valid token."""

    def __init__(self, line: int, column: int, detail: str):
        self.line = line
        self.column = column
        self.detail = detail
        super().__init__(f"Error léxico en línea {line}, columna {column}: {detail}")

class SyntacticError(Exception):
    """Raised by the parser when the next token does not fit the grammar."""

    def __init__(self, line: int, column: int, expected: list[str], found: Token):
        self.line = line
        self.column = column
        self.expected = expected
        self.found = found
        super().__init__(
            f"Error sintáctico en línea {line}, columna {column}: "
            f"{_describe_expected(expected)} y se encontró {_describe_found(found)}"
        )

def _describe_expected(expected: list[str]) -> str:
    if len(expected) == 1:
        return f"se esperaba {expected[0]}"
    
    return f"se esperaba uno de: {', '.join(expected)}"

def _describe_found(token: Token) -> str:
    if token.type == "EOF":
        return "EOF (fin del archivo)"
    
    return f"{token.type} ('{token.lexeme}')"

    class SemanticError(Exception):
    """Collected (not raised) by the semantic analyzer when the program breaks a rule."""

    def __init__(self, line: int, column: int, detail: str):
        self.line = line
        self.column = column
        self.detail = detail
        super().__init__(f"Error semántico en línea {line}, columna {column}: {detail}")