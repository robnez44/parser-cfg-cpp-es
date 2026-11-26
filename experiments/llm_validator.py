"""Validator for the answers of the LLM (CONTRATO_FASE2.md, section 11).

The LLM answers with a JSON object:

    {"accepted": true, "tree": "(Sentence ...)", "upos": [...], "violated_rule": null}

The validator checks that the tree only uses productions of grammars/es.gram
and words of spanish/lexicon.tsv with their own token type, and that its
leaves are the words of the sentence. A tree that does not pass counts as a
deviation from the rules, even if "accepted" is the right answer.

The validator does not decide whether the sentence should be accepted: that
is measured by metrics.py against the labels of the test set. It only checks
that the derivation the LLM wrote is a real derivation of es.gram.
"""

import csv
import json
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

from nltk import Tree

from verifier.grammar import EPSILON, Grammar, nullable_set, read_grammar

ROOT = Path(__file__).resolve().parent.parent
GRAMMAR_PATH = ROOT / "grammars" / "es.gram"
LEXICON_PATH = ROOT / "spanish" / "lexicon.tsv"

# Same split as spanish/lexer.py: a word, or a period on its own even if it is
# stuck to a word ("manzana."). It is repeated here so the validator does not
# depend on the parser branch.
WORD = re.compile(r"[^\s.]+|\.")


class ResponseError(Exception):
    """The raw answer of the LLM is not the JSON object the prompt asks for."""


@dataclass
class Validation:
    """Result of checking one answer. ``valid`` is False when ``errors`` is not empty."""

    errors: list[str] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return not self.errors


def load_lexicon(path: Path = LEXICON_PATH) -> dict[str, dict[str, str]]:
    """Return a dictionary from each word to its row of the lexicon."""
    with open(path, encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file, delimiter="\t", quoting=csv.QUOTE_NONE)
        return {row["word"]: row for row in reader}


GRAMMAR = read_grammar(GRAMMAR_PATH)
LEXICON = load_lexicon()


def split_words(sentence: str) -> list[str]:
    """Return the words of the sentence in lowercase, with the period apart."""
    text = unicodedata.normalize("NFC", sentence).lower()
    return WORD.findall(text)


# ---------- Reading the raw answer ----------

FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def parse_response(raw: str) -> dict:
    """Turn the raw text of the LLM into the answer dictionary.

    Accepts the JSON alone or inside a ```json block. Raises ResponseError if
    there is no JSON object or if "accepted" is not true or false. The other
    keys are optional; a missing key is read as null.
    """
    text = raw.strip()
    fenced = FENCE.search(text)
    if fenced is not None:
        text = fenced.group(1).strip()

    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end < start:
        raise ResponseError("la respuesta no tiene un objeto JSON")

    try:
        data = json.loads(text[start:end + 1])
    except json.JSONDecodeError as error:
        raise ResponseError(f"la respuesta no es JSON válido ({error.msg})") from error

    if not isinstance(data, dict):
        raise ResponseError("la respuesta no es un objeto JSON")
    if not isinstance(data.get("accepted"), bool):
        raise ResponseError("el campo 'accepted' no es true ni false")

    upos = data.get("upos")
    if not (isinstance(upos, list) and all(isinstance(tag, str) for tag in upos)):
        upos = None

    tree = data.get("tree")
    if not isinstance(tree, str) or not tree.strip():
        tree = None

    return {
        "accepted": data["accepted"],
        "tree": tree,
        "upos": upos,
        "violated_rule": data.get("violated_rule"),
    }


# ---------- Checking the tree ----------

def validate(response: dict, sentence: str, grammar: Grammar = GRAMMAR,
             lexicon: dict[str, dict[str, str]] = LEXICON) -> Validation:
    """Check one answer already read by parse_response.

    - If the LLM accepts, the tree must exist and be a derivation of the
      sentence with es.gram.
    - If it rejects, the tree must be null: a rejected sentence has no tree.
    """
    result = Validation()

    if not response["accepted"]:
        if response["tree"] is not None:
            result.errors.append("rechazó la oración pero devolvió un árbol")
        return result

    if response["tree"] is None:
        result.errors.append("aceptó la oración pero no devolvió el árbol")
        return result

    try:
        tree = Tree.fromstring(response["tree"])
    except ValueError as error:
        result.errors.append(f"el árbol no está bien formado ({error})")
        return result

    result.errors.extend(check_tree(tree, sentence, grammar, lexicon))
    return result


