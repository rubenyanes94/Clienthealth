import type { DirectoryDoctor } from "@/api/types";
import { buildingsOf, fold, matches, specialtiesOf } from "./search";

function doctor(overrides: Partial<DirectoryDoctor> = {}): DirectoryDoctor {
  return {
    id: 1,
    name: "Prueba Uno, Ana",
    display_name: "Ana Prueba Uno",
    specialties: ["Cardiología"],
    specialty_text: "Cardiología",
    offices: [{ building: "Anexo B", floor: "5", office: "5B", text: "" }],
    schedule: [],
    by_appointment: true,
    phones: [],
    emails: [],
    raw_lines: [],
    review_notes: [],
    source_url: "",
    search_text: "prueba uno, ana ana prueba uno cardiologia anexo b piso 5 consultorio 5b",
    ...overrides,
  };
}

describe("búsqueda del directorio", () => {
  it("ignora tildes y mayúsculas", () => {
    expect(fold("Cardiología ÁLVAREZ")).toBe("cardiologia alvarez");
    expect(matches(doctor(), "CARDIOLOGÍA")).toBe(true);
  });

  it("exige todas las palabras", () => {
    expect(matches(doctor(), "ana 5b")).toBe(true);
    expect(matches(doctor(), "ana pediatria")).toBe(false);
    expect(matches(doctor(), "   ")).toBe(true);
  });

  it("lista edificios y especialidades sin repetir", () => {
    const list = [
      doctor(),
      doctor({
        id: 2,
        specialties: ["Cardiología", "Neurología"],
        offices: [{ building: "Anexo A", floor: "2", office: "275", text: "" }],
      }),
    ];
    expect(buildingsOf(list)).toEqual(["Anexo A", "Anexo B"]);
    expect(specialtiesOf(list)).toEqual([
      { name: "Cardiología", count: 2 },
      { name: "Neurología", count: 1 },
    ]);
  });
});
