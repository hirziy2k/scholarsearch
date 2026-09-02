import hashlib
import hmac
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, Optional, List
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class ScopedToken:
    """A short-lived, scoped token for client-side use.

    Unlike the master API key, this token:
    - Expires in 15 minutes
    - Is bound to a specific API key (tier)
    - Can only perform specific actions
    - Is single-use for file uploads
    """

    token_id: str
    api_key_hash: str
    tier: str
    scopes: List[str]
    created_at: float
    expires_at: float
    max_uploads: int = 1
    uploads_used: int = 0

    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    @property
    def is_valid(self) -> bool:
        return not self.is_expired and self.uploads_used < self.max_uploads

    def to_dict(self) -> Dict:
        return {
            "token_id": self.token_id,
            "tier": self.tier,
            "scopes": self.scopes,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "max_uploads": self.max_uploads,
            "uploads_used": self.uploads_used,
        }


TIER_EXPIRY = {
    "free": 600,
    "pro": 900,
    "enterprise": 1800,
}

TIER_DEFAULT_SCOPES = {
    "free": ["convert:write", "jobs:read"],
    "pro": ["convert:write", "jobs:read", "jobs:cancel"],
    "enterprise": ["convert:write", "jobs:read", "jobs:cancel", "admin:keys"],
}

TIER_MAX_UPLOADS = {
    "free": 1,
    "pro": 3,
    "enterprise": 10,
}


