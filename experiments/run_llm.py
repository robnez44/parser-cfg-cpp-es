"""Experiment with the LLM (CONTRATO_FASE2.md, section 11).

Sends each sentence of data/test_set.jsonl to Claude Haiku with the zero-shot
and the few-shot prompt, saves every call in logs/llm/<mode>.jsonl and writes
results/llm_zero.jsonl and results/llm_few.jsonl from those logs.

The logs are the source of the results. A call that is already in the log is
never repeated, so with complete logs the script does not use the API at all
and anyone can rebuild the results without a key:

    uv run python -m experiments.run_llm              # calls only what is missing
    uv run python -m experiments.run_llm --offline    # never calls the API

The key goes in the ANTHROPIC_API_KEY environment variable or in a .env file
(ignored by git), never in the code.
"""

import argparse
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from nltk import Tree

from experiments.llm_validator import ResponseError, attachment, parse_response, validate

ROOT = Path(__file__).resolve().parent.parent
TEST_SET = ROOT / "data" / "test_set.jsonl"
PROMPTS = ROOT / "prompts"
LOGS = ROOT / "logs" / "llm"
RESULTS = ROOT / "results"

MODES = {"zero": "zero_shot.txt", "few": "few_shot.txt"}
MARKER = "<<ORACION>>"

DEFAULT_MODEL = "claude-haiku-5-5"
# The model's own reasoning counts toward max_tokens, so there is room for it
# before the JSON answer.
MAX_TOKENS = 8192
# Haiku 5.5 does not accept temperature (any value returns a 400 error), so the
# variation between calls is measured by repeating each sentence instead.
DEFAULT_REPEATS = 3


# ---------- Inputs ----------

