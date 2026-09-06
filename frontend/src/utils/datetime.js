/**
 * La API devuelve datetimes naive (Postgres guarda UTC sin offset), así que
 * `new Date("2026-09-06T23:28:00")` los interpreta como hora local y corre
 * todos los "hace N minutos" tantas horas como el offset del browser — en
 * Chile eso da diferencias negativas ("hace -3 h"). Marcamos el string como
 * UTC antes de parsear.
 */
export function parseApiDate(value) {
  if (!value) return null;
  const hasTimezone = /(Z|[+-]\d{2}:?\d{2})$/.test(value);
  return new Date(hasTimezone ? value : `${value}Z`);
}
