"""
Transforma la respuesta cruda de la API de Zerto en la estructura que
pinta la pestaña "Zerto" de la Observability Console.
"""
from zerto_client import ZertoClient, describe_status, describe_substatus


def _first(d: dict, *keys, default=None):
    for key in keys:
        if key in d and d[key] is not None:
            return d[key]
    return default


def _extract_number(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, dict):
        for k in ("Value", "value", "Seconds", "seconds"):
            if k in value and value[k] is not None:
                try:
                    return int(value[k])
                except (TypeError, ValueError):
                    pass
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _seconds_to_human(seconds) -> str:
    seconds = _extract_number(seconds)
    if seconds is None:
        return "—"
    if seconds < 60:
        return f"{seconds}s"
    minutes, secs = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}m" + (f" {secs}s" if secs else "")
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes}m"


def _vpg_summary(vpg: dict) -> dict:
    status_raw = _first(vpg, "status", "Status")
    substatus_raw = _first(vpg, "subStatus", "SubStatus")
    status_label = describe_status(status_raw)
    is_meeting_sla = status_label not in ("NotMeetingSLA",)

    actual_rpo = _extract_number(_first(vpg, "actualRPO", "ActualRPO", "actualRpoSeconds"))
    configured_rpo = _extract_number(_first(vpg, "configuredRpoSeconds", "ConfiguredRpoSeconds", default=300)) or 300
    journal_history = _extract_number(_first(vpg, "journalHistoryInSeconds", "JournalHistory"))
    configured_journal = _extract_number(_first(vpg, "configuredJournalHistoryInSeconds", default=48 * 3600)) or 48 * 3600
    failsafe_history = _extract_number(_first(vpg, "failSafeHistoryInSeconds", "FailSafeHistory"))
    configured_failsafe = _extract_number(_first(vpg, "configuredFailSafeHistoryInSeconds", default=4 * 3600)) or 4 * 3600

    return {
        "vpg_identifier": _first(vpg, "vpgIdentifier", "VpgIdentifier", "id"),
        "name": _first(vpg, "vpgName", "VpgName", "name", default="VPG"),
        "status_label": status_label,
        "substatus_label": describe_substatus(substatus_raw) if substatus_raw is not None else None,
        "is_meeting_sla": is_meeting_sla,
        "source_site": _first(vpg, "sourceSiteName", "SourceSiteName"),
        "target_site": _first(vpg, "targetSiteName", "TargetSiteName"),
        "actual_rpo_seconds": actual_rpo,
        "actual_rpo_human": _seconds_to_human(actual_rpo),
        "configured_rpo_seconds": configured_rpo,
        "rpo_ratio_percent": round(min((actual_rpo or 0) / configured_rpo * 100, 100), 1) if configured_rpo else 0,
        "journal_history_human": _seconds_to_human(journal_history),
        "configured_journal_human": _seconds_to_human(configured_journal),
        "journal_ratio_percent": round(min((journal_history or 0) / configured_journal * 100, 100), 1) if configured_journal else 0,
        "failsafe_history_human": _seconds_to_human(failsafe_history),
        "configured_failsafe_human": _seconds_to_human(configured_failsafe),
        "failsafe_ratio_percent": round(min((failsafe_history or 0) / configured_failsafe * 100, 100), 1) if configured_failsafe else 0,
    }


def _vm_summary(vm: dict) -> dict:
    status_raw = _first(vm, "status", "Status")
    return {
        "name": _first(vm, "vmName", "VmName", "name", default="VM"),
        "status_label": describe_status(status_raw) if status_raw is not None else "—",
        "actual_rpo_human": _seconds_to_human(_first(vm, "actualRPO", "ActualRPO")),
        "iops": _first(vm, "iops", "IOPS", default=0),
        "journal_size_human": _first(vm, "journalUsedStorageHuman", "journalSizeHuman", default="—"),
    }


def _alert_summary(alert: dict) -> dict:
    return {
        "level": _first(alert, "level", "Level", default="Info"),
        "description": _first(alert, "description", "Description", default=""),
        "entity": _first(alert, "entity", "AffectedVpgs", default=""),
        "turned_on": _first(alert, "turnedOn", "TurnedOn"),
    }


def _event_summary(event: dict) -> dict:
    return {
        "time": _first(event, "eventTime", "TimeStamp", "time"),
        "site": _first(event, "siteName", "Site", default=""),
        "description": _first(event, "description", "Description", default=""),
        "user": _first(event, "userName", "User", default="system"),
    }


async def build_site_payload(client: ZertoClient, label: str) -> dict:
    try:
        vpgs_raw = await client.get_vpgs()
    except Exception as exc:
        return {
            "label": label,
            "reachable": False,
            "error": str(exc),
            "vpgs": [],
            "protected_vms": [],
            "active_alerts": [],
            "recent_events": [],
        }

    vpgs = [_vpg_summary(v) for v in vpgs_raw]

    protected_vms: list[dict] = []
    for raw_vpg in vpgs_raw:
        vpg_id = _first(raw_vpg, "vpgIdentifier", "VpgIdentifier", "id")
        if not vpg_id:
            continue
        vms_raw = await client.get_vpg_vms(vpg_id)
        protected_vms.extend(_vm_summary(vm) for vm in vms_raw)

    alerts_raw = await client.get_alerts()
    events_raw = await client.get_events()

    return {
        "label": label,
        "reachable": True,
        "error": None,
        "vpgs": vpgs,
        "protected_vms": protected_vms,
        "active_alerts": [_alert_summary(a) for a in alerts_raw],
        "recent_events": [_event_summary(e) for e in events_raw][:20],
    }
