"""A minimal Telegram Bot API client.

Deliberately `urllib` from the stdlib rather than `requests`: sending a
message is one HTTPS POST, and staying stdlib-only keeps `requirements.txt`
at Django alone — which is the property that lets CI install dependencies
in a couple of seconds and lets a host with no build step run this.
"""

import json
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

API_ROOT = "https://api.telegram.org"
TIMEOUT_SECONDS = 10


def _call(method, params):
    """POST to one Bot API method and return its `result`.

    Raises ImproperlyConfigured if no token is set, and RuntimeError with
    Telegram's own description for any API-level failure.
    """
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        raise ImproperlyConfigured(
            "TELEGRAM_BOT_TOKEN is not set. Add it to .env — see .env.example."
        )

    url = f"{API_ROOT}/bot{token}/{method}"
    data = urllib.parse.urlencode(params).encode("utf-8")
    request = urllib.request.Request(url, data=data)

    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        # Telegram answers 4xx with a JSON body explaining what was wrong,
        # which is far more useful than the bare status line.
        payload = json.loads(exc.read().decode("utf-8"))

    if not payload.get("ok"):
        raise RuntimeError(
            f"Telegram API error on {method}: "
            f"{payload.get('error_code')} {payload.get('description')}"
        )

    return payload["result"]


def send_message(chat_id, text):
    """Send `text` to one chat."""
    return _call("sendMessage", {"chat_id": chat_id, "text": text})


def get_updates():
    """Return recent updates sent to the bot.

    Telegram only keeps these for about 24 hours, and a chat id is the only
    way to message someone — the API will not reveal one otherwise, which is
    why linking an account always starts with the user messaging the bot.
    """
    return _call("getUpdates", {})
