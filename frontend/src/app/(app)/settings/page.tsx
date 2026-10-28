"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlarmClock,
  BellRing,
  Play,
  RefreshCw,
  ShieldAlert,
  Timer,
  TrendingUp,
} from "lucide-react";
import { useEffect } from "react";
import { useForm, useWatch } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { RequireRole } from "@/components/auth-gate";
import {
  AlertBanner,
  Button,
  Card,
  CardHeader,
  Field,
  Input,
  PageHeader,
  Skeleton,
} from "@/components/ui";
import { apiFetch, errorMessage } from "@/lib/api";
import type { AlertRunResult, ThresholdSettings } from "@/lib/types";
import { formatDateTime, pluralise } from "@/lib/utils";

const settingsSchema = z
  .object({
    safe_threshold_days: z
      .number({ error: "Enter a number" })
      .int()
      .min(0)
      .max(365),
    escalation_threshold_days: z
      .number({ error: "Enter a number" })
      .int()
      .min(1)
      .max(365),
    deadline_reminder_days: z
      .number({ error: "Enter a number" })
      .int()
      .min(0)
      .max(365),
    severe_delay_multiplier: z
      .number({ error: "Enter a number" })
      .min(1)
      .max(10),
  })
  .refine(
    (values) => values.escalation_threshold_days > values.safe_threshold_days,
    {
      path: ["escalation_threshold_days"],
      message: "Escalation threshold must be greater than the safe threshold",
    },
  );

type SettingsValues = z.infer<typeof settingsSchema>;

export default function SettingsPage() {
  return (
    <RequireRole roles={["SUPER_ADMIN"]}>
      <SettingsContent />
    </RequireRole>
  );
}

