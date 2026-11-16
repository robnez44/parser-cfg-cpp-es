"""FIRST and FOLLOW sets, LL(1) parsing table and conflict detection.

Standard algorithms (Aho, Lam, Sethi, Ullman, "Compilers", section 4.4):

  FIRST(α):  terminals that can start a string derived from α, plus ε if α can vanish.
  FOLLOW(A): terminals that can appear right after A in some sentential form, plus $
             if A can be at the end of the input.
  M[A, a]:   for each production A -> α, put it in M[A, a] for every a in FIRST(α);
             if ε is in FIRST(α), also for every a in FOLLOW(A).

A grammar is LL(1) exactly when no cell M[A, a] has more than one production.
"""

from __future__ import annotations

from dataclasses import dataclass

from .grammar import EPSILON, END_MARKER, Grammar, Production, nullable_set


@dataclass(frozen=True)
class Conflict:
    """A cell of the table with more than one production.

    ``kind`` says where the overlap comes from:
      FIRST/FIRST    two alternatives can start with the same terminal.
      FIRST/FOLLOW   one alternative starts with the terminal and another can vanish
                     while the terminal can follow the nonterminal (dangling else).
      FOLLOW/FOLLOW  two alternatives can vanish (the grammar is ambiguous).
    """

    nonterminal: str
    terminal: str
    productions: tuple[Production, ...]
    kind: str


@dataclass
class Analysis:
    grammar: Grammar
    nullable: set[str]
    first: dict[str, set[str]]
    follow: dict[str, set[str]]
    table: dict[tuple[str, str], list[Production]]
    conflicts: list[Conflict]
    terminal_order: list[str]  # grammar terminals in order of appearance, then $

    def accepted(self, extra: set[tuple[str, str]] | None = None) -> set[tuple[str, str]]:
        """Conflicts declared as accepted in the grammar file, plus any given by the caller."""
        return set(self.grammar.accepted_conflicts) | (extra or set())

    def unaccepted_conflicts(self, extra: set[tuple[str, str]] | None = None) -> list[Conflict]:
        accepted = self.accepted(extra)
        return [c for c in self.conflicts if (c.nonterminal, c.terminal) not in accepted]

    def is_ll1(self, extra: set[tuple[str, str]] | None = None) -> bool:
        """True when every conflict is an accepted one (no conflicts at all counts too)."""
        return not self.unaccepted_conflicts(extra)


def first_of_sequence(symbols: tuple[str, ...], first: dict[str, set[str]], nullable: set[str]) -> set[str]:
    """FIRST of a string of symbols. Contains ε when every symbol can vanish."""
    result: set[str] = set()
    for symbol in symbols:
        if symbol in first:  # nonterminal
            result |= first[symbol] - {EPSILON}
            if symbol not in nullable:
                return result
        else:  # terminal
            result.add(symbol)
            return result
    result.add(EPSILON)
    return result


def compute_first(grammar: Grammar, nullable: set[str]) -> dict[str, set[str]]:
    first: dict[str, set[str]] = {nt: set() for nt in grammar.nonterminals}
    changed = True
    while changed:
        changed = False
        for production in grammar.productions:
            found = first_of_sequence(production.rhs, first, nullable)
            if not found <= first[production.lhs]:
                first[production.lhs] |= found
                changed = True
    return first


def compute_follow(grammar: Grammar, first: dict[str, set[str]], nullable: set[str]) -> dict[str, set[str]]:
    follow: dict[str, set[str]] = {nt: set() for nt in grammar.nonterminals}
    follow[grammar.start].add(END_MARKER)
    changed = True
    while changed:
        changed = False
        for production in grammar.productions:
            for index, symbol in enumerate(production.rhs):
                if symbol not in follow:
                    continue
                beta_first = first_of_sequence(production.rhs[index + 1 :], first, nullable)
                addition = beta_first - {EPSILON}
                if EPSILON in beta_first:
                    addition |= follow[production.lhs]
                if not addition <= follow[symbol]:
                    follow[symbol] |= addition
                    changed = True
    return follow


def analyze(grammar: Grammar) -> Analysis:
    """Compute FIRST, FOLLOW, the LL(1) table and the list of conflicts."""
    nullable = nullable_set(grammar)
    first = compute_first(grammar, nullable)
    follow = compute_follow(grammar, first, nullable)
    terminal_order = list(grammar.terminals) + [END_MARKER]
    terminal_rank = {t: i for i, t in enumerate(terminal_order)}
    nonterminal_rank = {nt: i for i, nt in enumerate(grammar.nonterminals)}

    # Each cell remembers how every production got there (via FIRST or via FOLLOW).
    entries: dict[tuple[str, str], list[tuple[Production, str]]] = {}
    for production in grammar.productions:
        rhs_first = first_of_sequence(production.rhs, first, nullable)
        placements = [(t, "FIRST") for t in rhs_first - {EPSILON}]
        if EPSILON in rhs_first:
            placements += [(t, "FOLLOW") for t in follow[production.lhs]]
        for terminal, via in placements:
            cell = entries.setdefault((production.lhs, terminal), [])
            if all(existing is not production for existing, _ in cell):
                cell.append((production, via))

    table = {cell: [p for p, _ in items] for cell, items in entries.items()}

    conflicts: list[Conflict] = []
    for (nonterminal, terminal), items in entries.items():
        if len(items) < 2:
            continue
        vias = {via for _, via in items}
        kind = "FIRST/FOLLOW" if len(vias) == 2 else f"{next(iter(vias))}/{next(iter(vias))}"
        conflicts.append(Conflict(nonterminal, terminal, tuple(p for p, _ in items), kind))
    conflicts.sort(key=lambda c: (nonterminal_rank[c.nonterminal], terminal_rank[c.terminal]))

    return Analysis(grammar, nullable, first, follow, table, conflicts, terminal_order)


