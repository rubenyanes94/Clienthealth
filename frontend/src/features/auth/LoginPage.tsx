import { useState, type FormEvent } from "react";
import { Navigate, useNavigate, useSearchParams } from "react-router";
import { HeartPulse } from "lucide-react";
import { useLogin, useMe } from "@/api/hooks";
import { Button } from "@/components/ui/Button";

export function LoginPage() {
  const me = useMe();
  const login = useLogin();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const next = params.get("next")?.startsWith("/") ? params.get("next")! : "/conversaciones";

  if (me.data) return <Navigate to={next} replace />;

  const submit = (event: FormEvent) => {
    event.preventDefault();
    login.mutate({ email, password }, { onSuccess: () => navigate(next, { replace: true }) });
  };

  return (
    <main className="flex min-h-dvh items-center justify-center px-4">
      <form
        onSubmit={submit}
        className="w-full max-w-sm rounded-card border border-line bg-surface p-6 shadow-card"
      >
        <div className="mb-6 flex items-center gap-3">
          <div className="flex size-10 items-center justify-center rounded-xl bg-brand text-brand-ink">
            <HeartPulse className="size-5" aria-hidden />
          </div>
          <div>
            <h1 className="text-base font-semibold leading-tight">Atención al Paciente</h1>
            <p className="text-sm text-ink-3">Centro Médico San Bernardino</p>
          </div>
        </div>

        <label className="mb-1 block text-sm font-medium" htmlFor="email">
          Correo
        </label>
        <input
          id="email"
          type="email"
          autoComplete="username"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="mb-4 h-10 w-full rounded-lg border border-line bg-surface-2 px-3 text-sm outline-none focus:border-brand"
        />
        <label className="mb-1 block text-sm font-medium" htmlFor="password">
          Contraseña
        </label>
        <input
          id="password"
          type="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="mb-4 h-10 w-full rounded-lg border border-line bg-surface-2 px-3 text-sm outline-none focus:border-brand"
        />
        {login.error && (
          <p role="alert" className="mb-4 rounded-lg bg-danger-soft px-3 py-2 text-sm text-danger">
            {login.error.message}
          </p>
        )}
        <Button type="submit" variant="primary" className="w-full" disabled={login.isPending}>
          {login.isPending ? "Entrando…" : "Entrar"}
        </Button>
      </form>
    </main>
  );
}
