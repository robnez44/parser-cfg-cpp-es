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


# ---------- Helpers ----------
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
        "Error sintáctico en línea 1, columna 1: se esperaba SEMICOLON y se encontró RBRACE ('}')"
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


# ---------- Node ----------
def test_leaves_skip_epsilon():
    a, plus, b = make_tokens(("ID", "a"), ("PLUS", "+"), ("ID", "b"))[:3]
    tree = Node(
        "E",
        [
            Node("ID", token=a),
            Node(
                "E'", [Node("PLUS", token=plus), Node("ID", token=b), Node("E'", [Node(EPSILON)])]
            ),
        ],
    )
    assert [t.lexeme for t in tree.leaves()] == ["a", "+", "b"]
    assert tree.children[1].children[2].children[0].is_epsilon()


# ---------- Tokens from text (temporary, until the lexer exists) ----------
SYMBOLS = {
    "+": "PLUS",
    "-": "MINUS",
    "*": "STAR",
    "/": "SLASH",
    "%": "PERCENT",
    "++": "INCREMENT",
    "--": "DECREMENT",
    "=": "ASSIGN",
    "+=": "PLUS_ASSIGN",
    "-=": "MINUS_ASSIGN",
    "*=": "STAR_ASSIGN",
    "/=": "SLASH_ASSIGN",
    "%=": "PERCENT_ASSIGN",
    "==": "EQUAL",
    "!=": "NOT_EQUAL",
    "<": "LESS",
    ">": "GREATER",
    "<=": "LESS_EQUAL",
    ">=": "GREATER_EQUAL",
    "&&": "AND",
    "||": "OR",
    "!": "NOT",
    "<<": "SHIFT_LEFT",
    ">>": "SHIFT_RIGHT",
    "(": "LPAREN",
    ")": "RPAREN",
    "{": "LBRACE",
    "}": "RBRACE",
    ",": "COMMA",
    ";": "SEMICOLON",
    ":": "COLON",
}

KEYWORDS = {
    "int",
    "float",
    "double",
    "char",
    "bool",
    "string",
    "void",
    "if",
    "else",
    "while",
    "do",
    "for",
    "switch",
    "case",
    "default",
    "break",
    "continue",
    "return",
    "cin",
    "cout",
    "endl",
    "true",
    "false",
    "using",
    "namespace",
    "std",
}


def toks(source: str) -> list[Token]:
    """Build tokens from a string whose tokens are separated by spaces, e.g. "a * 2"."""
    pairs = []
    for word in source.split():
        if word in SYMBOLS:
            pairs.append((SYMBOLS[word], word))
        elif word.startswith("#include"):
            pairs.append(("INCLUDE", word))
        elif word in KEYWORDS:
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


# ---------- Primary and Literal ----------
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


def test_primary_unclosed_parenthesis():
    parser = Parser(toks("( a"))
    with pytest.raises(SyntacticError) as info:
        parser.primary()
    assert info.value.expected == ["RPAREN"]
    assert info.value.found.type == "EOF"


# ---------- Postfix and unary ----------
def test_postfix_expr_increment_on_variable():
    tree = parse_with("postfix_expr", "x ++")
    assert labels(tree) == ["Primary", "PostfixOpt"]
    assert tree.children[1].children[0].label == "INCREMENT"


def test_postfix_expr_without_operator_has_epsilon():
    tree = parse_with("postfix_expr", "x")
    assert tree.children[1].children[0].is_epsilon()


@pytest.mark.parametrize("source", ["5 ++", "f ( ) --", "( x ) ++"])
def test_postfix_expr_increment_needs_variable(source):
    parser = Parser(toks(source))
    with pytest.raises(SyntacticError) as info:
        parser.postfix_expr()
    assert info.value.expected == ["ID"]


def test_unary_expr_prefix_operators_nest_to_the_right():
    tree = parse_with("unary_expr", "- ! x")
    assert labels(tree) == ["UnaryOp", "UnaryExpr"]
    inner = tree.children[1]
    assert labels(inner) == ["UnaryOp", "UnaryExpr"]
    assert text(inner) == "! x"


