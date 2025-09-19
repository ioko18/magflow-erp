"""
Well-known endpoints for service discovery and metadata.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

from app.security.keys import get_key_manager
from app.core.config import settings

router = APIRouter(
    prefix="/.well-known",
    tags=["well-known"],
    responses={404: {"description": "Not found"}},
)


@router.get("/jwks.json", response_model=dict)
async def get_jwks():
    """
    Returns the JSON Web Key Set (JWKS) containing the public keys
    that can be used to verify JWT tokens issued by this service.

    This endpoint follows the JWK Set specification (RFC 7517).
    """
    try:
        key_manager = get_key_manager()
        jwks = key_manager.get_jwks()
        return JSONResponse(
            content=jsonable_encoder(jwks),
            headers={
                "Cache-Control": f"public, max-age={settings.jwks_cache_max_age}",
                "Access-Control-Allow-Origin": "*",
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve JWKS: {str(e)}",
        )


@router.get("/openid-configuration", response_model=dict)
async def get_openid_configuration():
    """
    Returns the OpenID Provider Configuration Information.

    This endpoint follows the OpenID Connect Discovery specification.
    """
    base_url = str(settings.SERVER_HOST)
    if settings.SERVER_HOST.port:
        base_url = f"{settings.SERVER_HOST.scheme}://{settings.SERVER_HOST.host}:{settings.SERVER_HOST.port}"
    else:
        base_url = f"{settings.SERVER_HOST.scheme}://{settings.SERVER_HOST.host}"

    return {
        "issuer": settings.jwt_issuer,
        "jwks_uri": f"{base_url}/.well-known/jwks.json",
        "authorization_endpoint": f"{base_url}/auth/authorize",
        "token_endpoint": f"{base_url}/auth/token",
        "userinfo_endpoint": f"{base_url}/auth/userinfo",
        "end_session_endpoint": f"{base_url}/auth/logout",
        "scopes_supported": ["openid", "profile", "email"],
        "response_types_supported": [
            "code",
            "token",
            "id_token",
            "code token",
            "code id_token",
            "token id_token",
            "code token id_token",
        ],
        "subject_types_supported": ["public"],
        "id_token_signing_alg_values_supported": ["RS256", "EdDSA"],
        "token_endpoint_auth_methods_supported": [
            "client_secret_basic",
            "private_key_jwt",
        ],
        "claims_supported": [
            "sub",
            "iss",
            "auth_time",
            "name",
            "given_name",
            "family_name",
            "email",
            "email_verified",
        ],
    }
