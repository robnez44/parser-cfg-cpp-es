from dataclasses import dataclass


@dataclass
class Symbol:
    """A name declared in the program, with its type and where it was declared."""

    name: str
    kind: str                         # "variable", "parameter" or "function"
    type: str                         # "int", "double", "string", ... For functions, the return type
    line: int
    column: int
    params: list[str] | None = None   # parameter types, only for functions


class SymbolTable:
    """A stack of scopes. Each scope is a dictionary from name to Symbol."""

    def __init__(self) -> None:
        self.scopes: list[dict[str, Symbol]] = [{}]   # the global scope is always there

    def enter_scope(self) -> None:
        self.scopes.append({})

    def exit_scope(self) -> None:
        if len(self.scopes) == 1:
            raise RuntimeError("cannot exit the global scope")
        self.scopes.pop()

    def declare(self, symbol: Symbol) -> Symbol | None:
        scope = self.scopes[-1]
        previous = scope.get(symbol.name)
        if previous is not None:
            return previous          # already in this scope: report it, keep the first one
        scope[symbol.name] = symbol
        return None

    def lookup(self, name: str) -> Symbol | None:
        for scope in reversed(self.scopes):    # innermost scope first
            if name in scope:
                return scope[name]
        return None

    def depth(self) -> int:
        return len(self.scopes)