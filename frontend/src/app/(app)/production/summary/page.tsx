"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { AlertBanner, Button, Card, Field, PageHeader, Textarea } from "@/components/ui";
import { apiFetch, errorMessage } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { ProductionSummary } from "@/lib/types";

function currentPeriod() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

function formatQuantity(value: number, unit: string) {
  return `${new Intl.NumberFormat(undefined, { maximumFractionDigits: 3 }).format(value)} ${unit}`;
}

function formatPercent(value: number | null) {
  return value === null ? "—" : `${value.toFixed(2)}%`;
}

export default function ProductionSummaryPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [period, setPeriod] = useState(currentPeriod);
  const [summaryText, setSummaryText] = useState("");
  const [markReviewed, setMarkReviewed] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [yearText, monthText] = period.split("-");
  const year = Number(yearText);
  const month = Number(monthText);

  const summaryQuery = useQuery({
    queryKey: ["production-summary", year, month],
    queryFn: () => apiFetch<ProductionSummary>(`/production/summary?year=${year}&month=${month}`),
  });
  const summary = summaryQuery.data;

  const saveReview = useMutation({
    mutationFn: () =>
      apiFetch(`/production/monthly-review/${year}/${month}`, {
        method: "PUT",
        body: JSON.stringify({ management_summary: summaryText.trim() || summary?.monthly_review?.management_summary || "", mark_reviewed: markReviewed }),
      }),
    onSuccess: async () => {
      setSaveError(null);
      await queryClient.invalidateQueries({ queryKey: ["production-summary", year, month] });
    },
    onError: (error) => setSaveError(errorMessage(error)),
  });

  const canReview = user?.role === "ADMIN" || user?.role === "SUPER_ADMIN";

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Production"
        title="Production summary"
        description="Monthly production performance, quality indicators and management review. Quantities are grouped by unit of measure."
        actions={
          <label className="flex items-center gap-2 text-sm font-medium text-slate-700">
            Reporting month
            <input
              aria-label="Reporting month"
              type="month"
              value={period}
              onChange={(event) => setPeriod(event.target.value)}
              className="h-10 rounded-lg border border-slate-300 bg-white px-3 text-sm"
            />
          </label>
        }
      />

      {summaryQuery.isError ? (
        <AlertBanner tone="danger" title="Could not load production summary">
          {errorMessage(summaryQuery.error)}
        </AlertBanner>
      ) : null}
      {saveError ? <AlertBanner tone="danger" title="Could not save management review">{saveError}</AlertBanner> : null}
      {summaryQuery.isLoading ? (
        <Card className="p-6 text-sm text-slate-500">Loading production summary…</Card>
      ) : null}

      {summary ? (
        <>
          <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <MetricCard label="Open actions" value={String(summary.open_actions)} detail="Not yet closed" />
            <MetricCard label="Overdue actions" value={String(summary.overdue_actions)} detail="Past their deadline" tone={summary.overdue_actions > 0 ? "warning" : "normal"} />
            <MetricCard label="Closed this month" value={String(summary.closed_this_month)} detail="Actions completed in selected month" />
            <MetricCard label="Production units" value={String(summary.units.length)} detail="Distinct units of measure reported" />
          </section>

          {summary.units.length === 0 ? (
            <Card className="p-8 text-center">
              <h2 className="font-semibold text-slate-900">No production records for this month</h2>
              <p className="mt-1 text-sm text-slate-500">Add daily production entries to populate the management summary.</p>
            </Card>
          ) : (
            <section className="space-y-4">
              {summary.units.map((unit) => (
                <Card key={unit.unit_of_measure} className="overflow-hidden">
                  <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 px-5 py-4">
                    <div>
                      <h2 className="font-semibold text-slate-900">Production performance</h2>
                      <p className="text-xs text-slate-500">Unit of measure: {unit.unit_of_measure} · {unit.entries_count} entries</p>
                    </div>
                    <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-700">{unit.unit_of_measure}</span>
                  </div>
                  <div className="grid gap-4 p-5 sm:grid-cols-2 xl:grid-cols-4">
                    <Kpi label="Planned quantity" value={formatQuantity(unit.planned_quantity, unit.unit_of_measure)} />
                    <Kpi label="Actual quantity" value={formatQuantity(unit.actual_quantity, unit.unit_of_measure)} />
                    <Kpi label="Accepted quantity" value={formatQuantity(unit.accepted_quantity, unit.unit_of_measure)} />
                    <Kpi label="Rejected quantity" value={formatQuantity(unit.rejected_quantity, unit.unit_of_measure)} />
                    <Kpi label="Plan achievement" value={formatPercent(unit.plan_achievement_percent)} />
                    <Kpi label="First pass yield" value={formatPercent(unit.first_pass_yield_percent)} />
                    <Kpi label="Rejection rate" value={formatPercent(unit.rejection_percent)} />
                    <Kpi label="Downtime" value={`${unit.downtime_hours.toFixed(2)} h (${formatPercent(unit.downtime_percent)})`} />
                    <Kpi label="Rework quantity" value={formatQuantity(unit.rework_quantity, unit.unit_of_measure)} />
                    <Kpi label="Production hours" value={`${unit.production_hours.toFixed(2)} h`} />
                  </div>
                </Card>
              ))}
            </section>
          )}

          <Card className="overflow-hidden">
            <div className="border-b border-slate-100 px-5 py-4">
              <h2 className="font-semibold text-slate-900">Management summary / key observations</h2>
              <p className="mt-1 text-xs text-slate-500">Record output versus plan, bottlenecks, quality concerns, constraints and decisions required.</p>
            </div>
            <div className="space-y-3 p-5">
              {summary.monthly_review ? (
                <div className="rounded-lg bg-slate-50 p-3 text-sm text-slate-700 whitespace-pre-wrap">
                  {summary.monthly_review.management_summary}
                  <p className="mt-2 text-xs text-slate-500">
                    Prepared by {summary.monthly_review.prepared_by.name}
                    {summary.monthly_review.reviewed_by ? ` · Reviewed by ${summary.monthly_review.reviewed_by.name}` : " · Not yet reviewed"}
                  </p>
                </div>
              ) : (
                <p className="text-sm text-slate-500">No management commentary has been saved for this month.</p>
              )}
              {canReview ? (
                <form
                  className="space-y-3"
                  onSubmit={(event) => {
                    event.preventDefault();
                    saveReview.mutate();
                  }}
                >
                  <Field label="Update management commentary">
                    <Textarea defaultValue={summary.monthly_review?.management_summary ?? ""} onChange={(event) => setSummaryText(event.target.value)} rows={4} placeholder="Summarise production performance, constraints and decisions required…" />
                  </Field>
                  <label className="flex items-center gap-2 text-sm text-slate-600">
                    <input type="checkbox" checked={markReviewed} onChange={(event) => setMarkReviewed(event.target.checked)} />
                    Mark this monthly review as reviewed
                  </label>
                  <Button type="submit" loading={saveReview.isPending} disabled={summaryText.trim().length < 3 && !summary.monthly_review?.management_summary}>
                    Save management review
                  </Button>
                  <p className="text-xs text-slate-500">Illustrative KPI targets from the Excel template are not enforced as company targets.</p>
                </form>
              ) : null}
            </div>
          </Card>
        </>
      ) : null}
    </div>
  );
}

function MetricCard({ label, value, detail, tone = "normal" }: { label: string; value: string; detail: string; tone?: "normal" | "warning" }) {
  return (
    <Card className="p-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</p>
      <p className={`mt-2 text-2xl font-bold ${tone === "warning" ? "text-amber-700" : "text-slate-900"}`}>{value}</p>
      <p className="mt-1 text-xs text-slate-500">{detail}</p>
    </Card>
  );
}

function Kpi({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-slate-500">{label}</p>
      <p className="mt-1 text-lg font-semibold text-slate-900">{value}</p>
    </div>
  );
}
