import { useCatalog, useMe } from "@/api/hooks";

/** Usuarios activos agrupados por área, para asignar tareas y casos a quien sea. */
export function PersonSelect({
  id,
  value,
  onChange,
  className,
}: {
  id: string;
  value: number | "";
  onChange: (value: number | "") => void;
  className?: string;
}) {
  const me = useMe();
  const catalog = useCatalog();
  const agents = catalog.data?.agents ?? [];
  const groups = [
    ...(catalog.data?.areas ?? []).map((a) => ({
      label: a.name,
      people: agents.filter((p) => p.area_id === a.id),
    })),
    { label: "Sin área", people: agents.filter((p) => p.area_id === null) },
  ].filter((g) => g.people.length > 0);

  return (
    <select
      id={id}
      value={value}
      onChange={(e) => onChange(e.target.value ? Number(e.target.value) : "")}
      className={className}
    >
      <option value="">Seleccione…</option>
      {groups.map((g) => (
        <optgroup key={g.label} label={g.label}>
          {g.people.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
              {p.id === me.data?.id ? " (usted)" : ""}
            </option>
          ))}
        </optgroup>
      ))}
    </select>
  );
}
