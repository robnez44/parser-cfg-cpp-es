"""Draws the parse tree with nltk.Tree in one of three views.

- console: the tree drawn with text in the terminal.
- window: an nltk window (needs tkinter and a display); falls back to console.
- outline: one node per line, for trees too wide for the terminal.

Each terminal leaf has two levels, the token type and the lexeme below it, so
the leaves of the drawing read the program from left to right.
"""

import warnings

from nltk import Tree

from minicpp.node import EPSILON, Node

VIEWS = ("console", "window", "outline")


def to_nltk(node: Node, compact: bool = False) -> Tree | str:
    """Convert a Node into an nltk.Tree.

    With compact=True, the branches that only derive ε are hidden. This only
    changes the drawing: the parse tree itself still follows the grammar.
    """
    if node.token is not None:
        return Tree(node.label, [node.token.lexeme])

    if node.is_epsilon():
        return EPSILON

    children = [
        to_nltk(child, compact)
        for child in node.children
        if not (compact and derives_only_epsilon(child))
    ]
    return Tree(node.label, children)


def derives_only_epsilon(node: Node) -> bool:
    """Return True if the subtree has no terminal leaves (its yield is ε)."""
    return not node.leaves()


def to_outline(node: Node, compact: bool = False) -> str:
    lines = [describe(node)]
    add_children(node, "", lines, compact)
    return "\n".join(lines)


def add_children(node: Node, prefix: str, lines: list[str], compact: bool) -> None:
    children = [
        child for child in node.children if not (compact and derives_only_epsilon(child))
    ]

    for index, child in enumerate(children):
        is_last = index == len(children) - 1
        connector = "└── " if is_last else "├── "
        lines.append(prefix + connector + describe(child))
        add_children(child, prefix + ("    " if is_last else "│   "), lines, compact)


def describe(node: Node) -> str:
    if node.token is not None:
        return f"{node.label} '{node.token.lexeme}'"

    return node.label


def show(node: Node, view: str = "console", compact: bool = False) -> None:
    if view not in VIEWS:
        raise ValueError(f"vista desconocida '{view}', opciones: {', '.join(VIEWS)}")

    if view == "outline":
        print(to_outline(node, compact))
        return

    tree = to_nltk(node, compact)

    if view == "window":
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")  # nltk warns on import when tkinter is missing
                tree.draw()
            return
        except Exception as error:  # no tkinter or no display (e.g. a server)
            print(f"No se pudo abrir la ventana ({error}); se muestra en la consola.")

    tree.pretty_print(unicodelines=True)
