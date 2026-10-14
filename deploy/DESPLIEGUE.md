# Despliegue en la nube

La demo está publicada en **https://integration-corte2.duckdns.org**, en un VPS Ubuntu 24.04 con Caddy como proxy inverso y HTTPS automático.

```
Internet ──HTTPS──▶ Caddy (:443, certificado automático)
                      │ reverse_proxy
                      ▼
          127.0.0.1:8090  python -m hsf_app.demo  (servicio systemd "practica-hsf")
                      │ un hilo + un socket por equipo
          127.0.0.1:8765 / 8766 / 8767  firmwares simulados SIM-001 / 002 / 003
```

## Decisiones

- **Controles abiertos, por decisión del dueño del servidor.** Los botones de cada equipo (encender, apagar, reiniciar y fallos) funcionan sin clave. Siguen activas las listas cerradas de comandos y equipos, la cabecera propia contra CSRF y el control de `Host`. "Saturar CPU" queda contenido por el techo de 1 CPU del servicio, para que no afecte a los demás sitios. Riesgo aceptado: un visitante puede apagar un equipo, y cualquiera puede volver a encenderlo. Para publicar sin controles, agregar `--solo-lectura` en `ExecStart` del servicio.
- **Todo escucha en `127.0.0.1`.** Solo Caddy queda expuesto. El dashboard acepta el dominio público con `--host-publico`, y cualquier otro `Host` sigue recibiendo 403.
- **Usuario de sistema `hsf` sin shell.** El código pertenece a root y es de solo lectura para el servicio. El servicio solo puede escribir en `data/` y `logs/` (`ProtectSystem=strict` + `ReadWritePaths`), y tiene un techo de 1 CPU y 400 MB porque el servidor es compartido.
- **Rotación diaria** de los CSV de la demo (7 días, comprimidos) con logrotate. `logs/demo.log` rota solo, a 1 MB × 3.
- **La hora de los eventos viaja en ISO UTC** y el navegador la muestra en la hora local de quien mira, aunque el servidor esté en Europe/Berlin.

## Instalar o actualizar

En el servidor, como root:

```bash
curl -fsSL https://raw.githubusercontent.com/Facabore/practica-hsf-segundo-corte/main/deploy/instalar.sh | bash
```

La primera vez hay que agregar además el bloque de `deploy/Caddyfile.snippet` al final de `/etc/caddy/Caddyfile`. Después: `caddy validate --config /etc/caddy/Caddyfile` y `systemctl reload caddy`, con `reload`, no `restart`, para no cortar los demás sitios.

## Operar

| Para… | Comando |
|---|---|
| Ver el estado | `systemctl status practica-hsf` |
| Ver los logs en vivo | `journalctl -u practica-hsf -f` |
| Reiniciar | `systemctl restart practica-hsf` |
| Detener | `systemctl stop practica-hsf` |
| Desplegar una versión nueva | volver a correr `instalar.sh` |
