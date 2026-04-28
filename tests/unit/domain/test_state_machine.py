"""Tests for the generic StateMachine."""

from enum import Enum, auto

import pytest

from src.domain.models.state_machine import InvalidTransition, StateMachine


class State(Enum):
    A = auto()
    B = auto()
    C = auto()


class Context:
    def __init__(self):
        self.log: list[str] = []


def make_sm() -> StateMachine:
    sm: StateMachine[State, bool, Context] = StateMachine()
    sm.add_transition(State.A, True, State.B, lambda ctx: ctx.log.append("A→B"))
    sm.add_transition(State.A, False, State.C, lambda ctx: ctx.log.append("A→C"))
    sm.add_transition(State.B, True, State.C, lambda ctx: ctx.log.append("B→C"))
    return sm


class TestStateMachineAddAndLookUp:
    def test_look_up_returns_correct_next_state(self):
        sm = make_sm()
        next_state, _ = sm.look_up(State.A, True)
        assert next_state == State.B

    def test_look_up_returns_correct_action(self):
        sm = make_sm()
        ctx = Context()
        _, action = sm.look_up(State.A, True)
        action(ctx)
        assert ctx.log == ["A→B"]

    def test_look_up_missing_transition_raises(self):
        sm = make_sm()
        with pytest.raises(InvalidTransition):
            sm.look_up(State.C, True)

    def test_add_transition_overwrites_existing(self):
        sm = make_sm()
        sm.add_transition(
            State.A, True, State.C, lambda ctx: ctx.log.append("overwrite")
        )
        next_state, action = sm.look_up(State.A, True)
        assert next_state == State.C
        ctx = Context()
        action(ctx)
        assert ctx.log == ["overwrite"]


class TestStateMachineHandle:
    def test_handle_executes_action_and_returns_next_state(self):
        sm = make_sm()
        ctx = Context()
        result = sm.handle(ctx, State.A, True)
        assert result == State.B
        assert ctx.log == ["A→B"]

    def test_handle_false_flag(self):
        sm = make_sm()
        ctx = Context()
        result = sm.handle(ctx, State.A, False)
        assert result == State.C
        assert ctx.log == ["A→C"]

    def test_handle_sequence(self):
        sm = make_sm()
        ctx = Context()
        s = State.A
        s = sm.handle(ctx, s, True)  # A → B
        s = sm.handle(ctx, s, True)  # B → C
        assert s == State.C
        assert ctx.log == ["A→B", "B→C"]

    def test_handle_missing_raises(self):
        sm = make_sm()
        ctx = Context()
        with pytest.raises(InvalidTransition):
            sm.handle(ctx, State.C, False)


class TestStateMachineTransitionDecorator:
    def test_decorator_registers_transition(self):
        sm: StateMachine[State, bool, Context] = StateMachine()

        @sm.transition(State.A, True, State.B)
        def on_a_true(ctx: Context) -> None:
            ctx.log.append("decorated")

        ctx = Context()
        result = sm.handle(ctx, State.A, True)
        assert result == State.B
        assert ctx.log == ["decorated"]

    def test_decorator_returns_original_function(self):
        sm: StateMachine[State, bool, Context] = StateMachine()

        @sm.transition(State.A, True, State.B)
        def my_fn(ctx: Context) -> None:
            pass

        assert my_fn.__name__ == "my_fn"
