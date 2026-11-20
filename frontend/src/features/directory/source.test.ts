import { fetchFromWebsite, parseExportFile, WebsiteUnreachable } from "./source";

const route = (url: string) => new URL(url).searchParams.get("rest_route");

function reply(body: unknown, status = 200) {
  return Promise.resolve(new Response(JSON.stringify(body), { status }));
}

describe("lectura de la web del centro", () => {
  it("recorre todas las páginas hasta la última", async () => {
    const pageOf = (n: number, size: number) =>
      Array.from({ length: size }, (_, i) => ({ id: n * 1000 + i }));
    const calls: string[] = [];
    const fetcher = ((url: string) => {
      calls.push(url);
      if (route(url) !== "/wp/v2/posts") return reply([]);
      const page = Number(new URL(url).searchParams.get("page"));
      return reply(pageOf(page, page === 1 ? 100 : 37));
    }) as unknown as typeof fetch;
    const progress: number[] = [];
    const data = await fetchFromWebsite((n) => progress.push(n), fetcher);
    expect(data.posts).toHaveLength(137);
    expect(progress).toEqual([100, 137]);
    expect(calls.filter((c) => route(c) === "/wp/v2/posts")).toHaveLength(2);
    expect(calls[0]).toContain("rest_route=%2Fwp%2Fv2%2Fcategories");
  });

  it("para cuando WordPress dice que no hay más páginas", async () => {
    const fetcher = ((url: string) => {
      const page = Number(new URL(url).searchParams.get("page"));
      if (route(url) === "/wp/v2/posts")
        return page === 1 ? reply(Array(100).fill({ id: 1 })) : reply({}, 400);
      return reply([]);
    }) as unknown as typeof fetch;
    expect((await fetchFromWebsite(undefined, fetcher)).posts).toHaveLength(100);
  });

  it("ofrece el plan B si la web no responde", async () => {
    const fetcher = (() =>
      Promise.reject(new TypeError("Failed to fetch"))) as unknown as typeof fetch;
    await expect(fetchFromWebsite(undefined, fetcher)).rejects.toBeInstanceOf(WebsiteUnreachable);
  });

  it("avisa si la web responde con error", async () => {
    const fetcher = (() => reply({}, 503)) as unknown as typeof fetch;
    await expect(fetchFromWebsite(undefined, fetcher)).rejects.toThrow("503");
  });

  it("valida el archivo importado", () => {
    expect(parseExportFile('{"posts": []}')).toEqual({ posts: [], categories: [], tags: [] });
    expect(() => parseExportFile('{"otra": 1}')).toThrow("no es una exportación");
  });
});