def test_unary_expr_prefix_increment_on_variable():
    tree = parse_with("unary_expr", "++ x")
    assert text(tree) == "++ x"


@pytest.mark.parametrize("source", ["++ 5", "-- - x", "++ x ++"])
def test_unary_expr_prefix_increment_needs_variable(source):
    parser = Parser(toks(source))
    with pytest.raises(SyntacticError) as info:
        parser.unary_expr()
    assert info.value.expected == ["ID"]


# ---------- Multiplicative level ----------
def test_mult_expr_single_factor_has_epsilon_tail():
    tree = parse_with("mult_expr", "x")
    assert labels(tree) == ["UnaryExpr", "MultExprTail"]
    assert tree.children[1].children[0].is_epsilon()


def test_mult_expr_all_operators():
    tree = parse_with("mult_expr", "a * b / c % 2")
    assert text(tree) == "a * b / c % 2"


def test_mult_expr_tail_nests_one_operator_per_level():
    tree = parse_with("mult_expr", "a * b / c")
    first_tail = tree.children[1]
    assert labels(first_tail) == ["MultOp", "UnaryExpr", "MultExprTail"]
    assert text(first_tail.children[0]) == "*"
    second_tail = first_tail.children[2]
    assert text(second_tail.children[0]) == "/"
    assert second_tail.children[2].children[0].is_epsilon()


def test_mult_expr_unary_binds_tighter():
    tree = parse_with("mult_expr", "- a * b")
    assert text(tree.children[0]) == "- a"


def test_mult_expr_stops_at_token_outside_its_level():
    parser = Parser(toks("a + b"))
    tree = parser.mult_expr()
    assert text(tree) == "a"
    assert parser.current().type == "PLUS"


def test_mult_expr_missing_right_operand():
    parser = Parser(toks("a *"))
    with pytest.raises(SyntacticError) as info:
        parser.mult_expr()
    assert info.value.found.type == "EOF"


# ---------- Binary levels ----------
def test_additive_expr_operators():
    tree = parse_with("additive_expr", "a + b - c")
    assert text(tree) == "a + b - c"
    assert text(tree.children[1].children[0]) == "+"


def test_additive_expr_multiplication_binds_tighter():
    tree = parse_with("additive_expr", "a * b + c")
    assert text(tree.children[0]) == "a * b"


@pytest.mark.parametrize("op", ["<", ">", "<=", ">="])
def test_relational_expr_operators(op):
    tree = parse_with("relational_expr", f"a {op} b + 1")
    assert text(tree.children[0]) == "a"
    assert text(tree.children[1].children[0]) == op
    assert text(tree.children[1].children[1]) == "b + 1"


@pytest.mark.parametrize("op", ["==", "!="])
def test_equality_expr_operators(op):
    tree = parse_with("equality_expr", f"a < b {op} c > d")
    assert text(tree.children[0]) == "a < b"
    assert text(tree.children[1].children[1]) == "c > d"


def test_or_expr_and_binds_tighter():
    tree = parse_with("or_expr", "a || b && c")
    assert text(tree.children[0]) == "a"
    assert text(tree.children[1].children[1]) == "b && c"


def test_expr_each_level_takes_the_next_one_as_operand():
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


def test_mult_expr_parentheses_override_precedence():
    tree = parse_with("mult_expr", "( a + b ) * c")
    assert text(tree.children[0]) == "( a + b )"


def test_expr_missing_operand_after_binary_operator():
    parser = Parser(toks("a + * b"))
    with pytest.raises(SyntacticError) as info:
        parser.expr()
    assert info.value.found.type == "STAR"
    assert "ID" in info.value.expected


# ---------- Assignment and Expr ----------
def test_expr_wraps_assign_expr():
    tree = parse_with("expr", "x")
    assert labels(tree) == ["AssignExpr"]


def test_assign_expr_simple():
    tree = parse_with("assign_expr", "a = b + 1")
    assert labels(tree) == ["OrExpr", "AssignTail"]
    assert text(tree.children[1]) == "= b + 1"


