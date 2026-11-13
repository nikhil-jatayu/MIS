"use client";

import { useQuery } from "@tanstack/react-query";
import { useMemo, useState, type FormEvent } from "react";

import {
  AlertBanner,
  Button,
  Card,
  Field,
  PageHeader,
  Select,
  Input,
  Skeleton,
} from "@/components/ui";
import { apiFetch, apiUrl, errorMessage } from "@/lib/api";
import type {
  Page,
  Project,
  ProductionReportDimensionMetric,
  ProductionReportMetric,
  ProductionReportSummary,
  ProductionReportTrendPoint,
} from "@/lib/types";

function currentMonth(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

function monthBounds(month: string): { from: string; to: string } {
  const [year, monthNumber] = month.split("-").map(Number);
  const lastDay = new Date(year, monthNumber, 0).getDate();
  return {
    from: `${month}-01`,
    to: `${month}-${String(lastDay).padStart(2, "0")}`,
  };
}

function formatQuantity(value: number, unit: string): string {
  return `${new Intl.NumberFormat(undefined, { maximumFractionDigits: 3 }).format(value)} ${unit}`;
}

function formatPercent(value: number | null): string {
  return value === null ? "—" : `${value.toFixed(2)}%`;
}

type AppliedFilters = {
  dateFrom: string;
  dateTo: string;
  productionLine: string;
  productModel: string;
  projectId: string;
  unitOfMeasure: string;
};

export default function ProductionReportsPage() {
  const initialMonth = currentMonth();
  const initialBounds = monthBounds(initialMonth);
  const [mode, setMode] = useState<"month" | "custom">("month");
  const [month, setMonth] = useState(initialMonth);
  const [dateFrom, setDateFrom] = useState(initialBounds.from);
  const [dateTo, setDateTo] = useState(initialBounds.to);
  const [productionLine, setProductionLine] = useState("");
  const [productModel, setProductModel] = useState("");
  const [projectId, setProjectId] = useState("");
  const [unitOfMeasure, setUnitOfMeasure] = useState("");
  const [filterError, setFilterError] = useState<string | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);
  const [pdfExportError, setPdfExportError] = useState<string | null>(null);
  const [isExporting, setIsExporting] = useState(false);
  const [isExportingPdf, setIsExportingPdf] = useState(false);
  const [applied, setApplied] = useState<AppliedFilters>({
    dateFrom: initialBounds.from,
    dateTo: initialBounds.to,
    productionLine: "",
    productModel: "",
    projectId: "",
    unitOfMeasure: "",
  });

  const projectsQuery = useQuery({
    queryKey: ["production-report-project-options"],
    queryFn: () => apiFetch<Page<Project>>("/projects?page=1&page_size=100"),
  });

  const queryString = useMemo(() => {
    const params = new URLSearchParams({ date_from: applied.dateFrom, date_to: applied.dateTo });
    if (applied.productionLine) params.set("production_line", applied.productionLine);
    if (applied.productModel) params.set("product_model", applied.productModel);
    if (applied.projectId) params.set("project_id", applied.projectId);
    if (applied.unitOfMeasure) params.set("unit_of_measure", applied.unitOfMeasure);
    return params.toString();
  }, [applied]);

  const reportQuery = useQuery({
    queryKey: ["production-report", queryString],
    queryFn: () => apiFetch<ProductionReportSummary>(`/production/reports/summary?${queryString}`),
  });

  function applyFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const bounds = mode === "month" ? monthBounds(month) : { from: dateFrom, to: dateTo };
    if (!bounds.from || !bounds.to || bounds.from > bounds.to) {
      setFilterError("The start date must be on or before the end date.");
      return;
    }
    setFilterError(null);
    setApplied({
      dateFrom: bounds.from,
      dateTo: bounds.to,
      productionLine: productionLine.trim(),
      productModel: productModel.trim(),
      projectId,
      unitOfMeasure,
    });
  }

  async function exportWorkbook() {
    setIsExporting(true);
    setExportError(null);
    try {
      const response = await fetch(apiUrl(`/production/reports/export.xlsx?${queryString}`), {
        method: "GET",
        credentials: "include",
        cache: "no-store",
        headers: { Accept: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" },
      });
      if (!response.ok) {
        let message = `Excel export failed (${response.status}).`;
        try {
          const body = await response.json();
          message = body?.error?.message ?? message;
        } catch {
          // Keep the HTTP fallback when the server doesn't return a JSON error.
        }
        throw new Error(message);
      }
      const blob = await response.blob();
      const objectUrl = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = objectUrl;
      anchor.download = `MIS_Production_Report_${applied.dateFrom}_to_${applied.dateTo}.xlsx`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
    } catch (error) {
      setExportError(errorMessage(error, "Could not export the Production workbook."));
    } finally {
      setIsExporting(false);
    }
  }

  async function exportPdf() {
    setIsExportingPdf(true);
    setPdfExportError(null);
    try {
      const response = await fetch(apiUrl(`/production/reports/export.pdf?${queryString}`), {
        method: "GET",
        credentials: "include",
        cache: "no-store",
        headers: { Accept: "application/pdf" },
      });
      if (!response.ok) {
        let message = `PDF export failed (${response.status}).`;
        try {
          const body = await response.json();
          message = body?.error?.message ?? message;
        } catch {
          // Keep the HTTP fallback when the server doesn't return a JSON error.
        }
        throw new Error(message);
      }
      const blob = await response.blob();
      const objectUrl = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = objectUrl;
      anchor.download = `MIS_Production_Management_Report_${applied.dateFrom}_to_${applied.dateTo}.pdf`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
    } catch (error) {
      setPdfExportError(errorMessage(error, "Could not export the Production PDF report."));
    } finally {
      setIsExportingPdf(false);
    }
  }

  const report = reportQuery.data;
  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Reports"
        title="Production analytics"
        description="Compare production output, first-pass quality, rework and downtime across monthly or custom reporting periods. Quantities remain separated by unit of measure."
      />

      <Card className="p-5">
        <form className="space-y-4" onSubmit={applyFilters}>
          <div className="flex flex-wrap items-center gap-2">
            <Button type="button" size="sm" variant={mode === "month" ? "primary" : "outline"} onClick={() => setMode("month")}>Monthly</Button>
            <Button type="button" size="sm" variant={mode === "custom" ? "primary" : "outline"} onClick={() => setMode("custom")}>Custom date range</Button>
          </div>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {mode === "month" ? (
              <Field label="Reporting month">
                <Input type="month" value={month} onChange={(event) => setMonth(event.target.value)} required />
              </Field>
            ) : (
              <>
                <Field label="Start date">
                  <Input type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} required />
                </Field>
                <Field label="End date">
                  <Input type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} required />
                </Field>
              </>
            )}
            <Field label="Production line" hint="Optional; partial match">
              <Input value={productionLine} onChange={(event) => setProductionLine(event.target.value)} placeholder="e.g. Line A" />
            </Field>
            <Field label="Product / model" hint="Optional; partial match">
              <Input value={productModel} onChange={(event) => setProductModel(event.target.value)} placeholder="e.g. Model X" />
            </Field>
            <Field label="Project">
              <Select value={projectId} onChange={(event) => setProjectId(event.target.value)}>
                <option value="">All projects</option>
                {(projectsQuery.data?.items ?? []).map((project) => (
                  <option key={project.id} value={project.id}>{project.name}</option>
                ))}
              </Select>
            </Field>
            <Field label="Unit of measure">
              <Input value={unitOfMeasure} onChange={(event) => setUnitOfMeasure(event.target.value)} placeholder="e.g. pcs, kg" />
            </Field>
          </div>
          {filterError ? <AlertBanner tone="danger">{filterError}</AlertBanner> : null}
          <div className="flex flex-wrap items-center gap-3">
            <Button type="submit" loading={reportQuery.isFetching}>Apply filters</Button>
            <p className="text-xs text-slate-500">Changing filters does not affect saved production records.</p>
          </div>
        </form>
      </Card>

      {reportQuery.isError ? (
        <AlertBanner tone="danger" title="Could not load production analytics">{errorMessage(reportQuery.error)}</AlertBanner>
      ) : null}
      {reportQuery.isLoading ? (
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 4 }).map((_, index) => <Skeleton key={index} className="h-28" />)}
        </div>
      ) : null}

      {report ? (
        <>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="font-semibold text-slate-900">Reporting results</h2>
              <p className="text-xs text-slate-500">{report.date_from} to {report.date_to} · {report.granularity === "day" ? "Daily trend" : "Monthly trend"}</p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700">{report.totals_by_unit.length} unit group(s)</span>
              <Button
                type="button"
                size="sm"
                variant="outline"
                loading={isExporting}
                disabled={isExportingPdf}
                onClick={exportWorkbook}
              >
                Export to Excel
              </Button>
              <Button
                type="button"
                size="sm"
                variant="primary"
                loading={isExportingPdf}
                disabled={isExporting}
                onClick={exportPdf}
              >
                Export management PDF
              </Button>
            </div>
          </div>
          {exportError ? <AlertBanner tone="danger" title="Excel export failed">{exportError}</AlertBanner> : null}
          {pdfExportError ? <AlertBanner tone="danger" title="PDF export failed">{pdfExportError}</AlertBanner> : null}

          <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <ActionMetric label="Actions created in period" value={report.actions.actions_created_in_period} />
            <ActionMetric label="Currently open actions" value={report.actions.current_open_actions} />
            <ActionMetric label="Currently overdue" value={report.actions.current_overdue_actions} warning={report.actions.current_overdue_actions > 0} />
            <ActionMetric label="Closed in period" value={report.actions.closed_actions_in_period} />
          </section>

          {report.totals_by_unit.length === 0 ? (
            <Card className="p-8 text-center">
              <h2 className="font-semibold text-slate-900">No production records match these filters</h2>
              <p className="mt-1 text-sm text-slate-500">You can still export the selected period and its action tracker, or try a wider date range.</p>
            </Card>
          ) : report.totals_by_unit.map((metric) => (
            <UnitSummary key={metric.unit_of_measure} metric={metric} />
          ))}

          <section className="grid gap-4 xl:grid-cols-2">
            <Breakdown title="Production-line performance" rows={report.by_line} />
            <Breakdown title="Product / model performance" rows={report.by_product} />
          </section>

          <TrendSection points={report.trend} />

          <Card className="p-5">
            <h3 className="text-sm font-semibold text-slate-900">Quality calculation notes</h3>
            <p className="mt-2 text-sm text-slate-600">{report.quality_definition}</p>
            <p className="mt-2 text-xs text-slate-500">{report.actions.scope_note}</p>
          </Card>
        </>
      ) : null}
    </div>
  );
}

