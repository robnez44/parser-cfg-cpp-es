import json
from types import SimpleNamespace

import pytest

from experiments import run_llm
from experiments.llm_validator import GRAMMAR, LEXICON, parse_response, validate
from experiments.run_llm import (
    MARKER,
    build_prompt,
    build_results,
    call_model,
    check_examples_outside_set,
    few_shot_sentences,
    load_prompt,
    pending_calls,
    result_line,
    run_mode,
)

PERRO_TREE = "(Sentence (Clause (NpSing (NpMS (DET_MS el) (NOUN_MS perro))) (VpSing (VERB_S duerme))))"
CARTA_VERB = (
    "(Sentence (Clause (NpSing (NpMS (DET_MS el) (NOUN_MS maestro))) (VpSing (VERB_S lee) "
    "(VpTail (Object (NounPhrase (NpSing (NpFS (DET_FS la) (NOUN_FS carta))))) (PpList (PrepPhrase "
    "(PREP en) (NounPhrase (NpSing (NpFS (DET_FS la) (NOUN_FS casa))))))))))"
)


def raw(accepted: bool, tree: str | None = None, upos=None, violated_rule=None) -> str:
    return json.dumps({"accepted": accepted, "tree": tree, "upos": upos, "violated_rule": violated_rule},
                      ensure_ascii=False)


def entry(repeat: int, raw_response: str) -> dict:
    return {"repeat": repeat, "raw_response": raw_response}


class FakeClient:
    """Stands in for anthropic.Anthropic: answers from a function and records the requests."""

    def __init__(self, answer=lambda prompt: raw(False)):
        self.requests = []
        self.answer = answer
        self.messages = self

    def create(self, **request):
        self.requests.append(request)
        prompt = request["messages"][0]["content"]
        return SimpleNamespace(
            model="claude-haiku-5-5-fake",
            stop_reason="end_turn",
            usage=SimpleNamespace(input_tokens=100, output_tokens=20),
            content=[
                SimpleNamespace(type="thinking", thinking="..."),
                SimpleNamespace(type="text", text=self.answer(prompt)),
            ],
        )


class NoCallsClient:
    @property
    def messages(self):
        raise AssertionError("no debía llamar a la API")


# ---------- prompts ----------

@pytest.mark.parametrize("mode", ["zero", "few"])
def test_prompt_has_the_marker_once(mode):
    assert load_prompt(mode).count(MARKER) == 1


@pytest.mark.parametrize("mode", ["zero", "few"])
def test_prompt_has_every_rule_of_es_gram(mode):
    text = load_prompt(mode)
    rules = {}
    for production in GRAMMAR.productions:
        rules.setdefault(production.lhs, []).append(" ".join(production.rhs) or "ε")
    for lhs, alternatives in rules.items():
        assert f"{lhs} -> {' | '.join(alternatives)}" in text


@pytest.mark.parametrize("mode", ["zero", "few"])
def test_prompt_has_every_word_of_the_lexicon_with_its_type(mode):
    lines = {line.split(" ")[0]: line for line in load_prompt(mode).splitlines() if " (" in line and "): " in line}
    for word, row in LEXICON.items():
        words = lines[row["type"]].split("): ")[1].split(", ")
        assert word in words, word
        assert f"{row['type']} ({row['upos']})" in lines[row["type"]]


def test_few_shot_is_zero_shot_plus_examples():
    zero, few = load_prompt("zero"), load_prompt("few")
    head, tail = zero.split("## Oración\n")
    assert few.startswith(head + "## Ejemplos resueltos")
    assert few.endswith("## Oración\n" + tail)


def test_few_shot_has_three_to_five_examples():
    assert 3 <= len(few_shot_sentences(load_prompt("few"))) <= 5
    assert few_shot_sentences(load_prompt("zero")) == []


def test_few_shot_examples_pass_the_validator():
    text = load_prompt("few")
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line.startswith("Oración: "):
            sentence = line.removeprefix("Oración: ")
            response = parse_response(lines[index + 1])
            assert validate(response, sentence).valid, sentence


def test_build_prompt_puts_the_sentence():
    prompt = build_prompt(load_prompt("zero"), "el perro duerme")
    assert MARKER not in prompt
    assert prompt.rstrip().endswith("el perro duerme")


def test_examples_outside_set_detects_overlap():
    template = "Oración: el niña come\nOración: el perro que corre duerme\n"
    test_set = [{"sentence": "El niña come."}, {"sentence": "el gato duerme"}]
    assert check_examples_outside_set(template, test_set) == ["el niña come"]


