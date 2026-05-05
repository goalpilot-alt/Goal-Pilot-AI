"""Expo Push Notification dispatcher.

Uses the Expo Push API: https://docs.expo.dev/push-notifications/sending-notifications/
No SDK required — plain HTTPS POST.
"""
import logging
import httpx
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

EXPO_PUSH_URL = 'https://exp.host/--/api/v2/push/send'


async def send_expo_push(messages: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Send a batch of push messages to Expo. Returns Expo's response payload.

    Each message dict should include at minimum: { 'to': <ExponentPushToken>, 'title': str, 'body': str }
    Optional: 'data' (dict), 'sound': 'default', 'priority': 'high'.
    """
    if not messages:
        return {'data': []}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(
                EXPO_PUSH_URL,
                json=messages,
                headers={
                    'Accept': 'application/json',
                    'Accept-Encoding': 'gzip, deflate',
                    'Content-Type': 'application/json',
                },
            )
            r.raise_for_status()
            return r.json()
    except Exception as e:
        logger.error(f'Expo push send failed: {e}')
        return {'error': str(e)}
