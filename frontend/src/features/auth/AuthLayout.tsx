import { HeartPulse } from "lucide-react";
import type { FormEvent, ReactNode } from "react";

/** Marco de las pantallas sin sesión: entrar, recuperar y crear la contraseña. */
export function AuthLayout({
  title,
  subtitle,
  onSubmit,
  children,
}: {
  title: string;
  subtitle: ReactNode;
  onSubmit?: (event: FormEvent) => void;
  children: ReactNode;
}) {
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
        onSubmit={(event) => {
          event.preventDefault();
          onSubmit?.(event);
        }}
        className="relative w-full max-w-md rounded-[2rem] bg-surface p-8 shadow-pop sm:p-10"
      >
        <div className="mb-8">
          <div className="mb-6 flex size-14 items-center justify-center rounded-full bg-ink text-white shadow-card">
            <HeartPulse className="size-6" aria-hidden />
          </div>
          <h1 className="text-3xl font-bold">{title}</h1>
          <p className="mt-1.5 text-sm text-ink-3">{subtitle}</p>
        </div>
        {children}
      </form>
    </main>
  );
}
