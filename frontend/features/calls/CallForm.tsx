"use client";

/**
 * CallForm — shared create/edit form for calls.
 *
 * Spec (calls-ui create/edit):
 *   - zod mirrors the DRF rules: external_entity conditional on call_type
 *     and end dates on/after start dates.
 *   - Success redirects to the call detail page.
 *   - Edit renders status and institution as read-only.
 */

import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { getErrorMessage } from "@/lib/errors";
import { useCreateCall, useUpdateCall } from "@/features/calls/mutations";
import {
  buildCallPayload,
  callFormSchema,
  type CallFormValues,
} from "@/features/calls/schemas";
import { CALL_TYPE_OPTIONS, getCallStatusLabel } from "@/features/calls/constants";
import type { Call } from "@/features/calls/types";

interface CallFormProps {
  mode: "create" | "edit";
  /** Call id (edit mode). */
  callId?: string;
  /** Detail used to seed the edit form. */
  initialValues?: Call | null;
}

const EMPTY_VALUES: CallFormValues = {
  title: "",
  description: "",
  call_type: "internal",
  external_entity: "",
  submission_start: "",
  submission_end: "",
  evaluation_start: "",
  evaluation_end: "",
};

function toFormValues(call: Call | null | undefined): CallFormValues {
  if (!call) return EMPTY_VALUES;
  return {
    title: call.title,
    description: call.description,
    call_type: call.call_type as CallFormValues["call_type"],
    external_entity: call.external_entity ?? "",
    submission_start: call.submission_start ?? "",
    submission_end: call.submission_end ?? "",
    evaluation_start: call.evaluation_start ?? "",
    evaluation_end: call.evaluation_end ?? "",
  };
}

export function CallForm({ mode, callId, initialValues }: CallFormProps) {
  const router = useRouter();
  const createCall = useCreateCall();
  const updateCall = useUpdateCall();

  const {
    register,
    handleSubmit,
    control,
    formState: { errors, isSubmitting },
  } = useForm<CallFormValues>({
    resolver: zodResolver(callFormSchema),
    defaultValues: toFormValues(initialValues),
  });

  const isEdit = mode === "edit";
  const pending = createCall.isPending || updateCall.isPending;

  function onSubmit(values: CallFormValues) {
    const payload = buildCallPayload(values);
    if (isEdit && callId) {
      updateCall.mutate(
        { id: callId, ...payload },
        {
          onSuccess: () => {
            toast.success("Convocatoria actualizada.");
            router.push(`/calls/${callId}`);
          },
          onError: (error) => toast.error(getErrorMessage(error)),
        },
      );
      return;
    }
    createCall.mutate(payload, {
      onSuccess: (created) => {
        toast.success("Convocatoria creada.");
        router.push(`/calls/${created.id}`);
      },
      onError: (error) => toast.error(getErrorMessage(error)),
    });
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{isEdit ? "Editar convocatoria" : "Nueva convocatoria"}</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="grid gap-4">
          <div>
            <Label htmlFor="call-title">Título</Label>
            <Input id="call-title" {...register("title")} />
            {errors.title ? (
              <p className="mt-1 text-sm text-destructive">{errors.title.message}</p>
            ) : null}
          </div>

          <div>
            <Label htmlFor="call-description">Descripción</Label>
            <textarea
              id="call-description"
              rows={4}
              className="flex w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              {...register("description")}
            />
            {errors.description ? (
              <p className="mt-1 text-sm text-destructive">
                {errors.description.message}
              </p>
            ) : null}
          </div>

          <div>
            <Label htmlFor="call-type">Tipo de convocatoria</Label>
            <Controller
              control={control}
              name="call_type"
              render={({ field }) => (
                <Select value={field.value} onValueChange={field.onChange}>
                  <SelectTrigger id="call-type" aria-label="Tipo de convocatoria">
                    <SelectValue placeholder="Selecciona el tipo" />
                  </SelectTrigger>
                  <SelectContent>
                    {CALL_TYPE_OPTIONS.map((opt) => (
                      <SelectItem key={opt.value} value={opt.value}>
                        {opt.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            />
            {errors.call_type ? (
              <p className="mt-1 text-sm text-destructive">{errors.call_type.message}</p>
            ) : null}
          </div>

          <div>
            <Label htmlFor="call-external-entity">Entidad externa</Label>
            <Input id="call-external-entity" {...register("external_entity")} />
            {errors.external_entity ? (
              <p className="mt-1 text-sm text-destructive">
                {errors.external_entity.message}
              </p>
            ) : null}
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <Label htmlFor="call-submission-start">Inicio de postulación</Label>
              <Input
                id="call-submission-start"
                type="date"
                {...register("submission_start")}
              />
              {errors.submission_start ? (
                <p className="mt-1 text-sm text-destructive">
                  {errors.submission_start.message}
                </p>
              ) : null}
            </div>
            <div>
              <Label htmlFor="call-submission-end">Cierre de postulación</Label>
              <Input
                id="call-submission-end"
                type="date"
                {...register("submission_end")}
              />
              {errors.submission_end ? (
                <p className="mt-1 text-sm text-destructive">
                  {errors.submission_end.message}
                </p>
              ) : null}
            </div>
            <div>
              <Label htmlFor="call-evaluation-start">Inicio de evaluación</Label>
              <Input
                id="call-evaluation-start"
                type="date"
                {...register("evaluation_start")}
              />
              {errors.evaluation_start ? (
                <p className="mt-1 text-sm text-destructive">
                  {errors.evaluation_start.message}
                </p>
              ) : null}
            </div>
            <div>
              <Label htmlFor="call-evaluation-end">Fin de evaluación</Label>
              <Input
                id="call-evaluation-end"
                type="date"
                {...register("evaluation_end")}
              />
              {errors.evaluation_end ? (
                <p className="mt-1 text-sm text-destructive">
                  {errors.evaluation_end.message}
                </p>
              ) : null}
            </div>
          </div>

          {isEdit && initialValues ? (
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <Label htmlFor="call-status">Estado</Label>
                <Input
                  id="call-status"
                  value={getCallStatusLabel(initialValues.status)}
                  disabled
                />
              </div>
              <div>
                <Label htmlFor="call-institution">Institución</Label>
                <Input
                  id="call-institution"
                  value={initialValues.institution}
                  disabled
                  readOnly
                />
              </div>
            </div>
          ) : null}

          <div>
            <Button type="submit" disabled={pending || isSubmitting}>
              {isEdit ? "Guardar cambios" : "Crear convocatoria"}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}