function ActionMetric({ label, value, warning = false }: { label: string; value: number; warning?: boolean }) {
  return (
    <Card className="p-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</p>
      <p className={`mt-2 text-2xl font-bold ${warning ? "text-amber-700" : "text-slate-900"}`}>{value}</p>
    </Card>
  );
}

function UnitSummary({ metric }: { metric: ProductionReportMetric }) {
  const kpis: Array<[string, string]> = [
    ["Planned", formatQuantity(metric.planned_quantity, metric.unit_of_measure)],
    ["Actual", formatQuantity(metric.actual_quantity, metric.unit_of_measure)],
    ["Accepted (first pass)", formatQuantity(metric.accepted_first_pass_quantity, metric.unit_of_measure)],
    ["First-pass non-acceptance", formatQuantity(metric.first_pass_non_acceptance_quantity, metric.unit_of_measure)],
    ["Plan achievement", formatPercent(metric.plan_achievement_percent)],
    ["First-pass yield", formatPercent(metric.first_pass_yield_percent)],
    ["Rework sent", formatQuantity(metric.rework_sent_quantity, metric.unit_of_measure)],
    ["Rework rate", formatPercent(metric.rework_rate_percent)],
    ["Downtime", `${metric.downtime_hours.toFixed(2)} h`],
    ["Downtime %", formatPercent(metric.downtime_percent)],
  ];
  return (
    <Card className="overflow-hidden">
      <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
        <h3 className="font-semibold text-slate-900">Production summary</h3>
        <span className="rounded-full bg-teal-50 px-3 py-1 text-xs font-semibold text-teal-800">{metric.unit_of_measure}</span>
      </div>
      <div className="grid gap-px bg-slate-100 sm:grid-cols-2 xl:grid-cols-5">
        {kpis.map(([label, value]) => (
          <div className="bg-white p-4" key={label}>
            <p className="text-xs font-medium text-slate-500">{label}</p>
            <p className="mt-1 text-lg font-semibold text-slate-900">{value}</p>
          </div>
        ))}
      </div>
    </Card>
  );
}

