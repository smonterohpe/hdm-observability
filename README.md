# hdm-observability

**Hospital Discharge Manager (HDM)** · Observability Console  
nginx · HTML/JS · VM Ubuntu 24.04 · Puerto 8080

## Pestañas

| Pestaña | Contenido |
|---|---|
| 📊 KPIs | 6 KPIs en tiempo real + ocupación por planta (7 unidades) |
| 🖥 Systems | Estado de las 4 VMs + log de eventos del sistema |
| 🛡 Zerto | VPG status + Demo Engine (Failover Test / Human Error / Ransomware / Recovery) |
| ℹ About | Descripción del sistema, arquitectura, KPIs |

## Instalación

```bash
# 1. Editar la IP de VM2 en nginx/hdm-observability.conf
# 2. Instalar
sudo bash scripts/install_observability.sh
```

## Demo Engine

Los 4 botones de la pestaña Zerto llaman directamente a los endpoints del backend:

- `POST /api/demo/failover-test` → Pausa RBG + log evento
- `POST /api/demo/human-error` → Borra tabla discharges
- `POST /api/demo/ransomware` → Corrompe datos (Wario)
- `POST /api/demo/recovery` → Reanuda RBG + log recovery