@pytest.mark.parametrize("op", ["+=", "-=", "*=", "/=", "%="])
def test_assign_expr_compound(op):
    tree = parse_with("assign_expr", f"a {op} 2")
    assert text(tree.children[1].children[0]) == op


def test_assign_expr_is_right_associative():
    tree = parse_with("assign_expr", "a = b = c")
    inner = tree.children[1].children[1]
    assert inner.label == "AssignExpr"
    assert text(inner) == "b = c"


def test_args_accept_an_assignment():
    tree = parse_with("expr", "f ( a = 1 , b + 2 )")
    assert text(tree) == "f ( a = 1 , b + 2 )"


@pytest.mark.parametrize(
    ("source", "found"),
    [
        ("a + b = c", "PLUS"),
        ("5 = x", "INT_LITERAL"),
        ("( a ) = b", "LPAREN"),
        ("a = b + c = d", "PLUS"),
    ],
)
def test_assign_expr_target_needs_variable(source, found):
    parser = Parser(toks(source))
    with pytest.raises(SyntacticError) as info:
        parser.expr()
    assert info.value.expected == ["ID"]
    assert info.value.found.type == found


def test_unary_expr_increment_error_points_after_the_variable():
    parser = Parser(toks("++ x ++"))
    with pytest.raises(SyntacticError) as info:
        parser.unary_expr()
    assert info.value.found.type == "INCREMENT"
    assert info.value.found.column == 3


# ---------- Declarations ----------
@pytest.mark.parametrize("type_name", ["int", "float", "double", "char", "bool", "string"])
def test_local_decl_of_each_type(type_name):
    tree = parse_with("local_decl", f"{type_name} x ;")
    assert labels(tree) == ["Type", "ID", "VarDeclTail", "SEMICOLON"]
    assert text(tree.children[0]) == type_name


def test_local_decl_with_several_variables():
    tree = parse_with("local_decl", "int a = 1 , b , c = a + 2 ;")
    declarators = tree.children[2].children[1]
    assert labels(declarators) == ["COMMA", "ID", "Initializer", "DeclaratorList"]
    assert text(declarators) == ", b , c = a + 2"


def test_local_decl_without_initializer_has_epsilon():
    tree = parse_with("local_decl", "int x ;")
    initializer = tree.children[2].children[0]
    assert initializer.children[0].is_epsilon()


@pytest.mark.parametrize(
    ("source", "expected"),
    [("int ;", ["ID"]), ("int x", ["SEMICOLON"]), ("int x = 1 b ;", ["SEMICOLON"])],
)
def test_local_decl_errors(source, expected):
    parser = Parser(toks(source))
    with pytest.raises(SyntacticError) as info:
        parser.local_decl()
    assert info.value.expected == expected


def test_stmt_void_is_not_a_variable_type():
    parser = Parser(toks("void x ;"))
    with pytest.raises(SyntacticError) as info:
        parser.stmt()
    assert info.value.found.type == "VOID"


# ---------- Statement selection ----------
@pytest.mark.parametrize(
    ("source", "kind"),
    [
        ("int x ;", "LocalDecl"),
        ("x = 1 ;", "ExprStmt"),
        ("f ( ) ;", "ExprStmt"),
        ("++ i ;", "ExprStmt"),
        ("if ( x ) ;", "IfStmt"),
        ("while ( x ) ;", "WhileStmt"),
        ("do ; while ( x ) ;", "DoWhileStmt"),
        ("for ( ; ; ) ;", "ForStmt"),
        ("switch ( x ) { }", "SwitchStmt"),
        ("break ;", "BreakStmt"),
        ("continue ;", "ContinueStmt"),
        ("return ;", "ReturnStmt"),
        ("cout << x ;", "CoutStmt"),
        ("cin >> x ;", "CinStmt"),
        ("{ }", "Block"),
        (";", "EmptyStmt"),
    ],
)
def test_stmt_chooses_by_first_token(source, kind):
    tree = parse_with("stmt", source)
    assert labels(tree) == [kind]


