#!/usr/bin/env bash
# Regenera docs/media/demo.gif y las capturas del README.
#
#   docker compose -f docker-compose.demo.yml up -d --build   # antes de correr esto
#   ./scripts/record-demo/record.sh
#
# Variables: WIDTH (ancho del gif, 900), FPS (10), DEMO_URL (http://localhost:8080)
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
WIDTH=${WIDTH:-900}
FPS=${FPS:-10}

cd "$HERE"
[ -d node_modules ] || { npm install; npx playwright install chromium; }

echo "==> reseteando datos de demo"
docker compose -f "$REPO/docker-compose.demo.yml" exec -T api \
  python -m app.scripts.seed_demo --reset

echo "==> grabando"
node record.mjs

echo "==> convirtiendo a gif (${WIDTH}px, ${FPS}fps)"
ffmpeg -y -loglevel error -i out/demo.webm \
  -vf "fps=${FPS},scale=${WIDTH}:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=96:stats_mode=diff[p];[s1][p]paletteuse=dither=bayer:bayer_scale=4" \
  -loop 0 out/demo.gif

echo "==> copiando a docs/media"
cp out/demo.gif "$REPO/docs/media/demo.gif"
for pair in "08-feed-transacciones:transacciones" "09-presupuestos:presupuestos" \
            "10-errores-parseo:errores" "05-detalle-transaccion:detalle"; do
  ffmpeg -y -loglevel error -i "out/shots/${pair%%:*}.png" \
    -vf "scale=1240:-1:flags=lanczos" "$REPO/docs/media/${pair##*:}.png"
done
ffmpeg -y -loglevel error -i out/shots/13-mobile.png \
  -vf "scale=420:-1:flags=lanczos" "$REPO/docs/media/mobile.png"

echo "==> tarjeta social (1280x640)"
node social.mjs
ffmpeg -y -loglevel error -i out/social.png \
  -vf "scale=1280:640:flags=lanczos" "$REPO/docs/media/social-preview.png"

ls -lh "$REPO/docs/media"
