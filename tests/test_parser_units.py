import pytest

from minicpp.errors import SyntacticError
from minicpp.node import EPSILON, Node
from minicpp.parser import Parser
from minicpp.tokens import Token

def make_tokens(*pairs: tuple[str, str]) -> list[Token]:
    """Build a token list by hand, all on line 1, ending with EOF."""
    tokens = [Token(type_, lexeme, 1, i + 1) for i, (type_, lexeme) in enumerate(pairs)]
    tokens.append(Token("EOF", "", 1, len(pairs) + 1))
    return tokens

# Helpers 

def test_consume_returns_leaf_and_advances():
    parser = Parser(make_tokens(("ID", "x"), ("SEMICOLON", ";")))
    leaf = parser.consume("ID")
    assert leaf.label == "ID"
    assert leaf.token.lexeme == "x"
    assert parser.current().type == "SEMICOLON"

def test_consume_wrong_type_raises_error():
    parser = Parser(make_tokens(("RBRACE", "}")))
    with pytest.raises(SyntacticError) as info:
        parser.consume("SEMICOLON")
    assert info.value.expected == ["SEMICOLON"]
    assert info.value.found.type == "RBRACE"
    assert str(info.value) == (
        "Error sintáctico en línea 1, columna 1: "
        "se esperaba SEMICOLON y se encontró RBRACE ('}')"
    )

def test_consume_at_end_of_file_raises_error():
    parser = Parser(make_tokens())
    with pytest.raises(SyntacticError) as info:
        parser.consume("SEMICOLON")
    assert "EOF (fin del archivo)" in str(info.value)

def test_check_accepts_several_types():
    parser = Parser(make_tokens(("PLUS", "+")))
    assert parser.check("PLUS", "MINUS")
    assert not parser.check("STAR")

def test_epsilon_returns_epsilon_leaf():
    parser = Parser(make_tokens())
    assert parser.epsilon().is_epsilon()

# Node 

def test_leaves_skip_epsilon():
    a, plus, b = make_tokens(("ID", "a"), ("PLUS", "+"), ("ID", "b"))[:3]
    tree = Node("E", [
        Node("ID", token=a),
        Node("E'", [Node("PLUS", token=plus), Node("ID", token=b), Node("E'", [Node(EPSILON)])]),
    ])
    assert [t.lexeme for t in tree.leaves()] == ["a", "+", "b"]
    assert tree.children[1].children[2].children[0].is_epsilon()