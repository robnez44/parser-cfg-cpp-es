import csv
import json
from pathlib import Path

import pytest

from experiments.classify_errors import (
    CSV_FIELDS,
    classify_results,
    main,
    write_errors,
)


def sample_item():
    return {
        "id": "L1-01",
        "level": 1,
        "sentence": "el perro duerme",
        "spanish_ok": True,
        "in_grammar": True,
        "upos": ["DET", "NOUN", "VERB"],
        "ambiguous": False,
        "attachment": None,
        "phenomena": ["svo", "intransitiva"],
        "note": "",
    }


def test_classifies_acceptance_against_both_references_and_upos():
    item = sample_item()
    result = {
        "id": item["id"],
        "tool": "spacy",
        "accepted": False,
        "upos": ["DET", "ADJ"],
    }

    errors = classify_results([item], [result])

    assert [(row["classification"], row["reference"]) for row in errors] == [
        ("falso negativo", "in_grammar"),
        ("falso negativo", "spanish_ok"),
        ("error de etiquetado", "upos"),
        ("error de etiquetado", "upos"),
    ]
    assert [row["word_index"] for row in errors[2:]] == [2, 3]
    assert errors[2]["expected"] == '"NOUN"'
    assert errors[2]["actual"] == '"ADJ"'


def test_missing_upos_output_counts_each_expected_tag_as_an_error():
    result = {"id": "L1-01", "tool": "hf", "accepted": True, "upos": None}

    errors = classify_results([sample_item()], [result])

    assert [row["word_index"] for row in errors] == [1, 2, 3]
    assert all(row["classification"] == "error de etiquetado" for row in errors)


def test_results_for_ungrammatical_spanish_skip_upos_classification():
    item = sample_item()
    item.update(spanish_ok=False, in_grammar=False, upos=None)
    result = {"id": item["id"], "tool": "parser", "accepted": False, "upos": None}

    assert classify_results([item], [result]) == []


def test_acceptance_null_is_not_counted_as_a_false_positive_or_negative():
    result = {"id": "L1-01", "tool": "hf", "accepted": None, "upos": ["DET", "NOUN", "VERB"]}

    assert classify_results([sample_item()], [result]) == []


@pytest.mark.parametrize(
    "items,results,message",
    [
        ([sample_item(), sample_item()], [], "IDs duplicados"),
        ([sample_item()], [{"id": "unknown", "tool": "hf"}], "ID desconocido"),
        (
            [sample_item()],
            [
                {"id": "L1-01", "tool": "hf", "accepted": True},
                {"id": "L1-01", "tool": "hf", "accepted": False},
            ],
            "duplicado",
        ),
    ],
)
def test_invalid_classification_inputs_are_reported(items, results, message):
    with pytest.raises(ValueError, match=message):
        classify_results(items, results)


def test_writes_csv_with_contract_fields(tmp_path):
    output = tmp_path / "nested" / "errors.csv"
    errors = classify_results(
        [sample_item()],
        [{"id": "L1-01", "tool": "spacy", "accepted": False, "upos": None}],
    )

    write_errors(errors, output)

    with output.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    assert rows[0]["classification"] == "falso negativo"
    assert tuple(rows[0].keys()) == CSV_FIELDS


def test_cli_requires_at_least_one_results_file(tmp_path):
    test_set = tmp_path / "test_set.jsonl"
    test_set.write_text(json.dumps(sample_item()) + "\n", encoding="utf-8")
    results_dir = tmp_path / "results"
    results_dir.mkdir()

    with pytest.raises(SystemExit) as error:
        main(["--test-set", str(test_set), "--results-dir", str(results_dir)])

    assert error.value.code == 2


def test_cli_reads_results_and_writes_the_classification_csv(tmp_path):
    test_set_path = tmp_path / "test_set.jsonl"
    test_set_path.write_text(json.dumps(sample_item()) + "\n", encoding="utf-8")
    results_dir = tmp_path / "results"
    results_dir.mkdir()
    result = {
        "id": "L1-01",
        "tool": "parser",
        "accepted": False,
        "upos": ["DET", "NOUN", "VERB"],
    }
    (results_dir / "parser.jsonl").write_text(json.dumps(result) + "\n", encoding="utf-8")
    output = tmp_path / "errors.csv"

    assert main(
        [
            "--test-set",
            str(test_set_path),
            "--results-dir",
            str(results_dir),
            "--output",
            str(output),
        ]
    ) == 0

    with output.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    assert [row["reference"] for row in rows] == ["in_grammar", "spanish_ok"]
    assert all(row["classification"] == "falso negativo" for row in rows)
