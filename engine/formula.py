from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Tuple


@dataclass(frozen=True)
class Formula:
    op: str
    args: Tuple["Formula", ...] = ()
    name: str | None = None


def Var(name: str) -> Formula:
    return Formula(op="VAR", name=name)


def Not(f: Formula) -> Formula:
    return Formula(op="NOT", args=(f,))


def And(*parts: Formula) -> Formula:
    flat = []
    for p in parts:
        if p.op == "AND":
            flat.extend(p.args)
        else:
            flat.append(p)
    if not flat:
        raise ValueError("And requires at least one formula")
    if len(flat) == 1:
        return flat[0]
    return Formula(op="AND", args=tuple(flat))


def Or(*parts: Formula) -> Formula:
    flat = []
    for p in parts:
        if p.op == "OR":
            flat.extend(p.args)
        else:
            flat.append(p)
    if not flat:
        raise ValueError("Or requires at least one formula")
    if len(flat) == 1:
        return flat[0]
    return Formula(op="OR", args=tuple(flat))


def Implies(left: Formula, right: Formula) -> Formula:
    return Formula(op="IMPLIES", args=(left, right))


def Iff(left: Formula, right: Formula) -> Formula:
    return Formula(op="IFF", args=(left, right))


def iter_vars(formula: Formula) -> Iterable[str]:
    if formula.op == "VAR":
        assert formula.name is not None
        yield formula.name
        return
    for arg in formula.args:
        yield from iter_vars(arg)
