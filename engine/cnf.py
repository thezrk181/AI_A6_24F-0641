from __future__ import annotations

from typing import Iterable, List, Set

from .formula import Formula, And, Not, Or

Clause = frozenset[str]


def to_cnf(formula: Formula) -> Formula:
    no_arrows = _eliminate_implications(formula)
    nnf = _push_not_inwards(no_arrows)
    return _distribute_or_over_and(nnf)


def to_cnf_clauses(formula: Formula) -> Set[Clause]:
    cnf_formula = to_cnf(formula)
    return _extract_clauses(cnf_formula)


def _eliminate_implications(formula: Formula) -> Formula:
    op = formula.op
    if op == "VAR":
        return formula
    if op == "NOT":
        return Not(_eliminate_implications(formula.args[0]))
    if op == "AND":
        return And(*[_eliminate_implications(a) for a in formula.args])
    if op == "OR":
        return Or(*[_eliminate_implications(a) for a in formula.args])
    if op == "IMPLIES":
        left = _eliminate_implications(formula.args[0])
        right = _eliminate_implications(formula.args[1])
        return Or(Not(left), right)
    if op == "IFF":
        left = _eliminate_implications(formula.args[0])
        right = _eliminate_implications(formula.args[1])
        return And(Or(Not(left), right), Or(Not(right), left))
    raise ValueError(f"Unsupported op: {op}")


def _push_not_inwards(formula: Formula) -> Formula:
    if formula.op == "VAR":
        return formula
    if formula.op == "NOT":
        inner = formula.args[0]
        if inner.op == "VAR":
            return formula
        if inner.op == "NOT":
            return _push_not_inwards(inner.args[0])
        if inner.op == "AND":
            return Or(*[_push_not_inwards(Not(a)) for a in inner.args])
        if inner.op == "OR":
            return And(*[_push_not_inwards(Not(a)) for a in inner.args])
        raise ValueError(f"NOT applied to unsupported op: {inner.op}")
    if formula.op == "AND":
        return And(*[_push_not_inwards(a) for a in formula.args])
    if formula.op == "OR":
        return Or(*[_push_not_inwards(a) for a in formula.args])
    raise ValueError(f"Unsupported op in NNF transform: {formula.op}")


def _distribute_or_over_and(formula: Formula) -> Formula:
    if formula.op in {"VAR", "NOT"}:
        return formula
    if formula.op == "AND":
        return And(*[_distribute_or_over_and(a) for a in formula.args])
    if formula.op == "OR":
        args = [_distribute_or_over_and(a) for a in formula.args]
        current = args[0]
        for nxt in args[1:]:
            current = _distribute_two(current, nxt)
        return current
    raise ValueError(f"Unsupported op in distribution: {formula.op}")


def _distribute_two(a: Formula, b: Formula) -> Formula:
    if a.op == "AND":
        return And(*[_distribute_two(x, b) for x in a.args])
    if b.op == "AND":
        return And(*[_distribute_two(a, y) for y in b.args])
    return Or(a, b)


def _extract_clauses(cnf_formula: Formula) -> Set[Clause]:
    conjunction_parts = _split_conjunction(cnf_formula)
    clauses: Set[Clause] = set()
    for part in conjunction_parts:
        literals = _split_disjunction(part)
        clause: Set[str] = set()
        for lit in literals:
            clause.add(_formula_to_literal(lit))
        clauses.add(frozenset(clause))
    return clauses


def _split_conjunction(formula: Formula) -> List[Formula]:
    if formula.op == "AND":
        parts: List[Formula] = []
        for arg in formula.args:
            parts.extend(_split_conjunction(arg))
        return parts
    return [formula]


def _split_disjunction(formula: Formula) -> List[Formula]:
    if formula.op == "OR":
        parts: List[Formula] = []
        for arg in formula.args:
            parts.extend(_split_disjunction(arg))
        return parts
    return [formula]


def _formula_to_literal(formula: Formula) -> str:
    if formula.op == "VAR":
        assert formula.name is not None
        return formula.name
    if formula.op == "NOT" and formula.args[0].op == "VAR":
        inner = formula.args[0]
        assert inner.name is not None
        return f"~{inner.name}"
    raise ValueError("Clause contains non-literal formula")
