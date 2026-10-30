import { displayPhone, formatElapsed, formatListTime, patientPhone, timeAgo } from "./format";

describe("format", () => {
  it("formatea teléfonos venezolanos", () => {
    expect(displayPhone("584141234567")).toBe("+58 414 123 4567");
    expect(displayPhone("15551234567")).toBe("+15551234567");
  });

  it("formatea el tiempo de espera", () => {
    const start = "2026-10-20T12:00:00Z";
    const t = new Date(start).getTime();
    expect(formatElapsed(start, t + 65_000)).toBe("1:05");
    expect(formatElapsed(start, t + 2 * 3600_000 + 5 * 60_000)).toBe("2 h 05 min");
    expect(formatElapsed(start, t - 1000)).toBe("0:00");
    expect(formatElapsed(start, t + (11 * 24 + 3) * 3600_000)).toBe("11 d 3 h");
  });

  it("usa la zona horaria de Caracas para decidir si es hoy", () => {
    // 03:00 UTC del 21 = 23:00 del 20 en Caracas
    const now = new Date("2026-10-21T03:30:00Z");
    expect(formatListTime("2026-10-21T03:00:00Z", now)).toMatch(/11:00/);
  });
});

describe("patientPhone", () => {
  it("muestra el número venezolano sin código de país", () => {
    expect(patientPhone("584141234567")).toBe("4141234567");
  });

  it("conserva el código de un número extranjero", () => {
    expect(patientPhone("573001234567")).toBe("+573001234567");
  });
});

describe("timeAgo", () => {
  const now = new Date("2026-10-30T15:00:00Z").getTime();
  it.each([
    ["2026-10-30T14:59:40Z", "ahora"],
    ["2026-10-30T14:55:00Z", "hace 5 min"],
    ["2026-10-30T12:30:00Z", "hace 2 h"],
  ])("%s", (iso, expected) => {
    expect(timeAgo(iso, now)).toBe(expected);
  });
});
