from typing import NoReturn

from minicpp.errors import SyntacticError
from minicpp.node import EPSILON, Node
from minicpp.tokens import Token

# ---------- Token groups used to choose between alternatives ----------
# Each group comes from a FIRST set of grammars/cpp.gram.

LITERALS = ("INT_LITERAL", "FLOAT_LITERAL", "STRING_LITERAL", "CHAR_LITERAL", "TRUE", "FALSE")  # FIRST(Literal)
PRIMARY_START = ("ID", *LITERALS, "LPAREN")                                 # FIRST(Primary)
ASSIGN_OPS = ("ASSIGN", "PLUS_ASSIGN", "MINUS_ASSIGN", "STAR_ASSIGN", "SLASH_ASSIGN", "PERCENT_ASSIGN")  # FIRST(AssignOp)
EQUALITY_OPS = ("EQUAL", "NOT_EQUAL")                                       # FIRST(EqualityOp)
RELATIONAL_OPS = ("LESS", "GREATER", "LESS_EQUAL", "GREATER_EQUAL")         # FIRST(RelationalOp)
ADDITIVE_OPS = ("PLUS", "MINUS")                                            # FIRST(AdditiveOp)
MULT_OPS = ("STAR", "SLASH", "PERCENT")                                     # FIRST(MultOp)
UNARY_OPS = ("NOT", "MINUS", "PLUS", "INCREMENT", "DECREMENT")              # FIRST(UnaryOp)
INCREMENT_OPS = ("INCREMENT", "DECREMENT")                                  # ++ and --
EXPR_START = (*UNARY_OPS, *PRIMARY_START)                                   # FIRST(Expr)
TYPES = ("INT", "FLOAT", "DOUBLE", "CHAR", "BOOL", "STRING")                # FIRST(Type)
CASE_LABELS = ("INT_LITERAL", "CHAR_LITERAL", "TRUE", "FALSE")              # CaseLabel without MINUS
STMT_START = (                                                              # FIRST(Stmt)
    *TYPES, "IF", "WHILE", "DO", "FOR", "SWITCH", "BREAK", "CONTINUE",
    "RETURN", "COUT", "CIN", "LBRACE", "SEMICOLON", *EXPR_START,
)


