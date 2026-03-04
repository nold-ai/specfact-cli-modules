"""Backlog auth command group."""

from __future__ import annotations

import os
import time
from datetime import UTC, datetime, timedelta
from typing import Any

import requests
import typer
from beartype import beartype
from icontract import ensure, require
from rich.console import Console

from specfact_backlog.backlog.auth_tokens import (
    clear_all_tokens,
    clear_token,
    get_token,
    normalize_provider,
    set_token,
    token_is_expired,
)


AZURE_DEVOPS_RESOURCE = "499b84ac-1321-427f-aa17-267ca6975798/.default"
AZURE_DEVOPS_SCOPES = [AZURE_DEVOPS_RESOURCE]
DEFAULT_GITHUB_BASE_URL = "https://github.com"
DEFAULT_GITHUB_API_URL = "https://api.github.com"
DEFAULT_GITHUB_SCOPES = "repo read:project project"
DEFAULT_GITHUB_CLIENT_ID = "Ov23lizkVHsbEIjZKvRD"

auth_app = typer.Typer(help="Authenticate backlog providers (Azure DevOps and GitHub)")
console = Console()


@beartype
@ensure(lambda result: isinstance(result, str), "Must return base URL")
def _normalize_github_host(base_url: str) -> str:
    trimmed = base_url.rstrip("/")
    if trimmed.endswith("/api/v3"):
        trimmed = trimmed[: -len("/api/v3")]
    if trimmed.endswith("/api"):
        trimmed = trimmed[: -len("/api")]
    return trimmed


@beartype
@ensure(lambda result: isinstance(result, str), "Must return API base URL")
def _infer_github_api_base_url(host_url: str) -> str:
    normalized = host_url.rstrip("/")
    if normalized.lower() == DEFAULT_GITHUB_BASE_URL:
        return DEFAULT_GITHUB_API_URL
    return f"{normalized}/api/v3"


@beartype
@require(lambda scopes: isinstance(scopes, str), "Scopes must be string")
@ensure(lambda result: isinstance(result, str), "Must return scope string")
def _normalize_scopes(scopes: str) -> str:
    if not scopes.strip():
        return DEFAULT_GITHUB_SCOPES
    if "," in scopes:
        parts = [part.strip() for part in scopes.split(",") if part.strip()]
        return " ".join(parts)
    return scopes.strip()


