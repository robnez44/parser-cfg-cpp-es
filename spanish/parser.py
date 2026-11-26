from typing import NoReturn

from minicpp.errors import SyntacticError
from minicpp.node import EPSILON, Node
from minicpp.tokens import Token

# ---------- Token groups used to choose between alternatives ----------
# Each group comes from a FIRST set of grammars/es.gram.

SING_DETS = ("DET_MS", "DET_FS")  # FIRST(NpSing)
PLUR_DETS = ("DET_MP", "DET_FP")  # FIRST(NpPlur)
DETERMINERS = (*SING_DETS, *PLUR_DETS)  # FIRST(NounPhrase)


class SpanishParser:
    """Recursive descent parser for the Spanish subset defined in grammars/es.gram.

    Each nonterminal of the grammar has one method with the same name in
    snake_case. The first line of each method's docstring is the production
    it implements. The parser never backtracks: it chooses every production
    by looking only at the current token (one token of lookahead).

    Agreement is part of the grammar, so there is one method for each copy
    of a nonterminal (np_ms, np_fs, np_mp, np_fp). A determiner that does
    not agree with its noun or a subject that does not agree with its verb
    is a syntactic error.
    """

    def __init__(self, tokens: list[Token]):
        self.tokens = tokens  # always ends with an EOF token
        self.pos = 0  # index of the current token

    def parse(self) -> Node:
        """Parse a whole sentence and return the root of the parse tree.

        After Sentence, the only token left must be EOF. If the sentence has
        no period, a PERIOD would also fit there, so it goes in the error.
        """
        tree = self.sentence()
        if not self.check("EOF"):
            end_mark = tree.children[1]
            self.error(["PERIOD", "EOF"] if end_mark.children[0].is_epsilon() else ["EOF"])
        return tree

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

    # ---------- Sentence ----------

    def sentence(self) -> Node:
        """Sentence -> Clause EndMark"""
        return Node("Sentence", [self.clause(), self.end_mark()])

    def clause(self) -> Node:
        """Clause -> NpSing VpSing | NpPlur VpPlur

        The determiner of the subject decides the number of the verb.
        """
        if self.check(*SING_DETS):
            return Node("Clause", [self.np_sing(), self.vp_sing()])
        if self.check(*PLUR_DETS):
            return Node("Clause", [self.np_plur(), self.vp_plur()])
        self.error(list(DETERMINERS))

    def end_mark(self) -> Node:
        """EndMark -> PERIOD | ε"""
        if self.check("PERIOD"):
            return Node("EndMark", [self.consume("PERIOD")])
        return Node("EndMark", [self.epsilon()])

    # ---------- Noun phrases ----------

    def noun_phrase(self) -> Node:
        """NounPhrase -> NpSing | NpPlur"""
        if self.check(*SING_DETS):
            return Node("NounPhrase", [self.np_sing()])
        if self.check(*PLUR_DETS):
            return Node("NounPhrase", [self.np_plur()])
        self.error(list(DETERMINERS))

    def np_sing(self) -> Node:
        """NpSing -> NpMS | NpFS"""
        if self.check("DET_MS"):
            return Node("NpSing", [self.np_ms()])
        if self.check("DET_FS"):
            return Node("NpSing", [self.np_fs()])
        self.error(list(SING_DETS))

    def np_plur(self) -> Node:
        """NpPlur -> NpMP | NpFP"""
        if self.check("DET_MP"):
            return Node("NpPlur", [self.np_mp()])
        if self.check("DET_FP"):
            return Node("NpPlur", [self.np_fp()])
        self.error(list(PLUR_DETS))

    def np_ms(self) -> Node:
        """NpMS -> DET_MS NOUN_MS AdjListMS NpTail"""
        return Node(
            "NpMS",
            [self.consume("DET_MS"), self.consume("NOUN_MS"), self.adj_list_ms(), self.np_tail()],
        )

    def np_fs(self) -> Node:
        """NpFS -> DET_FS NOUN_FS AdjListFS NpTail"""
        return Node(
            "NpFS",
            [self.consume("DET_FS"), self.consume("NOUN_FS"), self.adj_list_fs(), self.np_tail()],
        )

    def np_mp(self) -> Node:
        """NpMP -> DET_MP NOUN_MP AdjListMP NpTail"""
        return Node(
            "NpMP",
            [self.consume("DET_MP"), self.consume("NOUN_MP"), self.adj_list_mp(), self.np_tail()],
        )

    def np_fp(self) -> Node:
        """NpFP -> DET_FP NOUN_FP AdjListFP NpTail"""
        return Node(
            "NpFP",
            [self.consume("DET_FP"), self.consume("NOUN_FP"), self.adj_list_fp(), self.np_tail()],
        )

    def adj_list_ms(self) -> Node:
        """AdjListMS -> ADJ_MS AdjListMS | ε"""
        if self.check("ADJ_MS"):
            return Node("AdjListMS", [self.consume("ADJ_MS"), self.adj_list_ms()])
        return Node("AdjListMS", [self.epsilon()])

    def adj_list_fs(self) -> Node:
        """AdjListFS -> ADJ_FS AdjListFS | ε"""
        if self.check("ADJ_FS"):
            return Node("AdjListFS", [self.consume("ADJ_FS"), self.adj_list_fs()])
        return Node("AdjListFS", [self.epsilon()])

    def adj_list_mp(self) -> Node:
        """AdjListMP -> ADJ_MP AdjListMP | ε"""
        if self.check("ADJ_MP"):
            return Node("AdjListMP", [self.consume("ADJ_MP"), self.adj_list_mp()])
        return Node("AdjListMP", [self.epsilon()])

    def adj_list_fp(self) -> Node:
        """AdjListFP -> ADJ_FP AdjListFP | ε"""
        if self.check("ADJ_FP"):
            return Node("AdjListFP", [self.consume("ADJ_FP"), self.adj_list_fp()])
        return Node("AdjListFP", [self.epsilon()])

    def np_tail(self) -> Node:
        """NpTail -> PrepPhrase NpTail | ε

        This is the only LL(1) conflict of the grammar: PREP is in
        FIRST(PrepPhrase NpTail) and also in FOLLOW(NpTail), because after the
        object a prepositional phrase can also start PpList. Choosing
        PrepPhrase NpTail whenever PREP appears attaches the phrase to the
        nearest noun, the same decision as the dangling else in C++.
        """
        if self.check("PREP"):
            return Node("NpTail", [self.prep_phrase(), self.np_tail()])
        return Node("NpTail", [self.epsilon()])

    def prep_phrase(self) -> Node:
        """PrepPhrase -> PREP NounPhrase"""
        return Node("PrepPhrase", [self.consume("PREP"), self.noun_phrase()])

    # ---------- Verb phrases ----------

    def vp_sing(self) -> Node:
        """VpSing -> VERB_S VpTail"""
        return Node("VpSing", [self.consume("VERB_S"), self.vp_tail()])

    def vp_plur(self) -> Node:
        """VpPlur -> VERB_P VpTail"""
        return Node("VpPlur", [self.consume("VERB_P"), self.vp_tail()])

    def vp_tail(self) -> Node:
        """VpTail -> Object AdvOpt PpList"""
        return Node("VpTail", [self.object(), self.adv_opt(), self.pp_list()])

    def object(self) -> Node:
        """Object -> NounPhrase | ε"""
        if self.check(*DETERMINERS):
            return Node("Object", [self.noun_phrase()])
        return Node("Object", [self.epsilon()])

    def adv_opt(self) -> Node:
        """AdvOpt -> ADV | ε"""
        if self.check("ADV"):
            return Node("AdvOpt", [self.consume("ADV")])
        return Node("AdvOpt", [self.epsilon()])

    def pp_list(self) -> Node:
        """PpList -> PrepPhrase PpList | ε

        With an object and no adverb, np_tail already took every PREP, so a
        phrase only gets here after an intransitive verb or after the adverb.
        """
        if self.check("PREP"):
            return Node("PpList", [self.prep_phrase(), self.pp_list()])
        return Node("PpList", [self.epsilon()])
