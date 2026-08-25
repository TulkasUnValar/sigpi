"""
Semantic signals for the progress (advances) module.

`progress_state_changed` is emitted once per successful FSM transition
by ProgressService._log_transition (spec delta RN-2). Payload contract:
progress_report, from_state, to_state, triggered_by (with apply-contract
aliases instance, old_status, new_status, user).

Emitted inside the sender's transaction with no I/O side effects.
"""

import django.dispatch

progress_state_changed = django.dispatch.Signal()
