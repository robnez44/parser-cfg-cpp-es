"""Reader and validator for the grammar file format (CONTRATO.md, section 5).

Format summary:
  - One rule per line: ``A -> alternative1 | alternative2``.
  - Symbols are separated by spaces; ``ε`` is the empty string.
  - A symbol is a nonterminal if it has a rule; every other symbol is a terminal.
  - The first rule defines the start symbol.
  - ``EOF`` is never written in the grammar: the verifier uses ``$``.
  - Lines starting with ``#`` are comments. Three comment shapes carry information:
      ``# ---------- Title ----------``                 starts a section (used by --class-notation)
      ``# Grammar for <what>``                           title of the grammar (first comment)
      ``# Accepted LL(1) conflict: M[NonTerminal, TOKEN]``  conflict the team decided to accept
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

EPSILON = "ε"
END_MARKER = "$"

_SECTION_RE = re.compile(r"^#\s*-{2,}\s*(?P<title>.+?)\s*-{2,}\s*$")
_ACCEPTED_RE = re.compile(
    r"^#\s*Accepted LL\(1\) conflicts?:\s*M\[\s*(?P<nt>[^,\]\s]+)\s*,\s*(?P<t>[^\]\s]+)\s*\]"
)
_TITLE_RE = re.compile(r"^#\s*Grammar for (?P<what>.+?)\s*$")

# A symbol that looks like a nonterminal (CamelCase, a single capital, optional primes)
# but has no rule is almost certainly a typo.
_NONTERMINAL_LIKE_RE = re.compile(r"[A-Z]'*|[A-Z][A-Za-z0-9]*[a-z][A-Za-z0-9]*'*")


class GrammarError(Exception):
    """The grammar file is malformed. The message is shown to the user, in Spanish."""

    def __init__(self, message: str, line: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.line = line

    def __str__(self) -> str:
        if self.line is None:
            return self.message
        return f"línea {self.line}: {self.message}"


@dataclass(frozen=True)
class Production:
    """One alternative of a rule. An empty ``rhs`` is the empty string ε."""

    lhs: str
    rhs: tuple[str, ...]
    line: int

    def __str__(self) -> str:
        return f"{self.lhs} -> {' '.join(self.rhs) if self.rhs else EPSILON}"


@dataclass(frozen=True)
class Diagnostic:
    """A problem found by :func:`validate`. ``level`` is ``"error"`` or ``"warning"``."""

    level: str
    message: str
    line: int | None = None

    def __str__(self) -> str:
        label = "Error" if self.level == "error" else "Aviso"
        where = f" en la línea {self.line}" if self.line is not None else ""
        return f"{label}{where}: {self.message}"


@dataclass
class Grammar:
    start: str
    productions: list[Production]
    nonterminals: list[str]
    terminals: list[str]
    sections: dict[str, str] = field(default_factory=dict)  # first nonterminal of a section -> title
    title: str | None = None
    accepted_conflicts: set[tuple[str, str]] = field(default_factory=set)
    _by_lhs: dict[str, list[Production]] = field(init=False, repr=False, default_factory=dict)

    def __post_init__(self) -> None:
        self._by_lhs = {nt: [] for nt in self.nonterminals}
        for production in self.productions:
            self._by_lhs[production.lhs].append(production)

    def productions_of(self, nonterminal: str) -> list[Production]:
        return self._by_lhs[nonterminal]

    def is_nonterminal(self, symbol: str) -> bool:
        return symbol in self._by_lhs


def parse_grammar(text: str) -> Grammar:
    """Parse the text of a grammar file. Raises :class:`GrammarError` with the offending line."""
    productions: list[Production] = []
    nonterminals: list[str] = []
    sections: dict[str, str] = {}
    accepted: set[tuple[str, str]] = set()
    title: str | None = None
    pending_section: str | None = None

    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue

        if line.startswith("#"):
            if (match := _SECTION_RE.match(line)) is not None:
                pending_section = match.group("title")
            elif (match := _ACCEPTED_RE.match(line)) is not None:
                accepted.add((match.group("nt"), match.group("t")))
            elif title is None and not productions and (match := _TITLE_RE.match(line)) is not None:
                title = match.group("what")
            continue

        if "->" not in line:
            raise GrammarError("se esperaba una regla con la forma 'A -> alternativa'", number)

        lhs_text, rhs_text = line.split("->", 1)
        lhs_symbols = lhs_text.split()
        if len(lhs_symbols) != 1:
            raise GrammarError("el lado izquierdo de una regla debe ser un solo símbolo", number)
        lhs = lhs_symbols[0]
        if lhs in (EPSILON, END_MARKER, "EOF"):
            raise GrammarError(f"'{lhs}' no puede ser el lado izquierdo de una regla", number)

        for alternative in rhs_text.split("|"):
            symbols = alternative.split()
            if not symbols:
                raise GrammarError("alternativa vacía: usa ε para la cadena vacía", number)
            if EPSILON in symbols and len(symbols) > 1:
                raise GrammarError("ε no puede mezclarse con otros símbolos en una alternativa", number)
            for symbol in symbols:
                if symbol in (END_MARKER, "EOF"):
                    raise GrammarError(
                        f"'{symbol}' no se escribe en la gramática: el verificador usa $ como fin de entrada",
                        number,
                    )
            rhs = () if symbols == [EPSILON] else tuple(symbols)
            productions.append(Production(lhs, rhs, number))

        if lhs not in nonterminals:
            nonterminals.append(lhs)
            if pending_section is not None:
                sections[lhs] = pending_section
                pending_section = None

    if not productions:
        raise GrammarError("la gramática no tiene reglas")

    defined = set(nonterminals)
    terminals: list[str] = []
    for production in productions:
        for symbol in production.rhs:
            if symbol not in defined and symbol not in terminals:
                terminals.append(symbol)

    return Grammar(
        start=nonterminals[0],
        productions=productions,
        nonterminals=nonterminals,
        terminals=terminals,
        sections=sections,
        title=title,
        accepted_conflicts=accepted,
    )


def read_grammar(path: str | Path) -> Grammar:
    """Read a grammar file (UTF-8)."""
    return parse_grammar(Path(path).read_text(encoding="utf-8"))


def nullable_set(grammar: Grammar) -> set[str]:
    """Nonterminals that can derive the empty string."""
    nullable: set[str] = set()
    changed = True
    while changed:
        changed = False
        for production in grammar.productions:
            if production.lhs not in nullable and all(s in nullable for s in production.rhs):
                nullable.add(production.lhs)
                changed = True
    return nullable


def left_recursion_cycles(grammar: Grammar) -> list[tuple[list[str], Production]]:
    """Cycles A =>+ A... through leftmost positions, skipping over nullable symbols.

    Returns one ``(cycle, production)`` pair per distinct cycle, where ``cycle`` lists the
    nonterminals in order (A, B, ..., A) and ``production`` is the first production of the cycle.
    """
    nullable = nullable_set(grammar)
    edges: dict[str, dict[str, Production]] = {nt: {} for nt in grammar.nonterminals}
    for production in grammar.productions:
        for symbol in production.rhs:
            if not grammar.is_nonterminal(symbol):
                break
            edges[production.lhs].setdefault(symbol, production)
            if symbol not in nullable:
                break

    cycles: list[tuple[list[str], Production]] = []
    seen: set[frozenset[str]] = set()
    for start in grammar.nonterminals:
        # Breadth-first search for the shortest path from `start` back to `start`.
        queue: list[list[str]] = [[start]]
        visited: set[str] = set()
        found: list[str] | None = None
        while queue and found is None:
            path = queue.pop(0)
            for successor in edges[path[-1]]:
                if successor == start:
                    found = path + [start]
                    break
                if successor not in visited:
                    visited.add(successor)
                    queue.append(path + [successor])
        if found is not None:
            key = frozenset(found)
            if key not in seen:
                seen.add(key)
                cycles.append((found, edges[found[0]][found[1]]))
    return cycles


def validate(grammar: Grammar) -> list[Diagnostic]:
    """Find mistakes in the grammar before analyzing it.

    Errors: symbols that look like nonterminals but have no rule, and nonterminals that
    derive no string of terminals. Warnings: unreachable nonterminals, repeated alternatives
    and left recursion (which always breaks LL(1)).
    """
    diagnostics: list[Diagnostic] = []

    # Symbols used on a right-hand side that look like a nonterminal but have no rule.
    first_use: dict[str, int] = {}
    for production in grammar.productions:
        for symbol in production.rhs:
            first_use.setdefault(symbol, production.line)
    for terminal in grammar.terminals:
        if _NONTERMINAL_LIKE_RE.fullmatch(terminal):
            diagnostics.append(
                Diagnostic(
                    "error",
                    f"el símbolo '{terminal}' se usa pero no tiene regla "
                    "(¿error de escritura? Los terminales se escriben con el nombre del token)",
                    first_use[terminal],
                )
            )

    # Nonterminals that derive no string of terminals.
    productive: set[str] = set()
    changed = True
    while changed:
        changed = False
        for production in grammar.productions:
            if production.lhs in productive:
                continue
            if all(not grammar.is_nonterminal(s) or s in productive for s in production.rhs):
                productive.add(production.lhs)
                changed = True
    for nonterminal in grammar.nonterminals:
        if nonterminal not in productive:
            line = grammar.productions_of(nonterminal)[0].line
            diagnostics.append(
                Diagnostic("error", f"el no terminal '{nonterminal}' no genera ninguna cadena de terminales", line)
            )

    # Nonterminals not reachable from the start symbol.
    reachable = {grammar.start}
    stack = [grammar.start]
    while stack:
        for production in grammar.productions_of(stack.pop()):
            for symbol in production.rhs:
                if grammar.is_nonterminal(symbol) and symbol not in reachable:
                    reachable.add(symbol)
                    stack.append(symbol)
    for nonterminal in grammar.nonterminals:
        if nonterminal not in reachable:
            line = grammar.productions_of(nonterminal)[0].line
            diagnostics.append(
                Diagnostic("warning", f"el no terminal '{nonterminal}' no se alcanza desde '{grammar.start}'", line)
            )

    # Repeated alternatives.
    seen_rhs: set[tuple[str, tuple[str, ...]]] = set()
    for production in grammar.productions:
        key = (production.lhs, production.rhs)
        if key in seen_rhs:
            diagnostics.append(Diagnostic("warning", f"alternativa repetida: {production}", production.line))
        seen_rhs.add(key)

    # Left recursion.
    for cycle, production in left_recursion_cycles(grammar):
        if len(cycle) == 2:
            message = f"recursión izquierda directa en '{cycle[0]}': {production}"
        else:
            message = "recursión izquierda indirecta: " + " -> ".join(cycle)
        diagnostics.append(
            Diagnostic("warning", message + " (impide que la gramática sea LL(1))", production.line)
        )

    return sorted(diagnostics, key=lambda d: (d.line is None, d.line or 0))
