import { api } from "@/api/client";

type Query = { from: string; to: string; area_id?: number };

/** Pide el informe PDF del período y lo descarga con un nombre que dice qué período cubre. */
export async function downloadReportPdf(query: Query): Promise<void> {
  const { data, response } = await api.GET("/api/reports/indicators.pdf", {
    params: { query },
    parseAs: "blob",
  });
  if (!response.ok || !data) {
    throw new Error(
      response.status === 403
        ? "Su cuenta no puede generar informes."
        : "No se pudo generar el informe. Intente de nuevo.",
    );
  }
  const url = URL.createObjectURL(data as Blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `informe-atencion_${query.from}_${query.to}.pdf`;
  link.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}
