beat_schedule = {
    "reconcile-pending-payments": {
        "task": "checkers.tasks.payments.reconcile_pending_payments",
        "schedule": 600.0,  # every 10 minutes
    },
}