def test_stmt_rejects_token_that_cannot_start_a_statement():
    parser = Parser(toks(")"))
    with pytest.raises(SyntacticError) as info:
        parser.stmt()
    assert info.value.found.type == "RPAREN"
    assert "IF" in info.value.expected


def test_expr_stmt_needs_semicolon():
    parser = Parser(toks("x = 1"))
    with pytest.raises(SyntacticError) as info:
        parser.stmt()
    assert info.value.expected == ["SEMICOLON"]
    assert info.value.found.type == "EOF"


def test_return_stmt_with_and_without_value():
    assert parse_with("return_stmt", "return ;").children[1].children[0].is_epsilon()
    assert text(parse_with("return_stmt", "return x + 1 ;").children[1]) == "x + 1"


# ---------- Blocks ----------
def test_block_with_statements():
    tree = parse_with("block", "{ int x ; x = 1 ; { x ++ ; } }")
    stmt_list = tree.children[1]
    assert labels(stmt_list) == ["Stmt", "StmtList"]
    assert text(stmt_list.children[0]) == "int x ;"


def test_block_empty_has_epsilon_list():
    tree = parse_with("block", "{ }")
    assert tree.children[1].children[0].is_epsilon()


def test_block_unclosed():
    parser = Parser(toks("{ x = 1 ;"))
    with pytest.raises(SyntacticError) as info:
        parser.block()
    assert info.value.expected == ["RBRACE"]
    assert info.value.found.type == "EOF"


def test_stmt_list_stops_at_token_outside_first_of_stmt():
    parser = Parser(toks("x = 1 ; }"))
    parser.stmt_list()
    assert parser.current().type == "RBRACE"


# ---------- If and dangling else ----------
def test_if_stmt_without_else_has_epsilon():
    tree = parse_with("if_stmt", "if ( x > 0 ) y = 1 ;")
    assert tree.children[5].children[0].is_epsilon()


def test_if_stmt_with_else():
    tree = parse_with("if_stmt", "if ( x ) y = 1 ; else y = 2 ;")
    assert text(tree.children[5]) == "else y = 2 ;"


def test_if_stmt_dangling_else_binds_to_nearest_if():
    tree = parse_with("if_stmt", "if ( a ) if ( b ) x = 1 ; else x = 2 ;")
    outer_else = tree.children[5]
    inner_if = tree.children[4].children[0]
    assert outer_else.children[0].is_epsilon()
    assert inner_if.label == "IfStmt"
    assert text(inner_if.children[5]) == "else x = 2 ;"


def test_if_stmt_braces_attach_else_to_outer_if():
    tree = parse_with("if_stmt", "if ( a ) { if ( b ) x = 1 ; } else x = 2 ;")
    assert text(tree.children[5]) == "else x = 2 ;"


def test_if_stmt_else_if_chain():
    tree = parse_with("if_stmt", "if ( a ) x = 1 ; else if ( b ) x = 2 ; else x = 3 ;")
    second_if = tree.children[5].children[1].children[0]
    assert second_if.label == "IfStmt"
    assert text(second_if.children[5]) == "else x = 3 ;"


# ---------- Loops ----------
def test_while_stmt():
    tree = parse_with("while_stmt", "while ( i < n ) { i ++ ; }")
    assert text(tree.children[2]) == "i < n"


def test_do_while_stmt():
    tree = parse_with("do_while_stmt", "do x ++ ; while ( x < 10 ) ;")
    assert labels(tree) == ["DO", "Stmt", "WHILE", "LPAREN", "Expr", "RPAREN", "SEMICOLON"]


def test_do_while_stmt_needs_final_semicolon():
    parser = Parser(toks("do x ++ ; while ( x < 10 )"))
    with pytest.raises(SyntacticError) as info:
        parser.do_while_stmt()
    assert info.value.expected == ["SEMICOLON"]


def test_for_stmt_with_declaration():
    tree = parse_with("for_stmt", "for ( int i = 0 ; i < n ; i ++ ) s += i ;")
    assert labels(tree.children[2]) == ["LocalDecl"]
    assert text(tree.children[3]) == "i < n"
    assert text(tree.children[5]) == "i ++"


