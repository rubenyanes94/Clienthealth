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
    <main className="relative flex min-h-dvh items-center justify-center overflow-hidden bg-canvas px-4">
      <div
        aria-hidden
        className="pointer-events-none absolute -top-40 -right-40 size-[32rem] rounded-full bg-[radial-gradient(circle_at_30%_30%,#ffffff,#d4d4d8_45%,#71717a_75%,#18181b)] opacity-20"
      />
      <div
        aria-hidden
        className="pointer-events-none absolute -bottom-32 -left-24 size-80 rounded-full border-[28px] border-surface-3"
      />
      <form
        onSubmit={submit}
        className="relative w-full max-w-md rounded-[2rem] bg-surface p-8 shadow-pop sm:p-10"
      >
        <div className="mb-8">
          <div className="mb-6 flex size-14 items-center justify-center rounded-full bg-ink text-white shadow-card">
            <HeartPulse className="size-6" aria-hidden />
          </div>
          <h1 className="text-3xl font-bold">Atención al Paciente</h1>
          <p className="mt-1.5 text-sm text-ink-3">
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
          <p role="alert" className="mb-4 rounded-2xl bg-danger-soft px-4 py-3 text-sm text-danger">
            {login.error.message}
          </p>
        )}
        <Button
          type="submit"
          variant="primary"
          size="lg"
          className="mt-2 w-full"
          disabled={login.isPending}
        >
          {login.isPending ? "Entrando…" : "Entrar"}
        </Button>
      </form>
    </main>
  );
}
