#!/usr/bin/env bash
# =============================================================================
# HDM — hdm-observability
# install_observability.sh — Instala nginx + console en Ubuntu 24.04
# Uso: sudo bash install_observability.sh
# IMPORTANTE: Editar nginx/hdm-observability.conf con la IP de VM2 antes de instalar
# =============================================================================
set -euo pipefail

WEB_DIR="/var/www/hdm-observability"

echo "=== HDM Observability Console — Instalación ==="

apt-get update -qq
apt-get install -y nginx

mkdir -p "$WEB_DIR"
cp -r html/* "$WEB_DIR/"
chown -R www-data:www-data "$WEB_DIR"

cp nginx/hdm-observability.conf /etc/nginx/sites-available/hdm-observability
ln -sf /etc/nginx/sites-available/hdm-observability /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

nginx -t && systemctl reload nginx
systemctl enable nginx

echo "=== Observability Console lista en http://0.0.0.0:8082 ==="
