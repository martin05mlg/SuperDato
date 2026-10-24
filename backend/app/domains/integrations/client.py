import base64
import json
import urllib.parse
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
import httpx
import jwt
from app.core.config import settings
from app.core.security import decrypt_secret, encrypt_secret

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
GOOGLE_REVOKE_URL = "https://oauth2.googleapis.com/revoke"
GMAIL_MESSAGES_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages"

GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/userinfo.email",
]

MERCADONA_GMAIL_QUERY = "(from:mercadona OR from:mail.mercadona.com OR subject:mercadona) has:attachment filename:pdf"


class GoogleOAuthClient:
    @staticmethod
    def get_authorization_url(
        user_id: str,
        household_id: str,
        client_id: Optional[str] = None,
        redirect_uri: Optional[str] = None,
    ) -> str:
        """Generates Google OAuth 2.0 consent screen URL with cryptographically signed JWT state."""
        now = datetime.now(timezone.utc)
        state_payload = {
            "u": user_id,
            "h": household_id,
            "type": "oauth_state",
            "iat": now,
            "exp": now + timedelta(minutes=15),
        }
        state_str = jwt.encode(
            state_payload,
            settings.SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )

        effective_client_id = client_id or settings.GOOGLE_CLIENT_ID or "mock-google-client-id"
        effective_redirect_uri = redirect_uri or settings.GOOGLE_REDIRECT_URI

        params = {
            "client_id": effective_client_id,
            "redirect_uri": effective_redirect_uri,
            "response_type": "code",
            "scope": " ".join(GMAIL_SCOPES),
            "access_type": "offline",
            "prompt": "consent",
            "state": state_str,
        }
        return f"{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}"

    @staticmethod
    def decode_state(state_str: str) -> Tuple[str, str]:
        """Verifies the cryptographic JWT signature and expiration of state_str and extracts user_id and household_id."""
        try:
            data = jwt.decode(
                state_str,
                settings.SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
            )
            if data.get("type") != "oauth_state" or not data.get("u") or not data.get("h"):
                raise ValueError("Payload de estado OAuth inválido.")
            return str(data["u"]), str(data["h"])
        except Exception:
            raise ValueError("Estado OAuth de Google inválido, expirado o manipulado.")

    @staticmethod
    async def exchange_code_for_tokens(
        code: str,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        redirect_uri: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Exchanges authorization code for access and refresh tokens."""
        effective_client_id = client_id or settings.GOOGLE_CLIENT_ID
        effective_client_secret = client_secret or settings.GOOGLE_CLIENT_SECRET
        effective_redirect_uri = redirect_uri or settings.GOOGLE_REDIRECT_URI

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "client_id": effective_client_id,
                    "client_secret": effective_client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": effective_redirect_uri,
                },
            )

            if response.status_code != 200:
                raise ValueError(f"Error al canjear código de Google OAuth: {response.text}")

            tokens = response.json()
            return tokens

    @staticmethod
    async def get_user_email(access_token: str) -> str:
        """Fetches the Google account email address."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if res.status_code != 200:
                raise ValueError("No se pudo obtener el perfil de usuario de Google.")
            return res.json().get("email", "")

    @staticmethod
    async def refresh_access_token(encrypted_tokens_str: str) -> Tuple[str, str]:
        """Decrypts stored tokens, refreshes access_token using refresh_token, and re-encrypts."""
        tokens_json = decrypt_secret(encrypted_tokens_str)
        tokens = json.loads(tokens_json)
        refresh_token = tokens.get("refresh_token")

        if not refresh_token:
            raise ValueError("No existe refresh_token almacenado para esta conexión.")

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                },
            )

            if response.status_code != 200:
                raise ValueError(f"Fallo al renovar token de Google: {response.text}")

            new_tokens = response.json()
            tokens["access_token"] = new_tokens["access_token"]
            tokens["expires_in"] = new_tokens.get("expires_in", 3600)

            updated_encrypted = encrypt_secret(json.dumps(tokens))
            return new_tokens["access_token"], updated_encrypted

    @staticmethod
    async def revoke_tokens(encrypted_tokens_str: str) -> bool:
        """Revokes token directly with Google OAuth API."""
        try:
            tokens_json = decrypt_secret(encrypted_tokens_str)
            tokens = json.loads(tokens_json)
            token = tokens.get("refresh_token") or tokens.get("access_token")

            if token:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    await client.post(GOOGLE_REVOKE_URL, params={"token": token})
            return True
        except Exception:
            return False

    @staticmethod
    async def search_mercadona_messages(access_token: str, query: Optional[str] = None) -> List[Dict[str, str]]:
        """Searches for Mercadona emails containing digital ticket PDFs."""
        q = query or MERCADONA_GMAIL_QUERY
        messages = []

        async with httpx.AsyncClient(timeout=20.0) as client:
            res = await client.get(
                GMAIL_MESSAGES_URL,
                params={"q": q, "maxResults": 100},
                headers={"Authorization": f"Bearer {access_token}"},
            )

            if res.status_code == 200:
                data = res.json()
                messages = data.get("messages", [])

        return messages

    @staticmethod
    async def fetch_pdf_attachment(access_token: str, message_id: str) -> Optional[bytes]:
        """Fetches and decodes the PDF attachment from a specific Gmail message."""
        async with httpx.AsyncClient(timeout=20.0) as client:
            msg_res = await client.get(
                f"{GMAIL_MESSAGES_URL}/{message_id}",
                params={"format": "full"},
                headers={"Authorization": f"Bearer {access_token}"},
            )

            if msg_res.status_code != 200:
                return None

            msg_data = msg_res.json()
            parts = msg_data.get("payload", {}).get("parts", [])

            for part in parts:
                filename = part.get("filename", "").lower()
                if filename.endswith(".pdf") and "body" in part:
                    att_id = part["body"].get("attachmentId")
                    if att_id:
                        # Fetch attachment
                        att_url = f"{GMAIL_MESSAGES_URL}/{message_id}/attachments/{att_id}"
                        att_res = await client.get(
                            att_url,
                            headers={"Authorization": f"Bearer {access_token}"},
                        )
                        if att_res.status_code == 200:
                            data_b64 = att_res.json().get("data", "")
                            # Standard base64url decode
                            pdf_bytes = base64.urlsafe_b64decode(data_b64.encode("utf-8"))
                            return pdf_bytes
                    elif "data" in part["body"]:
                        data_b64 = part["body"]["data"]
                        return base64.urlsafe_b64decode(data_b64.encode("utf-8"))

        return None