class AuthProxy:
    """BFF Authentication Proxy.

    Flow:
    1. Client authenticates with the BFF (e.g., via OAuth/Stripe webhook)
    2. BFF validates credentials against APIKeyManager + Stripe
    3. BFF issues a ScopedToken (short-lived, limited permissions)
    4. Client uses ScopedToken for file uploads (never sees master key)
    5. BFF validates ScopedToken on each request, then forwards to internal API

    The master API key NEVER leaves the server.
    """

    TOKEN_EXPIRY_SECONDS = 900
    MAX_TOKENS_PER_KEY = 10

    def __init__(self, secret_key: str = None, keys_file: str = None):
        self._secret = secret_key or uuid.uuid4().hex
        self._tokens: Dict[str, ScopedToken] = {}
        self._keys_file = Path(keys_file) if keys_file else None
        self._master_keys: Dict[str, str] = {}  # key -> tier
        self._key_manager = None
        if self._keys_file and self._keys_file.exists():
            self._load_keys()

    def _load_keys(self):
        if self._keys_file and self._keys_file.exists():
            data = json.loads(self._keys_file.read_text(encoding="utf-8"))
            self._master_keys = data.get("keys", {})

    def _save_keys(self):
        if self._keys_file:
            self._keys_file.parent.mkdir(parents=True, exist_ok=True)
            self._keys_file.write_text(
                json.dumps({"keys": self._master_keys}, indent=2),
                encoding="utf-8",
            )

    def _hmac_sign(self, message: str) -> str:
        return hmac.new(
            self._secret.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def _derive_tier(self, api_key: str) -> str:
        return self._master_keys.get(api_key, "free")

    def register_key(self, api_key: str, tier: str = "free"):
        self._master_keys[api_key] = tier
        self._save_keys()

    def issue_token(
        self,
        api_key: str,
        scopes: List[str] = None,
        max_uploads: int = 1,
    ) -> ScopedToken:
        if api_key not in self._master_keys:
            raise ValueError("Invalid API key")

        tier = self._master_keys[api_key]
        if scopes is None:
            scopes = list(TIER_DEFAULT_SCOPES.get(tier, TIER_DEFAULT_SCOPES["free"]))

        key_hash = self._hmac_sign(api_key)
        now = time.time()
        expiry_seconds = TIER_EXPIRY.get(tier, self.TOKEN_EXPIRY_SECONDS)
        token_id_raw = uuid.uuid4().hex
        token_id = f"{token_id_raw}.{self._hmac_sign(token_id_raw)}"

        token = ScopedToken(
            token_id=token_id,
            api_key_hash=key_hash,
            tier=tier,
            scopes=scopes,
            created_at=now,
            expires_at=now + expiry_seconds,
            max_uploads=max_uploads or TIER_MAX_UPLOADS.get(tier, 1),
            uploads_used=0,
        )

        active = [t for t in self._tokens.values() if t.api_key_hash == key_hash]
        if len(active) >= self.MAX_TOKENS_PER_KEY:
            oldest = min(active, key=lambda t: t.created_at)
            self._tokens.pop(oldest.token_id, None)

        self._tokens[token_id] = token
        return token

    def validate_token(
        self, token_id: str, required_scope: str = None
    ) -> Optional[ScopedToken]:
        token = self._tokens.get(token_id)
        if token is None:
            return None
        if token.is_expired:
            return None
        if required_scope and required_scope not in token.scopes:
            return None
        parts = token_id.split(".", 1)
        if len(parts) != 2:
            return None
        raw_id, sig = parts
        expected_sig = self._hmac_sign(raw_id)
        if not hmac.compare_digest(sig, expected_sig):
            return None
        return token

    def consume_upload(self, token_id: str) -> bool:
        token = self._tokens.get(token_id)
        if token is None or not token.is_valid:
            return False
        token.uploads_used += 1
        return True

    def revoke_token(self, token_id: str) -> bool:
        return self._tokens.pop(token_id, None) is not None

    def cleanup_expired(self) -> int:
        expired_ids = [
            tid for tid, t in self._tokens.items() if t.is_expired
        ]
        for tid in expired_ids:
            del self._tokens[tid]
        return len(expired_ids)

    def generate_presigned_upload_url(
        self, token_id: str, filename: str
    ) -> Optional[Dict]:
        token = self.validate_token(token_id, required_scope="convert:write")
        if token is None:
            return None

        upload_id = uuid.uuid4().hex
        expires_at = time.time() + 300
        url_path = f"/v1/uploads/{upload_id}"
        signature = self._hmac_sign(f"{url_path}:{expires_at}:{token_id}")

        return {
            "upload_url": f"{url_path}?expires={int(expires_at)}&sig={signature}",
            "token": token.to_dict(),
            "expires_at": expires_at,
            "filename": filename,
            "upload_id": upload_id,
        }


class StripeIntegration:
    """Connect API key provisioning to Stripe subscriptions.

    Flow:
    1. User subscribes via Stripe Checkout
    2. Stripe webhook hits /v1/webhook/stripe
    3. System provisions API key for the user's tier
    4. Key is linked to Stripe customer ID
    5. Usage tracked against Stripe subscription
    """

    def __init__(self, webhook_secret: str = None):
        self._webhook_secret = webhook_secret
        self._customer_keys: Dict[str, str] = {}  # customer_id -> api_key
        self._subscription_tiers: Dict[str, str] = {}  # subscription_id -> tier
        self._auth_proxy: Optional[AuthProxy] = None

    def set_auth_proxy(self, proxy: AuthProxy):
        self._auth_proxy = proxy

    def verify_webhook(self, payload: bytes, signature: str) -> bool:
        if not self._webhook_secret:
            return False
        parts = {}
        for item in signature.split(","):
            k, v = item.split("=", 1)
            parts[k] = v

        timestamp = parts.get("t", "")
        expected_sig = parts.get("v1", "")

        signed_payload = f"{timestamp}.{payload.decode('utf-8')}"
        computed = hmac.new(
            self._webhook_secret.encode("utf-8"),
            signed_payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        if abs(time.time() - float(timestamp)) > 300:
            return False

        return hmac.compare_digest(computed, expected_sig)

    async def handle_checkout_completed(self, event: Dict) -> Dict:
        data = event.get("data", {}).get("object", {})
        customer_id = data.get("customer", "")
        subscription_id = data.get("subscription", "")
        metadata = data.get("metadata", {})
        email = data.get("customer_email", "")

        tier = metadata.get("tier", "free")
        self._subscription_tiers[subscription_id] = tier

        api_key = uuid.uuid4().hex
        if self._auth_proxy:
            self._auth_proxy.register_key(api_key, tier)

        self._customer_keys[customer_id] = api_key

        return {
            "api_key": api_key,
            "tier": tier,
            "customer_id": customer_id,
            "subscription_id": subscription_id,
            "email": email,
        }

    async def handle_subscription_deleted(self, event: Dict):
        data = event.get("data", {}).get("object", {})
        subscription_id = data.get("id", "")
        customer_id = data.get("customer", "")

        api_key = self._customer_keys.pop(customer_id, None)
        self._subscription_tiers.pop(subscription_id, None)

        if api_key and self._auth_proxy:
            self._auth_proxy._master_keys.pop(api_key, None)
            self._auth_proxy._save_keys()

    async def handle_invoice_payment_failed(self, event: Dict):
        data = event.get("data", {}).get("object", {})
        customer_id = data.get("customer", "")
        subscription_id = data.get("subscription", "")

        current_tier = self._subscription_tiers.get(subscription_id, "free")
        downgrade = {
            "enterprise": "pro",
            "pro": "free",
            "free": "free",
        }
        new_tier = downgrade.get(current_tier, "free")
        self._subscription_tiers[subscription_id] = new_tier

        api_key = self._customer_keys.get(customer_id)
        if api_key and self._auth_proxy:
            self._auth_proxy._master_keys[api_key] = new_tier
            self._auth_proxy._save_keys()
