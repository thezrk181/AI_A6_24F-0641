from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple

from .cnf import Clause, to_cnf_clauses
from .formula import Iff, Or, Var
from .resolution import negate_literal, resolution_refutation

Cell = Tuple[int, int]


@dataclass
class WumpusWorld:
    rows: int
    cols: int
    pit_probability: float = 0.2
    pits: Set[Cell] = field(default_factory=set)
    wumpus: Cell | None = None

    def __post_init__(self) -> None:
        self._randomize_hazards()

    def _randomize_hazards(self) -> None:
        self.pits.clear()
        start = (0, 0)

        for r in range(self.rows):
            for c in range(self.cols):
                if (r, c) == start:
                    continue
                if random.random() < self.pit_probability:
                    self.pits.add((r, c))

        candidates = [(r, c) for r in range(self.rows) for c in range(self.cols) if (r, c) != start]
        self.wumpus = random.choice(candidates)

        if self.wumpus in self.pits:
            self.pits.remove(self.wumpus)

    def adjacent(self, r: int, c: int) -> List[Cell]:
        neighbors: List[Cell] = []
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < self.rows and 0 <= nc < self.cols:
                neighbors.append((nr, nc))
        return neighbors

    def percepts(self, r: int, c: int) -> Dict[str, bool]:
        neighbors = self.adjacent(r, c)
        breeze = any(cell in self.pits for cell in neighbors)
        stench = self.wumpus in neighbors
        return {"breeze": breeze, "stench": stench}


class KnowledgeBase:
    def __init__(self, rows: int, cols: int) -> None:
        self.rows = rows
        self.cols = cols
        self.clauses: Set[Clause] = set()
        self.total_resolution_steps = 0

    @staticmethod
    def pit_symbol(r: int, c: int) -> str:
        return f"P_{r}_{c}"

    @staticmethod
    def wumpus_symbol(r: int, c: int) -> str:
        return f"W_{r}_{c}"

    @staticmethod
    def breeze_symbol(r: int, c: int) -> str:
        return f"B_{r}_{c}"

    @staticmethod
    def stench_symbol(r: int, c: int) -> str:
        return f"S_{r}_{c}"

    def tell_formula(self, formula) -> None:
        self.clauses |= to_cnf_clauses(formula)

    def tell_literal(self, literal: str) -> None:
        self.clauses.add(frozenset([literal]))

    def ask_literal(self, literal: str) -> bool:
        # KB |= literal is proven by checking KB ∧ ~literal is inconsistent.
        negated_query = {frozenset([negate_literal(literal)])}
        contradiction, steps = resolution_refutation(self.clauses, negated_query)
        self.total_resolution_steps += steps
        return contradiction


