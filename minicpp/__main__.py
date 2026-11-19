"""Command line: uv run python -m minicpp file.cpp

Runs the three stages (lexer, parser and semantic analyzer) and prints
"Programa válido" or the errors. Messages are in Spanish (CONTRATO.md, section 3).
"""

import argparse
import sys

from minicpp import analyze
from minicpp.errors import LexicalError, SyntacticError
from minicpp.lexer import tokenize
from minicpp.tokens import Token
from minicpp.visualization import VIEWS, show


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m minicpp",
        description="Analiza un programa del subconjunto de C++: lexer, parser y analizador semántico.",
    )
    parser.add_argument("file", help="archivo .cpp a analizar")
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
    lines = [f"{'Línea':>5}  {'Col':>4}  {'Tipo':<16}Lexema"]

    for token in tokens:
        lines.append(f"{token.line:>5}  {token.column:>4}  {token.type:<16}{token.lexeme}")

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """Run the command line. Returns 0 if the program is valid, 1 if it has
    errors and 2 if the file could not be read."""
    # The Windows console may not use UTF-8, and the output has ε, └ and accents.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")

    args = build_argument_parser().parse_args(argv)

    try:
        # utf-8-sig also removes the BOM that some Windows editors add
        with open(args.file, encoding="utf-8-sig") as file:
            code = file.read()
    except FileNotFoundError:
        print(f"No se encontró el archivo '{args.file}'", file=sys.stderr)
        return 2
    except UnicodeDecodeError:
        print(f"El archivo '{args.file}' no está en UTF-8", file=sys.stderr)
        return 2

    try:
        if args.tokens:
            print(format_tokens(tokenize(code)))
            print()
        tree, semantic_errors = analyze(code)
    except (LexicalError, SyntacticError) as error:
        print(error, file=sys.stderr)
        return 1

    if args.tree:
        show(tree, args.view, args.compact)
        print()

    if semantic_errors:
        for error in semantic_errors:
            print(error, file=sys.stderr)
        return 1

    print("Programa válido")
    return 0


if __name__ == "__main__":
    sys.exit(main())
