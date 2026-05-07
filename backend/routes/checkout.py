import logging
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from emergentintegrations.payments.stripe.checkout import (
    CheckoutSessionRequest, CheckoutSessionResponse, CheckoutStatusResponse,
)

from core.auth import get_current_user
from core.config import PACKAGES
from core.db import db
from models.schemas import CheckoutSessionReq
from services.stripe import get_checkout

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post('/checkout/session')
async def create_checkout_session(
    req: CheckoutSessionReq,
    http_request: Request,
    user: dict = Depends(get_current_user),
):
    if req.package_id not in PACKAGES:
        raise HTTPException(status_code=400, detail='Invalid package')
    pkg = PACKAGES[req.package_id]

    origin = req.origin_url.rstrip('/')
    success_url = f'{origin}/payment/success?session_id={{CHECKOUT_SESSION_ID}}'
    cancel_url = f'{origin}/pricing'

    checkout = get_checkout(http_request)
    metadata = {
        'user_id': user['id'],
        'user_email': user['email'],
        'package_id': req.package_id,
        'plan': pkg['plan'],
        'billing': pkg['billing'],
    }

    checkout_req = CheckoutSessionRequest(
        amount=pkg['amount'],
        currency=pkg['currency'],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata=metadata,
    )
    session: CheckoutSessionResponse = await checkout.create_checkout_session(checkout_req)

    await db.payment_transactions.insert_one({
        'id': str(uuid.uuid4()),
        'session_id': session.session_id,
        'user_id': user['id'],
        'user_email': user['email'],
        'package_id': req.package_id,
        'plan': pkg['plan'],
        'billing': pkg['billing'],
        'amount': pkg['amount'],
        'currency': pkg['currency'],
        'payment_status': 'initiated',
        'status': 'open',
        'metadata': metadata,
        'created_at': datetime.now(timezone.utc).isoformat(),
        'updated_at': datetime.now(timezone.utc).isoformat(),
    })

    return {'url': session.url, 'session_id': session.session_id}


@router.get('/checkout/status/{session_id}')
async def get_checkout_status(session_id: str, user: dict = Depends(get_current_user)):
    tx = await db.payment_transactions.find_one({'session_id': session_id, 'user_id': user['id']}, {'_id': 0})
    if not tx:
        raise HTTPException(status_code=404, detail='Transaction not found')

    if tx.get('payment_status') == 'paid':
        return {
            'payment_status': 'paid',
            'status': tx.get('status', 'complete'),
            'amount_total': int(tx['amount'] * 100),
            'currency': tx['currency'],
            'plan': tx['plan'],
            'billing': tx['billing'],
        }

    try:
        checkout = get_checkout()
        status: CheckoutStatusResponse = await checkout.get_checkout_status(session_id)
        update = {
            'payment_status': status.payment_status,
            'status': status.status,
            'updated_at': datetime.now(timezone.utc).isoformat(),
        }
        await db.payment_transactions.update_one({'session_id': session_id}, {'$set': update})
        if status.payment_status == 'paid' and tx.get('payment_status') != 'paid':
            await db.users.update_one(
                {'id': user['id']},
                {'$set': {'plan': tx['plan'], 'billing': tx['billing'], 'upgraded_at': datetime.now(timezone.utc).isoformat()}},
            )
        return {
            'payment_status': status.payment_status,
            'status': status.status,
            'amount_total': status.amount_total,
            'currency': status.currency,
            'plan': tx['plan'],
            'billing': tx['billing'],
        }
    except Exception as e:
        logger.warning(f'Stripe status lookup failed for {session_id}: {e}. Falling back to local state.')
        return {
            'payment_status': tx.get('payment_status', 'unpaid'),
            'status': tx.get('status', 'open'),
            'amount_total': int(tx['amount'] * 100),
            'currency': tx['currency'],
            'plan': tx['plan'],
            'billing': tx['billing'],
        }


@router.post('/webhook/stripe')
async def stripe_webhook(request: Request):
    """Stripe webhook — validates signature with STRIPE_WEBHOOK_SECRET. Idempotent."""
    body = await request.body()
    signature = request.headers.get('Stripe-Signature', '')
    checkout = get_checkout()
    try:
        event = await checkout.handle_webhook(body, signature)
    except Exception as e:
        logger.error(f'Stripe webhook validation error: {e}')
        raise HTTPException(status_code=400, detail='Invalid webhook')

    event_type = getattr(event, 'event_type', None) or getattr(event, 'type', None)
    logger.info(f'Stripe webhook received: type={event_type} session={event.session_id} status={event.payment_status}')

    if event.payment_status == 'paid' and event.session_id:
        tx = await db.payment_transactions.find_one({'session_id': event.session_id})
        if not tx:
            logger.warning(f'Webhook paid for unknown session_id={event.session_id}')
            return {'ok': True, 'ignored': True}
        if tx.get('payment_status') == 'paid':
            return {'ok': True, 'already_processed': True}

        await db.payment_transactions.update_one(
            {'session_id': event.session_id},
            {'$set': {
                'payment_status': 'paid',
                'status': 'complete',
                'updated_at': datetime.now(timezone.utc).isoformat(),
                'webhook_event_type': event_type,
            }},
        )
        await db.users.update_one(
            {'id': tx['user_id']},
            {'$set': {
                'plan': tx['plan'],
                'billing': tx['billing'],
                'upgraded_at': datetime.now(timezone.utc).isoformat(),
            }},
        )
        logger.info(f"User {tx['user_id']} upgraded via webhook to {tx['plan']}/{tx['billing']}")

    return {'ok': True}


@router.post('/subscription/upgrade')
async def upgrade(plan: str, billing: str = 'monthly', user: dict = Depends(get_current_user)):
    """Legacy mock kept for backward compat. Do not use for real upgrades."""
    if plan not in ('free', 'pro', 'coach'):
        raise HTTPException(status_code=400, detail='Invalid plan')
    if billing not in ('monthly', 'annual'):
        raise HTTPException(status_code=400, detail='Invalid billing cycle')
    await db.users.update_one(
        {'id': user['id']},
        {'$set': {'plan': plan, 'billing': billing, 'upgraded_at': datetime.now(timezone.utc).isoformat()}},
    )
    return {'ok': True, 'plan': plan, 'billing': billing}


@router.post('/subscription/cancel')
async def cancel_subscription(user: dict = Depends(get_current_user)):
    """Downgrade the user to the Free plan immediately.

    Note: the current Stripe integration uses one-time payments, so there is no
    recurring subscription to cancel at Stripe \u2014 the user simply loses paid features.
    Emails a confirmation. Idempotent: free users can call this safely.
    """
    current_plan = user.get('plan', 'free')
    if current_plan == 'free':
        return {'ok': True, 'plan': 'free', 'already_free': True}

    await db.users.update_one(
        {'id': user['id']},
        {
            '$set': {
                'plan': 'free',
                'cancelled_at': datetime.now(timezone.utc).isoformat(),
                'previous_plan': current_plan,
            },
            '$unset': {'billing': ''},
        },
    )

    # Fail-soft email
    try:
        from services.email import send_subscription_cancelled_email
        await send_subscription_cancelled_email(to=user['email'], name=user.get('name'), plan=current_plan)
    except Exception as e:
        logger.error(f'Cancellation email failed: {e}')

    return {'ok': True, 'plan': 'free', 'previous_plan': current_plan}