@beartype
@require(lambda client_id: isinstance(client_id, str) and len(client_id) > 0, "Client ID required")
@require(lambda base_url: isinstance(base_url, str) and len(base_url) > 0, "Base URL required")
@require(
    lambda base_url: base_url.startswith(("https://", "http://")),
    "Base URL must include http(s) scheme",
)
@require(lambda scopes: isinstance(scopes, str), "Scopes must be string")
@ensure(lambda result: isinstance(result, dict), "Must return device code response")
def _request_github_device_code(client_id: str, base_url: str, scopes: str) -> dict[str, Any]:
    endpoint = f"{base_url.rstrip('/')}/login/device/code"
    headers = {"Accept": "application/json"}
    payload = {"client_id": client_id, "scope": scopes}
    response = requests.post(endpoint, data=payload, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()


@beartype
@require(lambda client_id: isinstance(client_id, str) and len(client_id) > 0, "Client ID required")
@require(lambda base_url: isinstance(base_url, str) and len(base_url) > 0, "Base URL required")
@require(
    lambda base_url: base_url.startswith(("https://", "http://")),
    "Base URL must include http(s) scheme",
)
@require(lambda device_code: isinstance(device_code, str) and len(device_code) > 0, "Device code required")
@require(lambda interval: isinstance(interval, int) and interval > 0, "Interval must be positive int")
@require(lambda expires_in: isinstance(expires_in, int) and expires_in > 0, "Expires_in must be positive int")
@ensure(lambda result: isinstance(result, dict), "Must return token response")
def _poll_github_device_token(
    client_id: str,
    base_url: str,
    device_code: str,
    interval: int,
    expires_in: int,
) -> dict[str, Any]:
    endpoint = f"{base_url.rstrip('/')}/login/oauth/access_token"
    headers = {"Accept": "application/json"}
    payload = {
        "client_id": client_id,
        "device_code": device_code,
        "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
    }
    deadline = time.monotonic() + expires_in
    poll_interval = interval
    while time.monotonic() < deadline:
        response = requests.post(endpoint, data=payload, headers=headers, timeout=30)
        response.raise_for_status()
        body = response.json()
        error = body.get("error")
        if not error:
            return body
        if error == "authorization_pending":
            time.sleep(poll_interval)
            continue
        if error == "slow_down":
            poll_interval += 5
            time.sleep(poll_interval)
            continue
        if error in {"expired_token", "access_denied"}:
            msg = body.get("error_description") or error
            raise RuntimeError(msg)
        msg = body.get("error_description") or error
        raise RuntimeError(msg)
    raise RuntimeError("Device code expired before authorization completed")


@beartype
@ensure(lambda result: result is None, "Must return None")
def _print_provider_status(provider: str, token_data: dict[str, Any], *, expired: bool) -> None:
    state = "expired" if expired else "valid"
    token_type = str(token_data.get("token_type") or "unknown")
    expires_at = token_data.get("expires_at")
    expires_fragment = f", expires_at={expires_at}" if expires_at else ""
    console.print(f"[bold]{provider}[/bold]: {state}, token_type={token_type}{expires_fragment}")


@beartype
@auth_app.command("azure-devops")
def auth_azure_devops(
    pat: str | None = typer.Option(None, "--pat", help="Store Azure DevOps PAT directly."),
    use_device_code: bool = typer.Option(
        False, "--use-device-code", help="Use device-code flow instead of interactive browser."
    ),
) -> None:
    """Authenticate to Azure DevOps via PAT or OAuth."""
    if pat:
        token_data = {
            "access_token": pat,
            "token_type": "basic",
            "issued_at": datetime.now(tz=UTC).isoformat(),
        }
        set_token("azure-devops", token_data)
        console.print("[bold green]✓[/bold green] Stored token for provider: azure-devops")
        return

    try:
        from azure.identity import (  # type: ignore[reportMissingImports]
            DeviceCodeCredential,
            InteractiveBrowserCredential,
        )
    except ImportError:
        console.print("[bold red]✗[/bold red] azure-identity is not installed.")
        console.print("Install dependencies with: pip install specfact-cli")
        raise typer.Exit(1) from None

    def prompt_callback(verification_uri: str, user_code: str, expires_on: datetime) -> None:
        if expires_on.tzinfo is None:
            expires_on = expires_on.replace(tzinfo=UTC)
        console.print(f"Open [bold]{verification_uri}[/bold] and enter [bold]{user_code}[/bold]")
        console.print(f"Code expires at: {expires_on.isoformat()}")

    token: Any = None
    if not use_device_code:
        try:
            credential = InteractiveBrowserCredential()
            token = credential.get_token(*AZURE_DEVOPS_SCOPES)
        except Exception:
            token = None
    if token is None:
        try:
            credential = DeviceCodeCredential(prompt_callback=prompt_callback)
            token = credential.get_token(*AZURE_DEVOPS_SCOPES)
        except Exception as error:
            console.print(f"[bold red]✗[/bold red] Authentication failed: {error}")
            raise typer.Exit(1) from error

    expires_on_timestamp = float(token.expires_on)
    if expires_on_timestamp > 1e10:
        expires_on_timestamp = expires_on_timestamp / 1000
    expires_at = datetime.fromtimestamp(expires_on_timestamp, tz=UTC).isoformat()
    token_data = {
        "access_token": token.token,
        "token_type": "bearer",
        "expires_at": expires_at,
        "resource": AZURE_DEVOPS_RESOURCE,
        "issued_at": datetime.now(tz=UTC).isoformat(),
    }
    set_token("azure-devops", token_data)
    console.print("[bold green]✓[/bold green] Stored token for provider: azure-devops")


@beartype
@auth_app.command("github")
def auth_github(
    client_id: str | None = typer.Option(
        None,
        "--client-id",
        help="GitHub OAuth app client ID (defaults to SpecFact app ID).",
    ),
    base_url: str = typer.Option(
        DEFAULT_GITHUB_BASE_URL,
        "--base-url",
        help="GitHub base URL (or enterprise host).",
    ),
    scopes: str = typer.Option(
        DEFAULT_GITHUB_SCOPES,
        "--scopes",
        help="OAuth scopes (comma or space separated).",
    ),
) -> None:
    """Authenticate to GitHub using RFC 8628 device code flow."""
    provided_client_id = client_id or os.environ.get("SPECFACT_GITHUB_CLIENT_ID")
    effective_client_id = provided_client_id or DEFAULT_GITHUB_CLIENT_ID
    if not effective_client_id:
        console.print("[bold red]✗[/bold red] GitHub client_id is required.")
        console.print("Use --client-id or set SPECFACT_GITHUB_CLIENT_ID.")
        raise typer.Exit(1)

    host_url = _normalize_github_host(base_url)
    if provided_client_id is None and host_url.lower() != DEFAULT_GITHUB_BASE_URL:
        console.print("[bold red]✗[/bold red] GitHub Enterprise requires a client ID.")
        console.print("Provide --client-id or set SPECFACT_GITHUB_CLIENT_ID.")
        raise typer.Exit(1)

    scope_string = _normalize_scopes(scopes)
    device_payload = _request_github_device_code(effective_client_id, host_url, scope_string)
    user_code = device_payload.get("user_code")
    verification_uri = device_payload.get("verification_uri")
    verification_uri_complete = device_payload.get("verification_uri_complete")
    device_code = device_payload.get("device_code")
    expires_in = int(device_payload.get("expires_in", 900))
    interval = int(device_payload.get("interval", 5))
    if not device_code:
        console.print("[bold red]✗[/bold red] Invalid device code response from GitHub")
        raise typer.Exit(1)
    if verification_uri_complete:
        console.print(f"Open: [bold]{verification_uri_complete}[/bold]")
    elif verification_uri and user_code:
        console.print(f"Open: [bold]{verification_uri}[/bold] and enter code [bold]{user_code}[/bold]")
    else:
        console.print("[bold red]✗[/bold red] Invalid device code response from GitHub")
        raise typer.Exit(1)

    token_payload = _poll_github_device_token(effective_client_id, host_url, device_code, interval, expires_in)
    access_token = token_payload.get("access_token")
    if not access_token:
        console.print("[bold red]✗[/bold red] GitHub did not return an access token")
        raise typer.Exit(1)

    expires_at = datetime.now(tz=UTC) + timedelta(seconds=expires_in)
    token_data: dict[str, Any] = {
        "access_token": access_token,
        "token_type": token_payload.get("token_type", "bearer"),
        "scopes": token_payload.get("scope", scope_string),
        "client_id": effective_client_id,
        "issued_at": datetime.now(tz=UTC).isoformat(),
        "expires_at": None,
        "base_url": host_url,
        "api_base_url": _infer_github_api_base_url(host_url),
    }
    if token_payload.get("expires_in"):
        token_data["expires_at"] = expires_at.isoformat()
    set_token("github", token_data)
    console.print("[bold green]✓[/bold green] Stored token for provider: github")


@beartype
@auth_app.command("status")
def auth_status() -> None:
    """Show stored auth state for supported providers."""
    providers = ("github", "azure-devops")
    found_any = False
    for provider in providers:
        active = get_token(provider, allow_expired=False)
        if active:
            _print_provider_status(provider, active, expired=False)
            found_any = True
            continue
        expired = get_token(provider, allow_expired=True)
        if expired:
            _print_provider_status(provider, expired, expired=token_is_expired(expired))
            found_any = True
    if not found_any:
        console.print("No stored authentication tokens found.")


@beartype
@auth_app.command("clear")
def auth_clear(
    provider: str | None = typer.Option(
        None,
        "--provider",
        help="Provider to clear (azure-devops or github). Clear all when omitted.",
    ),
) -> None:
    """Clear stored auth tokens."""
    if provider:
        normalized = normalize_provider(provider)
        clear_token(normalized)
        console.print(f"Cleared stored token for {normalized}")
        return

    clear_all_tokens()
    console.print("Cleared all stored tokens")
