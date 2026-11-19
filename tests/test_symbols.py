import pytest

from minicpp.symbols import Symbol, SymbolTable


def var(name: str, type_: str = "int", line: int = 1) -> Symbol:
    return Symbol(name, "variable", type_, line, 1)


def test_declare_and_lookup_in_global_scope():
    table = SymbolTable()
    assert table.declare(var("x")) is None
    assert table.lookup("x").type == "int"


def test_lookup_of_unknown_name_returns_none():
    assert SymbolTable().lookup("x") is None


def test_declare_twice_in_same_scope_returns_previous_symbol():
    table = SymbolTable()
    first = var("x", "int", line=2)
    table.declare(first)
    assert table.declare(var("x", "double", line=5)) is first


def test_redeclaration_keeps_the_first_symbol():
    table = SymbolTable()
    table.declare(var("x", "int"))
    table.declare(var("x", "double"))
    assert table.lookup("x").type == "int"


def test_inner_scope_sees_outer_names():
    table = SymbolTable()
    table.declare(var("x"))
    table.enter_scope()
    assert table.lookup("x") is not None


def test_name_disappears_when_its_scope_closes():
    table = SymbolTable()
    table.enter_scope()
    table.declare(var("i"))
    table.exit_scope()
    assert table.lookup("i") is None


def test_shadowing_is_allowed_in_an_inner_scope():
    table = SymbolTable()
    table.declare(var("x", "int"))
    table.enter_scope()
    assert table.declare(var("x", "string")) is None
    assert table.lookup("x").type == "string"


def test_outer_symbol_comes_back_after_shadowing_ends():
    table = SymbolTable()
    table.declare(var("x", "int"))
    table.enter_scope()
    table.declare(var("x", "string"))
    table.exit_scope()
    assert table.lookup("x").type == "int"


def test_sibling_scopes_do_not_share_names():
    table = SymbolTable()
    table.enter_scope()
    table.declare(var("a"))
    table.exit_scope()
    table.enter_scope()
    assert table.lookup("a") is None
    assert table.declare(var("a")) is None


def test_function_symbol_keeps_return_type_and_parameter_types():
    table = SymbolTable()
    table.declare(Symbol("suma", "function", "int", 3, 5, ["int", "int"]))
    symbol = table.lookup("suma")
    assert symbol.kind == "function"
    assert symbol.params == ["int", "int"]


def test_symbol_keeps_its_position():
    table = SymbolTable()
    table.declare(Symbol("x", "variable", "int", 4, 9))
    assert (table.lookup("x").line, table.lookup("x").column) == (4, 9)


def test_depth_follows_enter_and_exit():
    table = SymbolTable()
    assert table.depth() == 1
    table.enter_scope()
    table.enter_scope()
    assert table.depth() == 3
    table.exit_scope()
    assert table.depth() == 2


def test_global_scope_cannot_be_closed():
    with pytest.raises(RuntimeError):
        SymbolTable().exit_scope()