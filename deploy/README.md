# systemd timer para sync horario

Estos archivos automatizan el `app.scripts.run_sync` en la droplet, sin
depender de cron ni de tener nada corriendo dentro del contenedor.

## Instalación (en la droplet, una vez)

```bash
ssh root@finanzas.ian1.cl

# Copiar las units a systemd
cp /opt/finanzas/deploy/finanzas-sync.service /etc/systemd/system/
cp /opt/finanzas/deploy/finanzas-sync.timer   /etc/systemd/system/

# Recargar systemd, habilitar y arrancar el timer
systemctl daemon-reload
systemctl enable --now finanzas-sync.timer

# Verificar
systemctl status finanzas-sync.timer
systemctl list-timers finanzas-sync.timer
```

## Comprobar que funciona

Disparar manualmente para confirmar que la unit corre:

```bash
systemctl start finanzas-sync.service
journalctl -u finanzas-sync.service -n 50 --no-pager
```

Debería verse algo como:
```
[ok] Run #42: fetched=3 parsed=1 skipped=2 errors=0 dup=0
```

## Cambiar la frecuencia

Editar `/etc/systemd/system/finanzas-sync.timer`, modificar `OnUnitActiveSec=`, y:

```bash
systemctl daemon-reload
systemctl restart finanzas-sync.timer
```

Valores típicos:
- `5min` para casi-tiempo-real
- `15min` balance razonable
- `1h` valor por defecto, suficiente para uso normal

## Logs históricos

```bash
# Ejecuciones recientes
journalctl -u finanzas-sync.service -n 100

# Solo desde el último boot
journalctl -u finanzas-sync.service -b
```

Los runs también quedan en la tabla `sync_runs` de la DB y se pueden ver desde
la UI en `/sync`.

## Desactivar temporalmente

```bash
systemctl stop finanzas-sync.timer        # parar (vuelve al reiniciar)
systemctl disable finanzas-sync.timer     # parar y no arrancar al boot
```
