export function minutes(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  if (value < 1) return "< 1 min";
  if (value < 60) return `${Math.round(value)} min`;
  const h = Math.floor(value / 60);
  const m = Math.round(value % 60);
  return m ? `${h} h ${m} min` : `${h} h`;
}

export function percent(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return `${(value * 100).toLocaleString("es-VE", { maximumFractionDigits: 1 })} %`;
}

export function decimal(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined) return "—";
  return value.toLocaleString("es-VE", { maximumFractionDigits: digits, minimumFractionDigits: 0 });
}

export function fraction(r: { numerator: number; denominator: number }): string {
  return r.denominator ? `${r.numerator} de ${r.denominator}` : "sin datos";
}