def test_for_stmt_with_expression_init():
    tree = parse_with("for_stmt", "for ( i = 0 ; i < n ; i ++ ) ;")
    assert labels(tree.children[2]) == ["OptExpr", "SEMICOLON"]


def test_for_stmt_with_all_parts_empty():
    tree = parse_with("for_stmt", "for ( ; ; ) break ;")
    for_init, condition, update = tree.children[2], tree.children[3], tree.children[5]
    assert for_init.children[0].children[0].is_epsilon()
    assert condition.children[0].is_epsilon()
    assert update.children[0].is_epsilon()


# ---------- Switch ----------
def test_switch_stmt_with_cases_and_default():
    tree = parse_with(
        "switch_stmt",
        "switch ( x ) { case 1 : y = 1 ; break ; case - 2 : case 'a' : default : y = 0 ; }",
    )
    first_case = tree.children[5].children[0]
    assert labels(first_case) == ["CASE", "CaseLabel", "COLON", "StmtList"]
    assert text(first_case.children[3]) == "y = 1 ; break ;"


@pytest.mark.parametrize("label", ["1", "- 2", "'a'", "true", "false"])
def test_case_label_accepts_literals(label):
    tree = parse_with("case_label", label)
    assert text(tree) == label


def test_case_label_rejects_variable():
    parser = Parser(toks("x"))
    with pytest.raises(SyntacticError) as info:
        parser.case_label()
    assert info.value.found.type == "ID"
    assert "INT_LITERAL" in info.value.expected


def test_case_without_statements_has_epsilon_list():
    tree = parse_with("case", "case 1 :")
    assert tree.children[3].children[0].is_epsilon()


# ---------- cin and cout ----------
def test_cout_stmt_with_several_items():
    tree = parse_with("cout_stmt", 'cout << "Total:" << x + 1 << endl ;')
    assert text(tree.children[2]) == '"Total:"'
    assert text(tree.children[3]) == "<< x + 1 << endl"


def test_cout_stmt_accepts_comparison_in_parentheses():
    tree = parse_with("cout_stmt", "cout << ( a < b ) ;")
    assert text(tree.children[2]) == "( a < b )"


def test_cout_stmt_rejects_comparison_without_parentheses():
    parser = Parser(toks("cout << a < b ;"))
    with pytest.raises(SyntacticError) as info:
        parser.cout_stmt()
    assert info.value.expected == ["SEMICOLON"]
    assert info.value.found.type == "LESS"


def test_cout_stmt_needs_shift_left():
    parser = Parser(toks("cout x ;"))
    with pytest.raises(SyntacticError) as info:
        parser.cout_stmt()
    assert info.value.expected == ["SHIFT_LEFT"]


def test_cin_stmt_with_several_variables():
    tree = parse_with("cin_stmt", "cin >> a >> b ;")
    assert text(tree.children[3]) == ">> b"


@pytest.mark.parametrize(
    ("source", "expected"),
    [("cin >> 5 ;", ["ID"]), ("cin >> a + 1 ;", ["SEMICOLON"]), ("cin << a ;", ["SHIFT_RIGHT"])],
)
def test_cin_stmt_errors(source, expected):
    parser = Parser(toks(source))
    with pytest.raises(SyntacticError) as info:
        parser.cin_stmt()
    assert info.value.expected == expected


# ---------- Program and header ----------
def parse_program(source: str) -> Node:
    """Parse a whole program written with tokens separated by spaces."""
    return Parser(toks(source)).parse()


def test_program_empty():
    tree = parse_program("")
    assert labels(tree) == ["Header", "GlobalList"]
    assert tree.leaves() == []


def test_header_full():
    tree = parse_program("#include<iostream> #include<string> using namespace std ;")
    header = tree.children[0]
    assert labels(header) == ["IncludeList", "UsingStd"]
    assert text(header) == "#include<iostream> #include<string> using namespace std ;"


@pytest.mark.parametrize("source", ["#include<iostream>", "using namespace std ;"])
def test_header_each_part_is_optional(source):
    tree = parse_program(source)
    assert text(tree.children[0]) == source