function SettingsContent() {
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: ["settings", "thresholds"],
    queryFn: () => apiFetch<ThresholdSettings>("/settings/thresholds"),
  });

  const {
    register,
    control,
    handleSubmit,
    reset,
    formState: { errors, isDirty },
  } = useForm<SettingsValues>({
    resolver: zodResolver(settingsSchema),
    defaultValues: {
      safe_threshold_days: 3,
      escalation_threshold_days: 7,
      deadline_reminder_days: 5,
      severe_delay_multiplier: 2,
    },
  });

  useEffect(() => {
    if (!query.data) return;
    reset({
      safe_threshold_days: query.data.safe_threshold_days,
      escalation_threshold_days: query.data.escalation_threshold_days,
      deadline_reminder_days: query.data.deadline_reminder_days,
      severe_delay_multiplier: query.data.severe_delay_multiplier,
    });
  }, [query.data, reset]);

  const save = useMutation({
    mutationFn: (values: SettingsValues) =>
      apiFetch<ThresholdSettings>("/settings/thresholds", {
        method: "PUT",
        body: JSON.stringify(values),
      }),
    onSuccess: (data) => {
      queryClient.setQueryData(["settings", "thresholds"], data);
      reset({
        safe_threshold_days: data.safe_threshold_days,
        escalation_threshold_days: data.escalation_threshold_days,
        deadline_reminder_days: data.deadline_reminder_days,
        severe_delay_multiplier: data.severe_delay_multiplier,
      });
      toast.success("Time Counter thresholds updated");
    },
    onError: (error) => toast.error(errorMessage(error)),
  });

  const runCheck = useMutation({
    mutationFn: () =>
      apiFetch<AlertRunResult>("/alerts/run-check", { method: "POST" }),
    onSuccess: (result) => {
      void queryClient.invalidateQueries({ queryKey: ["alerts"] });
      void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      toast.success(
        `Evaluated ${result.evaluated_projects} projects; created ${result.alerts_created} alerts.`,
      );
    },
    onError: (error) => toast.error(errorMessage(error)),
  });

  const safeThreshold = useWatch({ control, name: "safe_threshold_days" }) || 0;
  const escalation = useWatch({ control, name: "escalation_threshold_days" }) || 0;
  const reminder = useWatch({ control, name: "deadline_reminder_days" }) || 0;
  const multiplier = useWatch({ control, name: "severe_delay_multiplier" }) || 1;
  const severeAfter = Math.floor(escalation * multiplier);

  if (query.isLoading) {
    return (
      <div>
        <Skeleton className="h-8 w-64" />
        <Skeleton className="mt-2 h-4 w-96" />
        <div className="mt-6 grid gap-6 xl:grid-cols-[1.4fr_1fr]">
          <Skeleton className="h-96" />
          <Skeleton className="h-96" />
        </div>
      </div>
    );
  }

  if (query.isError) {
    return (
      <div>
        <PageHeader title="Time Counter" />
        <AlertBanner
          tone="danger"
          title="Unable to load thresholds"
          action={
            <Button variant="outline" size="sm" onClick={() => query.refetch()}>
              <RefreshCw className="h-3.5 w-3.5" />
              Retry
            </Button>
          }
        >
          {errorMessage(query.error)}
        </AlertBanner>
      </div>
    );
  }

  return (
    <div className="animate-rise-in">
      <PageHeader
        eyebrow="Super Admin configuration"
        title="Time Counter"
        description="Configure when inactivity and approaching deadlines create alerts, and when escalations reach Admins or Super Admins."
        actions={
          <Button
            variant="outline"
            onClick={() => runCheck.mutate()}
            loading={runCheck.isPending}
          >
            <Play className="h-4 w-4" />
            Run check now
          </Button>
        }
      />

      <div className="grid gap-6 xl:grid-cols-[1.35fr_1fr]">
        <Card>
          <CardHeader
            title="Alert thresholds"
            description="Changes apply to the next scheduled or manual run."
            action={
              query.data?.updated_at ? (
                <span className="text-[10px] text-slate-400">
                  Updated {formatDateTime(query.data.updated_at)}
                </span>
              ) : null
            }
          />
          <form
            className="space-y-5 p-5"
            onSubmit={handleSubmit((values) => save.mutate(values))}
            noValidate
          >
            <div className="grid gap-5 sm:grid-cols-2">
              <Field
                label="Safe threshold"
                htmlFor="safe_threshold_days"
                error={errors.safe_threshold_days?.message}
                hint="Days without a status or progress update before a standard alert."
                required
              >
                <Input
                  id="safe_threshold_days"
                  type="number"
                  min={0}
                  max={365}
                  step={1}
                  {...register("safe_threshold_days", { valueAsNumber: true })}
                />
              </Field>
              <Field
                label="Escalation threshold"
                htmlFor="escalation_threshold_days"
                error={errors.escalation_threshold_days?.message}
                hint="Days after which alerts escalate to Admins instead of users."
                required
              >
                <Input
                  id="escalation_threshold_days"
                  type="number"
                  min={1}
                  max={365}
                  step={1}
                  {...register("escalation_threshold_days", { valueAsNumber: true })}
                />
              </Field>
              <Field
                label="Deadline reminder window"
                htmlFor="deadline_reminder_days"
                error={errors.deadline_reminder_days?.message}
                hint="Days before the deadline when a standard reminder is sent."
                required
              >
                <Input
                  id="deadline_reminder_days"
                  type="number"
                  min={0}
                  max={365}
                  step={1}
                  {...register("deadline_reminder_days", { valueAsNumber: true })}
                />
              </Field>
              <Field
                label="Severe delay multiplier"
                htmlFor="severe_delay_multiplier"
                error={errors.severe_delay_multiplier?.message}
                hint="Multiplies the escalation threshold to reach Super Admins."
                required
              >
                <Input
                  id="severe_delay_multiplier"
                  type="number"
                  min={1}
                  max={10}
                  step={0.1}
                  {...register("severe_delay_multiplier", { valueAsNumber: true })}
                />
              </Field>
            </div>

            <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
              <p className="text-[10px] font-semibold tracking-wide text-slate-500 uppercase">
                Live rule preview
              </p>
              <div className="mt-3 space-y-2.5 text-xs text-slate-600">
                <PreviewRow
                  icon={BellRing}
                  text={`Standard alert after ${pluralise(safeThreshold, "inactive day")}.`}
                />
                <PreviewRow
                  icon={TrendingUp}
                  text={`Escalated alert after ${pluralise(escalation, "inactive day")}.`}
                />
                <PreviewRow
                  icon={ShieldAlert}
                  text={`Severe escalation to Super Admins after ${pluralise(severeAfter, "inactive day")}.`}
                />
                <PreviewRow
                  icon={AlarmClock}
                  text={`Deadline reminder inside ${pluralise(reminder, "day")}.`}
                />
              </div>
            </div>

            <div className="flex justify-end gap-2 border-t border-slate-100 pt-4">
              <Button
                type="button"
                variant="outline"
                disabled={!isDirty || save.isPending}
                onClick={() => reset()}
              >
                Reset
              </Button>
              <Button type="submit" loading={save.isPending} disabled={!isDirty}>
                Save thresholds
              </Button>
            </div>
          </form>
        </Card>

        <div className="space-y-6">
          <Card>
            <CardHeader
              title="How the Time Counter works"
              description="Server-side APScheduler job"
            />
            <div className="space-y-4 p-5 text-sm leading-6 text-slate-600">
              <div className="flex gap-3">
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-teal-50 text-[#0f5c73]">
                  <Timer className="h-4 w-4" />
                </span>
                <p>
                  For each active project, pending days are counted from the later
                  of the last status change and the last progress log.
                </p>
              </div>
              <div className="flex gap-3">
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-amber-50 text-amber-700">
                  <BellRing className="h-4 w-4" />
                </span>
                <p>
                  Standard alerts go only to the project’s assigned members. They
                  are also used for deadline reminders inside the configured window.
                </p>
              </div>
              <div className="flex gap-3">
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-red-50 text-red-700">
                  <ShieldAlert className="h-4 w-4" />
                </span>
                <p>
                  Beyond the escalation threshold, users are bypassed and Admins are
                  notified. Severe delays also notify Super Admins.
                </p>
              </div>
              <div className="flex gap-3">
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-slate-100 text-slate-600">
                  <RefreshCw className="h-4 w-4" />
                </span>
                <p>
                  De-duplication allows at most one alert per project, type,
                  recipient, and calendar day.
                </p>
              </div>
            </div>
          </Card>

          <AlertBanner tone="warning" title="Operational note">
            Thresholds are stored in the database and audited. Keep escalation above
            the safe threshold. The scheduler interval and timezone are startup
            configuration values.
          </AlertBanner>
        </div>
      </div>
    </div>
  );
}

function PreviewRow({
  icon: Icon,
  text,
}: {
  icon: typeof BellRing;
  text: string;
}) {
  return (
    <div className="flex items-start gap-2">
      <Icon className="mt-0.5 h-3.5 w-3.5 shrink-0 text-slate-400" />
      <span>{text}</span>
    </div>
  );
}
