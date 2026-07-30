"""
Signal definitions for the project_workflow module.

`project_state_changed` is defined here so the `projects` module can
import and emit it without creating a circular dependency.

Provides: project, from_state, to_state, triggered_by
"""

import django.dispatch

project_state_changed = django.dispatch.Signal()