def test_using_std_needs_semicolon():
    with pytest.raises(SyntacticError) as info:
        parse_program("using namespace std int x ;")
    assert info.value.expected == ["SEMICOLON"]
    assert info.value.found.type == "INT"


# ---------- Global declarations and functions ----------
def test_global_decl_variables():
    tree = parse_program("int x = 5 , y ;")
    global_decl = tree.children[1].children[0]
    assert labels(global_decl) == ["Type", "ID", "GlobalDeclTail"]
    assert labels(global_decl.children[2]) == ["VarDeclTail", "SEMICOLON"]


def test_global_decl_function_with_parameters():
    tree = parse_program("int suma ( int a , int b ) { return a + b ; }")
    tail = tree.children[1].children[0].children[2]
    assert labels(tail) == ["LPAREN", "Params", "RPAREN", "Block"]
    assert text(tail.children[1]) == "int a , int b"


def test_global_decl_void_function_without_parameters():
    tree = parse_program('void saludar ( ) { cout << "hola" << endl ; }')
    global_decl = tree.children[1].children[0]
    assert labels(global_decl) == ["VOID", "ID", "LPAREN", "Params", "RPAREN", "Block"]
    assert global_decl.children[3].children[0].is_epsilon()


def test_global_list_several_declarations():
    tree = parse_program("int total ; void f ( ) { } int main ( ) { return 0 ; }")
    first = tree.children[1]
    second = first.children[1]
    third = second.children[1]
    assert text(first.children[0]) == "int total ;"
    assert text(second.children[0]) == "void f ( ) { }"
    assert text(third.children[0]) == "int main ( ) { return 0 ; }"
    assert third.children[1].children[0].is_epsilon()


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("void x ;", ["LPAREN"]),
        ("int f ( ) ;", ["LBRACE"]),
        ("int f ( int ) { }", ["ID"]),
        ("int main ( ) { int f ( ) { } }", ["SEMICOLON"]),
    ],
)
def test_global_decl_errors(source, expected):
    with pytest.raises(SyntacticError) as info:
        parse_program(source)
    assert info.value.expected == expected


def test_params_trailing_comma():
    with pytest.raises(SyntacticError) as info:
        parse_program("int f ( int a , ) { }")
    assert info.value.found.type == "RPAREN"
    assert "INT" in info.value.expected


# ---------- parse() and EOF ----------
def test_parse_rejects_extra_closing_brace():
    with pytest.raises(SyntacticError) as info:
        parse_program("int main ( ) { } }")
    assert info.value.found.type == "RBRACE"
    assert "EOF" in info.value.expected
    assert "VOID" in info.value.expected


def test_parse_rejects_statement_outside_function():
    with pytest.raises(SyntacticError) as info:
        parse_program("x = 1 ;")
    assert info.value.found.type == "ID"
    assert "EOF" in info.value.expected


def test_parse_rejects_include_after_declarations():
    with pytest.raises(SyntacticError) as info:
        parse_program("int x ; #include<iostream>")
    assert info.value.found.type == "INCLUDE"


# ---------- Complete program ----------
FACTORIAL = """
#include<iostream>
using namespace std ;

int factorial ( int n ) {
    int r = 1 ;
    for ( int i = 2 ; i <= n ; i ++ ) {
        r *= i ;
    }
    return r ;
}

int main ( ) {
    int n ;
    cin >> n ;
    if ( n < 0 )
        cout << "Numero_invalido" << endl ;
    else
        cout << "Factorial:" << factorial ( n ) << endl ;
    return 0 ;
}
"""


def test_program_complete_is_accepted():
    tree = parse_program(FACTORIAL)
    assert tree.label == "Program"
    assert text(tree) == " ".join(FACTORIAL.split())


def test_program_complete_tree_follows_the_grammar():
    tree = parse_program(FACTORIAL)
    functions = tree.children[1]
    factorial = functions.children[0]
    main = functions.children[1].children[0]
    assert text(factorial.children[1]) == "factorial"
    assert text(main.children[1]) == "main"
    assert functions.children[1].children[1].children[0].is_epsilon()