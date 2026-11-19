from dataclasses import dataclass


@dataclass
class Token:
    type: str
    lexeme: str
    line: int      # lines and columns start at 1
    column: int


# Reserved words: the lexer matches them as ID and then looks them up here.
KEYWORDS = {
    "using": "USING",
    "namespace": "NAMESPACE",
    "std": "STD",

    "int": "INT",
    "float": "FLOAT",
    "double": "DOUBLE",
    "char": "CHAR",
    "bool": "BOOL",
    "string": "STRING",
    "void": "VOID",

    "if": "IF",
    "else": "ELSE",
    "while": "WHILE",
    "do": "DO",
    "for": "FOR",
    "switch": "SWITCH",
    "case": "CASE",
    "default": "DEFAULT",
    "break": "BREAK",
    "continue": "CONTINUE",
    "return": "RETURN",

    "cin": "CIN",
    "cout": "COUT",
    "endl": "ENDL",

    "true": "TRUE",
    "false": "FALSE",
}
