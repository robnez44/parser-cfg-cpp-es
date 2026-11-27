"""Classify disagreements between tool outputs and the labeled Spanish test set."""

import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEST_SET_PATH = ROOT / "data" / "test_set.jsonl"
RESULTS_DIR = ROOT / "results"
OUTPUT_PATH = RESULTS_DIR / "errors.csv"
REFERENCES = ("in_grammar", "spanish_ok")
CSV_FIELDS = (
    "id",
    "tool",
    "classification",
    "reference",
    "phenomena",
    "expected",
    "actual",
    "word_index",
)


def read_jsonl(path: Path) -> list[dict]:
    """Read JSON objects from a JSONL file and identify malformed lines."""
    entries = []
    with path.open(encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"{path}:{line_number}: JSON inválido: {error.msg}") from error
            if not isinstance(entry, dict):
                raise ValueError(f"{path}:{line_number}: cada línea debe ser un objeto JSON")
            entries.append(entry)
    return entries


def scalar(value) -> str:
    """Serialize a CSV cell without losing JSON values such as booleans or lists."""
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def classify_acceptance(item: dict, result: dict, reference: str) -> dict | None:
    """Return one FP/FN row when a tool's acceptance disagrees with a reference."""
    actual = result.get("accepted")
    if actual is None:
        return None
    if not isinstance(actual, bool):
        raise ValueError(f"{item['id']}: accepted debe ser boolean o null")

    expected = item[reference]
    if actual == expected:
        return None

    return {
        "id": item["id"],
        "tool": result["tool"],
        "classification": "falso positivo" if actual else "falso negativo",
        "reference": reference,
        "phenomena": scalar(item["phenomena"]),
        "expected": scalar(expected),
        "actual": scalar(actual),
        "word_index": "",
    }


def classify_upos(item: dict, result: dict) -> list[dict]:
    """Return a row for each UPOS position that differs from the expected labels."""
    expected = item["upos"]
    if expected is None:
        return []

    actual = result.get("upos")
    if actual is not None and (
        not isinstance(actual, list) or not all(isinstance(tag, str) for tag in actual)
    ):
        raise ValueError(f"{item['id']}: upos debe ser una lista de etiquetas o null")

    actual = actual or []
    rows = []
    for index in range(max(len(expected), len(actual))):
        expected_tag = expected[index] if index < len(expected) else None
        actual_tag = actual[index] if index < len(actual) else None
        if expected_tag == actual_tag:
            continue
        rows.append(
            {
                "id": item["id"],
                "tool": result["tool"],
                "classification": "error de etiquetado",
                "reference": "upos",
                "phenomena": scalar(item["phenomena"]),
                "expected": scalar(expected_tag),
                "actual": scalar(actual_tag),
                "word_index": index + 1,
            }
        )
    return rows


def classify_results(test_set: list[dict], tool_results: list[dict]) -> list[dict]:
    """Classify acceptance errors against both references and UPOS mismatches."""
    items_by_id = {item["id"]: item for item in test_set}
    if len(items_by_id) != len(test_set):
        raise ValueError("el set de prueba contiene IDs duplicados")

    results_by_key = set()
    errors = []
    for result in tool_results:
        item_id = result.get("id")
        tool = result.get("tool")
        if item_id not in items_by_id:
            raise ValueError(f"resultado con ID desconocido: {item_id!r}")
        if not isinstance(tool, str) or not tool:
            raise ValueError(f"{item_id}: falta el nombre de la herramienta")
        key = (tool, item_id)
        if key in results_by_key:
            raise ValueError(f"resultado duplicado para {tool}/{item_id}")
        results_by_key.add(key)

        item = items_by_id[item_id]
        for reference in REFERENCES:
            row = classify_acceptance(item, result, reference)
            if row is not None:
                errors.append(row)
        errors.extend(classify_upos(item, result))
    return errors


def write_errors(errors: list[dict], path: Path = OUTPUT_PATH) -> None:
    """Write classified disagreements to the contract's CSV output."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(errors)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--test-set", type=Path, default=TEST_SET_PATH)
    parser.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    args = parser.parse_args(argv)

    files = sorted(args.results_dir.glob("*.jsonl"))
    if not files:
        parser.error(f"no hay archivos de resultados JSONL en {args.results_dir}")

    test_set = read_jsonl(args.test_set)
    tool_results = [result for path in files for result in read_jsonl(path)]
    errors = classify_results(test_set, tool_results)
    write_errors(errors, args.output)
    print(f"Clasificación escrita en {args.output} ({len(errors)} discrepancias)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
