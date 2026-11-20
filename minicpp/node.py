from minicpp.tokens import Token

EPSILON = "ε"

class Node:
    """A node of the parse tree.

    Nonterminal nodes have children, terminal leaves have a token,
    and epsilon leaves have the label "ε" and nothing else.
    """

    def __init__(self, label: str, children: list["Node"] | None = None, token: Token | None = None):
        self.label = label             # nonterminal, token type or "ε"
        self.children = children or []
        self.token = token             # only on terminal leaves

    def is_epsilon(self) -> bool:
        """Return True if this node is an ε leaf."""
        return self.label == EPSILON

    def leaves(self) -> list[Token]:
        """Return the tokens of the terminal leaves from left to right, skipping ε.

        This is the yield (frontier) of the tree: the string it derives.
        """
        if self.token is not None:
            return [self.token]
        
        tokens = []

        for child in self.children:
            tokens.extend(child.leaves())

        return tokens

    def pretty(self, indent: int = 0) -> str:
        """Return the tree as indented text, one node per line (for debugging)."""
        text = "  " * indent + self.label

        if self.token is not None:
            text += f" '{self.token.lexeme}'"

        lines = [text]

        for child in self.children:
            lines.append(child.pretty(indent + 1))

        return "\n".join(lines)

    def __repr__(self) -> str:
        if self.token is not None:
            return f"Node({self.label!r}, token={self.token.lexeme!r})"
        
        return f"Node({self.label!r}, children={len(self.children)})"