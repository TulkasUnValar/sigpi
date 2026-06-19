"use client";

/**
 * Dropdown to switch the active institution.
 * Only renders when the user belongs to more than one institution.
 */

import { useAuthStore } from "@/store/auth";

export default function InstitutionSelector() {
  const { institutions, activeInstitution, switchInstitution, isLoading } =
    useAuthStore();

  // Don't render if switching isn't useful
  if (institutions.length <= 1) return null;

  async function handleChange(e: React.ChangeEvent<HTMLSelectElement>) {
    const newId = e.target.value;
    if (newId === activeInstitution?.id) return;
    await switchInstitution(newId);
  }

  return (
    <select
      value={activeInstitution?.id ?? ""}
      onChange={handleChange}
      disabled={isLoading}
      aria-label="Active institution"
    >
      {institutions.map((inst) => (
        <option key={inst.id} value={inst.id}>
          {inst.name}
        </option>
      ))}
    </select>
  );
}
