"use client";

/**
 * ExternalProfilesManager — the External profiles tab of the researcher
 * detail. Inline create/delete for {provider, url}.
 *
 * Spec (researchers-ui external profiles):
 *   - Provider ∈ cvlac, orcid, google_scholar, linkedin, researchgate.
 *   - POST /profiles/ creates; the list refreshes on success.
 *   - Nested DELETE /profiles/{id}/.
 */

import { useMemo, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { getErrorMessage } from "@/lib/errors";
import { useResearcherProfiles } from "@/features/researchers/queries";
import {
  useCreateExternalProfile,
  useDeleteExternalProfile,
} from "@/features/researchers/mutations";
import { PROVIDER_LABELS, PROFILE_PROVIDERS } from "@/features/researchers/constants";

interface ExternalProfilesManagerProps {
  researcherId: string;
}

/** Create is valid when a provider and a non-empty url are chosen. */
export function profileFormValid(provider: string, url: string): boolean {
  return provider !== "" && url.trim() !== "";
}

export function ExternalProfilesManager({ researcherId }: ExternalProfilesManagerProps) {
  const profilesQuery = useResearcherProfiles(researcherId);

  const [provider, setProvider] = useState("");
  const [url, setUrl] = useState("");

  const createProfile = useCreateExternalProfile(researcherId);
  const deleteProfile = useDeleteExternalProfile(researcherId);

  const profiles = useMemo(() => profilesQuery.data?.results ?? [], [profilesQuery.data]);
  const valid = profileFormValid(provider, url);

  function handleCreate() {
    if (!valid) return;
    createProfile.mutate(
      { provider, url: url.trim() },
      {
        onSuccess: () => {
          toast.success("Perfil externo añadido.");
          setProvider("");
          setUrl("");
        },
        onError: (error) => toast.error(getErrorMessage(error)),
      },
    );
  }

  return (
    <div className="space-y-6">
      <div className="rounded-lg border p-4">
        <h3 className="mb-3 text-sm font-semibold">Nuevo perfil externo</h3>
        <div className="grid gap-3 sm:grid-cols-2">
          <div>
            <Label htmlFor="prof-provider">Proveedor</Label>
            <select
              id="prof-provider"
              aria-label="Proveedor"
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
              className="mt-1 h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
            >
              <option value="">Seleccione…</option>
              {PROFILE_PROVIDERS.map((p) => (
                <option key={p} value={p}>
                  {PROVIDER_LABELS[p]}
                </option>
              ))}
            </select>
          </div>
          <div>
            <Label htmlFor="prof-url">URL</Label>
            <Input
              id="prof-url"
              type="url"
              placeholder="https://…"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
            />
          </div>
        </div>
        <Button className="mt-3" size="sm" onClick={handleCreate} disabled={!valid}>
          Añadir perfil
        </Button>
      </div>

      {profiles.length === 0 ? (
        <p className="py-8 text-center text-sm text-muted-foreground">Sin perfiles externos.</p>
      ) : (
        <ul className="divide-y">
          {profiles.map((p) => (
            <li key={p.id} className="flex items-center justify-between gap-3 py-3 text-sm">
              <div className="flex items-center gap-2">
                <span className="font-medium">
                  {PROVIDER_LABELS[p.provider as keyof typeof PROVIDER_LABELS] ?? p.provider}
                </span>
                <a href={p.url} target="_blank" rel="noreferrer" className="text-primary underline">
                  {p.url}
                </a>
              </div>
              <Button variant="ghost" size="sm" onClick={() => deleteProfile.mutate(p.id)}>
                Eliminar
              </Button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
