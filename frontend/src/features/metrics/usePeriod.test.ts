import { rangeFor } from "./usePeriod";

describe("períodos", () => {
  const now = new Date("2026-11-25T15:00:00Z");

  it("este mes va del día 1 a hoy", () => {
    expect(rangeFor("month", now)).toEqual({ from: "2026-11-01", to: "2026-11-25" });
  });

  it("el mes anterior es el mes completo", () => {
    expect(rangeFor("prev_month", now)).toEqual({ from: "2026-10-01", to: "2026-10-31" });
    expect(rangeFor("prev_month", new Date("2026-03-10T15:00:00Z"))).toEqual({
      from: "2026-02-01",
      to: "2026-02-28",
    });
    expect(rangeFor("prev_month", new Date("2027-01-05T15:00:00Z"))).toEqual({
      from: "2026-12-01",
      to: "2026-12-31",
    });
  });
});
