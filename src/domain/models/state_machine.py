from dataclasses import dataclass, field
from enum import Enum
from typing import Callable

type Action[C] = Callable[[C], None]


class InvalidTransition(Exception): ...


@dataclass
class StateMachine[S: Enum, F: bool, C]:
    transitions: dict[tuple[S, F], tuple[S, Action[C]]] = field(default_factory=dict)

    def add_transition(
        self, from_state: S, flag: F, to_state: S, func: Action[C]
    ) -> None:
        self.transitions[(from_state, flag)] = (to_state, func)

    def look_up(self, state: S, flag: F) -> tuple[S, Action[C]]:
        try:
            return self.transitions[(state, flag)]
        except KeyError as e:
            raise InvalidTransition(
                f"No hay transición desde '{state}' con flag={flag}."
            ) from e

    def handle(self, ctx: C, state: S, flag: F) -> S:
        next_state, action = self.look_up(state=state, flag=flag)
        action(ctx)
        return next_state

    def transition(self, from_state: S, flag: F, to_state: S):
        def decorator(fn: Action[C]) -> Action[C]:
            self.add_transition(
                from_state=from_state, flag=flag, to_state=to_state, func=fn
            )
            return fn

        return decorator
