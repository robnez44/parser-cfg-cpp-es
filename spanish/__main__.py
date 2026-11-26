"""Command line: uv run python -m spanish "el niño come una manzana"

Runs the lexer and the parser and prints "Oración válida" or the error.
Messages are in Spanish (CONTRATO_FASE2.md, section 3).
"""

import argparse
import sys

from minicpp.errors import LexicalError, SyntacticError
from minicpp.tokens import Token
from minicpp.visualization import VIEWS, show
from spanish import analyze
from spanish.lexer import LEXICON, tokenize


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m spanish",
        description="Analiza una oración del subconjunto del español: lexer y parser.",
    )
    # nargs="+" also accepts the words without quotes, which helps in PowerShell
    parser.add_argument("sentence", nargs="+", help="oración a analizar, entre comillas o palabra por palabra")
    parser.add_argument("--tokens", action="store_true", help="muestra los tokens que produce el lexer")
    parser.add_argument("--tree", action="store_true", help="dibuja el árbol de análisis sintáctico")
    parser.add_argument(
        "--view",
        choices=VIEWS,
        default="console",
        help="cómo dibujar el árbol: console (terminal), window (ventana de NLTK) u outline (un nodo por línea)",
    )
    parser.add_argument(
        "--compact", action="store_true", help="oculta en el dibujo las ramas que solo derivan ε"
    )
    return parser


def format_tokens(tokens: list[Token]) -> str:
    lines = [f"{'Col':>4}  {'Tipo':<10}{'UPOS':<7}Palabra"]

    for token in tokens:
        upos = LEXICON[token.lexeme]["upos"] if token.lexeme in LEXICON else ""
        lines.append(f"{token.column:>4}  {token.type:<10}{upos:<7}{token.lexeme}")

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """Run the command line. Returns 0 if the sentence is valid and 1 if it has an error."""
    # The Windows console may not use UTF-8, and the output has ñ, ε, └ and accents.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")

    args = build_argument_parser().parse_args(argv)
    sentence = " ".join(args.sentence)

    try:
        if args.tokens:
            print(format_tokens(tokenize(sentence)))
            print()
        tree = analyze(sentence)
    except (LexicalError, SyntacticError) as error:
        print(error, file=sys.stderr)
        return 1

    if args.tree:
        show(tree, args.view, args.compact)
        print()

    print("Oración válida")
    return 0


if __name__ == "__main__":
    sys.exit(main())
