"""Tests for the LL(1) verifier (P4).

The grammars in grammars/test_grammars/ come from Aho et al., "Compilers", where FIRST, FOLLOW and
the table are known, so the expected values here are the ones in the book, not the ones the code printed.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:  # lets a bare `pytest` find the verifier package
    sys.path.insert(0, str(ROOT))

from verifier import class_notation, ll1  # noqa: E402
from verifier.__main__ import main  # noqa: E402
from verifier.grammar import (  # noqa: E402
    EPSILON,
    END_MARKER,
    GrammarError,
    parse_grammar,
    read_grammar,
    validate,
)

TEST_GRAMMARS = ROOT / "grammars" / "test_grammars"
CPP_GRAM = ROOT / "grammars" / "cpp.gram"
CPP_BNF = ROOT / "grammars" / "cpp.bnf"


def analysis_of(name: str) -> ll1.Analysis:
    return ll1.analyze(read_grammar(TEST_GRAMMARS / name))


def productions_text(conflict: ll1.Conflict) -> list[str]:
    return [str(p) for p in conflict.productions]


# ---------------------------------------------------------------------------
# FIRST, FOLLOW and table: Aho's expression grammar (LL(1))
# ---------------------------------------------------------------------------


def test_expression_grammar_first_sets():
    first = analysis_of("aho_expr_ll1.gram").first
    assert first["E"] == {"(", "id"}
    assert first["T"] == {"(", "id"}
    assert first["F"] == {"(", "id"}
    assert first["E'"] == {"+", EPSILON}
    assert first["T'"] == {"*", EPSILON}


def test_expression_grammar_follow_sets():
    follow = analysis_of("aho_expr_ll1.gram").follow
    assert follow["E"] == {")", END_MARKER}
    assert follow["E'"] == {")", END_MARKER}
    assert follow["T"] == {"+", ")", END_MARKER}
    assert follow["T'"] == {"+", ")", END_MARKER}
    assert follow["F"] == {"+", "*", ")", END_MARKER}


def test_expression_grammar_table():
    table = {cell: [str(p) for p in ps] for cell, ps in analysis_of("aho_expr_ll1.gram").table.items()}
    assert table == {
        ("E", "id"): ["E -> T E'"],
        ("E", "("): ["E -> T E'"],
        ("E'", "+"): ["E' -> + T E'"],
        ("E'", ")"): [f"E' -> {EPSILON}"],
        ("E'", END_MARKER): [f"E' -> {EPSILON}"],
        ("T", "id"): ["T -> F T'"],
        ("T", "("): ["T -> F T'"],
        ("T'", "+"): [f"T' -> {EPSILON}"],
        ("T'", "*"): ["T' -> * F T'"],
        ("T'", ")"): [f"T' -> {EPSILON}"],
        ("T'", END_MARKER): [f"T' -> {EPSILON}"],
        ("F", "id"): ["F -> id"],
        ("F", "("): ["F -> ( E )"],
    }


def test_expression_grammar_is_ll1():
    analysis = analysis_of("aho_expr_ll1.gram")
    assert analysis.conflicts == []
    assert analysis.is_ll1()
    assert validate(analysis.grammar) == []


def test_nullable_nonterminals_do_not_break_ll1():
    analysis = analysis_of("aho_nullable.gram")
    assert analysis.nullable == {"A", "B"}
    assert analysis.first["S"] == {"a", "b"}
    assert analysis.first["A"] == {EPSILON}
    assert analysis.follow["A"] == {"a", "b"}
    assert analysis.follow["B"] == {"a", "b"}
    assert analysis.conflicts == []


# ---------------------------------------------------------------------------
# Conflicts
# ---------------------------------------------------------------------------


def test_dangling_else_conflict():
    analysis = analysis_of("aho_dangling_else.gram")
    assert analysis.first["S'"] == {"e", EPSILON}
    assert analysis.follow["S'"] == {"e", END_MARKER}
    assert len(analysis.conflicts) == 1
    conflict = analysis.conflicts[0]
    assert (conflict.nonterminal, conflict.terminal) == ("S'", "e")
    assert conflict.kind == "FIRST/FOLLOW"
    assert productions_text(conflict) == ["S' -> e S", f"S' -> {EPSILON}"]
    assert not analysis.is_ll1()


def test_accepting_a_conflict_makes_the_grammar_ll1_except_that_conflict():
    analysis = analysis_of("aho_dangling_else.gram")
    assert analysis.is_ll1({("S'", "e")})
    assert analysis.unaccepted_conflicts({("S'", "e")}) == []


def test_left_recursion_gives_first_first_conflicts():
    analysis = analysis_of("aho_left_recursive.gram")
    cells = {(c.nonterminal, c.terminal) for c in analysis.conflicts}
    assert cells == {("E", "("), ("E", "id"), ("T", "("), ("T", "id")}
    assert {c.kind for c in analysis.conflicts} == {"FIRST/FIRST"}


def test_common_prefix_gives_first_first_conflict():
    analysis = analysis_of("common_prefix.gram")
    assert [(c.nonterminal, c.terminal, c.kind) for c in analysis.conflicts] == [("S", "a", "FIRST/FIRST")]
    assert productions_text(analysis.conflicts[0]) == ["S -> a b", "S -> a c"]


def test_spanish_prepositional_phrase_is_a_conflict_at_the_preposition():
    analysis = analysis_of("spanish_pp_attachment.gram")
    assert [(c.nonterminal, c.terminal, c.kind) for c in analysis.conflicts] == [
        ("NounTail", "PREP", "FIRST/FOLLOW")
    ]
    assert productions_text(analysis.conflicts[0]) == ["NounTail -> PREP NounPhrase", f"NounTail -> {EPSILON}"]


def test_a_production_is_not_a_conflict_with_itself():
    # `A -> B a` where B is nullable puts the production in M[A, a] twice (via FIRST and via FOLLOW).
    analysis = ll1.analyze(parse_grammar("S -> A a\nA -> ε | b\n"))
    assert analysis.conflicts == []


def test_conflict_report_uses_the_contract_format():
    analysis = analysis_of("aho_dangling_else.gram")
    assert ll1.format_conflict(analysis.conflicts[0]) == (
        f"Conflict at M[S', e]:\n  S' -> e S\n  S' -> {EPSILON}"
    )


# ---------------------------------------------------------------------------
# The C++ subset grammar (P1)
# ---------------------------------------------------------------------------


def test_cpp_grammar_size_matches_the_contract():
    grammar = read_grammar(CPP_GRAM)
    assert len(grammar.nonterminals) == 68
    assert len(grammar.productions) == 144
    assert len(grammar.terminals) == 63


def test_cpp_grammar_is_ll1_except_for_the_dangling_else():
    analysis = ll1.analyze(read_grammar(CPP_GRAM))
    assert [(c.nonterminal, c.terminal) for c in analysis.conflicts] == [("ElsePart", "ELSE")]
    assert analysis.conflicts[0].kind == "FIRST/FOLLOW"
    assert productions_text(analysis.conflicts[0]) == ["ElsePart -> ELSE Stmt", f"ElsePart -> {EPSILON}"]
    assert analysis.is_ll1()  # the conflict is declared as accepted in cpp.gram


def test_cpp_grammar_has_no_mistakes_or_left_recursion():
    assert validate(read_grammar(CPP_GRAM)) == []


def test_cpp_grammar_start_symbol_and_follow_of_start():
    analysis = ll1.analyze(read_grammar(CPP_GRAM))
    assert analysis.grammar.start == "Program"
    assert analysis.follow["Program"] == {END_MARKER}


@pytest.mark.skipif(not CPP_BNF.exists(), reason="grammars/cpp.bnf does not exist yet")
def test_cpp_bnf_is_up_to_date_with_cpp_gram():
    grammar = read_grammar(CPP_GRAM)
    generated = class_notation.convert(grammar, ll1.analyze(grammar), "grammars/cpp.gram")
    assert generated == CPP_BNF.read_text(encoding="utf-8"), (
        "cpp.bnf is out of date; regenerate it with: "
        "python -m verifier grammars/cpp.gram --class-notation -o grammars/cpp.bnf"
    )


# ---------------------------------------------------------------------------
# Reading and validating grammar files
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text, line",
    [
        ("S -> a\nthis is not a rule\n", 2),
        ("S -> a |\n", 1),
        ("S -> a | | b\n", 1),
        ("S a -> b\n", 1),
        ("S -> ε a\n", 1),
        ("S -> a EOF\n", 1),
        ("S -> a $\n", 1),
        ("EOF -> a\n", 1),
    ],
)
def test_malformed_grammar_reports_the_line(text, line):
    with pytest.raises(GrammarError) as error:
        parse_grammar(text)
    assert error.value.line == line


def test_grammar_without_rules_is_an_error():
    with pytest.raises(GrammarError):
        parse_grammar("# only comments\n\n")


def test_rules_split_across_lines_are_merged_under_one_nonterminal():
    grammar = parse_grammar("S -> a\nT -> b\nS -> c\n")
    assert grammar.nonterminals == ["S", "T"]
    assert [str(p) for p in grammar.productions_of("S")] == ["S -> a", "S -> c"]


def test_typo_in_a_nonterminal_is_an_error():
    diagnostics = validate(parse_grammar("Program -> Header Stmt\nHeader -> INCLUDE\nStmt -> Exprr SEMICOLON\n"))
    errors = [d for d in diagnostics if d.level == "error"]
    assert len(errors) == 1
    assert "Exprr" in errors[0].message
    assert errors[0].line == 3


def test_nonterminal_that_derives_nothing_is_an_error():
    diagnostics = validate(parse_grammar("S -> A\nA -> A a\n"))
    assert any(d.level == "error" and "'A'" in d.message and "no genera" in d.message for d in diagnostics)


def test_unreachable_nonterminal_and_repeated_alternative_are_warnings():
    diagnostics = validate(parse_grammar("S -> a | a\nUnused -> b\n"))
    messages = [d.message for d in diagnostics]
    assert all(d.level == "warning" for d in diagnostics)
    assert any("'Unused'" in m and "no se alcanza" in m for m in messages)
    assert any("repetida" in m for m in messages)


def test_direct_and_indirect_left_recursion_are_found():
    messages = [d.message for d in validate(read_grammar(TEST_GRAMMARS / "aho_indirect_left_recursion.gram"))]
    assert any("indirecta" in m and "S -> A -> S" in m for m in messages)
    assert any("directa" in m and "'A'" in m for m in messages)


def test_left_recursion_hidden_behind_a_nullable_prefix_is_found():
    # S => B S a with B nullable: S is left recursive even though S is not the first symbol.
    messages = [d.message for d in validate(parse_grammar("S -> B S a | b\nB -> ε\n"))]
    assert any("recursión izquierda" in m for m in messages)


def test_accepted_conflict_comment_is_read():
    grammar = parse_grammar("# Accepted LL(1) conflict: M[ElsePart, ELSE] (dangling else)\nS -> a\n")
    assert grammar.accepted_conflicts == {("ElsePart", "ELSE")}


# ---------------------------------------------------------------------------
# Class notation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "camel, snake",
    [("Program", "program"), ("AdditiveExprTail", "additive_expr_tail"), ("ElsePart", "else_part"), ("E'", "e'")],
)
def test_to_snake_case(camel, snake):
    assert class_notation.to_snake_case(camel) == snake


def test_class_notation_of_a_small_grammar():
    grammar = parse_grammar(
        "# Grammar for tiny sums\n"
        "Sum -> Term SumTail\n"
        "SumTail -> PLUS Term SumTail | ε\n"
        "Term -> ID | LPAREN Sum RPAREN\n"
    )
    text = class_notation.convert(grammar, ll1.analyze(grammar), "grammars/tiny.gram")
    head = "<sum_tail> ::= "
    assert "# LL(1) grammar for tiny sums, in class notation." in text
    assert "<sum> ::= <term> <sum_tail>" in text
    assert f'{head}"+" <term> <sum_tail>\n{" " * (len(head) - 2)}| ε' in text
    term_head = "<term> ::= "
    assert f'{term_head}<identifier>\n{" " * (len(term_head) - 2)}| "(" <sum> ")"' in text
    assert "# Lexical level" in text
    assert "<identifier> ::= a letter" in text
    assert "<int_literal>" not in text  # only categories the grammar uses are defined


def test_unknown_terminals_are_quoted_as_written():
    grammar = parse_grammar("S -> DET NOUN\n")
    text = class_notation.convert(grammar, ll1.analyze(grammar))
    assert '<s> ::= "DET" "NOUN"' in text
    assert "# Lexical level" not in text


# ---------------------------------------------------------------------------
# Text reports and command line
# ---------------------------------------------------------------------------


def test_first_and_follow_reports():
    analysis = analysis_of("aho_expr_ll1.gram")
    # Names are padded to the width of the longest one (E' and T' have 2 characters).
    assert f"FIRST(E') = {{ +, {EPSILON} }}" in ll1.format_first(analysis)
    assert "FIRST(E)  = { (, id }" in ll1.format_first(analysis)
    assert "FOLLOW(F)  = { +, *, ), $ }" in ll1.format_follow(analysis)


def test_grid_table_marks_conflicts_with_several_productions():
    grid = ll1.format_table_grid(analysis_of("aho_dangling_else.gram"))
    legend, table = grid.split("\n\n", 1)
    assert "p3: S' -> e S" in legend
    assert f"p4: S' -> {EPSILON}" in legend
    row = next(line for line in table.splitlines() if line.startswith("| S' |"))
    assert "p3, p4" in row


def test_command_line_exit_codes(capsys):
    assert main([str(TEST_GRAMMARS / "aho_expr_ll1.gram")]) == 0
    assert main([str(TEST_GRAMMARS / "aho_dangling_else.gram")]) == 1
    assert main([str(TEST_GRAMMARS / "aho_dangling_else.gram"), "--accept", "S':e"]) == 0
    assert main([str(TEST_GRAMMARS / "does_not_exist.gram")]) == 2
    capsys.readouterr()


def test_command_line_prints_all_sections_by_default(capsys):
    assert main([str(TEST_GRAMMARS / "aho_dangling_else.gram")]) == 1
    out = capsys.readouterr().out
    for title in ("== FIRST ==", "== FOLLOW ==", "== Tabla LL(1) ==", "== Conflictos ==", "== Resumen =="):
        assert title in out
    assert f"Conflict at M[S', e]:\n  S' -> e S\n  S' -> {EPSILON}" in out


def test_command_line_can_print_a_single_section(capsys):
    main([str(TEST_GRAMMARS / "aho_expr_ll1.gram"), "--first"])
    out = capsys.readouterr().out
    assert "== FIRST ==" in out and "== FOLLOW ==" not in out


def test_command_line_stops_on_grammar_errors(tmp_path, capsys):
    bad = tmp_path / "bad.gram"
    bad.write_text("Program -> Header\nHeader -> Exprr\n", encoding="utf-8")
    assert main([str(bad)]) == 2
    captured = capsys.readouterr()
    assert "Exprr" in captured.err
    assert "== FIRST ==" not in captured.out


def test_command_line_class_notation_to_file(tmp_path, capsys):
    destination = tmp_path / "out.bnf"
    assert main([str(CPP_GRAM), "--class-notation", "-o", str(destination)]) == 0
    capsys.readouterr()
    text = destination.read_text(encoding="utf-8")
    assert text.startswith("# LL(1) grammar for the C++ subset (Phase 1), in class notation.")
    assert "<program> ::= <header> <global_list>" in text