def check_tree(tree: Tree, sentence: str, grammar: Grammar = GRAMMAR,
               lexicon: dict[str, dict[str, str]] = LEXICON) -> list[str]:
    """Return the list of problems of the tree. An empty list means it is valid."""
    errors: list[str] = []

    if tree.label() != grammar.start:
        errors.append(f"la raíz es '{tree.label()}' y debía ser '{grammar.start}'")

    check_node(tree, grammar, nullable_set(grammar), lexicon, errors)

    words = [word for _, word in preterminals(tree)]
    expected = split_words(sentence)
    if words != expected:
        errors.append(
            f"las hojas del árbol ({' '.join(words)}) no son la oración ({' '.join(expected)})"
        )

    return errors


def check_node(node: Tree, grammar: Grammar, nullable: set[str],
               lexicon: dict[str, dict[str, str]], errors: list[str]) -> None:
    """Check one node and its subtree, adding each problem to errors."""
    label = node.label()

    if label in grammar.terminals:
        check_leaf(node, lexicon, errors)
        return

    if not grammar.is_nonterminal(label):
        errors.append(f"'{label}' no es un símbolo de la gramática")
        return

    if is_epsilon_node(node):
        if () not in {p.rhs for p in grammar.productions_of(label)}:
            errors.append(f"{label} no puede derivar ε")
        return

    if any(not isinstance(child, Tree) for child in node):
        errors.append(f"{label} tiene una palabra suelta; cada palabra va dentro de su tipo de token")
        return

    children = tuple(child.label() for child in node)
    if not any(matches(children, p.rhs, nullable) for p in grammar.productions_of(label)):
        errors.append(f"no existe la producción {label} -> {' '.join(children)}")

    for child in node:
        check_node(child, grammar, nullable, lexicon, errors)


def check_leaf(node: Tree, lexicon: dict[str, dict[str, str]], errors: list[str]) -> None:
    """A terminal node has exactly one word, and the lexicon gives it that same type."""
    label = node.label()

    if len(node) != 1 or isinstance(node[0], Tree):
        errors.append(f"el terminal {label} debe tener exactamente una palabra")
        return

    word = unicodedata.normalize("NFC", node[0]).lower()
    entry = lexicon.get(word)

    if entry is None:
        errors.append(f"palabra fuera del vocabulario '{word}'")
    elif entry["type"] != label:
        errors.append(f"'{word}' es {entry['type']} en el lexicón, no {label}")


def is_epsilon_node(node: Tree) -> bool:
    """(NpTail ε) or (NpTail) with nothing inside."""
    return len(node) == 0 or (len(node) == 1 and node[0] == EPSILON)


def matches(children: tuple[str, ...], rhs: tuple[str, ...], nullable: set[str]) -> bool:
    """Return True if the children are the right side of the production.

    A nullable nonterminal of the right side may be missing among the
    children. That allows the compact tree, where the branches that only
    derive ε are left out (the same as --compact in the visualization).
    """
    if not rhs:
        return not children
    if children and children[0] == rhs[0] and matches(children[1:], rhs[1:], nullable):
        return True
    return rhs[0] in nullable and matches(children, rhs[1:], nullable)


def preterminals(tree: Tree) -> list[tuple[str, str]]:
    """Return (token type, word) for each terminal node, from left to right."""
    pairs = []
    for subtree in tree.subtrees():
        if len(subtree) == 1 and not isinstance(subtree[0], Tree) and subtree[0] != EPSILON:
            pairs.append((subtree.label(), unicodedata.normalize("NFC", subtree[0]).lower()))
    return pairs


# ---------- Prepositional phrase attachment (task C) ----------

def attachment(tree: Tree) -> str | None:
    """Return where the first prepositional phrase after the verb is attached.

    "noun" if it hangs from NpTail (it modifies the noun of the object),
    "verb" if it hangs from PpList (it modifies the verb), and None if there is
    no prepositional phrase after the verb. Both trees are derivations of
    es.gram: that is the accepted conflict M[NpTail, PREP].
    """
    for vp_tail in tree.subtrees(lambda node: node.label() == "VpTail"):
        for parent in vp_tail.subtrees():
            for child in parent:
                if isinstance(child, Tree) and child.label() == "PrepPhrase":
                    return "noun" if parent.label() == "NpTail" else "verb"
    return None
