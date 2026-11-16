"""LL(1) grammar verifier: FIRST, FOLLOW, parsing table, conflicts and class-notation output.

Usage: ``python -m verifier grammars/cpp.gram``.
"""

from .grammar import Grammar, GrammarError, Production, read_grammar, parse_grammar, validate
from .ll1 import Analysis, Conflict, analyze

__all__ = [
    "Analysis",
    "Conflict",
    "Grammar",
    "GrammarError",
    "Production",
    "analyze",
    "parse_grammar",
    "read_grammar",
    "validate",
]
