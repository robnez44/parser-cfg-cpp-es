"""Command line for the LL(1) verifier.

    python -m verifier grammars/cpp.gram
    python -m verifier grammars/cpp.gram --conflicts
    python -m verifier grammars/cpp.gram --class-notation -o grammars/cpp.bnf

Exit status: 0 if the grammar is LL(1) (accepted conflicts allowed), 1 if it has conflicts
that were not accepted, 2 if the grammar file has errors or cannot be read.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import class_notation, ll1
from .grammar import GrammarError, read_grammar, validate


def _parse_accepted(values: list[str]) -> set[tuple[str, str]]:
    accepted: set[tuple[str, str]] = set()
    for value in values:
        nonterminal, separator, terminal = value.partition(":")
        if not separator or not nonterminal or not terminal:
            raise SystemExit(f"--accept espera NoTerminal:TOKEN (por ejemplo ElsePart:ELSE), no '{value}'")
        accepted.add((nonterminal, terminal))
    return accepted


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m verifier",
        description="Verificador LL(1): calcula FIRST, FOLLOW, la tabla y los conflictos de una gramática.",
    )
    parser.add_argument("grammar", help="archivo de gramática (.gram)")
    parser.add_argument("--first", action="store_true", help="imprime solo los conjuntos FIRST")
    parser.add_argument("--follow", action="store_true", help="imprime solo los conjuntos FOLLOW")
    parser.add_argument("--table", action="store_true", help="imprime solo la tabla LL(1)")
    parser.add_argument("--conflicts", action="store_true", help="imprime solo los conflictos y el resumen")
    parser.add_argument(
        "--table-format",
        choices=("list", "grid"),
        default="list",
        help="forma de la tabla: lista de entradas M[A, a] o cuadrícula en Markdown (por defecto: list)",
    )
    parser.add_argument(
        "--accept",
        action="append",
        default=[],
        metavar="NoTerminal:TOKEN",
        help="acepta un conflicto, por ejemplo ElsePart:ELSE (se puede repetir)",
    )
    parser.add_argument(
        "--class-notation",
        action="store_true",
        help="imprime la gramática en la notación de clase (<regla> ::= ...) en vez del análisis",
    )
    parser.add_argument("-o", "--output", help="con --class-notation, escribe el resultado en este archivo")
    return parser


def main(argv: list[str] | None = None) -> int:
    # Windows consoles often use a code page that cannot print ε.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    args = _build_parser().parse_args(argv)
    extra_accepted = _parse_accepted(args.accept)

    try:
        grammar = read_grammar(args.grammar)
    except OSError as error:
        print(f"No se pudo leer '{args.grammar}': {error.strerror}", file=sys.stderr)
        return 2
    except GrammarError as error:
        print(f"Error en {args.grammar}, {error}", file=sys.stderr)
        return 2

    diagnostics = validate(grammar)
    errors = [d for d in diagnostics if d.level == "error"]
    for diagnostic in diagnostics:
        print(f"{args.grammar}: {diagnostic}", file=sys.stderr)
    if errors:
        print("La gramática tiene errores; corrígelos antes de analizarla.", file=sys.stderr)
        return 2

    analysis = ll1.analyze(grammar)

    if args.class_notation:
        text = class_notation.convert(grammar, analysis, args.grammar)
        if args.output:
            Path(args.output).write_text(text, encoding="utf-8", newline="\n")
            print(f"Gramática en notación de clase escrita en {args.output}")
        else:
            sys.stdout.write(text)
        return 0

    sections: list[tuple[str, str]] = []
    selected = args.first or args.follow or args.table or args.conflicts
    if args.first or not selected:
        sections.append(("FIRST", ll1.format_first(analysis)))
    if args.follow or not selected:
        sections.append(("FOLLOW", ll1.format_follow(analysis)))
    if args.table or not selected:
        table = ll1.format_table_grid(analysis) if args.table_format == "grid" else ll1.format_table(analysis)
        sections.append(("Tabla LL(1)", table))
    if args.conflicts or not selected:
        sections.append(("Conflictos", ll1.format_conflicts(analysis, extra_accepted)))
    sections.append(("Resumen", ll1.format_summary(analysis, extra_accepted)))

    print("\n\n".join(f"== {title} ==\n{body}" for title, body in sections))
    return 0 if analysis.is_ll1(extra_accepted) else 1


if __name__ == "__main__":
    sys.exit(main())
