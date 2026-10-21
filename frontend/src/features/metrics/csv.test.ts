import { toCsv } from "./csv";

describe("toCsv", () => {
  it("usa punto y coma, coma decimal y escapa comillas", () => {
    const csv = toCsv(
      ["Área", "Valor"],
      [
        ['Lab; sede "A"', 4.25],
        ["Imagen", null],
      ],
    );
    expect(csv).toBe('﻿Área;Valor\r\n"Lab; sede ""A""";4,25\r\nImagen;');
  });
});