def read_jsonl(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as file:
        return [json.loads(line) for line in file if line.strip()]


def load_prompt(mode: str) -> str:
    text = (PROMPTS / MODES[mode]).read_text(encoding="utf-8")
    if text.count(MARKER) != 1:
        raise ValueError(f"el prompt {MODES[mode]} debe tener {MARKER} una sola vez")
    return text


def build_prompt(template: str, sentence: str) -> str:
    return template.replace(MARKER, sentence)


def few_shot_sentences(template: str) -> list[str]:
    """Return the sentences of the solved examples of the few-shot prompt."""
    return re.findall(r"^Oración: (.+)$", template, re.MULTILINE)


def check_examples_outside_set(template: str, test_set: list[dict]) -> list[str]:
    """Return the few-shot examples that are also in the test set (it must be empty)."""
    sentences = {normalize(item["sentence"]) for item in test_set}
    return [example for example in few_shot_sentences(template) if normalize(example) in sentences]


def normalize(sentence: str) -> str:
    return " ".join(sentence.lower().replace(".", " ").split())


def load_env_file(path: Path = ROOT / ".env") -> None:
    """Read KEY=VALUE lines from .env without overwriting variables already set."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        key, sep, value = line.partition("=")
        if sep and not key.strip().startswith("#"):
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


# ---------- Calling the model ----------

def call_model(client, model: str, prompt: str, thinking: str) -> dict:
    """Send one prompt and return what the log needs from the answer."""
    request = {
        "model": model,
        "max_tokens": MAX_TOKENS,
        "messages": [{"role": "user", "content": prompt}],
    }
    if thinking == "disabled":
        request["thinking"] = {"type": "disabled"}

    response = client.messages.create(**request)
    raw = "".join(block.text for block in response.content if block.type == "text")

    return {
        "response_model": response.model,
        "stop_reason": response.stop_reason,
        "usage": {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        },
        "raw_response": raw,
    }


def log_entry(mode: str, model: str, thinking: str, item: dict, repeat: int,
              prompt: str, answer: dict) -> dict:
    """Build one line of logs/llm/<mode>.jsonl, with the validator result."""
    try:
        response = parse_response(answer["raw_response"])
        parse_error = None
        errors = validate(response, item["sentence"]).errors
    except ResponseError as error:
        response = None
        parse_error = str(error)
        errors = [str(error)]

    return {
        "date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "model": model,
        **{key: answer[key] for key in ("response_model", "stop_reason", "usage")},
        "mode": mode,
        "thinking": thinking,
        "id": item["id"],
        "repeat": repeat,
        "sentence": item["sentence"],
        "prompt": prompt,
        "raw_response": answer["raw_response"],
        "parsed": response,
        "parse_error": parse_error,
        "validator": {"valid": not errors, "errors": errors},
    }


def pending_calls(test_set: list[dict], log: list[dict], repeats: int) -> list[tuple[dict, int]]:
    """Return the (sentence, repeat) pairs that are not in the log yet."""
    done = {(entry["id"], entry["repeat"]) for entry in log}
    return [(item, repeat) for item in test_set for repeat in range(1, repeats + 1)
            if (item["id"], repeat) not in done]


def run_mode(client, mode: str, test_set: list[dict], repeats: int, model: str,
             thinking: str, log_path: Path) -> int:
    """Call the model for each missing pair and append it to the log at once.

    Each line is written as soon as it arrives, so if the run stops halfway
    the next run continues from there. Returns the number of calls made.
    """
    template = load_prompt(mode)
    log = read_jsonl(log_path) if log_path.exists() else []
    todo = pending_calls(test_set, log, repeats)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    with open(log_path, "a", encoding="utf-8") as file:
        for number, (item, repeat) in enumerate(todo, start=1):
            prompt = build_prompt(template, item["sentence"])
            answer = call_model(client, model, prompt, thinking)
            entry = log_entry(mode, model, thinking, item, repeat, prompt, answer)
            file.write(json.dumps(entry, ensure_ascii=False) + "\n")
            file.flush()
            print(f"  [{mode}] {number}/{len(todo)} {item['id']} repetición {repeat}")

    return len(todo)


# ---------- From the logs to the results ----------

def result_line(tool: str, item_id: str, entries: list[dict], sentence: str) -> dict:
    """Combine the repetitions of one sentence into one line of results/<tool>.jsonl.

    The answer is the majority vote on "accepted" among the answers that could
    be read; the tree and the UPOS come from the first repetition that voted
    with the majority. The validator runs again on the raw answer, so a fix to
    the validator changes the results without calling the API again.
    """
    entries = sorted(entries, key=lambda entry: entry["repeat"])
    readable, problems = [], []
    for entry in entries:
        try:
            readable.append(parse_response(entry["raw_response"]))
        except ResponseError as error:
            problems.append(str(error))

    if not readable:
        return {
            "id": item_id, "tool": tool, "accepted": None, "upos": None, "attachment": None,
            "tree": None, "error": f"respuesta inválida: {problems[0]}", "valid_tree": False,
        }

    votes = Counter(response["accepted"] for response in readable)
    majority = max(votes, key=lambda value: (votes[value], value == readable[0]["accepted"]))
    chosen = next(response for response in readable if response["accepted"] == majority)

    errors = validate(chosen, sentence).errors
    tree, place = chosen["tree"], None
    if tree is not None:
        try:
            parsed = Tree.fromstring(tree)
            tree = parsed.pformat(margin=sys.maxsize)
            place = attachment(parsed) if chosen["accepted"] else None
        except ValueError:
            pass

    messages = [f"validador: {error}" for error in errors]
    if not chosen["accepted"] and chosen["violated_rule"]:
        messages.insert(0, str(chosen["violated_rule"]))

    return {
        "id": item_id,
        "tool": tool,
        "accepted": chosen["accepted"],
        "upos": chosen["upos"],
        "attachment": place,
        "tree": tree,
        "error": "; ".join(messages) or None,
        "valid_tree": not errors,
    }


def build_results(mode: str, test_set: list[dict], log: list[dict]) -> list[dict]:
    by_id: dict[str, list[dict]] = {}
    for entry in log:
        by_id.setdefault(entry["id"], []).append(entry)

    return [result_line(f"llm_{mode}", item["id"], by_id[item["id"]], item["sentence"])
            for item in test_set if item["id"] in by_id]


def summary(mode: str, test_set: list[dict], log: list[dict], results: list[dict]) -> str:
    """Short text for the console: what is in the log and how the answers look."""
    by_id: dict[str, set] = {}
    for entry in log:
        accepted = (entry["parsed"] or {}).get("accepted")
        by_id.setdefault(entry["id"], set()).add(accepted)

    unstable = sum(1 for answers in by_id.values() if len(answers) > 1)
    unreadable = sum(1 for line in results if line["accepted"] is None)
    invalid = sum(1 for line in results if line["accepted"] is not None and not line["valid_tree"])

    return (
        f"llm_{mode}: {len(results)}/{len(test_set)} oraciones, {len(log)} llamadas en el log; "
        f"aceptadas {sum(1 for line in results if line['accepted'])}, "
        f"respuestas ilegibles {unreadable}, árboles inválidos {invalid}, "
        f"oraciones con repeticiones que no coinciden {unstable}"
    )


def thinking_mismatch(logs: dict[str, Path], thinking: str) -> tuple[Path, str] | None:
    """Return (log, mode) of the first log that was made with another thinking mode."""
    for path in logs.values():
        if not path.exists():
            continue
        for entry in read_jsonl(path):
            if entry.get("thinking") not in (None, thinking):
                return path, entry.get("thinking")
    return None


def write_jsonl(path: Path, lines: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        for line in lines:
            file.write(json.dumps(line, ensure_ascii=False) + "\n")


# ---------- Command line ----------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Experimento del LLM con los prompts zero-shot y few-shot")
    parser.add_argument("--mode", choices=["zero", "few", "both"], default="both")
    parser.add_argument("--repeats", type=int, default=DEFAULT_REPEATS,
                        help=f"repeticiones por oración (por defecto {DEFAULT_REPEATS})")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--thinking", choices=["disabled", "adaptive"], default="adaptive",
                        help="adaptive deja el razonamiento del modelo (por defecto); disabled lo apaga")
    parser.add_argument("--offline", action="store_true",
                        help="no llama a la API: solo arma los resultados con los logs que haya")
    parser.add_argument("--limit", type=int, help="usa solo las primeras N oraciones (para probar)")
    args = parser.parse_args(argv)

    if not TEST_SET.exists():
        print(f"No existe {TEST_SET.relative_to(ROOT)}; hace falta el set de prueba.")
        return 1

    test_set = read_jsonl(TEST_SET)[: args.limit]
    overlap = check_examples_outside_set(load_prompt("few"), test_set)
    if overlap:
        print("Estos ejemplos del few-shot están en el set de prueba: " + ", ".join(overlap))
        return 1

    modes = ["zero", "few"] if args.mode == "both" else [args.mode]
    logs = {mode: LOGS / f"{mode}.jsonl" for mode in modes}

    if not args.offline:
        needed = sum(
            len(pending_calls(test_set, read_jsonl(path) if path.exists() else [], args.repeats))
            for path in logs.values()
        )
        mixed = thinking_mismatch(logs, args.thinking) if needed else None
        if mixed:
            print(f"El log {mixed[0].relative_to(ROOT)} se hizo con thinking={mixed[1]} y ahora pides "
                  f"thinking={args.thinking}. No se mezclan: borra el log o usa --thinking {mixed[1]}.")
            return 1

        if needed:
            load_env_file()
            if not os.environ.get("ANTHROPIC_API_KEY"):
                print(f"Faltan {needed} llamadas y no hay ANTHROPIC_API_KEY. "
                      "Usa --offline para armar los resultados solo con los logs.")
                return 1

            import anthropic

            client = anthropic.Anthropic(max_retries=5)
            for mode in modes:
                try:
                    run_mode(client, mode, test_set, args.repeats, args.model, args.thinking, logs[mode])
                except anthropic.APIError as error:
                    print(f"Error de la API en el modo {mode}: {error}")
                    print("Lo que ya se guardó queda en el log; al volver a correr se sigue desde ahí.")
                    return 1

    for mode in modes:
        log = read_jsonl(logs[mode]) if logs[mode].exists() else []
        results = build_results(mode, test_set, log)
        write_jsonl(RESULTS / f"llm_{mode}.jsonl", results)
        print(summary(mode, test_set, log, results))

    return 0


if __name__ == "__main__":
    sys.exit(main())
