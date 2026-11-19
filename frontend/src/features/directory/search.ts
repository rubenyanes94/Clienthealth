import type { DirectoryDoctor } from "@/api/types";

/** Minúsculas y sin tildes, igual que `search_text` del servidor. */
export function fold(text: string): string {
  return text
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .toLowerCase();
}

/** Cada palabra escrita debe aparecer en el médico: «cardio anexo b» o «5b». */
export function matches(doctor: DirectoryDoctor, query: string): boolean {
  const words = fold(query).split(/\s+/).filter(Boolean);
  return words.every((word) => doctor.search_text.includes(word));
}

export function buildingsOf(doctors: DirectoryDoctor[]): string[] {
  const all = doctors.flatMap((d) => d.offices.map((o) => o.building).filter(Boolean)) as string[];
  return [...new Set(all)].sort((a, b) => a.localeCompare(b, "es"));
}

export function specialtiesOf(doctors: DirectoryDoctor[]): { name: string; count: number }[] {
  const counts = new Map<string, number>();
  for (const d of doctors) for (const s of d.specialties) counts.set(s, (counts.get(s) ?? 0) + 1);
  return [...counts]
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => a.name.localeCompare(b.name, "es"));
}
