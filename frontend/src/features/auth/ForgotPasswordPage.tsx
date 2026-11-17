import { useState } from "react";
import { Link } from "react-router";
import { useRequestReset } from "@/api/hooks";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { fieldClass } from "@/components/ui/Sheet";
import { AuthLayout } from "./AuthLayout";

/** «¿Olvidó su contraseña?». El mensaje final es el mismo exista o no la cuenta. */
export function ForgotPasswordPage() {
  const request = useRequestReset();
  const [email, setEmail] = useState("");

  if (request.isSuccess) {
    return (
      <AuthLayout title="Revise su correo" subtitle="Le enviamos las instrucciones.">
        <p className="rounded-2xl bg-surface-2 px-4 py-3 text-sm leading-relaxed text-ink-2">
          Si <strong>{email}</strong> corresponde a una cuenta activa, en unos minutos le llegará un
          enlace para crear una contraseña nueva. Vence en una hora y solo sirve una vez.
        </p>
        <p className="mt-3 text-sm text-ink-3">
          ¿No llega? Revise la carpeta de correo no deseado o pídale ayuda a un administrador.
        </p>
        <Link
          to="/login"
          className="mt-6 flex h-13 w-full items-center justify-center rounded-full bg-ink text-[15px] font-medium text-white shadow-card transition hover:bg-zinc-800"
        >
          Volver a entrar
        </Link>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout
      title="Recuperar el acceso"
      subtitle="Escriba el correo de su cuenta y le enviaremos un enlace."
      onSubmit={() => request.mutate(email.trim())}
    >
      <Field label="Correo" htmlFor="reset-email" required>
        <input
          id="reset-email"
          type="email"
          autoComplete="username"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className={fieldClass}
        />
      </Field>
      {request.error && (
        <p role="alert" className="mt-4 rounded-2xl bg-danger-soft px-4 py-3 text-sm text-danger">
          {request.error.message}
        </p>
      )}
      <Button
        type="submit"
        variant="primary"
        size="lg"
        className="mt-6 w-full"
        disabled={request.isPending || !email.trim()}
      >
        {request.isPending ? "Enviando…" : "Enviar enlace"}
      </Button>
      <Link
        to="/login"
        className="mt-4 flex h-11 items-center justify-center rounded-full text-sm font-medium text-ink-2 transition hover:bg-surface-3 hover:text-ink"
      >
        Volver a entrar
      </Link>
    </AuthLayout>
  );
}
