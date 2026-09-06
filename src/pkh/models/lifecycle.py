"""Lifecycle state machine with transition validation."""

from __future__ import annotations

from datetime import datetime, timezone

from pkh.models.knowledge import KnowledgeObject, LifecycleState
from pkh.utils.exceptions import LifecycleError

# 13 valid (was 14 in docs; removed SUPERSEDED->ARCHIVED extra
# and DEPRECATED->SUPERSEDED cycle to avoid loop). See fix-plan 1.4
VALID_TRANSITIONS: dict[LifecycleState, set[LifecycleState]] = {
    LifecycleState.DISCOVERED: {LifecycleState.EXTRACTED, LifecycleState.ARCHIVED},
    LifecycleState.EXTRACTED: {LifecycleState.VALIDATING, LifecycleState.DISCOVERED},
    LifecycleState.VALIDATING: {LifecycleState.ACTIVE, LifecycleState.EXTRACTED},
    LifecycleState.ACTIVE: {
        LifecycleState.UPDATED,
        LifecycleState.SUPERSEDED,
        LifecycleState.DEPRECATED,
    },
    LifecycleState.UPDATED: {LifecycleState.VALIDATING, LifecycleState.ACTIVE},
    LifecycleState.SUPERSEDED: {LifecycleState.DEPRECATED},
    LifecycleState.DEPRECATED: {LifecycleState.ARCHIVED},
    LifecycleState.ARCHIVED: set(),
}


def can_transition(from_state: LifecycleState, to_state: LifecycleState) -> bool:
    return to_state in VALID_TRANSITIONS.get(from_state, set())


def transition(
    obj: KnowledgeObject,
    new_state: LifecycleState,
    reason: str = "",
) -> KnowledgeObject:
    if not can_transition(obj.lifecycle_state, new_state):
        raise LifecycleError(
            f"Invalid transition {obj.lifecycle_state.value} -> {new_state.value}: not allowed"
        )
    obj.lifecycle_state = new_state
    obj.updated_at = datetime.now(timezone.utc)
    if reason:
        # store reason in properties for audit
        obj.properties["_last_transition_reason"] = reason
    return obj


class LifecycleStateMachine:
    """State machine wrapper."""

    valid_transitions = VALID_TRANSITIONS

    @staticmethod
    def can_transition(from_state: LifecycleState, to_state: LifecycleState) -> bool:
        return can_transition(from_state, to_state)

    @staticmethod
    def transition(
        obj: KnowledgeObject, new_state: LifecycleState, reason: str = ""
    ) -> KnowledgeObject:
        return transition(obj, new_state, reason)

    @staticmethod
    def allowed_targets(state: LifecycleState) -> set[LifecycleState]:
        return VALID_TRANSITIONS.get(state, set())
