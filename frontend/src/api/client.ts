import createClient, { type Middleware } from "openapi-fetch";
import type { paths } from "./schema";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

const redirectOn401: Middleware = {
  onResponse({ response, request }) {
    const isSessionCheck = new URL(request.url).pathname === "/api/auth/me";
    if (response.status === 401 && !isSessionCheck && window.location.pathname !== "/login") {
      window.location.assign(`/login?next=${encodeURIComponent(window.location.pathname)}`);
    }
    return response;
  },
};

// Rutas relativas: mismo dominio en producción y proxy de Vite en desarrollo.
export const api = createClient<paths>({ baseUrl: window.location.origin, credentials: "include" });
api.use(redirectOn401);

type Result<T> = { data?: T; error?: unknown; response: Response };

function messageOf(error: unknown): string {
  if (error && typeof error === "object" && "detail" in error) {
    const detail = (error as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) return "Revise los datos del formulario";
  }
  return "Ocurrió un error. Intente de nuevo.";
}

/** Devuelve los datos o lanza ApiError con el mensaje del backend. */
export async function unwrap<T>(promise: Promise<Result<T>>): Promise<T> {
  const { data, error, response } = await promise;
  if (!response.ok) throw new ApiError(response.status, messageOf(error));
  return data as T;
}