# ---------- calling the model ----------

def test_call_model_sends_no_temperature_and_disables_thinking():
    client = FakeClient(lambda prompt: raw(False))
    answer = call_model(client, "claude-haiku-5-5", "hola", "disabled")
    request = client.requests[0]
    assert "temperature" not in request
    assert request["thinking"] == {"type": "disabled"}
    assert request["model"] == "claude-haiku-5-5"
    assert answer["raw_response"] == raw(False)
    assert answer["response_model"] == "claude-haiku-5-5-fake"
    assert answer["usage"] == {"input_tokens": 100, "output_tokens": 20}


def test_call_model_adaptive_sends_no_thinking_field():
    client = FakeClient()
    call_model(client, "claude-haiku-5-5", "hola", "adaptive")
    assert "thinking" not in client.requests[0]


def test_pending_calls_skips_what_is_in_the_log():
    test_set = [{"id": "L1-01"}, {"id": "L1-02"}]
    log = [{"id": "L1-01", "repeat": 1}, {"id": "L1-01", "repeat": 2}]
    pending = [(item["id"], repeat) for item, repeat in pending_calls(test_set, log, 2)]
    assert pending == [("L1-02", 1), ("L1-02", 2)]


def test_run_mode_writes_the_log_and_does_not_repeat_calls(tmp_path):
    test_set = [{"id": "L1-01", "sentence": "el perro duerme"},
                {"id": "L2-01", "sentence": "el niña come"}]
    answers = {"el perro duerme": raw(True, PERRO_TREE, ["DET", "NOUN", "VERB"]),
               "el niña come": raw(False, None, ["DET", "NOUN", "VERB"], "concordancia")}
    client = FakeClient(lambda prompt: answers[prompt.rstrip().splitlines()[-1]])
    log_path = tmp_path / "zero.jsonl"

    assert run_mode(client, "zero", test_set, 2, "claude-haiku-5-5", "disabled", log_path) == 4
    log = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    assert [(line["id"], line["repeat"]) for line in log] == [
        ("L1-01", 1), ("L1-01", 2), ("L2-01", 1), ("L2-01", 2),
    ]
    first = log[0]
    assert first["model"] == "claude-haiku-5-5"
    assert first["mode"] == "zero"
    assert first["prompt"].rstrip().endswith("el perro duerme")
    assert first["validator"] == {"valid": True, "errors": []}
    assert first["date"]

    assert run_mode(NoCallsClient(), "zero", test_set, 2, "claude-haiku-5-5", "disabled", log_path) == 0


def test_log_entry_records_unreadable_answers(tmp_path):
    client = FakeClient(lambda prompt: "no sé")
    run_mode(client, "zero", [{"id": "L1-01", "sentence": "el perro duerme"}], 1,
             "claude-haiku-5-5", "disabled", tmp_path / "zero.jsonl")
    line = json.loads((tmp_path / "zero.jsonl").read_text(encoding="utf-8"))
    assert line["parsed"] is None
    assert line["parse_error"] == "la respuesta no tiene un objeto JSON"
    assert line["validator"]["valid"] is False


# ---------- results ----------

def test_result_line_accepted_with_valid_tree():
    line = result_line("llm_zero", "L2-07", [entry(1, raw(True, CARTA_VERB, ["DET"]))],
                       "el maestro lee la carta en la casa")
    assert line == {
        "id": "L2-07", "tool": "llm_zero", "accepted": True, "upos": ["DET"], "attachment": "verb",
        "tree": CARTA_VERB, "error": None, "valid_tree": True,
    }


def test_result_line_rejected_keeps_the_violated_rule():
    line = result_line("llm_few", "L2-01", [entry(1, raw(False, None, None, "concordancia de género"))],
                       "el niña come")
    assert line["accepted"] is False
    assert line["error"] == "concordancia de género"
    assert line["valid_tree"] is True
    assert line["attachment"] is None


def test_result_line_invalid_tree_is_a_deviation():
    tree = PERRO_TREE.replace("(DET_MS el)", "(DET_FS el)")
    line = result_line("llm_zero", "L1-01", [entry(1, raw(True, tree))], "el perro duerme")
    assert line["accepted"] is True
    assert line["valid_tree"] is False
    assert line["error"].startswith("validador: ")


