
import hashlib
import hmac
import json
import uuid
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from app.config import settings

URL = "https://api-dealguru.up.railway.app/api/webhooks/razorpay"

payload = {
    "entity": "event",
    "event": "payment.captured",
    "contains": ["payment"],
    "payload": {
        "payment": {
            "entity": {
                "id": "pay_test_webhook",
                "order_id": "order_test_11d2a1a784c346beb9f9e585bce1612d",
                "amount": 29900,
                "currency": "INR",
                "status": "captured",
                "method": "upi"
            }
        }
    }
}

body = json.dumps(payload, separators=(",", ":")).encode("utf-8")

signature = hmac.new(
    settings.razorpay_webhook_secret.encode("utf-8"),
    body,
    hashlib.sha256
).hexdigest()

event_id = "manual-capture-test-" + str(uuid.uuid4())

def send_test(test_signature):
    request = Request(
        URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-Razorpay-Signature": test_signature,
            "X-Razorpay-Event-Id": event_id
        },
        method="POST"
    )

    try:
        with urlopen(request, timeout=20) as response:
            print("HTTP:", response.status)
            print("Response:", response.read().decode())
    except HTTPError as error:
        print("HTTP:", error.code)
        print("Response:", error.read().decode())

print("\nTEST 1: Valid payment.captured event")
send_test(signature)

print("\nTEST 2: Invalid signature")
send_test("invalid-signature")
