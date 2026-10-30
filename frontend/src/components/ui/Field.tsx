import type { ReactNode } from "react";

/** Etiqueta, control y mensaje de error. Un campo obligatorio vacío se marca al intentar guardar. */
export function Field({
  label,
  htmlFor,
  required = false,
  error,
  children,
}: {
  label: string;
  htmlFor: string;
  required?: boolean;
  error?: string;
  children: ReactNode;
}) {
  return (
    <div>
      <label className="mb-1.5 block text-sm font-medium" htmlFor={htmlFor}>
        {required && (
          <span className="text-danger" aria-hidden>
            *{" "}
          </span>
        )}
        {label}
      </label>
      {children}
      {error && (
        <p role="alert" className="mt-1.5 text-sm text-danger">
          {error}
        </p>
      )}
    </div>
  );
}

export const invalidFieldClass = "bg-danger-soft! ring-danger/50! focus:ring-danger!";
