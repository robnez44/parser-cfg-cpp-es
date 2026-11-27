"""Runs the Spanish parser on the test set (CONTRATO_FASE2.md, sections 6 and 8).

Reads data/test_set.jsonl and writes results/parser.jsonl, one line per
sentence. It does not need internet or a key:

    uv run python -m experiments.run_parser
"""

import argparse
import json
import sys
from pathlib import Path

from experiments.llm_validator import attachment
from minicpp.errors import LexicalError, SyntacticError
from minicpp.visualization import to_nltk
from spanish import analyze
from spanish.lexer import LEXICON

ROOT = Path(__file__).resolve().parent.parent
TEST_SET = ROOT / "data" / "test_set.jsonl"
OUTPUT = ROOT / "results" / "parser.jsonl"


def read_jsonl(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as file:
        return [json.loads(line) for line in file if line.strip()]


def write_jsonl(path: Path, lines: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        for line in lines:
            file.write(json.dumps(line, ensure_ascii=False) + "\n")


def result_line(item: dict) -> dict:
    """Run the parser on one sentence and return its line of results/parser.jsonl."""
    try:
        tree = analyze(item["sentence"])
    except (LexicalError, SyntacticError) as error:
        return {
            "id": item["id"], "tool": "parser", "accepted": False, "upos": None,
            "attachment": None, "tree": None, "error": str(error),
        }

    drawing = to_nltk(tree)
    return {
        "id": item["id"],
        "tool": "parser",
        "accepted": True,
        # the period has no UPOS in the test set (section 7)
        "upos": [LEXICON[t.lexeme]["upos"] for t in tree.leaves() if t.type != "PERIOD"],
        # the same function the LLM uses, so task C measures both the same way
        "attachment": attachment(drawing),
        "tree": drawing.pformat(margin=sys.maxsize),
        "error": None,
    }


def summary(results: list[dict]) -> str:
    accepted = sum(1 for line in results if line["accepted"])
    lexical = sum(1 for line in results if (line["error"] or "").startswith("Error léxico"))
    return (
        f"parser: {len(results)} oraciones, aceptadas {accepted}, rechazadas {len(results) - accepted} "
        f"({lexical} léxicas y {len(results) - accepted - lexical} sintácticas)"
    )


def in_grammar_differences(test_set: list[dict], results: list[dict]) -> list[str]:
    """Return the ids where the parser does not agree with in_grammar (section 7)."""
    return [item["id"] for item, line in zip(test_set, results) if item["in_grammar"] != line["accepted"]]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Corre el parser del español sobre el set de prueba")
    parser.add_argument("--test-set", type=Path, default=TEST_SET)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args(argv)

    if not args.test_set.exists():
        print(f"No existe {args.test_set}; hace falta el set de prueba.")
        return 1

    test_set = read_jsonl(args.test_set)
    results = [result_line(item) for item in test_set]
    write_jsonl(args.output, results)
    print(summary(results))

    differences = in_grammar_differences(test_set, results)
    if differences:
        print("No coinciden con in_grammar: " + ", ".join(differences))
    return 0


if __name__ == "__main__":
    sys.exit(main())
