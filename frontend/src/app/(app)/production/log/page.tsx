"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { TableRowsSkeleton } from "@/components/loading-skeletons";
import {
  AlertBanner,
  Button,
  Card,
  EmptyState,
  Field,
  Input,
  PageHeader,
  Select,
  Pagination,
  Textarea,
} from "@/components/ui";
import { apiFetch, errorMessage } from "@/lib/api";
import type { Page, ProductionEntry, ProductionEntryCreate, Project } from "@/lib/types";

function today() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
}

const initialForm = (): ProductionEntryCreate => ({
  production_date: today(),
  production_line: "",
  product_model: "",
  work_order_customer: "",
  process_stage: "",
  unit_of_measure: "pcs",
  planned_quantity: 0,
  actual_quantity: 0,
  accepted_quantity: 0,
  rework_quantity: 0,
  production_hours: 0,
  downtime_hours: 0,
  remarks: "",
});

export default function ProductionLogPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [form, setForm] = useState<ProductionEntryCreate>(initialForm);
  const [formError, setFormError] = useState<string | null>(null);
  const projectsQuery = useQuery({
    queryKey: ["production-project-options"],
    queryFn: () => apiFetch<Page<Project>>("/projects?page=1&page_size=100"),
  });
  const entriesQuery = useQuery({
    queryKey: ["production-entries", page],
    queryFn: () => apiFetch<Page<ProductionEntry>>(`/production/entries?page=${page}&page_size=20`),
  });
  const createEntry = useMutation({
    mutationFn: () => apiFetch<ProductionEntry>("/production/entries", { method: "POST", body: JSON.stringify(form) }),
    onSuccess: async () => {
      setForm(initialForm());
      setFormError(null);
      await queryClient.invalidateQueries({ queryKey: ["production-entries"] });
      await queryClient.invalidateQueries({ queryKey: ["production-summary"] });
    },
    onError: (error) => setFormError(errorMessage(error)),
  });

  function update<K extends keyof ProductionEntryCreate>(key: K, value: ProductionEntryCreate[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Production" title="Production log" description="Enter one record per production line, product/model, process stage and reporting date." />

      <Card className="overflow-hidden">
        <div className="border-b border-slate-100 px-5 py-4">
          <h2 className="font-semibold text-slate-900">Add production entry</h2>
          <p className="mt-1 text-xs text-slate-500">Rejected quantity and performance percentages are calculated automatically.</p>
        </div>
        <form
          className="space-y-4 p-5"
          onSubmit={(event) => {
            event.preventDefault();
            setFormError(null);
            createEntry.mutate();
          }}
        >
          {formError ? <AlertBanner tone="danger">{formError}</AlertBanner> : null}
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            <Field label="Production date" required><Input type="date" value={form.production_date} onChange={(e) => update("production_date", e.target.value)} required /></Field>
            <Field label="Production line" required><Input value={form.production_line} onChange={(e) => update("production_line", e.target.value)} maxLength={120} required placeholder="e.g. Line 1" /></Field>
            <Field label="Product / model" required><Input value={form.product_model} onChange={(e) => update("product_model", e.target.value)} maxLength={200} required /></Field>
            <Field label="Work order / customer"><Input value={form.work_order_customer ?? ""} onChange={(e) => update("work_order_customer", e.target.value)} maxLength={200} /></Field>
            <Field label="MIS project (optional)">
              <Select value={form.project_id ?? ""} onChange={(e) => update("project_id", e.target.value || null)}>
                <option value="">Not linked to a project</option>
                {projectsQuery.data?.items.filter((project) => project.type === "PRODUCTION").map((project) => (
                  <option key={project.id} value={project.id}>{project.name}</option>
                ))}
              </Select>
            </Field>
            <Field label="Process stage" required><Input value={form.process_stage} onChange={(e) => update("process_stage", e.target.value)} maxLength={120} required placeholder="e.g. Assembly" /></Field>
            <Field label="Unit of measure" required><Input value={form.unit_of_measure} onChange={(e) => update("unit_of_measure", e.target.value)} maxLength={30} required placeholder="e.g. pcs, kg, litres" /></Field>
            <Field label="Planned quantity" required><Input type="number" min="0" step="0.001" value={form.planned_quantity} onChange={(e) => update("planned_quantity", Number(e.target.value))} required /></Field>
            <Field label="Actual quantity" required><Input type="number" min="0" step="0.001" value={form.actual_quantity} onChange={(e) => update("actual_quantity", Number(e.target.value))} required /></Field>
            <Field label="Accepted quantity" required><Input type="number" min="0" step="0.001" value={form.accepted_quantity} onChange={(e) => update("accepted_quantity", Number(e.target.value))} required /></Field>
            <Field label="Rework quantity"><Input type="number" min="0" step="0.001" value={form.rework_quantity} onChange={(e) => update("rework_quantity", Number(e.target.value))} /></Field>
            <Field label="Production hours"><Input type="number" min="0" step="0.01" value={form.production_hours} onChange={(e) => update("production_hours", Number(e.target.value))} /></Field>
            <Field label="Downtime hours"><Input type="number" min="0" step="0.01" value={form.downtime_hours} onChange={(e) => update("downtime_hours", Number(e.target.value))} /></Field>
          </div>
          <Field label="Remarks"><Textarea rows={2} value={form.remarks ?? ""} onChange={(e) => update("remarks", e.target.value)} maxLength={5000} /></Field>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-xs text-slate-500">Rejected quantity = actual quantity − accepted quantity.</p>
            <Button type="submit" loading={createEntry.isPending}>Save production entry</Button>
          </div>
        </form>
      </Card>

      <Card className="overflow-hidden">
        <div className="border-b border-slate-100 px-5 py-4">
          <h2 className="font-semibold text-slate-900">Production records</h2>
          <p className="mt-1 text-xs text-slate-500">{entriesQuery.data?.total ?? 0} records</p>
        </div>
        {entriesQuery.isError ? <div className="p-5"><AlertBanner tone="danger">{errorMessage(entriesQuery.error)}</AlertBanner></div> : null}
        {entriesQuery.isLoading ? <TableRowsSkeleton rows={5} columns={11} /> : null}
        {entriesQuery.data && entriesQuery.data.items.length === 0 ? <EmptyState title="No production entries yet" description="Use the form above to record the first production entry." /> : null}
        {entriesQuery.data && entriesQuery.data.items.length > 0 ? (
          <>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[1050px] text-left text-sm">
                <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                  <tr>{["Date", "Line", "Product / model", "Stage", "Unit", "Planned", "Actual", "Accepted", "Rejected", "Plan %", "FPY %"].map((label) => <th key={label} className="px-4 py-3 font-semibold">{label}</th>)}</tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {entriesQuery.data.items.map((entry) => (
                    <tr key={entry.id} className="hover:bg-slate-50/70">
                      <td className="whitespace-nowrap px-4 py-3">{entry.production_date}</td>
                      <td className="px-4 py-3">{entry.production_line}</td>
                      <td className="px-4 py-3 font-medium text-slate-900">{entry.product_model}</td>
                      <td className="px-4 py-3">{entry.process_stage}</td>
                      <td className="px-4 py-3">{entry.unit_of_measure}</td>
                      <td className="px-4 py-3 tabular-nums">{entry.planned_quantity}</td>
                      <td className="px-4 py-3 tabular-nums">{entry.actual_quantity}</td>
                      <td className="px-4 py-3 tabular-nums">{entry.accepted_quantity}</td>
                      <td className="px-4 py-3 tabular-nums">{entry.rejected_quantity}</td>
                      <td className="px-4 py-3 tabular-nums">{entry.plan_achievement_percent == null ? "—" : `${entry.plan_achievement_percent.toFixed(1)}%`}</td>
                      <td className="px-4 py-3 tabular-nums">{entry.first_pass_yield_percent == null ? "—" : `${entry.first_pass_yield_percent.toFixed(1)}%`}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination page={entriesQuery.data.page} pages={entriesQuery.data.pages} total={entriesQuery.data.total} onPageChange={setPage} />
          </>
        ) : null}
      </Card>
    </div>
  );
}
