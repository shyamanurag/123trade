"""
ShareKhan Authentication Callback Endpoint
Real production flow: handle redirect, exchange token, update orchestrator
"""

from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse
import logging
import os
import urllib.parse

from src.core.sharekhan_orchestrator import ShareKhanTradingOrchestrator
from src.api.sharekhan_daily_auth import DailyAuthSession, get_session_key
from src.config.database import get_redis
from brokers.sharekhan import ShareKhanIntegration

router = APIRouter()
logger = logging.getLogger(__name__)


async def get_orchestrator() -> ShareKhanTradingOrchestrator:
    return await ShareKhanTradingOrchestrator.get_instance()


@router.get("/auth/sharekhan/callback")
async def sharekhan_auth_callback(
    request: Request,
    code: str | None = None,
    request_token: str | None = None,
    error: str | None = None,
    state: str | None = None,
    orchestrator: ShareKhanTradingOrchestrator = Depends(get_orchestrator),
):
    """
    Handle ShareKhan authentication callback
    - Accepts either request_token (preferred) or code
    - Exchanges for access/session tokens
    - Updates orchestrator and in-memory session for immediate production use
    """
    try:
        # Error from provider
        if error:
            logger.error(f"ShareKhan authentication error: {error}")
            return HTMLResponse(
                f"""
                <html>
                    <body>
                        <h2>❌ ShareKhan Authentication Failed</h2>
                        <p>Error: {error}</p>
                        <p>Please try authenticating again.</p>
                    </body>
                </html>
                """,
                status_code=400,
            )

        # Prefer request_token; if only code provided, use it as request_token
        token_from_provider = request_token or code
        if not token_from_provider:
            # Try to parse from full query string just in case
            qs = urllib.parse.urlparse(str(request.url)).query
            params = urllib.parse.parse_qs(qs)
            token_from_provider = (
                (params.get("request_token") or params.get("code") or [None])[0]
            )

        if not token_from_provider:
            logger.error("No request_token/code received from ShareKhan")
            raise HTTPException(status_code=400, detail="request_token not received")

        logger.info("✅ Received ShareKhan callback token (masked)")

        # Prepare client credentials
        api_key = os.getenv("SHAREKHAN_API_KEY")
        api_secret = os.getenv("SHAREKHAN_SECRET_KEY")
        client_id = os.getenv("SHAREKHAN_CUSTOMER_ID")
        if not api_key or not api_secret or not client_id:
            raise HTTPException(status_code=500, detail="ShareKhan credentials not configured")

        # Exchange token with ShareKhan
        sk = ShareKhanIntegration(api_key=api_key, secret_key=api_secret, customer_id=client_id)
        auth_ok = await sk.authenticate(request_token=token_from_provider)
        if not auth_ok or not sk.access_token or not sk.session_token:
            raise HTTPException(status_code=401, detail="ShareKhan authentication failed during token exchange")

        # Update orchestrator (global production session)
        try:
            if orchestrator and orchestrator.sharekhan_integration:
                orchestrator.sharekhan_integration.access_token = sk.access_token
                orchestrator.sharekhan_integration.session_token = sk.session_token
                orchestrator.sharekhan_integration.is_authenticated = True
                logger.info("✅ Orchestrator updated with ShareKhan tokens")
        except Exception as e:
            logger.warning(f"Could not update orchestrator tokens: {e}")

        # Persist to Redis (with in-memory fallback) for default user context
        try:
            default_user_id = int(os.getenv("DEFAULT_USER_ID", "1"))
            session_key = get_session_key(default_user_id, client_id)
            session = DailyAuthSession(
                user_id=default_user_id,
                sharekhan_client_id=client_id,
                request_token=token_from_provider,
                access_token=sk.access_token,
                session_token=sk.session_token,
                authenticated_at=datetime.now(),
                expires_at=datetime.now() + timedelta(hours=24),
                is_valid=True,
                last_error=None,
            )
            # Save to Redis
            try:
                redis = await get_redis()
                if redis:
                    payload = {
                        "user_id": session.user_id,
                        "sharekhan_client_id": session.sharekhan_client_id,
                        "request_token": session.request_token,
                        "access_token": session.access_token,
                        "session_token": session.session_token,
                        "authenticated_at": session.authenticated_at.isoformat() if session.authenticated_at else None,
                        "expires_at": session.expires_at.isoformat() if session.expires_at else None,
                        "is_valid": session.is_valid,
                        "last_error": session.last_error,
                    }
                    key = f"sharekhan:session:{session_key}"
                    await redis.set(key, json.dumps(payload))
                    await redis.expire(key, 24*3600)
            except Exception:
                pass
        except Exception as e:
            logger.warning(f"Could not store daily session: {e}")

        # Render minimal success page and auto-close
        return HTMLResponse(
            """
            <html>
              <body>
                <h2>✅ ShareKhan Authentication Successful</h2>
                <p>You can close this window and return to the app.</p>
                <script>
                  try { window.opener && window.opener.postMessage({ type: 'SHAREKHAN_AUTH_SUCCESS' }, '*'); } catch (e) {}
                  setTimeout(() => window.close(), 1500);
                </script>
              </body>
            </html>
            """
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in ShareKhan callback: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/auth/sharekhan")
async def sharekhan_auth_redirect():
    """Serve a page with a link to ShareKhan auth using production callback URL."""
    try:
        api_key = os.getenv("SHAREKHAN_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="ShareKhan API key not configured")

        # Determine public base URL for callback
        public_base = os.getenv(
            "PUBLIC_BASE_URL", "https://trade123-edtd2.ondigitalocean.app"
        ).rstrip("/")
        redirect_uri = f"{public_base}/auth/sharekhan/callback"

        # Use newtrade sharekhan login endpoint; include state
        import uuid
        state = str(uuid.uuid4())
        from urllib.parse import quote as _quote
        sharekhan_auth_url = (
            f"https://newtrade.sharekhan.com/api/login?api_key={api_key}&redirect_uri={_quote(redirect_uri, safe='')}&state={state}&response_type=code"
        )

        return HTMLResponse(
            f"""
            <html>
              <body>
                <h2>🔐 ShareKhan Authentication</h2>
                <p>Click below to authenticate with ShareKhan:</p>
                <a href="{sharekhan_auth_url}" target="_blank" style="display:inline-block;padding:10px 20px;background:#007bff;color:#fff;text-decoration:none;border-radius:6px;">Authenticate with ShareKhan</a>
                <p><small>You'll be redirected to ShareKhan's secure login portal.</small></p>
              </body>
            </html>
            """
        )

    except Exception as e:
        logger.error(f"Error initiating ShareKhan auth: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))