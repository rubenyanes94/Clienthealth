import { decimal, fraction, minutes, percent } from "./format";
import { rangeFor } from "./usePeriod";

describe("formato de indicadores", () => {
  it("minutos", () => {
    expect(minutes(null)).toBe("—");
    expect(minutes(0.4)).toBe("< 1 min");
    expect(minutes(14.6)).toBe("15 min");
    expect(minutes(80)).toBe("1 h 20 min");
    expect(minutes(120)).toBe("2 h");
  });

  it("porcentajes y fracciones", () => {
    expect(percent(null)).toBe("—");
    expect(percent(0.5)).toBe("50 %");
    expect(fraction({ numerator: 2, denominator: 4 })).toBe("2 de 4");
    expect(fraction({ numerator: 0, denominator: 0 })).toBe("sin datos");
    expect(decimal(4.25, 2)).toBe("4,25");
  });

  it("períodos en hora de Caracas", () => {
    // 02:00 UTC del 21 = 22:00 del 20 en Caracas
    const now = new Date("2026-10-21T02:00:00Z");
    expect(rangeFor("today", now)).toEqual({ from: "2026-10-20", to: "2026-10-20" });
    expect(rangeFor("7d", now)).toEqual({ from: "2026-10-14", to: "2026-10-20" });
    expect(rangeFor("month", now)).toEqual({ from: "2026-10-01", to: "2026-10-20" });
  });
});
