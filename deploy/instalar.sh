#!/usr/bin/env bash
# Instala o actualiza la demo en un servidor Ubuntu con systemd (ejecutar como root).
# Es idempotente: se puede volver a correr para desplegar una versión nueva.
# La configuración de Caddy NO se toca acá: ver deploy/DESPLIEGUE.md.
set -euo pipefail

REPO="https://github.com/Facabore/practica-hsf-segundo-corte.git"
DIR="/opt/practica-hsf"

python3 -c "import ensurepip" 2>/dev/null || { apt-get update -qq && apt-get install -y -qq python3-venv; }
id hsf >/dev/null 2>&1 || useradd --system --home-dir "$DIR" --shell /usr/sbin/nologin hsf

if [ -d "$DIR/.git" ]; then
    git -C "$DIR" pull --ff-only
else
    git clone "$REPO" "$DIR"
fi

python3 -m venv "$DIR/.venv"
"$DIR/.venv/bin/pip" install --quiet --upgrade pip
"$DIR/.venv/bin/pip" install --quiet psutil

# El código queda de root (solo lectura para el servicio); solo data/ y logs/ son del servicio.
chown -R root:root "$DIR"
chown -R hsf:hsf "$DIR/data" "$DIR/logs"

install -m 644 "$DIR/deploy/practica-hsf.service" /etc/systemd/system/practica-hsf.service
install -m 644 "$DIR/deploy/logrotate-practica-hsf" /etc/logrotate.d/practica-hsf
systemctl daemon-reload
systemctl enable practica-hsf
systemctl restart practica-hsf
systemctl --no-pager --lines=5 status practica-hsf
