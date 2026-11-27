"""The two trees of the ambiguous sentence (CONTRATO_FASE2.md, section 5).

"el maestro lee la carta en la casa" has two readings: "en la casa" modifies
"carta" (the noun) or "lee" (the verb). A grammar written without thinking of
LL(1), grammars/es_natural.gram, derives the sentence in both ways, and
nltk.ChartParser finds both trees.

This module also reads grammars/es.gram and grammars/es_base.gram as plain CFGs.
They are LL(1) except for M[NpTail, PREP], and that conflict is exactly where
the ambiguity lives, so as CFGs they still give two trees. The parser of the
project gets one tree because it decides in NpTail: it never tries the other.

    uv run python -m experiments.ambiguity_trees

prints the trees and writes the two drawings to docs/informe/fase2/figures/.
"""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path
from typing import Callable
from xml.sax.saxutils import escape

from nltk import CFG, ChartParser, Nonterminal, Production, Tree

from verifier.grammar import Grammar, read_grammar

ROOT = Path(__file__).resolve().parent.parent
GRAMMARS = ROOT / "grammars"
LEXICON_PATH = ROOT / "spanish" / "lexicon.tsv"
FIGURES = ROOT / "docs" / "informe" / "fase2" / "figures"

AMBIGUOUS_SENTENCE = "el maestro lee la carta en la casa"

# Same split as spanish/lexer.py: a word, or a period on its own.
WORD = re.compile(r"[^\s.]+|\.")

# Parents of a PrepPhrase that mean "attached to the noun" or "attached to the verb",
# in es_natural.gram and in es.gram / es_base.gram.
NOUN_PARENTS = {"NounPhrase", "NpTail"}
VERB_PARENTS = {"VerbPhrase", "PpList"}


def read_lexicon() -> list[dict[str, str]]:
    with open(LEXICON_PATH, encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file, delimiter="\t"))


def by_upos(row: dict[str, str]) -> str:
    """Terminal of es_natural.gram and es_base.gram: one per category (DET, NOUN, ...)."""
    return {"ADP": "PREP", "PUNCT": "PERIOD"}.get(row["upos"], row["upos"])


def by_type(row: dict[str, str]) -> str:
    """Terminal of es.gram: the token type of the lexicon (DET_MS, NOUN_FP, ...)."""
    return row["type"]


def to_nltk_cfg(grammar: Grammar, terminal_of: Callable[[dict[str, str]], str]) -> CFG:
    """Turn a .gram file into an nltk CFG, adding one lexical rule per word of the lexicon.

    The .gram files stop at the token types. nltk needs the words, so every token
    type ``T`` becomes a nonterminal with ``T -> 'word'`` for each word of that type.
    """
    productions = [
        Production(Nonterminal(p.lhs), [Nonterminal(symbol) for symbol in p.rhs])
        for p in grammar.productions
    ]
    for row in read_lexicon():
        terminal = terminal_of(row)
        if terminal in grammar.terminals:
            productions.append(Production(Nonterminal(terminal), [row["word"]]))
    return CFG(Nonterminal(grammar.start), productions)


def split_words(sentence: str) -> list[str]:
    return WORD.findall(sentence.lower())


def parse_all(cfg: CFG, sentence: str) -> list[Tree]:
    """Every tree of the sentence. A sentence with a word outside the lexicon has none."""
    try:
        return list(ChartParser(cfg).parse(split_words(sentence)))
    except ValueError:
        return []


def attachment(tree: Tree) -> str | None:
    """``"noun"`` or ``"verb"`` according to the parent of the (first) PrepPhrase, ``None`` if there is none."""

    def walk(node: Tree, parent: str | None) -> str | None:
        if node.label() == "PrepPhrase":
            if parent in NOUN_PARENTS:
                return "noun"
            if parent in VERB_PARENTS:
                return "verb"
            return None
        for child in node:
            if isinstance(child, Tree):
                found = walk(child, node.label())
                if found:
                    return found
        return None

    return walk(tree, None)


# ---------------------------------------------------------------------------
# Drawing
# ---------------------------------------------------------------------------

COLUMN = 96        # horizontal space of one word
ROW = 62           # vertical space of one level
MARGIN = 28
TEXT = "#1f2933"
LINE = "#7b8794"
ACCENT = "#c2410c"
FONT = "font-family=\"Consolas, 'DejaVu Sans Mono', monospace\" font-size=\"14\""


