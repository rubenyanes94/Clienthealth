import { EMPTY_PATIENT, splitName, validatePatient } from "./form";

const valid = {
  first_name: "María",
  last_name: "Pérez",
  national_id: "V-12.345.678",
  phone: "0414-1234567",
  email: "maria@example.com",
};

describe("validatePatient", () => {
  it("exige los cinco datos", () => {
    expect(Object.keys(validatePatient(EMPTY_PATIENT)).sort()).toEqual([
      "email",
      "first_name",
      "last_name",
      "national_id",
      "phone",
    ]);
  });

  it("acepta un paciente completo", () => {
    expect(validatePatient(valid)).toEqual({});
  });

  it.each(["4141234567", "0414-1234567", "+58 414 123 4567", "+57 300 123 4567"])(
    "acepta el teléfono %s",
    (phone) => {
      expect(validatePatient({ ...valid, phone }).phone).toBeUndefined();
    },
  );

  it.each(["0414567890", "414123456", "58414123456"])("rechaza el teléfono %s", (phone) => {
    expect(validatePatient({ ...valid, phone }).phone).toBeDefined();
  });

  it("rechaza correo, cédula y teléfono mal escritos", () => {
    const errors = validatePatient({ ...valid, email: "x@", national_id: "12", phone: "123" });
    expect(Object.keys(errors).sort()).toEqual(["email", "national_id", "phone"]);
  });
});

describe("splitName", () => {
  it.each([
    [null, "", ""],
    ["María", "María", ""],
    ["María Pérez", "María", "Pérez"],
    ["María José Pérez", "María", "José Pérez"],
    ["María José Pérez Gómez", "María José", "Pérez Gómez"],
  ])("%s", (name, first, last) => {
    expect(splitName(name)).toEqual({ first_name: first, last_name: last });
  });
});
