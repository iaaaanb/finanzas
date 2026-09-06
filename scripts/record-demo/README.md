# record-demo

Regenera `docs/media/demo.gif` y las capturas del README manejando el stack de
demo con Playwright. No hay que grabar la pantalla a mano: el script maneja un
Chromium, dibuja un cursor sintético y graba video, que después ffmpeg pasa a
GIF.

## Uso

```bash
docker compose -f docker-compose.demo.yml up -d --build
./scripts/record-demo/record.sh
```

La primera corrida instala Playwright y su Chromium (~150 MB). Requiere
`ffmpeg` en el PATH.

Variables: `WIDTH` (ancho del GIF, default 900), `FPS` (10),
`DEMO_URL` (http://localhost:8080).

## Qué graba

`record.mjs` sigue este recorrido, que es también el resumen de la app:
portada con pendientes → sincronizar → volver a pendientes → abrir una
transacción → ver el email del banco que la originó → confirmarla y ver el
saldo y el presupuesto moverse. Después, ya sin grabar, saca las capturas
sueltas para el README.

Cada corrida arranca con `seed_demo --reset`, así que el resultado es
reproducible: si una toma sale mal, se ajusta el script y se vuelve a correr.