function Breakdown({ title, rows }: { title: string; rows: ProductionReportDimensionMetric[] }) {
  const grouped = new Map<string, ProductionReportDimensionMetric[]>();
  for (const row of rows) {
    const current = grouped.get(row.unit_of_measure) ?? [];
    current.push(row);
    grouped.set(row.unit_of_measure, current);
  }
  return (
    <Card className="overflow-hidden">
      <div className="border-b border-slate-100 px-5 py-4">
        <h3 className="font-semibold text-slate-900">{title}</h3>
      </div>
      <div className="space-y-5 p-5">
        {rows.length === 0 ? <p className="text-sm text-slate-500">No breakdown data for this period.</p> : null}
        {[...grouped.entries()].map(([unit, items]) => (
          <div className="space-y-3" key={unit}>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{unit}</p>
            {items.map((item) => (
              <div className="flex flex-wrap items-center justify-between gap-2 text-sm" key={`${unit}-${item.dimension_value}`}>
                <span className="font-medium text-slate-700">{item.dimension_value}</span>
                <span className="text-slate-500">{formatQuantity(item.actual_quantity, unit)} actual · {formatPercent(item.first_pass_yield_percent)} FPY</span>
              </div>
            ))}
          </div>
        ))}
      </div>
    </Card>
  );
}

