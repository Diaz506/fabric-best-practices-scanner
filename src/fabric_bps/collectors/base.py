"""Admin API client + token providers.

Two ways to authenticate against the Fabric / Power BI *read-only admin* APIs:
  - fabric_notebook_token_provider(): inside a Fabric notebook (uses notebookutils).
  - service_principal_token_provider(): headless, via MSAL client credentials.

Prerequisite (tenant admin, one-time): enable the tenant setting
"Service principals can use read-only admin APIs" and add the SP to the allowed group,
or run under a user with Fabric Administrator / Power BI Service Administrator role.
"""
from __future__ import annotations

from typing import Callable

PBI_BASE = "https://api.powerbi.com/v1.0/myorg"
FABRIC_BASE = "https://api.fabric.microsoft.com/v1"
POWERBI_SCOPE = "https://analysis.windows.net/powerbi/api/.default"


class AdminClient:
    def __init__(self, token_provider: Callable[[], str], session=None):
        self._token_provider = token_provider
        if session is None:
            import requests

            session = requests.Session()
        self._session = session

    def get(self, url: str, params: dict = None) -> dict:
        headers = {"Authorization": f"Bearer {self._token_provider()}"}
        resp = self._session.get(url, headers=headers, params=params, timeout=60)
        resp.raise_for_status()
        return resp.json()


def fabric_notebook_token_provider(resource: str = "pbi") -> Callable[[], str]:
    def _provider() -> str:
        import notebookutils  # available in the Fabric runtime

        return notebookutils.credentials.getToken(resource)

    return _provider


def service_principal_token_provider(
    tenant_id: str, client_id: str, client_secret: str, scope: str = POWERBI_SCOPE
) -> Callable[[], str]:
    def _provider() -> str:
        import msal

        app = msal.ConfidentialClientApplication(
            client_id,
            authority=f"https://login.microsoftonline.com/{tenant_id}",
            client_credential=client_secret,
        )
        result = app.acquire_token_for_client(scopes=[scope])
        if "access_token" not in result:
            raise RuntimeError(
                f"Token acquisition failed: {result.get('error_description', result)}"
            )
        return result["access_token"]

    return _provider
