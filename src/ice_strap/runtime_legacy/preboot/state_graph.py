from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional


@dataclass(frozen=True)
class State:
    name: str


@dataclass(frozen=True)
class Transition:
    source: str
    event: str
    target: str
    guard: Optional[Callable[[dict], bool]] = None


class StateGraph:
    """
    Piccola FSM generica per modellare i passi del preboot lato backend.

    Non è vincolata al grafo JS, ma può seguire gli stessi nomi di fase/evento.
    """

    def __init__(self, initial: str):
        self.initial = initial
        self.states: Dict[str, State] = {}
        self.transitions: List[Transition] = []

    def add_state(self, name: str) -> None:
        self.states[name] = State(name)

    def add_transition(
        self,
        source: str,
        event: str,
        target: str,
        guard: Optional[Callable[[dict], bool]] = None,
    ) -> None:
        self.transitions.append(
            Transition(source=source, event=event, target=target, guard=guard)
        )

    def next_state(self, current: str, event: str, ctx: dict) -> str:
        """
        Restituisce lo stato successivo dato (current, event, ctx).
        Se nessuna transizione è valida, restituisce current.
        """
        for t in self.transitions:
            if t.source == current and t.event == event:
                if t.guard is None or t.guard(ctx):
                    return t.target
        return current
