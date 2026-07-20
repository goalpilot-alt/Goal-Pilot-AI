"""Stripe integration using the official stripe-python SDK.

Replaces the previous emergentintegrations dependency so the app can deploy on
any hosting platform (Railway, Render, Fly, etc.).
"""
import logging
from typing import Any

import stripe

from core.config import STRIPE_API_KEY, STRIPE_WEBHOOK_SECRET

logger = logging.getLogger(__name__)

# Configure the SDK once at import time.
stripe.api_key = STRIPE_API_KEY


def _amount_to_cents(amount: float) -> int:
    return int(round(amount * 100))


async def create_checkout_session(
    *,
    amount: float,
    currency: str,
    success_url: str,
    cancel_url: str,
    metadata: dict[str, str],
    product_name: str = 'GoalPilot Subscription',
) -> dict[str, Any]:
    """Create a Stripe Checkout Session (one-time payment).

    Returns a dict with keys: url, session_id.
    """
    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        mode='payment',
        line_items=[{
            'price_data': {
                'currency': currency.lower(),
                'unit_amount': _amount_to_cents(amount),
                'product_data': {'name': product_name},
            },
            'quantity': 1,
        }],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={str(k): str(v) for k, v in metadata.items()},
    )
    return {'url': session.url, 'session_id': session.id}


async def get_checkout_status(session_id: str) -> dict[str, Any]:
    """Retrieve current status of a Checkout Session.

    Returns dict with: payment_status, status, amount_total, currency.
    """
    session = stripe.checkout.Session.retrieve(session_id)
    return {
        'payment_status': session.payment_status,
        'status': session.status or 'open',
        'amount_total': session.amount_total or 0,
        'currency': session.currency or 'usd',
    }


def verify_webhook(body: bytes, signature: str) -> dict[str, Any]:
    """Validate a Stripe webhook signature and return a normalized event dict.

    Returns dict with: event_type, session_id, payment_status.
    Raises stripe.error.SignatureVerificationError on bad signature.
    """
    if not STRIPE_WEBHOOK_SECRET:
        raise ValueError('STRIPE_WEBHOOK_SECRET is not configured')

    event = stripe.Webhook.construct_event(
        payload=body,
        sig_header=signature,
        secret=STRIPE_WEBHOOK_SECRET,
    )

    obj = event.data.object if event.data else None
    session_id = None
    payment_status = None
    if obj is not None:
        session_id = getattr(obj, 'id', None) or (obj.get('id') if isinstance(obj, dict) else None)
        payment_status = (
            getattr(obj, 'payment_status', None)
            or (obj.get('payment_status') if isinstance(obj, dict) else None)
        )

    return {
        'event_type': event.type,
        'session_id': session_id,
        'payment_status': payment_status,
    }
