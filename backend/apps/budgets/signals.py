"""
Semantic signals for the budgets module.

`budget_overrun_attempted` is emitted when BudgetService.add_execution
rejects an over-limit execution without authorization (spec delta RN-4).
Payload contract: budget_line, attempted_amount, requested_by,
institution (with apply-contract aliases instance, approved_amount).
"""

import django.dispatch

budget_overrun_attempted = django.dispatch.Signal()
