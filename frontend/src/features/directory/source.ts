import type { WpExport, WpPost, WpTerm } from "@/api/types";

/** La web del centro. Solo responde desde Venezuela: la lee el navegador, nunca nuestro servidor. */
export const SOURCE_SITE = "https://www.centromedicodecaracas.com";
const PER_PAGE = 100;
/** Si la web no responde, la conexión se queda colgada en vez de fallar: se corta a los 20 s. */
export const REQUEST_TIMEOUT_MS = 20_000;

/** La web no respondió o el navegador no pudo leerla: conviene ofrecer el plan B. */
export class WebsiteUnreachable extends Error {}
const POST_FIELDS = "id,link,modified,title,content,categories,tags,class_list";

type Fetcher = typeof fetch;

async function collect<T>(
  route: string,
  fields: string,
  onProgress?: (count: number) => void,
  fetcher: Fetcher = fetch,
): Promise<T[]> {
  const out: T[] = [];
  for (let page = 1; page <= 100; page++) {
    const url = `${SOURCE_SITE}/?rest_route=${encodeURIComponent(route)}&per_page=${PER_PAGE}&page=${page}&_fields=${fields}`;
    let response: Response;
    try {
      response = await fetcher(url, {
        credentials: "omit",
        cache: "no-store",
        signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
      });
    } catch {
      // Red caída, web que no responde o permisos entre sitios: el navegador no da más detalle.
      throw new WebsiteUnreachable(
        "La web del centro no respondió desde este navegador. Use el plan B de abajo.",
      );
    }
    if (response.status === 400 && page > 1) break; // WordPress responde 400 después de la última
    if (!response.ok) throw new Error(`La web del centro respondió ${response.status}`);
    const batch = (await response.json()) as T[];
    out.push(...batch);
    onProgress?.(out.length);
    if (batch.length < PER_PAGE) break;
  }
  return out;
}

/** Trae todas las fichas, especialidades y letras desde la interfaz de datos de WordPress. */
export async function fetchFromWebsite(
  onProgress?: (count: number) => void,
  fetcher: Fetcher = fetch,
): Promise<WpExport> {
  const categories = await collect<WpTerm>("/wp/v2/categories", "id,name,slug", undefined, fetcher);
  const tags = await collect<WpTerm>("/wp/v2/tags", "id,name,slug", undefined, fetcher);
  const posts = await collect<WpPost>("/wp/v2/posts", POST_FIELDS, onProgress, fetcher);
  return { posts, categories, tags };
}

/** Lee un archivo descargado con el script y comprueba que tenga la forma esperada. */
export function parseExportFile(text: string): WpExport {
  const data = JSON.parse(text) as Partial<WpExport>;
  if (!data || !Array.isArray(data.posts)) {
    throw new Error("El archivo no es una exportación del directorio");
  }
  return { posts: data.posts, categories: data.categories ?? [], tags: data.tags ?? [] };
}

/**
 * Plan B: se pega en la consola del navegador (F12) estando en la web del centro. Como corre en
 * la propia web, no depende de permisos entre sitios. Descarga «directorio.json» para importarlo.
 */
export const EXPORT_SCRIPT = `(async () => {
  const get = async (route, fields) => {
    const out = [];
    for (let page = 1; page <= 100; page++) {
      const r = await fetch(location.origin + "/?rest_route=" + encodeURIComponent(route) +
        "&per_page=100&page=" + page + "&_fields=" + fields);
      if (r.status === 400 && page > 1) break;
      if (!r.ok) throw new Error("La web respondió " + r.status);
      const batch = await r.json();
      out.push(...batch);
      console.log(route, out.length);
      if (batch.length < 100) break;
    }
    return out;
  };
  const data = {
    categories: await get("/wp/v2/categories", "id,name,slug"),
    tags: await get("/wp/v2/tags", "id,name,slug"),
    posts: await get("/wp/v2/posts", "${POST_FIELDS}"),
  };
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([JSON.stringify(data)], { type: "application/json" }));
  a.download = "directorio.json";
  a.click();
  console.log("Listo:", data.posts.length, "entradas descargadas");
})();`;
