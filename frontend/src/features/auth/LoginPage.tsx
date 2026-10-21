import { useState, type FormEvent } from "react";
import { Navigate, useNavigate, useSearchParams } from "react-router";
import { HeartPulse } from "lucide-react";
import { useLogin, useMe } from "@/api/hooks";
import { Button } from "@/components/ui/Button";
import { fieldClass } from "@/components/ui/Sheet";

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
    <main className="flex min-h-dvh items-center justify-center bg-surface-2 px-4">
      <form onSubmit={submit} className="w-full max-w-sm rounded-2xl bg-surface p-8 shadow-pop">
        <div className="mb-8">
          <div className="mb-5 flex size-11 items-center justify-center rounded-xl bg-ink text-white shadow-card">
            <HeartPulse className="size-5" aria-hidden />
          </div>
          <h1 className="text-xl font-semibold">Atención al Paciente</h1>
          <p className="mt-1 text-sm text-ink-3">
            Centro Médico San Bernardino · Ingrese con su cuenta
          </p>
        </div>

        <label className="mb-1.5 block text-sm font-medium" htmlFor="email">
          Correo
        </label>
        <input
          id="email"
          type="email"
          autoComplete="username"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className={`mb-4 ${fieldClass}`}
        />
        <label className="mb-1.5 block text-sm font-medium" htmlFor="password">
          Contraseña
        </label>
        <input
          id="password"
          type="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className={`mb-4 ${fieldClass}`}
        />
        {login.error && (
          <p role="alert" className="mb-4 rounded-lg bg-danger-soft px-3 py-2 text-sm text-danger">
            {login.error.message}
          </p>
        )}
        <Button type="submit" variant="primary" className="mt-2 w-full" disabled={login.isPending}>
          {login.isPending ? "Entrando…" : "Entrar"}
        </Button>
      </form>
    </main>
  );
}
