from __future__ import annotations

from typing import Iterable, Set, Tuple

Clause = frozenset[str]


def negate_literal(lit: str) -> str:
    return lit[1:] if lit.startswith("~") else f"~{lit}"


def is_tautology(clause: Clause) -> bool:
    return any(negate_literal(lit) in clause for lit in clause)


def pl_resolve(c1: Clause, c2: Clause) -> Set[Clause]:
    resolvents: Set[Clause] = set()
    for lit in c1:
        comp = negate_literal(lit)
        if comp not in c2:
            continue
        merged = (set(c1) - {lit}) | (set(c2) - {comp})
        resolvent = frozenset(merged)
        if is_tautology(resolvent):
            continue
        resolvents.add(resolvent)
    return resolvents


def resolution_refutation(
    kb_clauses: Set[Clause],
    negated_query_clauses: Set[Clause],
    max_clauses: int = 8000,
    max_steps: int = 20000,
) -> Tuple[bool, int]:
    clauses: Set[Clause] = set(kb_clauses) | set(negated_query_clauses)
    if frozenset() in clauses:
        return True, 0

    steps = 0
    while True:
        new: Set[Clause] = set()
        clause_list = list(clauses)

        for i in range(len(clause_list)):
            for j in range(i + 1, len(clause_list)):
                steps += 1
                if steps >= max_steps:
                    return False, steps
                resolvents = pl_resolve(clause_list[i], clause_list[j])
                if frozenset() in resolvents:
                    return True, steps
                new |= resolvents

        if not new or new.issubset(clauses):
            return False, steps

        clauses |= new
        if len(clauses) > max_clauses:
            return False, steps
