import pytest

from minicpp.lexer import tokenize
from minicpp.node import EPSILON, Node
from minicpp.parser import Parser
from minicpp.visualization import show, to_nltk, to_outline

PROGRAM = "int main() {\n    int x = 2 + 3 * 4;\n    return 0;\n}\n"


def parse(code: str) -> Node:
    return Parser(tokenize(code)).parse()


def test_leaves_of_the_drawing_read_the_program():
    tree = to_nltk(parse(PROGRAM), compact=True)
    assert tree.leaves() == ["int", "main", "(", ")", "{", "int", "x", "=", "2", "+",
                             "3", "*", "4", ";", "return", "0", ";", "}"]


def test_full_tree_keeps_epsilon_leaves_and_compact_hides_them():
    root = parse(PROGRAM)
    assert EPSILON in to_nltk(root).leaves()
    assert EPSILON not in to_nltk(root, compact=True).leaves()


def test_compact_does_not_change_the_parse_tree():
    root = parse(PROGRAM)
    before = root.pretty()
    to_nltk(root, compact=True)
    assert root.pretty() == before


def test_drawing_keeps_the_labels_of_the_grammar():
    tree = to_nltk(parse(PROGRAM))
    assert tree.label() == "Program"
    labels = {subtree.label() for subtree in tree.subtrees()}
    assert {"Header", "GlobalList", "AdditiveExprTail", "MultExprTail", "INT_LITERAL"} <= labels


def test_terminal_is_type_over_lexeme():
    tree = to_nltk(parse(PROGRAM), compact=True)
    terminal = next(t for t in tree.subtrees() if t.label() == "ID")
    assert terminal.leaves() == ["main"]


def test_outline_has_one_node_per_line():
    outline = to_outline(parse(PROGRAM), compact=True).splitlines()
    assert outline[0] == "Program"
    assert outline[1] == "└── GlobalList"
    assert any(line.endswith("STAR '*'") for line in outline)


def test_unknown_view_raises_error():
    with pytest.raises(ValueError):
        show(parse(PROGRAM), view="svg")
