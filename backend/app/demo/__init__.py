"""Modo demo: datos de ejemplo + Gmail falso.

Existe para que cualquiera pueda levantar la app completa sin credenciales de
Gmail ni cuentas bancarias reales — incluido el botón "Sincronizar ahora", que
en demo lee de una casilla en memoria (`app.demo.inbox`) en vez de la API de
Google.

Se activa con la variable de entorno `DEMO_MODE=1` (ver `docker-compose.demo.yml`).
Nada de este paquete se importa cuando el flag está apagado.
"""
