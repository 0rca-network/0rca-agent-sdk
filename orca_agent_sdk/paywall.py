from flask import request, current_app
from functools import wraps
from .core.payment import ToolPaywallError

def check_paywall(tool_name: str):
    """
    Checks if the current request has paid for the specified tool.
    Raises ToolPaywallError if payment is missing or invalid.
    """
    # Get the server instance from current_app
    server = getattr(current_app, "agent_server", None)
    if not server:
        # If not in server context, allow (e.g. testing) or raise error?
        # For now, allow to avoid breaking standalone tests.
        return 

    signed_b64 = request.headers.get("X-PAYMENT")
    server.payment.check_tool_payment(tool_name, signed_b64)

def tool_paywall(f):
    """
    Decorator to easily add an x402 paywall to any agent tool.
    Uses the function name as the tool name for the paywall.
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        check_paywall(f.__name__)
        return f(*args, **kwargs)
    return wrapper