function TrendSection({ points }: { points: ProductionReportTrendPoint[] }) {
  const grouped = new Map<string, ProductionReportTrendPoint[]>();
  for (const point of points) {
    const current = grouped.get(point.unit_of_measure) ?? [];
    current.push(point);
    grouped.set(point.unit_of_measure, current);
  }
  return (
    <Card className="overflow-hidden">
      <div className="border-b border-slate-100 px-5 py-4">
        <h3 className="font-semibold text-slate-900">Production trend</h3>
        <p className="text-xs text-slate-500">Planned versus actual production over the selected reporting period.</p>
      </div>
      <div className="space-y-5 p-5">
        {points.length === 0 ? <p className="text-sm text-slate-500">No trend data for this period.</p> : null}
        {[...grouped.entries()].map(([unit, items]) => {
          const maxValue = Math.max(1, ...items.map((item) => Math.max(item.actual_quantity, item.planned_quantity)));
          return (
            <div key={unit} className="space-y-3">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{unit}</p>
              {items.map((point) => (
                <div key={`${unit}-${point.period}`} className="grid gap-2 sm:grid-cols-[100px_1fr] sm:items-center">
                  <span className="text-xs font-medium text-slate-600">{point.period}</span>
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="w-16 text-[10px] text-slate-500">Actual</span>
                      <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-teal-600" style={{ width: `${Math.min(100, (point.actual_quantity / maxValue) * 100)}%` }} /></div>
                      <span className="w-24 text-right text-[10px] text-slate-600">{formatQuantity(point.actual_quantity, unit)}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="w-16 text-[10px] text-slate-500">Planned</span>
                      <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-slate-400" style={{ width: `${Math.min(100, (point.planned_quantity / maxValue) * 100)}%` }} /></div>
                      <span className="w-24 text-right text-[10px] text-slate-600">{formatQuantity(point.planned_quantity, unit)}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          );
        })}
      </div>
    </Card>
  );
}
