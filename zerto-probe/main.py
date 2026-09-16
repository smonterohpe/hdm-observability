"""
zerto-probe para HDM — Hospital Discharge Manager
Corre en el puerto 5003 (FBS usa el 5002 en la misma VM).
"""
import time

from fastapi import FastAPI

from aggregator import build_site_payload
from config import get_settings
from zerto_client import ZertoClient

app = FastAPI(title="zerto-probe-hdm")
settings = get_settings()

origin_client = ZertoClient(
    host=settings.origin_zvma_host,
    username=settings.origin_zvma_username,
    password=settings.origin_zvma_password,
    client_id=settings.keycloak_client_id,
    verify_ssl=settings.verify_ssl,
)

destination_client = ZertoClient(
    host=settings.destination_zvma_host,
    username=settings.destination_zvma_username,
    password=settings.destination_zvma_password,
    client_id=settings.keycloak_client_id,
    verify_ssl=settings.verify_ssl,
)

_cache: dict = {"data": None, "fetched_at": 0.0}


@app.get("/zerto/data")
async def zerto_data() -> dict:
    now = time.monotonic()
    if _cache["data"] is not None and (now - _cache["fetched_at"]) < settings.cache_ttl_seconds:
        return _cache["data"]

    origin_payload      = await build_site_payload(origin_client,      settings.origin_zvma_label)
    destination_payload = await build_site_payload(destination_client,  settings.destination_zvma_label)

    data = {
        "remote": origin_payload,
        "local":  destination_payload,
        "fetched_at": time.time(),
    }
    _cache["data"] = data
    _cache["fetched_at"] = now
    return data


@app.get("/zerto/health")
async def zerto_health() -> dict:
    results = {}
    for name, client in (("origin", origin_client), ("destination", destination_client)):
        try:
            await client.get_local_site()
            results[name] = "ok"
        except Exception as exc:
            results[name] = f"error: {exc}"
    return results


@app.on_event("shutdown")
async def shutdown() -> None:
    await origin_client.aclose()
    await destination_client.aclose()
