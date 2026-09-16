#!/usr/bin/env bash
# =============================================================================
# HDM — zerto-probe
# install_zerto_probe.sh
# Instala el zerto-probe-hdm en VM4 (puerto 5003, coexiste con FBS en 5002)
# Uso: sudo bash install_zerto_probe.sh
# REQUISITO: rellenar .env con las credenciales reales de los ZVMA primero
# =============================================================================
set -euo pipefail

PROBE_DIR="/opt/zerto-probe-hdm"
SERVICE_USER="probe"

echo "=== HDM zerto-probe — Instalación ==="

# 1. Usuario de servicio (compartido con FBS si ya existe)
id -u $SERVICE_USER &>/dev/null || useradd -r -s /bin/false $SERVICE_USER

# 2. Copiar ficheros
mkdir -p "$PROBE_DIR"
cp zerto-probe/*.py        "$PROBE_DIR/"
cp zerto-probe/requirements.txt "$PROBE_DIR/"
cp zerto-probe/zerto-probe-hdm.service /etc/systemd/system/

# 3. .env — copiar si no existe aún
if [ ! -f "$PROBE_DIR/.env" ]; then
    cp zerto-probe/.env.example "$PROBE_DIR/.env"
    echo ""
    echo "⚠️  IMPORTANTE: edita $PROBE_DIR/.env con las credenciales reales de los ZVMA"
    echo "   nano $PROBE_DIR/.env"
    echo ""
fi

# 4. Virtualenv e instalación de dependencias
python3 -m venv "$PROBE_DIR/venv"
"$PROBE_DIR/venv/bin/pip" install --upgrade pip -q
"$PROBE_DIR/venv/bin/pip" install -r "$PROBE_DIR/requirements.txt" -q

chown -R $SERVICE_USER:$SERVICE_USER "$PROBE_DIR"

# 5. Systemd
systemctl daemon-reload
systemctl enable zerto-probe-hdm
systemctl start  zerto-probe-hdm

echo ""
echo "=== zerto-probe-hdm listo en http://127.0.0.1:5003 ==="
echo "    Verificar: curl http://localhost:5003/zerto/health"
