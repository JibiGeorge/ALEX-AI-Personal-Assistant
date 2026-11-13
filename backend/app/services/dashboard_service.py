from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import io
import json
import logging
import secrets
import socket
import time
import uuid
from typing import Any, Optional

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from fastapi import WebSocket

from app.schemas.mobile import MobileGatewayStatus, PairingInitResponse, PairingResponse

logger = logging.getLogger(__name__)

# Alphabet excluding visually ambiguous characters (O, 0, I, 1, L)
UNAMBIGUOUS_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
DEFAULT_SALT = b"ALEX-MOBILE-GATEWAY-v1"
PBKDF2_ITERATIONS = 200_000
PAIRING_TTL_SECONDS = 300
RATE_LIMIT_ATTEMPTS = 5
RATE_LIMIT_WINDOW_SECONDS = 60


class DashboardService:
    """Mobile Gateway & Secure Pairing Service.

    Provides LAN discovery, QR code generation, PBKDF2-HMAC-SHA256 key derivation,
    AES-256-GCM encrypted communication channels, rate limiting, and real-time
    WebSocket event dispatch for mobile companion clients.
    """

    def __init__(
        self,
        port: int = 8766,
        salt: bytes = DEFAULT_SALT,
        iterations: int = PBKDF2_ITERATIONS,
        pairing_ttl: int = PAIRING_TTL_SECONDS,
    ) -> None:
        self.port = port
        self._salt = salt
        self._iterations = iterations
        self._pairing_ttl = pairing_ttl

        self._current_pairing_code: Optional[str] = None
        self._pairing_code_created_at: float = 0.0
        self._failed_attempts: dict[str, list[float]] = {}
        self._paired_sessions: dict[str, dict[str, Any]] = {}
        self._active_websockets: set[WebSocket] = set()
        self._pending_approvals: dict[str, dict[str, Any]] = {}

    def get_lan_ip(self) -> str:
        """Detect the primary local area network (LAN) IP address."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                # Does not actually transmit packets, routes to determine outbound interface
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except Exception:
            return "127.0.0.1"

    def generate_pairing_info(self) -> PairingInitResponse:
        """Generate an 8-character pairing code and QR code image data URI."""
        now = time.time()
        # Reuse existing code if still valid with >60s remaining
        if (
            self._current_pairing_code is not None
            and (now - self._pairing_code_created_at) < (self._pairing_ttl - 60)
        ):
            code = self._current_pairing_code
            expires_in = int(self._pairing_ttl - (now - self._pairing_code_created_at))
        else:
            code = "".join(secrets.choice(UNAMBIGUOUS_ALPHABET) for _ in range(8))
            self._current_pairing_code = code
            self._pairing_code_created_at = now
            expires_in = self._pairing_ttl

        lan_ip = self.get_lan_ip()
        pairing_url = f"alex://pair?host={lan_ip}&port={self.port}&code={code}"

        # Generate QR code
        qr_data_uri = self._generate_qr_data_uri(pairing_url)

        return PairingInitResponse(
            pairing_code=code,
            qr_data_uri=qr_data_uri,
            pairing_url=pairing_url,
            lan_host=lan_ip,
            port=self.port,
            expires_in_seconds=expires_in,
        )

    def _generate_qr_data_uri(self, data: str) -> str:
        """Render a QR code image as a base64 data URI."""
        try:
            import qrcode  # pylint: disable=import-outside-toplevel

            qr = qrcode.QRCode(box_size=4, border=2)
            qr.add_data(data)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            return f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode('ascii')}"
        except Exception as exc:
            logger.warning("QR code generation failed, returning placeholder: %s", exc)
            return "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg'/>"

    def derive_key(self, code: str) -> bytes:
        """Derive a 256-bit AES key from a pairing code using 200,000 PBKDF2 rounds."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self._salt,
            iterations=self._iterations,
        )
        normalized_code = code.strip().upper().encode("utf-8")
        return kdf.derive(normalized_code)

    def verify_and_pair(
        self,
        client_ip: str,
        code: str,
        device_name: str = "Mobile Client",
        device_platform: str = "iOS",
    ) -> PairingResponse:
        """Validate pairing code with rate limiting and establish a paired session."""
        now = time.time()

        # Enforce IP-based rate limiting (5 failed attempts per 60s)
        attempts = [
            t for t in self._failed_attempts.get(client_ip, [])
            if now - t < RATE_LIMIT_WINDOW_SECONDS
        ]
        self._failed_attempts[client_ip] = attempts

        if len(attempts) >= RATE_LIMIT_ATTEMPTS:
            raise PermissionError("Too many failed pairing attempts. Please wait 60 seconds.")

        # Check code validity and expiration
        normalized_code = code.strip().upper()
        if (
            self._current_pairing_code is None
            or normalized_code != self._current_pairing_code
            or (now - self._pairing_code_created_at) > self._pairing_ttl
        ):
            self._failed_attempts.setdefault(client_ip, []).append(now)
            raise ValueError("Invalid or expired pairing code.")

        # Clear failed attempts on success
        self._failed_attempts.pop(client_ip, None)

        # Derive symmetric encryption key
        aes_key = self.derive_key(normalized_code)
        session_token = secrets.token_urlsafe(32)

        self._paired_sessions[session_token] = {
            "device_name": device_name,
            "device_platform": device_platform,
            "aes_key": aes_key,
            "client_ip": client_ip,
            "created_at": now,
        }

        logger.info(
            "Paired mobile client '%s' (%s) from %s",
            device_name, device_platform, client_ip
        )

        return PairingResponse(
            success=True,
            session_token=session_token,
            salt=base64.b64encode(self._salt).decode("ascii"),
            iterations=self._iterations,
            message="Pairing successful",
        )

    def get_session(self, session_token: str) -> Optional[dict[str, Any]]:
        """Retrieve paired session metadata by session token."""
        return self._paired_sessions.get(session_token)

    def is_authenticated(self, session_token: str) -> bool:
        """Check if a session token is active."""
        return session_token in self._paired_sessions

    def encrypt(self, session_token: str, plaintext: bytes | str) -> dict[str, str]:
        """Encrypt payload using AES-256-GCM under the session key."""
        session = self.get_session(session_token)
        if not session:
            raise ValueError("Invalid or expired session token.")

        key = session["aes_key"]
        aes = AESGCM(key)
        iv = secrets.token_bytes(12)

        if isinstance(plaintext, str):
            data = plaintext.encode("utf-8")
        else:
            data = plaintext

        ciphertext = aes.encrypt(iv, data, None)

        return {
            "iv": base64.b64encode(iv).decode("ascii"),
            "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
        }

    def decrypt(self, session_token: str, iv_b64: str, ciphertext_b64: str) -> bytes:
        """Decrypt AES-256-GCM ciphertext using the session key."""
        session = self.get_session(session_token)
        if not session:
            raise ValueError("Invalid or expired session token.")

        key = session["aes_key"]
        aes = AESGCM(key)

        iv = base64.b64decode(iv_b64)
        ciphertext = base64.b64decode(ciphertext_b64)

        return aes.decrypt(iv, ciphertext, None)

    def register_websocket(self, ws: WebSocket) -> None:
        """Register an active mobile client WebSocket connection."""
        self._active_websockets.add(ws)

    def unregister_websocket(self, ws: WebSocket) -> None:
        """Unregister a disconnected mobile client WebSocket."""
        self._active_websockets.discard(ws)

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Broadcast an event message to all connected mobile WebSockets."""
        payload_str = json.dumps(message)
        dead: list[WebSocket] = []

        for ws in self._active_websockets:
            try:
                await ws.send_text(payload_str)
            except Exception:
                dead.append(ws)

        for ws in dead:
            self._active_websockets.discard(ws)

    def get_status(self) -> MobileGatewayStatus:
        """Get the current operational status of the Mobile Gateway."""
        return MobileGatewayStatus(
            active=True,
            lan_ip=self.get_lan_ip(),
            port=self.port,
            paired_devices=len(self._paired_sessions),
            pending_approvals=len(self._pending_approvals),
        )

    def sign_decision(self, session_token: str, request_id: str, approved: bool) -> str:
        """Create HMAC-SHA256 signature for approval decision using session AES key."""
        session = self.get_session(session_token)
        if not session:
            raise ValueError("Invalid session token")
        key = session["aes_key"]
        data = f"{request_id}:{approved}".encode("utf-8")
        return hmac.new(key, data, hashlib.sha256).hexdigest()

    def verify_decision_signature(
        self,
        session_token: str,
        request_id: str,
        approved: bool,
        signature: str,
    ) -> bool:
        """Verify HMAC-SHA256 signature for approval decision."""
        try:
            expected = self.sign_decision(session_token, request_id, approved)
            return hmac.compare_digest(expected, signature)
        except Exception:
            return False

    async def request_action_approval(
        self,
        action_id: str,
        params: dict[str, Any],
        timeout: float = 15.0,
    ) -> bool:
        """Broadcast approval prompt to connected mobile devices and await decision."""
        if not self._paired_sessions and not self._active_websockets:
            logger.debug("No paired mobile devices to authorize action %s", action_id)
            return False

        request_id = str(uuid.uuid4())
        loop = asyncio.get_running_loop()
        future: asyncio.Future[bool] = loop.create_future()

        self._pending_approvals[request_id] = {
            "request_id": request_id,
            "action_id": action_id,
            "params": params,
            "created_at": time.time(),
            "timeout": timeout,
            "future": future,
        }

        # Broadcast push approval alert over WebSocket
        msg = {
            "type": "action_approval_required",
            "request_id": request_id,
            "action": action_id,
            "params": params,
            "timeout": timeout,
            "timestamp": time.time(),
        }
        await self.broadcast(msg)

        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except (asyncio.TimeoutError, Exception) as exc:
            logger.info("Action approval for %s (id: %s) timed out or failed: %s", action_id, request_id, exc)
            return False
        finally:
            self._pending_approvals.pop(request_id, None)

    def resolve_approval(
        self,
        request_id: str,
        approved: bool,
        session_token: Optional[str] = None,
        signature: Optional[str] = None,
    ) -> bool:
        """Resolve a pending action approval request."""
        entry = self._pending_approvals.get(request_id)
        if not entry:
            return False

        if session_token:
            if not self.is_authenticated(session_token):
                return False
            if signature and not self.verify_decision_signature(session_token, request_id, approved, signature):
                return False

        fut: asyncio.Future[bool] = entry["future"]
        if not fut.done():
            fut.set_result(approved)
            return True
        return False

    def list_pending_approvals(self) -> list[dict[str, Any]]:
        """List active pending action approval requests."""
        now = time.time()
        active = []
        for rid, item in list(self._pending_approvals.items()):
            if now - item["created_at"] <= item["timeout"]:
                active.append({
                    "request_id": item["request_id"],
                    "action_id": item["action_id"],
                    "params": item["params"],
                    "created_at": item["created_at"],
                    "timeout": item["timeout"],
                })
        return active


