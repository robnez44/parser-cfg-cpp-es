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


# Tokens from text (temporary, until the lexer exists)

SYMBOLS = {
    "+": "PLUS", "-": "MINUS", "*": "STAR", "/": "SLASH", "%": "PERCENT",
    "++": "INCREMENT", "--": "DECREMENT",
    "=": "ASSIGN", "+=": "PLUS_ASSIGN", "-=": "MINUS_ASSIGN",
    "*=": "STAR_ASSIGN", "/=": "SLASH_ASSIGN", "%=": "PERCENT_ASSIGN",
    "==": "EQUAL", "!=": "NOT_EQUAL",
    "<": "LESS", ">": "GREATER", "<=": "LESS_EQUAL", ">=": "GREATER_EQUAL",
    "&&": "AND", "||": "OR", "!": "NOT",
    "(": "LPAREN", ")": "RPAREN", ",": "COMMA", ";": "SEMICOLON",
}

def toks(source: str) -> list[Token]:
    """Build tokens from a string whose tokens are separated by spaces, e.g. "a * 2"."""
    pairs = []
    for word in source.split():
        if word in SYMBOLS:
            pairs.append((SYMBOLS[word], word))
        elif word in ("true", "false"):
            pairs.append((word.upper(), word))
        elif word.isdigit():
            pairs.append(("INT_LITERAL", word))
        elif word.replace(".", "", 1).isdigit():
            pairs.append(("FLOAT_LITERAL", word))
        elif word.startswith('"'):
            pairs.append(("STRING_LITERAL", word))
        elif word.startswith("'"):
            pairs.append(("CHAR_LITERAL", word))
        else:
            pairs.append(("ID", word))
    return make_tokens(*pairs)

def parse_with(method: str, source: str) -> Node:
    """Run one parser method on the source and check that it consumed everything."""
    parser = Parser(toks(source))
    tree = getattr(parser, method)()
    assert parser.current().type == "EOF"
    return tree

def text(node: Node) -> str:
    """Rebuild the source covered by a node from its leaves."""
    return " ".join(token.lexeme for token in node.leaves())

def labels(node: Node) -> list[str]:
    """Return the labels of the children of a node."""
    return [child.label for child in node.children]

# Primary and Literal

@pytest.mark.parametrize("source", ["42", "3.14", '"hola"', "'a'", "true", "false"])
def test_primary_accepts_every_literal(source):
    tree = parse_with("primary", source)
    assert labels(tree) == ["Literal"]
    assert text(tree) == source

def test_primary_identifier_has_epsilon_id_tail():
    tree = parse_with("primary", "x")
    assert labels(tree) == ["ID", "IdTail"]
    assert tree.children[1].children[0].is_epsilon()

def test_primary_function_call_with_arguments():
    tree = parse_with("primary", "f ( a , b * 2 )")
    id_tail = tree.children[1]
    assert labels(id_tail) == ["LPAREN", "Args", "RPAREN"]
    assert text(tree) == "f ( a , b * 2 )"

def test_primary_function_call_without_arguments():
    tree = parse_with("primary", "f ( )")
    args = tree.children[1].children[1]
    assert args.children[0].is_epsilon()

def test_primary_parenthesized_expression():
    tree = parse_with("primary", "( a * b )")
    assert tree.children[0].label == "LPAREN"
    assert tree.children[2].label == "RPAREN"
    assert text(tree) == "( a * b )"

def test_primary_rejects_operator():
    parser = Parser(toks("*"))
    with pytest.raises(SyntacticError) as info:
        parser.primary()
    assert info.value.found.type == "STAR"
    assert "ID" in info.value.expected

def test_unclosed_parenthesis():
    parser = Parser(toks("( a"))
    with pytest.raises(SyntacticError) as info:
        parser.primary()
    assert info.value.expected == ["RPAREN"]
    assert info.value.found.type == "EOF"

# Postfix and unary

def test_postfix_increment_on_variable():
    tree = parse_with("postfix_expr", "x ++")
    assert labels(tree) == ["Primary", "PostfixOpt"]
    assert tree.children[1].children[0].label == "INCREMENT"

def test_postfix_without_operator_has_epsilon():
    tree = parse_with("postfix_expr", "x")
    assert tree.children[1].children[0].is_epsilon()

@pytest.mark.parametrize("source", ["5 ++", "f ( ) --", "( x ) ++"])
def test_postfix_increment_needs_variable(source):
    parser = Parser(toks(source))
    with pytest.raises(SyntacticError) as info:
        parser.postfix_expr()
    assert info.value.expected == ["ID"]

def test_prefix_operators_nest_to_the_right():
    tree = parse_with("unary_expr", "- ! x")
    assert labels(tree) == ["UnaryOp", "UnaryExpr"]
    inner = tree.children[1]
    assert labels(inner) == ["UnaryOp", "UnaryExpr"]
    assert text(inner) == "! x"

def test_prefix_increment_on_variable():
    tree = parse_with("unary_expr", "++ x")
    assert text(tree) == "++ x"

@pytest.mark.parametrize("source", ["++ 5", "-- - x", "++ x ++"])
def test_prefix_increment_needs_variable(source):
    parser = Parser(toks(source))
    with pytest.raises(SyntacticError) as info:
        parser.unary_expr()
    assert info.value.expected == ["ID"]

# Multiplicative level 