def test_result_line_majority_vote():
    entries = [entry(1, raw(False)), entry(2, raw(True, PERRO_TREE)), entry(3, raw(True, PERRO_TREE))]
    line = result_line("llm_zero", "L1-01", entries, "el perro duerme")
    assert line["accepted"] is True
    assert line["tree"] == PERRO_TREE


def test_result_line_tie_goes_to_the_first_repetition():
    entries = [entry(2, raw(True, PERRO_TREE)), entry(1, raw(False))]
    assert result_line("llm_zero", "L1-01", entries, "el perro duerme")["accepted"] is False


def test_result_line_ignores_unreadable_repetitions():
    entries = [entry(1, "error"), entry(2, raw(True, PERRO_TREE))]
    assert result_line("llm_zero", "L1-01", entries, "el perro duerme")["accepted"] is True


def test_result_line_all_unreadable():
    line = result_line("llm_zero", "L1-01", [entry(1, "nada")], "el perro duerme")
    assert line["accepted"] is None
    assert line["upos"] is None
    assert line["valid_tree"] is False
    assert line["error"] == "respuesta inválida: la respuesta no tiene un objeto JSON"


def test_build_results_follows_the_order_of_the_set():
    test_set = [{"id": "L1-02", "sentence": "el perro duerme"}, {"id": "L1-01", "sentence": "el perro duerme"}]
    log = [{"id": "L1-01", "repeat": 1, "raw_response": raw(False)},
           {"id": "L1-02", "repeat": 1, "raw_response": raw(False)}]
    assert [line["id"] for line in build_results("zero", test_set, log)] == ["L1-02", "L1-01"]


# ---------- command line ----------

@pytest.fixture
def project(tmp_path, monkeypatch):
    """A copy of the paths of run_llm inside a temporary folder."""
    (tmp_path / "data").mkdir()
    test_set = [{"id": "L1-01", "sentence": "el perro duerme"}]
    (tmp_path / "data" / "test_set.jsonl").write_text(
        "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in test_set), encoding="utf-8")
    monkeypatch.setattr(run_llm, "ROOT", tmp_path)
    monkeypatch.setattr(run_llm, "TEST_SET", tmp_path / "data" / "test_set.jsonl")
    monkeypatch.setattr(run_llm, "LOGS", tmp_path / "logs" / "llm")
    monkeypatch.setattr(run_llm, "RESULTS", tmp_path / "results")
    monkeypatch.setattr(run_llm, "load_env_file", lambda: None)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    return tmp_path


def test_main_without_key_stops_before_calling(project, capsys):
    assert run_llm.main([]) == 1
    assert "no hay ANTHROPIC_API_KEY" in capsys.readouterr().out


def test_main_offline_builds_results_from_the_logs(project):
    logs = project / "logs" / "llm"
    logs.mkdir(parents=True)
    line = {"id": "L1-01", "repeat": 1, "raw_response": raw(True, PERRO_TREE), "parsed": {"accepted": True}}
    (logs / "zero.jsonl").write_text(json.dumps(line, ensure_ascii=False) + "\n", encoding="utf-8")

    assert run_llm.main(["--offline", "--mode", "zero"]) == 0
    results = [json.loads(text) for text in (project / "results" / "llm_zero.jsonl").read_text("utf-8").splitlines()]
    assert results[0]["accepted"] is True
    assert results[0]["tool"] == "llm_zero"


def test_main_with_complete_logs_does_not_need_a_key(project):
    logs = project / "logs" / "llm"
    logs.mkdir(parents=True)
    line = {"id": "L1-01", "repeat": 1, "raw_response": raw(False), "parsed": {"accepted": False}}
    for mode in ("zero", "few"):
        (logs / f"{mode}.jsonl").write_text(json.dumps(line) + "\n", encoding="utf-8")
    assert run_llm.main(["--repeats", "1"]) == 0


def test_main_stops_if_an_example_is_in_the_set(project, capsys):
    example = few_shot_sentences(load_prompt("few"))[0]
    (project / "data" / "test_set.jsonl").write_text(
        json.dumps({"id": "L1-01", "sentence": example}, ensure_ascii=False) + "\n", encoding="utf-8")
    assert run_llm.main(["--offline"]) == 1
    assert "están en el set de prueba" in capsys.readouterr().out


def test_main_without_test_set(project, capsys):
    (project / "data" / "test_set.jsonl").unlink()
    assert run_llm.main(["--offline"]) == 1
    assert "hace falta el set de prueba" in capsys.readouterr().out
