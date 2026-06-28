from __future__ import annotations
from collections import defaultdict, deque
from typing import Iterable
from app.skills.base import Skill

class SkillRegistry:
    def __init__(self) -> None:
        self._skills: dict[str, Skill] = {}

    def register(self, skill: Skill) -> None:
        self._skills[skill.meta.id] = skill

    def get(self, skill_id: str) -> Skill:
        return self._skills[skill_id]

    def all_ids(self) -> list[str]:
        return list(self._skills.keys())

    def downstream_of(self, skill_id: str) -> list[str]:
        return [s.meta.id for s in self._skills.values()
                if skill_id in s.meta.depends_on]

    def topological_sort(self, skill_ids: Iterable[str]) -> list[str]:
        ids = set(skill_ids)
        indeg: dict[str, int] = {sid: 0 for sid in ids}
        for sid in ids:
            for dep in self._skills[sid].meta.depends_on:
                if dep in ids:
                    indeg[sid] += 1
        queue = deque([sid for sid, d in indeg.items() if d == 0])
        order: list[str] = []
        while queue:
            n = queue.popleft()
            order.append(n)
            for d in self.downstream_of(n):
                if d in indeg:
                    indeg[d] -= 1
                    if indeg[d] == 0:
                        queue.append(d)
        if len(order) != len(ids):
            raise ValueError("Cycle detected in skill DAG")
        return order

    def compute_rerun_set(self, seed: Iterable[str]) -> list[str]:
        rerun: set[str] = set(seed)
        changed = True
        while changed:
            changed = False
            for sid, skill in self._skills.items():
                if sid in rerun:
                    continue
                if not skill.meta.propagate_downstream:
                    continue
                if self._has_ancestor_in(sid, rerun):
                    rerun.add(sid)
                    changed = True
        return self.topological_sort(rerun)

    def _has_ancestor_in(self, sid: str, target: set[str]) -> bool:
        visited: set[str] = set()
        stack: list[str] = list(self._skills[sid].meta.depends_on)
        while stack:
            a = stack.pop()
            if a in target:
                return True
            if a in visited:
                continue
            visited.add(a)
            if a in self._skills:
                stack.extend(self._skills[a].meta.depends_on)
        return False

registry = SkillRegistry()