def test_single_factor_has_epsilon_tail():
    tree = parse_with("mult_expr", "x")
    assert labels(tree) == ["UnaryExpr", "MultExprTail"]
    assert tree.children[1].children[0].is_epsilon()

def test_all_multiplicative_operators():
    tree = parse_with("mult_expr", "a * b / c % 2")
    assert text(tree) == "a * b / c % 2"

def test_tail_nests_one_operator_per_level():
    tree = parse_with("mult_expr", "a * b / c")
    first_tail = tree.children[1]
    assert labels(first_tail) == ["MultOp", "UnaryExpr", "MultExprTail"]
    assert text(first_tail.children[0]) == "*"
    second_tail = first_tail.children[2]
    assert text(second_tail.children[0]) == "/"
    assert second_tail.children[2].children[0].is_epsilon()

def test_unary_binds_tighter_than_multiplication():
    tree = parse_with("mult_expr", "- a * b")
    assert text(tree.children[0]) == "- a"

def test_mult_stops_at_token_outside_its_level():
    parser = Parser(toks("a + b"))
    tree = parser.mult_expr()
    assert text(tree) == "a"
    assert parser.current().type == "PLUS"

def test_missing_right_operand():
    parser = Parser(toks("a *"))
    with pytest.raises(SyntacticError) as info:
        parser.mult_expr()
    assert info.value.found.type == "EOF"

# Binary levels 

def test_additive_operators():
    tree = parse_with("additive_expr", "a + b - c")
    assert text(tree) == "a + b - c"
    assert text(tree.children[1].children[0]) == "+"

def test_multiplication_binds_tighter_than_addition():
    tree = parse_with("additive_expr", "a * b + c")
    assert text(tree.children[0]) == "a * b"

@pytest.mark.parametrize("op", ["<", ">", "<=", ">="])
def test_relational_operators(op):
    tree = parse_with("relational_expr", f"a {op} b + 1")
    assert text(tree.children[0]) == "a"
    assert text(tree.children[1].children[0]) == op
    assert text(tree.children[1].children[1]) == "b + 1"

@pytest.mark.parametrize("op", ["==", "!="])
def test_equality_operators(op):
    tree = parse_with("equality_expr", f"a < b {op} c > d")
    assert text(tree.children[0]) == "a < b"
    assert text(tree.children[1].children[1]) == "c > d"

def test_and_binds_tighter_than_or():
    tree = parse_with("or_expr", "a || b && c")
    assert text(tree.children[0]) == "a"
    assert text(tree.children[1].children[1]) == "b && c"

def test_each_level_takes_the_next_one_as_operand():
    tree = parse_with("expr", "a || b && c == d < e + f * g")
    or_expr = tree.children[0].children[0]
    and_expr = or_expr.children[1].children[1]
    equality = and_expr.children[1].children[1]
    relational = equality.children[1].children[1]
    additive = relational.children[1].children[1]
    mult = additive.children[1].children[1]
    assert text(and_expr) == "b && c == d < e + f * g"
    assert text(equality) == "c == d < e + f * g"
    assert text(relational) == "d < e + f * g"
    assert text(additive) == "e + f * g"
    assert text(mult) == "f * g"

def test_parentheses_override_precedence():
    tree = parse_with("mult_expr", "( a + b ) * c")
    assert text(tree.children[0]) == "( a + b )"

def test_missing_operand_after_binary_operator():
    parser = Parser(toks("a + * b"))
    with pytest.raises(SyntacticError) as info:
        parser.expr()
    assert info.value.found.type == "STAR"
    assert "ID" in info.value.expected

# ---------- Assignment and Expr ----------

def test_expr_wraps_assign_expr():
    tree = parse_with("expr", "x")
    assert labels(tree) == ["AssignExpr"]

def test_simple_assignment():
    tree = parse_with("assign_expr", "a = b + 1")
    assert labels(tree) == ["OrExpr", "AssignTail"]
    assert text(tree.children[1]) == "= b + 1"

@pytest.mark.parametrize("op", ["+=", "-=", "*=", "/=", "%="])
def test_compound_assignment(op):
    tree = parse_with("assign_expr", f"a {op} 2")
    assert text(tree.children[1].children[0]) == op

def test_assignment_is_right_associative():
    tree = parse_with("assign_expr", "a = b = c")
    inner = tree.children[1].children[1]
    assert inner.label == "AssignExpr"
    assert text(inner) == "b = c"

def test_assignment_inside_call_arguments():
    tree = parse_with("expr", "f ( a = 1 , b + 2 )")
    assert text(tree) == "f ( a = 1 , b + 2 )"

@pytest.mark.parametrize(
    ("source", "found"),
    [("a + b = c", "PLUS"), ("5 = x", "INT_LITERAL"), ("( a ) = b", "LPAREN"), ("a = b + c = d", "PLUS")],
)
def test_assignment_needs_variable(source, found):
    parser = Parser(toks(source))
    with pytest.raises(SyntacticError) as info:
        parser.expr()
    assert info.value.expected == ["ID"]
    assert info.value.found.type == found

def test_increment_error_points_after_the_variable():
    parser = Parser(toks("++ x ++"))
    with pytest.raises(SyntacticError) as info:
        parser.unary_expr()
    assert info.value.found.type == "INCREMENT"
    assert info.value.found.column == 3