@dataclass
class AgentEpisode:
    rows: int
    cols: int
    pit_probability: float = 0.2
    world: WumpusWorld = field(init=False)
    kb: KnowledgeBase = field(init=False)
    agent_pos: Cell = field(default=(0, 0))
    visited: Set[Cell] = field(default_factory=set)
    last_message: str = ""

    def __post_init__(self) -> None:
        self.world = WumpusWorld(self.rows, self.cols, self.pit_probability)
        self.kb = KnowledgeBase(self.rows, self.cols)
        self.agent_pos = (0, 0)
        self.visited = {(0, 0)}
        self._tell_current_cell_safe()
        self._tell_percepts_for_current_cell()
        self.last_message = "Episode started. Agent is at (0,0)."

    def adjacent(self, r: int, c: int) -> List[Cell]:
        return self.world.adjacent(r, c)

    def _tell_current_cell_safe(self) -> None:
        r, c = self.agent_pos
        self.kb.tell_literal(f"~{self.kb.pit_symbol(r, c)}")
        self.kb.tell_literal(f"~{self.kb.wumpus_symbol(r, c)}")

    def _tell_percepts_for_current_cell(self) -> None:
        r, c = self.agent_pos
        p = self.world.percepts(r, c)
        neighbors = self.adjacent(r, c)

        breeze_var = Var(self.kb.breeze_symbol(r, c))
        stench_var = Var(self.kb.stench_symbol(r, c))

        if neighbors:
            pit_neighbors = [Var(self.kb.pit_symbol(nr, nc)) for nr, nc in neighbors]
            w_neighbors = [Var(self.kb.wumpus_symbol(nr, nc)) for nr, nc in neighbors]

            pit_disjunction = Or(*pit_neighbors)
            wumpus_disjunction = Or(*w_neighbors)

            self.kb.tell_formula(Iff(breeze_var, pit_disjunction))
            self.kb.tell_formula(Iff(stench_var, wumpus_disjunction))

        self.kb.tell_literal(self.kb.breeze_symbol(r, c) if p["breeze"] else f"~{self.kb.breeze_symbol(r, c)}")
        self.kb.tell_literal(self.kb.stench_symbol(r, c) if p["stench"] else f"~{self.kb.stench_symbol(r, c)}")

        # Fast local entailment: if no breeze/stench here, all adjacent cells are free of that hazard.
        if not p["breeze"]:
            for nr, nc in neighbors:
                self.kb.tell_literal(f"~{self.kb.pit_symbol(nr, nc)}")

        if not p["stench"]:
            for nr, nc in neighbors:
                self.kb.tell_literal(f"~{self.kb.wumpus_symbol(nr, nc)}")

    def percepts(self) -> Dict[str, bool]:
        r, c = self.agent_pos
        return self.world.percepts(r, c)

    def is_safe_by_proof(self, cell: Cell) -> bool:
        r, c = cell
        no_pit = self.kb.ask_literal(f"~{self.kb.pit_symbol(r, c)}")
        no_wumpus = self.kb.ask_literal(f"~{self.kb.wumpus_symbol(r, c)}")
        return no_pit and no_wumpus

    def is_hazard_by_proof(self, cell: Cell) -> bool:
        r, c = cell
        pit = self.kb.ask_literal(self.kb.pit_symbol(r, c))
        wumpus = self.kb.ask_literal(self.kb.wumpus_symbol(r, c))
        return pit or wumpus

    def move_if_safe(self, target: Cell) -> bool:
        ar, ac = self.agent_pos
        if target not in self.adjacent(ar, ac):
            self.last_message = "Move rejected: target is not adjacent."
            return False

        if target not in self.visited and not self.is_safe_by_proof(target):
            self.last_message = "Move rejected: KB cannot prove target is safe yet."
            return False

        self.agent_pos = target
        self.visited.add(target)
        self._tell_current_cell_safe()
        self._tell_percepts_for_current_cell()
        self.last_message = f"Moved to ({target[0]},{target[1]})."
        return True

    def auto_step(self) -> bool:
        ar, ac = self.agent_pos
        frontier = [cell for cell in self.adjacent(ar, ac) if cell not in self.visited]

        safe_frontier = [cell for cell in frontier if self.is_safe_by_proof(cell)]
        if not safe_frontier:
            self.last_message = "No provably safe adjacent unvisited cell. Exploration stopped."
            return False

        return self.move_if_safe(safe_frontier[0])

    def grid_beliefs(self) -> List[List[Dict[str, bool | str]]]:
        # Restrict expensive theorem-proving to visited cells and their immediate frontier.
        frontier: Set[Cell] = set(self.visited)
        for vr, vc in self.visited:
            for n in self.adjacent(vr, vc):
                frontier.add(n)

        beliefs: List[List[Dict[str, bool | str]]] = []
        for r in range(self.rows):
            row: List[Dict[str, bool | str]] = []
            for c in range(self.cols):
                cell = (r, c)
                visited = cell in self.visited

                if visited:
                    status = "safe"
                else:
                    if cell not in frontier:
                        status = "unknown"
                    else:
                        if self.is_hazard_by_proof(cell):
                            status = "hazard"
                        elif self.is_safe_by_proof(cell):
                            status = "safe"
                        else:
                            status = "unknown"

                row.append(
                    {
                        "status": status,
                        "visited": visited,
                        "agent": cell == self.agent_pos,
                    }
                )
            beliefs.append(row)
        return beliefs

    def export_state(self) -> Dict[str, object]:
        r, c = self.agent_pos
        return {
            "rows": self.rows,
            "cols": self.cols,
            "agent": {"r": r, "c": c},
            "percepts": self.percepts(),
            "inferenceSteps": self.kb.total_resolution_steps,
            "message": self.last_message,
            "visited": [[vr, vc] for vr, vc in sorted(self.visited)],
            "grid": self.grid_beliefs(),
        }
