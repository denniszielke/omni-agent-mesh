import random
from typing import Annotated

from agent_framework import ai_function


@ai_function(
    name="submit_payment",
    description="Submit a payment request that always requires human approval.",
    approval_mode="always_require",
)
def submit_payment(
    amount: Annotated[float, "Payment amount in USD"],
    recipient: Annotated[str, "Recipient name or vendor ID"],
    reference: Annotated[str, "Short description for the payment reference"],
) -> str:
    """Simulate submitting a payment to an external payments system.

    In a real implementation this would call a banking or payments API.
    Here we just return a confirmation message.
    """
    return (
        f"Payment of ${amount:.2f} to '{recipient}' has been submitted "
        f"with reference '{reference}'."
    )


@ai_function(
    name="get_account_balance",
    description="Retrieves the current account balance for the user in USD.",
)
def get_account_balance() -> float:
    """Return a pseudo-random account balance.

    This operation is read-only and does not require approval.
    """
    balance = random.uniform(1000, 5000)
    return round(balance, 2)