# ---------------------------------------------------------------------------
# Text reports
# ---------------------------------------------------------------------------


def _sorted_symbols(symbols: set[str], order: list[str]) -> list[str]:
    rank = {t: i for i, t in enumerate(order)}
    terminals = sorted((s for s in symbols if s != EPSILON), key=lambda s: rank[s])
    return terminals + ([EPSILON] if EPSILON in symbols else [])


def _format_sets(name: str, sets: dict[str, set[str]], analysis: Analysis) -> str:
    width = max(len(nt) for nt in analysis.grammar.nonterminals)
    lines = []
    for nonterminal in analysis.grammar.nonterminals:
        members = ", ".join(_sorted_symbols(sets[nonterminal], analysis.terminal_order))
        lines.append(f"{name}({nonterminal}){' ' * (width - len(nonterminal))} = {{ {members} }}")
    return "\n".join(lines)


def format_first(analysis: Analysis) -> str:
    return _format_sets("FIRST", analysis.first, analysis)


def format_follow(analysis: Analysis) -> str:
    return _format_sets("FOLLOW", analysis.follow, analysis)


def format_table(analysis: Analysis) -> str:
    """The table as a list of entries ``M[A, a] = production``; conflicting cells list all productions."""
    rank = {t: i for i, t in enumerate(analysis.terminal_order)}
    lines: list[str] = []
    for nonterminal in analysis.grammar.nonterminals:
        cells = sorted(
            (t for (nt, t) in analysis.table if nt == nonterminal),
            key=lambda t: rank[t],
        )
        for terminal in cells:
            productions = analysis.table[(nonterminal, terminal)]
            if len(productions) == 1:
                lines.append(f"M[{nonterminal}, {terminal}] = {productions[0]}")
            else:
                lines.append(f"M[{nonterminal}, {terminal}] = CONFLICTO")
                lines.extend(f"    {p}" for p in productions)
    return "\n".join(lines)


def format_table_grid(analysis: Analysis) -> str:
    """The table as a Markdown grid: rows are nonterminals, columns are terminals.

    Cells show production numbers (a legend lists them), so the grid stays narrow.
    A cell with several numbers is a conflict. Only terminals that appear in some cell are shown.
    """
    numbers = {id(p): i for i, p in enumerate(analysis.grammar.productions, start=1)}
    used = {t for (_, t) in analysis.table}
    columns = [t for t in analysis.terminal_order if t in used]

    legend = [f"p{numbers[id(p)]}: {p}" for p in analysis.grammar.productions]
    header = "| | " + " | ".join(columns) + " |"
    separator = "|---|" + "---|" * len(columns)
    rows = []
    for nonterminal in analysis.grammar.nonterminals:
        cells = []
        for terminal in columns:
            productions = analysis.table.get((nonterminal, terminal), [])
            cells.append(", ".join(f"p{numbers[id(p)]}" for p in productions))
        rows.append(f"| {nonterminal} | " + " | ".join(cells) + " |")
    return "\n".join(legend + ["", header, separator] + rows)


def format_conflict(conflict: Conflict) -> str:
    """One conflict, in the format fixed by CONTRATO.md section 5."""
    lines = [f"Conflict at M[{conflict.nonterminal}, {conflict.terminal}]:"]
    lines.extend(f"  {p}" for p in conflict.productions)
    return "\n".join(lines)


def format_conflicts(analysis: Analysis, extra_accepted: set[tuple[str, str]] | None = None) -> str:
    """All conflicts, then a one-line classification of each (kind and whether it is accepted)."""
    if not analysis.conflicts:
        return "No hay conflictos."
    accepted = analysis.accepted(extra_accepted)
    blocks = [format_conflict(c) for c in analysis.conflicts]
    kinds = [
        f"M[{c.nonterminal}, {c.terminal}]: {c.kind}"
        + (" (aceptado)" if (c.nonterminal, c.terminal) in accepted else " (SIN ACEPTAR)")
        for c in analysis.conflicts
    ]
    return "\n".join(blocks) + "\n\nTipo de cada conflicto:\n" + "\n".join(f"  {k}" for k in kinds)


def format_summary(analysis: Analysis, extra_accepted: set[tuple[str, str]] | None = None) -> str:
    grammar = analysis.grammar
    unaccepted = analysis.unaccepted_conflicts(extra_accepted)
    accepted_count = len(analysis.conflicts) - len(unaccepted)
    lines = [
        f"{len(grammar.nonterminals)} no terminales, {len(grammar.productions)} producciones, "
        f"{len(grammar.terminals)} terminales (sin contar $).",
        f"Conflictos LL(1): {len(analysis.conflicts)} ({accepted_count} aceptados, {len(unaccepted)} sin aceptar).",
    ]
    if not analysis.conflicts:
        lines.append("Resultado: la gramática es LL(1).")
    elif not unaccepted:
        lines.append("Resultado: la gramática es LL(1) salvo los conflictos aceptados.")
    else:
        lines.append("Resultado: la gramática NO es LL(1).")
    return "\n".join(lines)
