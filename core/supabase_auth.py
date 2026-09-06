"""Service layer integrasi Supabase Auth (OAuth Google/GitHub + signup)."""
import base64
import hashlib
import secrets
import urllib.parse

import httpx
from django.conf import settings

SUPPORTED_PROVIDERS = ('google', 'github')

PROVIDER_SCOPES = {
    'google': 'openid email profile',
    'github': 'openid email read:user user:email',
}

_PLACEHOLDER_URL = 'https://your-project.supabase.co'
_PLACEHOLDER_KEY = 'your-anon-key'


def is_configured():
    """True bila SUPABASE_URL dan SUPABASE_ANON_KEY sudah diisi nyata."""
    return bool(
        settings.SUPABASE_URL
        and settings.SUPABASE_ANON_KEY
        and settings.SUPABASE_URL != _PLACEHOLDER_URL
        and settings.SUPABASE_ANON_KEY != _PLACEHOLDER_KEY
    )


def _base_url():
    return settings.SUPABASE_URL.rstrip('/')


def _headers():
    return {
        'apikey': settings.SUPABASE_ANON_KEY,
        'Content-Type': 'application/json',
    }


def generate_pkce():
    """Buat pasangan code_verifier / code_challenge (SHA-256 S256)."""
    code_verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(code_verifier.encode('ascii')).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b'=').decode('ascii')
    return code_verifier, code_challenge


def authorize_url(provider, redirect_to):
    """Bangun URL Supabase authorize untuk OAuth provider."""
    if provider not in SUPPORTED_PROVIDERS:
        raise ValueError(f'Provider tidak didukung: {provider}')
    code_verifier, code_challenge = generate_pkce()
    params = urllib.parse.urlencode({
        'provider': provider,
        'scopes': PROVIDER_SCOPES[provider],
        'redirect_to': redirect_to,
        'code_challenge': code_challenge,
        'code_challenge_method': 'S256',
    })
    return f'{_base_url()}/auth/v1/authorize?{params}', code_verifier


def exchange_code(code, code_verifier):
    """Tukar authorization code menjadi session/user Supabase (PKCE)."""
    # Di Vercel, timeout terlalu singkat bisa 500 cold start — beri 20s tetap, tapi log detail saat gagal
    response = httpx.post(
        f'{_base_url()}/auth/v1/token?grant_type=pkce',
        headers=_headers(),
        json={'auth_code': code, 'code_verifier': code_verifier},
        timeout=20,
    )
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        # Supabase balikan body JSON berisi msg — lempar dengan detail supaya tidak jadi 500 generik
        try:
            detail = response.json()
        except Exception:
            detail = response.text[:500]
        raise RuntimeError(f'Supabase token exchange gagal ({response.status_code}): {detail}') from exc
    return response.json()


def sign_up(email, password, full_name):
    """Daftarkan akun email/password di Supabase Auth."""
    response = httpx.post(
        f'{_base_url()}/auth/v1/signup',
        headers=_headers(),
        json={'email': email, 'password': password, 'data': {'full_name': full_name}},
        timeout=20,
    )
    response.raise_for_status()
    return response.json()
