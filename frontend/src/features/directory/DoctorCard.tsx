import { Clock, ExternalLink, Mail, MapPin, Phone, Smartphone } from "lucide-react";
import { useState } from "react";
import type { DirectoryDoctor } from "@/api/types";
import { Pill } from "@/components/ui/Pill";

/** La ubicación va primero y en grande: es lo que se pregunta en la sala. */
function Location({ office }: { office: DirectoryDoctor["offices"][number] }) {
  if (!office.building && !office.office) {
    return <p className="rounded-2xl bg-surface-3 px-4 py-3 text-sm text-ink-2">{office.text}</p>;
  }
  return (
    <div className="flex items-center gap-3 rounded-2xl bg-ink px-4 py-3 text-white">
      <MapPin className="size-5 shrink-0 text-white/70" aria-hidden />
      <div className="min-w-0">
        <div className="text-sm text-white/70">{office.building ?? "Edificio sin indicar"}</div>
        <div className="text-xl leading-tight font-bold">
          {office.floor && `Piso ${office.floor}`}
          {office.floor && office.office && " · "}
          {office.office && `Consultorio ${office.office}`}
        </div>
      </div>
    </div>
  );
}

export function DoctorCard({ doctor }: { doctor: DirectoryDoctor }) {
  const [original, setOriginal] = useState(false);
  const review = doctor.review_notes.length > 0;
  return (
    <article className="flex flex-col gap-3 rounded-3xl bg-surface p-5 shadow-card">
      <div>
        <div className="flex flex-wrap items-start justify-between gap-2">
          <h2 className="text-lg leading-snug font-semibold">{doctor.display_name}</h2>
          {review && <Pill tone="warn">Revisar datos</Pill>}
        </div>
        <p className="mt-0.5 text-sm text-ink-3">
          {doctor.specialties.join(" · ") || doctor.specialty_text || "Especialidad sin indicar"}
        </p>
      </div>

      {doctor.offices.length > 0 ? (
        doctor.offices.map((o, i) => <Location key={i} office={o} />)
      ) : (
        <p className="rounded-2xl bg-warn-soft px-4 py-3 text-sm text-warn">
          La web no indica dónde queda el consultorio.
        </p>
      )}

      {(doctor.schedule.length > 0 || doctor.by_appointment) && (
        <div className="flex gap-2 text-sm text-ink-2">
          <Clock className="mt-0.5 size-4 shrink-0 text-ink-3" aria-hidden />
          <div>
            {doctor.schedule.map((line) => (
              <div key={line}>{line}</div>
            ))}
            {doctor.by_appointment && <div className="font-medium text-ink">Previa cita</div>}
          </div>
        </div>
      )}

      {(doctor.phones.length > 0 || doctor.emails.length > 0) && (
        <div className="flex flex-wrap gap-2">
          {doctor.phones.map((p) => (
            <a
              key={p.number + p.label}
              href={`tel:${p.number}`}
              className="inline-flex min-h-11 items-center gap-1.5 rounded-full bg-surface-3 px-4 text-sm font-medium text-ink-2 transition hover:bg-ink hover:text-white"
            >
              {p.mobile ? (
                <Smartphone className="size-4" aria-hidden />
              ) : (
                <Phone className="size-4" aria-hidden />
              )}
              {p.display}
              <span className="text-xs font-normal opacity-70">{p.label}</span>
            </a>
          ))}
          {doctor.emails.map((email) => (
            <a
              key={email}
              href={`mailto:${email}`}
              className="inline-flex min-h-11 max-w-full items-center gap-1.5 rounded-full bg-surface-3 px-4 text-sm font-medium text-ink-2 transition hover:bg-ink hover:text-white"
            >
              <Mail className="size-4 shrink-0" aria-hidden />
              <span className="truncate">{email}</span>
            </a>
          ))}
        </div>
      )}

      <div className="mt-auto flex flex-wrap items-center gap-3 border-t border-line pt-3 text-xs">
        <button
          type="button"
          onClick={() => setOriginal((v) => !v)}
          className="h-9 rounded-full px-3 font-medium text-ink-2 transition hover:bg-surface-3"
          aria-expanded={original}
        >
          {original ? "Ocultar la ficha original" : "Ver la ficha original"}
        </button>
        {doctor.source_url && (
          <a
            href={doctor.source_url}
            target="_blank"
            rel="noreferrer"
            className="inline-flex h-9 items-center gap-1 rounded-full px-3 font-medium text-ink-2 transition hover:bg-surface-3"
          >
            En la web <ExternalLink className="size-3" aria-hidden />
          </a>
        )}
      </div>
      {original && (
        <div className="rounded-2xl bg-surface-2 p-3 text-sm text-ink-2">
          {review && (
            <ul className="mb-2 space-y-0.5 text-warn">
              {doctor.review_notes.map((n) => (
                <li key={n}>{n}</li>
              ))}
            </ul>
          )}
          {doctor.raw_lines.map((line, i) => (
            <div key={i}>{line}</div>
          ))}
        </div>
      )}
    </article>
  );
}