class Parser:
    """Recursive descent parser for the C++ subset defined in grammars/cpp.gram.

    Each nonterminal of the grammar has one method with the same name in
    snake_case. The first line of each method's docstring is the production
    it implements. The parser never backtracks: it chooses every production
    by looking only at the current token (one token of lookahead).
    """

    def __init__(self, tokens: list[Token]):
        self.tokens = tokens   # always ends with an EOF token
        self.pos = 0           # index of the current token

    # ---------- Helpers ----------

    def current(self) -> Token:
        """Return the lookahead token without consuming it."""
        return self.tokens[self.pos]

    def check(self, *token_types: str) -> bool:
        """Return True if the current token is one of the given types."""
        return self.current().type in token_types

    def consume(self, token_type: str) -> Node:
        """Consume the current token if it has the expected type.

        Returns a terminal leaf for the parse tree, or raises SyntacticError.
        """
        token = self.current()
        if token.type != token_type:
            self.error([token_type])
        self.pos += 1
        return Node(token_type, token=token)

    def consume_one_of(self, token_types: tuple[str, ...]) -> Node:
        """Consume the current token if it is any of the given types."""
        if not self.check(*token_types):
            self.error(list(token_types))
        return self.consume(self.current().type)

    def epsilon(self) -> Node:
        """Return an ε leaf, used when a production derives the empty string."""
        return Node(EPSILON)

    def error(self, expected: list[str]) -> NoReturn:
        """Raise a SyntacticError at the current token."""
        token = self.current()
        raise SyntacticError(token.line, token.column, expected, token)

    def require_variable(self, target: Node) -> None:
        """Check that the target of an assignment, ++ or -- is a plain variable.

        The grammar cannot express this rule and stay LL(1), so it is checked
        here (CONTRATO.md, section 2). The error points at the first token
        that breaks the rule: the target itself if it does not start with an
        identifier, or the token right after the identifier otherwise.
        """
        tokens = target.leaves()
        if len(tokens) == 1 and tokens[0].type == "ID":
            return
        offending = tokens[1] if tokens[0].type == "ID" else tokens[0]
        raise SyntacticError(offending.line, offending.column, ["ID"], offending)

    # ---------- Variable declarations ----------

    def type(self) -> Node:
        """Type -> INT | FLOAT | DOUBLE | CHAR | BOOL | STRING"""
        return Node("Type", [self.consume_one_of(TYPES)])

    def var_decl_tail(self) -> Node:
        """VarDeclTail -> Initializer DeclaratorList"""
        return Node("VarDeclTail", [self.initializer(), self.declarator_list()])

    def initializer(self) -> Node:
        """Initializer -> ASSIGN Expr | ε"""
        if self.check("ASSIGN"):
            return Node("Initializer", [self.consume("ASSIGN"), self.expr()])
        return Node("Initializer", [self.epsilon()])

    def declarator_list(self) -> Node:
        """DeclaratorList -> COMMA ID Initializer DeclaratorList | ε"""
        if self.check("COMMA"):
            return Node("DeclaratorList", [
                self.consume("COMMA"), self.consume("ID"), self.initializer(), self.declarator_list(),
            ])
        return Node("DeclaratorList", [self.epsilon()])

    def local_decl(self) -> Node:
        """LocalDecl -> Type ID VarDeclTail SEMICOLON"""
        return Node("LocalDecl", [self.type(), self.consume("ID"), self.var_decl_tail(), self.consume("SEMICOLON")])

    # ---------- Statements ----------

    def block(self) -> Node:
        """Block -> LBRACE StmtList RBRACE"""
        return Node("Block", [self.consume("LBRACE"), self.stmt_list(), self.consume("RBRACE")])

    def stmt_list(self) -> Node:
        """StmtList -> Stmt StmtList | ε"""
        if self.check(*STMT_START):
            return Node("StmtList", [self.stmt(), self.stmt_list()])
        return Node("StmtList", [self.epsilon()])

    def stmt(self) -> Node:
        """Stmt -> LocalDecl | ExprStmt | IfStmt | WhileStmt | DoWhileStmt | ForStmt | SwitchStmt
        | BreakStmt | ContinueStmt | ReturnStmt | CoutStmt | CinStmt | Block | EmptyStmt"""
        if self.check(*TYPES):
            child = self.local_decl()
        elif self.check("IF"):
            child = self.if_stmt()
        elif self.check("WHILE"):
            child = self.while_stmt()
        elif self.check("DO"):
            child = self.do_while_stmt()
        elif self.check("FOR"):
            child = self.for_stmt()
        elif self.check("SWITCH"):
            child = self.switch_stmt()
        elif self.check("BREAK"):
            child = self.break_stmt()
        elif self.check("CONTINUE"):
            child = self.continue_stmt()
        elif self.check("RETURN"):
            child = self.return_stmt()
        elif self.check("COUT"):
            child = self.cout_stmt()
        elif self.check("CIN"):
            child = self.cin_stmt()
        elif self.check("LBRACE"):
            child = self.block()
        elif self.check("SEMICOLON"):
            child = self.empty_stmt()
        elif self.check(*EXPR_START):
            child = self.expr_stmt()
        else:
            self.error(list(STMT_START))
        return Node("Stmt", [child])

    def expr_stmt(self) -> Node:
        """ExprStmt -> Expr SEMICOLON"""
        return Node("ExprStmt", [self.expr(), self.consume("SEMICOLON")])

    def empty_stmt(self) -> Node:
        """EmptyStmt -> SEMICOLON"""
        return Node("EmptyStmt", [self.consume("SEMICOLON")])

    def if_stmt(self) -> Node:
        """IfStmt -> IF LPAREN Expr RPAREN Stmt ElsePart"""
        return Node("IfStmt", [
            self.consume("IF"), self.consume("LPAREN"), self.expr(), self.consume("RPAREN"),
            self.stmt(), self.else_part(),
        ])

    def else_part(self) -> Node:
        """ElsePart -> ELSE Stmt | ε

        This is the only LL(1) conflict of the grammar (dangling else):
        ELSE is in FIRST(ELSE Stmt) and also in FOLLOW(ElsePart). Choosing
        ELSE Stmt whenever ELSE appears binds each else to the nearest if,
        as C++ does.
        """
        if self.check("ELSE"):
            return Node("ElsePart", [self.consume("ELSE"), self.stmt()])
        return Node("ElsePart", [self.epsilon()])

    def while_stmt(self) -> Node:
        """WhileStmt -> WHILE LPAREN Expr RPAREN Stmt"""
        return Node("WhileStmt", [
            self.consume("WHILE"), self.consume("LPAREN"), self.expr(), self.consume("RPAREN"), self.stmt(),
        ])

    def do_while_stmt(self) -> Node:
        """DoWhileStmt -> DO Stmt WHILE LPAREN Expr RPAREN SEMICOLON"""
        return Node("DoWhileStmt", [
            self.consume("DO"), self.stmt(), self.consume("WHILE"), self.consume("LPAREN"),
            self.expr(), self.consume("RPAREN"), self.consume("SEMICOLON"),
        ])

    def for_stmt(self) -> Node:
        """ForStmt -> FOR LPAREN ForInit OptExpr SEMICOLON OptExpr RPAREN Stmt"""
        return Node("ForStmt", [
            self.consume("FOR"), self.consume("LPAREN"), self.for_init(), self.opt_expr(),
            self.consume("SEMICOLON"), self.opt_expr(), self.consume("RPAREN"), self.stmt(),
        ])

    def for_init(self) -> Node:
        """ForInit -> LocalDecl | OptExpr SEMICOLON"""
        if self.check(*TYPES):
            return Node("ForInit", [self.local_decl()])
        return Node("ForInit", [self.opt_expr(), self.consume("SEMICOLON")])

    def opt_expr(self) -> Node:
        """OptExpr -> Expr | ε"""
        if self.check(*EXPR_START):
            return Node("OptExpr", [self.expr()])
        return Node("OptExpr", [self.epsilon()])

    def switch_stmt(self) -> Node:
        """SwitchStmt -> SWITCH LPAREN Expr RPAREN LBRACE CaseList RBRACE"""
        return Node("SwitchStmt", [
            self.consume("SWITCH"), self.consume("LPAREN"), self.expr(), self.consume("RPAREN"),
            self.consume("LBRACE"), self.case_list(), self.consume("RBRACE"),
        ])

    def case_list(self) -> Node:
        """CaseList -> Case CaseList | ε"""
        if self.check("CASE", "DEFAULT"):
            return Node("CaseList", [self.case(), self.case_list()])
        return Node("CaseList", [self.epsilon()])

    def case(self) -> Node:
        """Case -> CASE CaseLabel COLON StmtList | DEFAULT COLON StmtList"""
        if self.check("CASE"):
            return Node("Case", [self.consume("CASE"), self.case_label(), self.consume("COLON"), self.stmt_list()])
        return Node("Case", [self.consume("DEFAULT"), self.consume("COLON"), self.stmt_list()])

    def case_label(self) -> Node:
        """CaseLabel -> INT_LITERAL | CHAR_LITERAL | MINUS INT_LITERAL | TRUE | FALSE"""
        if self.check("MINUS"):
            return Node("CaseLabel", [self.consume("MINUS"), self.consume("INT_LITERAL")])
        if self.check(*CASE_LABELS):
            return Node("CaseLabel", [self.consume_one_of(CASE_LABELS)])
        self.error([*CASE_LABELS, "MINUS"])

    def break_stmt(self) -> Node:
        """BreakStmt -> BREAK SEMICOLON"""
        return Node("BreakStmt", [self.consume("BREAK"), self.consume("SEMICOLON")])

    def continue_stmt(self) -> Node:
        """ContinueStmt -> CONTINUE SEMICOLON"""
        return Node("ContinueStmt", [self.consume("CONTINUE"), self.consume("SEMICOLON")])

    def return_stmt(self) -> Node:
        """ReturnStmt -> RETURN OptExpr SEMICOLON"""
        return Node("ReturnStmt", [self.consume("RETURN"), self.opt_expr(), self.consume("SEMICOLON")])

    # ---------- Input and output ----------

    def cout_stmt(self) -> Node:
        """CoutStmt -> COUT SHIFT_LEFT CoutItem CoutTail SEMICOLON"""
        return Node("CoutStmt", [
            self.consume("COUT"), self.consume("SHIFT_LEFT"), self.cout_item(), self.cout_tail(),
            self.consume("SEMICOLON"),
        ])

    def cout_tail(self) -> Node:
        """CoutTail -> SHIFT_LEFT CoutItem CoutTail | ε"""
        if self.check("SHIFT_LEFT"):
            return Node("CoutTail", [self.consume("SHIFT_LEFT"), self.cout_item(), self.cout_tail()])
        return Node("CoutTail", [self.epsilon()])

    def cout_item(self) -> Node:
        """CoutItem -> ENDL | AdditiveExpr"""
        if self.check("ENDL"):
            return Node("CoutItem", [self.consume("ENDL")])
        return Node("CoutItem", [self.additive_expr()])

    def cin_stmt(self) -> Node:
        """CinStmt -> CIN SHIFT_RIGHT ID CinTail SEMICOLON"""
        return Node("CinStmt", [
            self.consume("CIN"), self.consume("SHIFT_RIGHT"), self.consume("ID"), self.cin_tail(),
            self.consume("SEMICOLON"),
        ])

    def cin_tail(self) -> Node:
        """CinTail -> SHIFT_RIGHT ID CinTail | ε"""
        if self.check("SHIFT_RIGHT"):
            return Node("CinTail", [self.consume("SHIFT_RIGHT"), self.consume("ID"), self.cin_tail()])
        return Node("CinTail", [self.epsilon()])

    # ---------- Expressions ----------

    def expr(self) -> Node:
        """Expr -> AssignExpr"""
        return Node("Expr", [self.assign_expr()])

    def assign_expr(self) -> Node:
        """AssignExpr -> OrExpr AssignTail"""
        left = self.or_expr()
        if self.check(*ASSIGN_OPS):
            self.require_variable(left)
        return Node("AssignExpr", [left, self.assign_tail()])

    def assign_tail(self) -> Node:
        """AssignTail -> AssignOp AssignExpr | ε"""
        if self.check(*ASSIGN_OPS):
            return Node("AssignTail", [self.assign_op(), self.assign_expr()])
        return Node("AssignTail", [self.epsilon()])

    def assign_op(self) -> Node:
        """AssignOp -> ASSIGN | PLUS_ASSIGN | MINUS_ASSIGN | STAR_ASSIGN | SLASH_ASSIGN | PERCENT_ASSIGN"""
        return Node("AssignOp", [self.consume_one_of(ASSIGN_OPS)])

    def or_expr(self) -> Node:
        """OrExpr -> AndExpr OrExprTail"""
        return Node("OrExpr", [self.and_expr(), self.or_expr_tail()])

    def or_expr_tail(self) -> Node:
        """OrExprTail -> OR AndExpr OrExprTail | ε"""
        if self.check("OR"):
            return Node("OrExprTail", [self.consume("OR"), self.and_expr(), self.or_expr_tail()])
        return Node("OrExprTail", [self.epsilon()])

    def and_expr(self) -> Node:
        """AndExpr -> EqualityExpr AndExprTail"""
        return Node("AndExpr", [self.equality_expr(), self.and_expr_tail()])

    def and_expr_tail(self) -> Node:
        """AndExprTail -> AND EqualityExpr AndExprTail | ε"""
        if self.check("AND"):
            return Node("AndExprTail", [self.consume("AND"), self.equality_expr(), self.and_expr_tail()])
        return Node("AndExprTail", [self.epsilon()])

    def equality_expr(self) -> Node:
        """EqualityExpr -> RelationalExpr EqualityExprTail"""
        return Node("EqualityExpr", [self.relational_expr(), self.equality_expr_tail()])

    def equality_expr_tail(self) -> Node:
        """EqualityExprTail -> EqualityOp RelationalExpr EqualityExprTail | ε"""
        if self.check(*EQUALITY_OPS):
            return Node("EqualityExprTail", [self.equality_op(), self.relational_expr(), self.equality_expr_tail()])
        return Node("EqualityExprTail", [self.epsilon()])

    def equality_op(self) -> Node:
        """EqualityOp -> EQUAL | NOT_EQUAL"""
        return Node("EqualityOp", [self.consume_one_of(EQUALITY_OPS)])

    def relational_expr(self) -> Node:
        """RelationalExpr -> AdditiveExpr RelationalExprTail"""
        return Node("RelationalExpr", [self.additive_expr(), self.relational_expr_tail()])

    def relational_expr_tail(self) -> Node:
        """RelationalExprTail -> RelationalOp AdditiveExpr RelationalExprTail | ε"""
        if self.check(*RELATIONAL_OPS):
            return Node("RelationalExprTail", [self.relational_op(), self.additive_expr(), self.relational_expr_tail()])
        return Node("RelationalExprTail", [self.epsilon()])

    def relational_op(self) -> Node:
        """RelationalOp -> LESS | GREATER | LESS_EQUAL | GREATER_EQUAL"""
        return Node("RelationalOp", [self.consume_one_of(RELATIONAL_OPS)])

    def additive_expr(self) -> Node:
        """AdditiveExpr -> MultExpr AdditiveExprTail"""
        return Node("AdditiveExpr", [self.mult_expr(), self.additive_expr_tail()])

    def additive_expr_tail(self) -> Node:
        """AdditiveExprTail -> AdditiveOp MultExpr AdditiveExprTail | ε"""
        if self.check(*ADDITIVE_OPS):
            return Node("AdditiveExprTail", [self.additive_op(), self.mult_expr(), self.additive_expr_tail()])
        return Node("AdditiveExprTail", [self.epsilon()])

    def additive_op(self) -> Node:
        """AdditiveOp -> PLUS | MINUS"""
        return Node("AdditiveOp", [self.consume_one_of(ADDITIVE_OPS)])

    def mult_expr(self) -> Node:
        """MultExpr -> UnaryExpr MultExprTail"""
        return Node("MultExpr", [self.unary_expr(), self.mult_expr_tail()])

    def mult_expr_tail(self) -> Node:
        """MultExprTail -> MultOp UnaryExpr MultExprTail | ε"""
        if self.check(*MULT_OPS):
            return Node("MultExprTail", [self.mult_op(), self.unary_expr(), self.mult_expr_tail()])
        return Node("MultExprTail", [self.epsilon()])

    def mult_op(self) -> Node:
        """MultOp -> STAR | SLASH | PERCENT"""
        return Node("MultOp", [self.consume_one_of(MULT_OPS)])

    def unary_expr(self) -> Node:
        """UnaryExpr -> UnaryOp UnaryExpr | PostfixExpr"""
        if self.check(*UNARY_OPS):
            op = self.unary_op()
            operand = self.unary_expr()
            if op.children[0].label in INCREMENT_OPS:
                self.require_variable(operand)
            return Node("UnaryExpr", [op, operand])
        return Node("UnaryExpr", [self.postfix_expr()])

    def unary_op(self) -> Node:
        """UnaryOp -> NOT | MINUS | PLUS | INCREMENT | DECREMENT"""
        return Node("UnaryOp", [self.consume_one_of(UNARY_OPS)])

    def postfix_expr(self) -> Node:
        """PostfixExpr -> Primary PostfixOpt"""
        primary = self.primary()
        if self.check(*INCREMENT_OPS):
            self.require_variable(primary)
        return Node("PostfixExpr", [primary, self.postfix_opt()])

    def postfix_opt(self) -> Node:
        """PostfixOpt -> INCREMENT | DECREMENT | ε"""
        if self.check(*INCREMENT_OPS):
            return Node("PostfixOpt", [self.consume_one_of(INCREMENT_OPS)])
        return Node("PostfixOpt", [self.epsilon()])

    def primary(self) -> Node:
        """Primary -> ID IdTail | Literal | LPAREN Expr RPAREN"""
        if self.check("ID"):
            return Node("Primary", [self.consume("ID"), self.id_tail()])
        if self.check(*LITERALS):
            return Node("Primary", [self.literal()])
        if self.check("LPAREN"):
            return Node("Primary", [self.consume("LPAREN"), self.expr(), self.consume("RPAREN")])
        self.error(list(PRIMARY_START))

    def id_tail(self) -> Node:
        """IdTail -> LPAREN Args RPAREN | ε"""
        if self.check("LPAREN"):
            return Node("IdTail", [self.consume("LPAREN"), self.args(), self.consume("RPAREN")])
        return Node("IdTail", [self.epsilon()])

    def args(self) -> Node:
        """Args -> Expr ArgsTail | ε"""
        if self.check("RPAREN"):
            return Node("Args", [self.epsilon()])
        return Node("Args", [self.expr(), self.args_tail()])

    def args_tail(self) -> Node:
        """ArgsTail -> COMMA Expr ArgsTail | ε"""
        if self.check("COMMA"):
            return Node("ArgsTail", [self.consume("COMMA"), self.expr(), self.args_tail()])
        return Node("ArgsTail", [self.epsilon()])

    def literal(self) -> Node:
        """Literal -> INT_LITERAL | FLOAT_LITERAL | STRING_LITERAL | CHAR_LITERAL | TRUE | FALSE"""
        return Node("Literal", [self.consume_one_of(LITERALS)])