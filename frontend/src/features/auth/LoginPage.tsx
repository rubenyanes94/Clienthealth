import { useState } from "react";
import { Link, Navigate, useNavigate, useSearchParams } from "react-router";
import { useLogin, useMe } from "@/api/hooks";
import { Button } from "@/components/ui/Button";
import { fieldClass } from "@/components/ui/Sheet";
import { AuthLayout } from "./AuthLayout";

export function LoginPage() {
  const me = useMe();
  const login = useLogin();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const next = params.get("next")?.startsWith("/") ? params.get("next")! : "/casos";

  if (me.data) return <Navigate to={next} replace />;

  const submit = () => {
    login.mutate({ email, password }, { onSuccess: () => navigate(next, { replace: true }) });
  };

  return (
    <AuthLayout
      title="Atención al Paciente"
      subtitle="Centro Médico San Bernardino · Ingrese con su cuenta"
      onSubmit={submit}
    >
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
      <Link
        to="/recuperar"
        className="mt-4 flex h-11 items-center justify-center rounded-full text-sm font-medium text-ink-2 transition hover:bg-surface-3 hover:text-ink"
      >
        ¿Olvidó su contraseña?
      </Link>
    </AuthLayout>
  );
}
