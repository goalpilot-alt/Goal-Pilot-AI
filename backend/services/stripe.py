from datetime import datetime, timezone
from typing import List
from fastapi import Request
from emergentintegrations.payments.stripe.checkout import (
    StripeCheckout,
    CheckoutSessionRequest,
    CheckoutSessionResponse,
    CheckoutStatusResponse,
)
from core.config import STRIPE_API_KEY, STRIPE_WEBHOOK_SECRET, PACKAGES
from core.db import db


def get_checkout(http_request: Request | None = None) -> StripeCheckout:
    if http_request is not None:
        host_url = str(http_request.base_url).rstrip('/')
        return StripeCheckout(
            api_key=STRIPE_API_KEY,
            webhook_url=f'{host_url}/api/webhook/stripe',
        )
    return StripeCheckout(
        api_key=STRIPE_API_KEY,
        webhook_secret=STRIPE_WEBHOOK_SECRET or None,
    )
