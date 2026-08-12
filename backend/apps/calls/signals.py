"""
Signal definitions for the calls module.

`call_state_changed` is emitted after every successful Call FSM transition
carried out by CallService.

Provides: call, from_state, to_state, triggered_by
"""

import django.dispatch

# NOTE: Keep this object stable — existing tests and the calls module
# hold references to it. Do NOT reassign this name.
call_state_changed = django.dispatch.Signal()