def draw_svg(tree: Tree, title: str, highlight: str = "PrepPhrase") -> str:
    """Draw a tree as a standalone SVG. The nodes called ``highlight`` and their branch are orange."""
    positions: dict[int, tuple[float, int]] = {}
    leaf_count = 0
    max_depth = 0

    def place(node: Tree, depth: int) -> float:
        nonlocal leaf_count, max_depth
        max_depth = max(max_depth, depth)
        children = [c for c in node if isinstance(c, Tree)]
        if not children:          # a preterminal: its only child is the word
            x = leaf_count * COLUMN
            leaf_count += 1
        else:
            xs = [place(child, depth + 1) for child in children]
            x = (xs[0] + xs[-1]) / 2
        positions[id(node)] = (x, depth)
        return x

    place(tree, 0)
    words_y = MARGIN + 34 + (max_depth + 1) * ROW
    width = (leaf_count - 1) * COLUMN + 2 * MARGIN + 40
    height = words_y + MARGIN
    shift = MARGIN + 20

    parts: list[str] = []

    def py(depth: int) -> int:
        return MARGIN + 34 + depth * ROW

    def inside(node: Tree, flag: bool) -> None:
        flag = flag or node.label() == highlight
        x, depth = positions[id(node)]
        x += shift
        children = [c for c in node if isinstance(c, Tree)]
        color = ACCENT if flag else LINE
        if not children:
            word = node[0]
            parts.append(
                f'<line x1="{x}" y1="{py(depth) + 6}" x2="{x}" y2="{words_y - 16}" stroke="{color}" stroke-width="1.3"/>'
            )
            parts.append(
                f'<text x="{x}" y="{words_y}" text-anchor="middle" {FONT} font-style="italic" '
                f'fill="{ACCENT if flag else TEXT}">{escape(str(word))}</text>'
            )
        for child in children:
            cx, cdepth = positions[id(child)]
            cflag = flag or child.label() == highlight
            parts.append(
                f'<line x1="{x}" y1="{py(depth) + 6}" x2="{cx + shift}" y2="{py(cdepth) - 14}" '
                f'stroke="{ACCENT if cflag else LINE}" stroke-width="1.3"/>'
            )
            inside(child, flag)
        parts.append(
            f'<text x="{x}" y="{py(depth)}" text-anchor="middle" {FONT} '
            f'font-weight="{"bold" if flag else "normal"}" fill="{ACCENT if flag else TEXT}">{escape(node.label())}</text>'
        )

    inside(tree, False)
    body = "\n  ".join(parts)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">\n'
        f'  <rect width="100%" height="100%" fill="white"/>\n'
        f'  <text x="{MARGIN}" y="{MARGIN}" {FONT} font-weight="bold" fill="{TEXT}">{escape(title)}</text>\n'
        f"  {body}\n</svg>\n"
    )


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------

TITLES = {
    "noun": "Lectura A: «en la casa» modifica a «carta» (se pega al sustantivo)",
    "verb": "Lectura B: «en la casa» modifica a «lee» (se pega al verbo)",
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Árboles de la oración ambigua con nltk.ChartParser sobre es_natural.gram."
    )
    parser.add_argument("sentence", nargs="?", default=AMBIGUOUS_SENTENCE, help="oración a analizar")
    parser.add_argument("--no-write", action="store_true", help="no escribe los dibujos SVG")
    args = parser.parse_args(argv)

    for name, terminal_of in (("es_natural", by_upos), ("es_base", by_upos), ("es", by_type)):
        grammar = read_grammar(GRAMMARS / f"{name}.gram")
        trees = parse_all(to_nltk_cfg(grammar, terminal_of), args.sentence)
        print(f"{name}.gram: {len(trees)} árbol(es) para «{args.sentence}»")
        if name == "es_natural":
            natural = trees

    print()
    for tree in sorted(natural, key=lambda t: attachment(t) != "noun"):   # reading A (noun) first
        kind = attachment(tree)
        print(f"--- {TITLES.get(kind, 'Lectura')}")
        tree.pretty_print()
        print(tree.pformat(margin=10_000))
        print()
        if not args.no_write and kind:
            FIGURES.mkdir(parents=True, exist_ok=True)
            path = FIGURES / f"ambiguity_{kind}.svg"
            path.write_text(draw_svg(tree, TITLES[kind]), encoding="utf-8")
            print(f"Dibujo escrito en {path.relative_to(ROOT)}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
