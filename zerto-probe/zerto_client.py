"""
Cliente para la API REST de un ZVMA (Zerto Virtual Manager Appliance).

Basado en el flujo de autenticación real documentado por Zerto:
  - Auth por Keycloak con grant_type=password (NO el flujo implícito
    que anuncia el swagger, que es solo para la UI).
  - Certificado autofirmado -> verificación TLS deshabilitada por defecto.
  - Token de corta duración (~60-300s) -> se cachea y se refresca con
    30s de margen.

NOTA IMPORTANTE: los nombres exactos de los campos JSON que devuelve
`/v1/vpgs` pueden variar ligeramente entre versiones de Zerto. Este
cliente usa `.get()` con varios alias razonables y separa el "mapeo"
en `aggregator.py` para que sea fácil de ajustar contra tu instancia
real sin tocar la lógica de autenticación/HTTP.
"""
import time

import httpx

# Enums documentados de Zerto (numéricos en el swagger real)
VPG_STATUS_MAP = {
    0: "Protecting",
    1: "Moving",
    2: "Recovered",
    3: "Removing",
    4: "TestingFailover",
    5: "FailingOver",
    6: "MovingCommitting",
    7: "FailingOverCommitting",
    8: "NotMeetingSLA",
}

VPG_SUBSTATUS_MAP = {
    0: "None",
    1: "InitialSync",
    2: "BitmapSync",
    3: "DeltaSync",
    20: "JournalDisconnected",
}


class ZertoAuthError(Exception):
    pass


class ZertoClient:
    def __init__(self, host: str, username: str, password: str,
                 client_id: str = "zerto-client", verify_ssl: bool = False):
        self.host = host
        self.username = username
        self.password = password
        self.client_id = client_id
        self.base_url = f"https://{host}"
        self._token: str | None = None
        self._token_expires_at: float = 0.0
        self._http = httpx.AsyncClient(verify=verify_ssl, timeout=10.0)

    async def _ensure_token(self) -> None:
        if self._token and time.monotonic() < self._token_expires_at - 30:
            return

        token_url = f"{self.base_url}/auth/realms/zerto/protocol/openid-connect/token"
        data = {
            "grant_type": "password",
            "username": self.username,
            "password": self.password,
            "client_id": self.client_id,
            "scope": "openid",
        }
        try:
            response = await self._http.post(token_url, data=data)
        except httpx.HTTPError as exc:
            raise ZertoAuthError(f"No se pudo contactar con {self.host}: {exc}")

        if response.status_code != 200:
            raise ZertoAuthError(
                f"Fallo de autenticación contra {self.host} "
                f"(HTTP {response.status_code}): {response.text[:300]}"
            )

        payload = response.json()
        self._token = payload["access_token"]
        expires_in = payload.get("expires_in", 60)
        self._token_expires_at = time.monotonic() + expires_in

    async def _get(self, path: str) -> dict | list:
        await self._ensure_token()
        headers = {"Authorization": f"Bearer {self._token}"}
        response = await self._http.get(f"{self.base_url}{path}", headers=headers)

        if response.status_code == 401:
            self._token = None
            await self._ensure_token()
            headers = {"Authorization": f"Bearer {self._token}"}
            response = await self._http.get(f"{self.base_url}{path}", headers=headers)

        response.raise_for_status()
        return response.json()

    async def get_local_site(self) -> dict:
        return await self._get("/v1/localsite")

    async def get_vpgs(self) -> list:
        result = await self._get("/v1/vpgs")
        return result if isinstance(result, list) else result.get("value", [])

    async def get_vpg_vms(self, vpg_identifier: str) -> list:
        try:
            result = await self._get(f"/v1/vpgs/{vpg_identifier}/vms")
            return result if isinstance(result, list) else result.get("value", [])
        except httpx.HTTPStatusError:
            return []

    async def get_alerts(self) -> list:
        try:
            result = await self._get("/v1/alerts")
            return result if isinstance(result, list) else result.get("value", [])
        except httpx.HTTPStatusError:
            return []

    async def get_events(self) -> list:
        try:
            result = await self._get("/v1/events")
            return result if isinstance(result, list) else result.get("value", [])
        except httpx.HTTPStatusError:
            return []

    async def aclose(self) -> None:
        await self._http.aclose()


def describe_status(status) -> str:
    if isinstance(status, int):
        return VPG_STATUS_MAP.get(status, f"Unknown({status})")
    return str(status)


def describe_substatus(substatus) -> str:
    if isinstance(substatus, int):
        return VPG_SUBSTATUS_MAP.get(substatus, f"Unknown({substatus})")
    return str(substatus)
