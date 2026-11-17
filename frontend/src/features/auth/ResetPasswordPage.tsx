import { useState } from "react";
import { Link, useNavigate } from "react-router";
import { useConfirmReset, useVerifyReset } from "@/api/hooks";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { fieldClass } from "@/components/ui/Sheet";
import { MIN_PASSWORD } from "../users/roles";
import { AuthLayout } from "./AuthLayout";

/**
 * Lee el enlace una sola vez y lo borra de la barra de direcciones: así no queda en el historial,
 * en capturas de pantalla ni en marcadores. Va después de `#` para que nunca llegue a ningún servidor.
 */
function takeToken(): string | null {
  const token = new URLSearchParams(window.location.hash.slice(1)).get("token");
  if (token) window.history.replaceState(null, "", window.location.pathname);
  return token;
}

export function ResetPasswordPage() {
  const navigate = useNavigate();
  const [token] = useState(takeToken);
  const check = useVerifyReset(token);
  const confirm = useConfirmReset();
  const [password, setPassword] = useState("");
  const [repeat, setRepeat] = useState("");

  if (!token || check.error) {
    return (
      <AuthLayout title="Enlace no válido" subtitle="No se puede usar este enlace.">
        <p className="rounded-2xl bg-danger-soft px-4 py-3 text-sm text-danger">
          {check.error?.message ?? "El enlace está incompleto. Ábralo de nuevo desde el correo."}
        </p>
        <p className="mt-3 text-sm text-ink-3">
          Los enlaces vencen y solo sirven una vez. Si ya creó su contraseña, simplemente entre.
        </p>
        <Link
          to="/recuperar"
          className="mt-6 flex h-13 w-full items-center justify-center rounded-full bg-ink text-[15px] font-medium text-white shadow-card transition hover:bg-zinc-800"
        >
          Pedir un enlace nuevo
        </Link>
        <Link
          to="/login"
          className="mt-3 flex h-11 items-center justify-center rounded-full text-sm font-medium text-ink-2 transition hover:bg-surface-3 hover:text-ink"
        >
          Ir a entrar
        </Link>
      </AuthLayout>
    );
  }

  if (!check.data) {
    return (
      <AuthLayout title="Un momento…" subtitle="Comprobando el enlace.">
        <span />
      </AuthLayout>
    );
  }

  const invite = check.data.purpose === "invite";
  const tooShort = password.length > 0 && password.length < MIN_PASSWORD;
  const mismatch = repeat.length > 0 && repeat !== password;
  const ready = password.length >= MIN_PASSWORD && password === repeat;

  return (
    <AuthLayout
      title={invite ? "Bienvenido" : "Nueva contraseña"}
      subtitle={
        invite
          ? `${check.data.name}, cree la contraseña de su cuenta para empezar.`
          : `${check.data.name}, escriba su nueva contraseña.`
      }
      onSubmit={() =>
        ready &&
        confirm.mutate(
          { token, new_password: password },
          { onSuccess: () => navigate("/casos", { replace: true }) },
        )
      }
    >
      <p className="mb-5 rounded-2xl bg-surface-2 px-4 py-3 text-sm text-ink-2">
        Usuario: <strong>{check.data.email}</strong>
      </p>
      <div className="space-y-4">
        <Field
          label="Contraseña"
          htmlFor="new-password"
          required
          error={tooShort ? `Mínimo ${MIN_PASSWORD} caracteres` : undefined}
        >
          <input
            id="new-password"
            type="password"
            autoComplete="new-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className={fieldClass}
          />
        </Field>
        <Field
          label="Repita la contraseña"
          htmlFor="repeat-password"
          required
          error={mismatch ? "No coincide" : undefined}
        >
          <input
            id="repeat-password"
            type="password"
            autoComplete="new-password"
            value={repeat}
            onChange={(e) => setRepeat(e.target.value)}
            className={fieldClass}
          />
        </Field>
      </div>
      <p className="mt-3 text-xs text-ink-3">
        Úsela solo usted: todo lo que se haga con su cuenta queda registrado a su nombre.
      </p>
      {confirm.error && (
        <p role="alert" className="mt-4 rounded-2xl bg-danger-soft px-4 py-3 text-sm text-danger">
          {confirm.error.message}
        </p>
      )}
      <Button
        type="submit"
        variant="primary"
        size="lg"
        className="mt-6 w-full"
        disabled={!ready || confirm.isPending}
      >
        {confirm.isPending
          ? "Guardando…"
          : invite
            ? "Crear contraseña y entrar"
            : "Guardar y entrar"}
      </Button>
    </AuthLayout>
  );
}
