"use client";

import { useQuery } from "@tanstack/react-query";
import { useMemo, useState, type FormEvent, type ReactNode } from "react";

import {
  AlertBanner,
  Button,
  Card,
  Field,
  Input,
  PageHeader,
  Select,
  Skeleton,
} from "@/components/ui";
import { apiFetch, errorMessage } from "@/lib/api";
import type { Page, Project } from "@/lib/types";
import type {
  CountBreakdown,
  OperationsReportSummary,
} from "@/lib/operations-reporting-types";

function isoDate(value: Date): string {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function initialDateRange() {
  const today = new Date();
  const start = new Date(today);
  start.setDate(today.getDate() - 29);
  return { from: isoDate(start), to: isoDate(today) };
}

function humanize(value: string): string {
  return value
    .toLowerCase()
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function formatDate(value: string | null): string {
  if (!value) return "—";
  return new Intl.DateTimeFormat(undefined, {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(new Date(`${value.slice(0, 10)}T00:00:00`));
}

function formatNumber(value: number | null, digits = 0): string {
  if (value === null) return "—";
  return new Intl.NumberFormat(undefined, {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  }).format(value);
}

function Metric({
  label,
  value,
  detail,
  warning = false,
}: {
  label: string;
  value: ReactNode;
  detail?: string;
  warning?: boolean;
}) {
  return (
    <Card className="p-4">
      <p className="text-xs font-medium text-slate-500">{label}</p>
      <p
        className={`mt-2 text-2xl font-bold tracking-tight ${warning ? "text-amber-700" : "text-slate-900"}`}
      >
        {value}
      </p>
      {detail ? <p className="mt-1 text-xs text-slate-500">{detail}</p> : null}
    </Card>
  );
}

function Breakdown({ title, rows }: { title: string; rows: CountBreakdown[] }) {
  const maximum = Math.max(1, ...rows.map((row) => row.count));
  return (
    <Card className="p-5">
      <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
      {rows.length === 0 ? (
        <p className="mt-4 text-sm text-slate-500">No records in this selection.</p>
      ) : (
        <div className="mt-4 space-y-3">
          {rows.map((row) => (
            <div key={row.label}>
              <div className="mb-1 flex items-center justify-between gap-3 text-xs">
                <span className="font-medium text-slate-700">{humanize(row.label)}</span>
                <span className="tabular-nums text-slate-500">{row.count}</span>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-slate-100">
                <div
                  className="h-full rounded-full bg-[#0f7185]"
                  style={{ width: `${(row.count / maximum) * 100}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

function ProjectTrend({ points }: { points: { period: string; projects_created: number }[] }) {
  const maximum = Math.max(1, ...points.map((point) => point.projects_created));
  return (
    <Card className="p-5">
      <h3 className="text-sm font-semibold text-slate-900">Project creation trend</h3>
      {points.length === 0 ? (
        <p className="mt-4 text-sm text-slate-500">No projects were created in this period.</p>
      ) : (
        <div className="mt-4 space-y-3">
          {points.map((point) => (
            <div key={point.period}>
              <div className="mb-1 flex items-center justify-between gap-3 text-xs">
                <span className="font-medium text-slate-700">{formatDate(point.period)}</span>
                <span className="tabular-nums text-slate-500">{point.projects_created}</span>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-slate-100">
                <div
                  className="h-full rounded-full bg-[#0f7185]"
                  style={{ width: `${(point.projects_created / maximum) * 100}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

function ScopeNote({ children }: { children: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-xs leading-5 text-slate-600">
      {children}
    </div>
  );
}

type Tab = "projects" | "inventory" | "purchases";

export default function OperationsReportsPage() {
  const initial = useMemo(() => initialDateRange(), []);
  const [dateFrom, setDateFrom] = useState(initial.from);
  const [dateTo, setDateTo] = useState(initial.to);
  const [projectId, setProjectId] = useState("");
  const [projectStatus, setProjectStatus] = useState("");
  const [projectType, setProjectType] = useState("");
  const [priority, setPriority] = useState("");
  const [purchaseStatus, setPurchaseStatus] = useState("");
  const [filterError, setFilterError] = useState<string | null>(null);
  const [applied, setApplied] = useState({
    dateFrom: initial.from,
    dateTo: initial.to,
    projectId: "",
    projectStatus: "",
    projectType: "",
    priority: "",
    purchaseStatus: "",
  });
  const [tab, setTab] = useState<Tab>("projects");

  const projectOptions = useQuery({
    queryKey: ["operations-report-project-options"],
    queryFn: () => apiFetch<Page<Project>>("/projects?page=1&page_size=100"),
  });

  const queryString = useMemo(() => {
    const params = new URLSearchParams({
      date_from: applied.dateFrom,
      date_to: applied.dateTo,
    });
    if (applied.projectId) params.set("project_id", applied.projectId);
    if (applied.projectStatus) params.set("project_status", applied.projectStatus);
    if (applied.projectType) params.set("project_type", applied.projectType);
    if (applied.priority) params.set("priority", applied.priority);
    if (applied.purchaseStatus) params.set("purchase_status", applied.purchaseStatus);
    return params.toString();
  }, [applied]);

  const reportQuery = useQuery({
    queryKey: ["operations-report", queryString],
    queryFn: () =>
      apiFetch<OperationsReportSummary>(`/operations/reports/summary?${queryString}`),
  });

  function applyFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!dateFrom || !dateTo || dateFrom > dateTo) {
      setFilterError("The start date must be on or before the end date.");
      return;
    }
    const dayDifference =
      (new Date(`${dateTo}T00:00:00`).getTime() -
        new Date(`${dateFrom}T00:00:00`).getTime()) /
      86_400_000;
    if (dayDifference > 365) {
      setFilterError("Choose a reporting period of 366 days or less.");
      return;
    }
    setFilterError(null);
    setApplied({
      dateFrom,
      dateTo,
      projectId,
      projectStatus,
      projectType,
      priority,
      purchaseStatus,
    });
  }

  const report = reportQuery.data;
  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Reports"
        title="Projects, inventory & purchasing"
        description="Review project portfolio health, current stock against active project demand, and purchase-request throughput in one place."
      />

      <Card className="p-5">
        <form className="space-y-4" onSubmit={applyFilters}>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <Field label="Start date">
              <Input
                type="date"
                value={dateFrom}
                onChange={(event) => setDateFrom(event.target.value)}
                required
              />
            </Field>
            <Field label="End date">
              <Input
                type="date"
                value={dateTo}
                onChange={(event) => setDateTo(event.target.value)}
                required
              />
            </Field>
            <Field label="Project">
              <Select value={projectId} onChange={(event) => setProjectId(event.target.value)}>
                <option value="">All projects</option>
                {(projectOptions.data?.items ?? []).map((project) => (
                  <option key={project.id} value={project.id}>
                    {project.name}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Project status">
              <Select
                value={projectStatus}
                onChange={(event) => setProjectStatus(event.target.value)}
              >
                <option value="">All statuses</option>
                {[
                  "PENDING_INVENTORY",
                  "READY_FOR_PRODUCTION",
                  "AWAITING_DELIVERY",
                  "IN_PRODUCTION",
                  "IN_TESTING",
                  "COMPLETED",
                ].map((value) => (
                  <option key={value} value={value}>
                    {humanize(value)}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Project type">
              <Select value={projectType} onChange={(event) => setProjectType(event.target.value)}>
                <option value="">All types</option>
                <option value="RND">R&amp;D</option>
                <option value="PRODUCTION">Production</option>
              </Select>
            </Field>
            <Field label="Priority">
              <Select value={priority} onChange={(event) => setPriority(event.target.value)}>
                <option value="">All priorities</option>
                {(["LOW", "MEDIUM", "HIGH", "CRITICAL"] as const).map((value) => (
                  <option key={value} value={value}>
                    {humanize(value)}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Purchase status">
              <Select
                value={purchaseStatus}
                onChange={(event) => setPurchaseStatus(event.target.value)}
              >
                <option value="">All statuses</option>
                {(["PENDING", "APPROVED", "REJECTED", "ORDERED", "DELIVERED"] as const).map(
                  (value) => (
                    <option key={value} value={value}>
                      {humanize(value)}
                    </option>
                  ),
                )}
              </Select>
            </Field>
          </div>
          {filterError ? <AlertBanner tone="danger">{filterError}</AlertBanner> : null}
          <div className="flex flex-wrap items-center gap-3">
            <Button type="submit" loading={reportQuery.isFetching}>
              Apply filters
            </Button>
            <p className="text-xs text-slate-500">
              Project and purchase records use the selected creation-date range. Inventory is a current snapshot.
            </p>
          </div>
        </form>
      </Card>

      {reportQuery.isError ? (
        <AlertBanner tone="danger" title="Could not load operations reports">
          {errorMessage(reportQuery.error)}
        </AlertBanner>
      ) : null}
      {reportQuery.isLoading ? (
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <Skeleton key={index} className="h-28" />
          ))}
        </div>
      ) : null}

      {report ? (
        <>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="font-semibold text-slate-900">Reporting results</h2>
              <p className="text-xs text-slate-500">
                {report.filters.date_from} to {report.filters.date_to} · Inventory snapshot {report.inventory.as_of}
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button size="sm" variant={tab === "projects" ? "primary" : "outline"} onClick={() => setTab("projects")}>Projects</Button>
              <Button size="sm" variant={tab === "inventory" ? "primary" : "outline"} onClick={() => setTab("inventory")}>Inventory</Button>
              <Button size="sm" variant={tab === "purchases" ? "primary" : "outline"} onClick={() => setTab("purchases")}>Purchases</Button>
            </div>
          </div>

          {tab === "projects" ? (
            <section className="space-y-4">
              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                <Metric label="Projects created in period" value={report.projects.total_projects} />
                <Metric label="Average current progress" value={report.projects.average_progress_percent === null ? "—" : `${formatNumber(report.projects.average_progress_percent, 1)}%`} />
                <Metric label="Currently overdue" value={report.projects.current_overdue_projects} warning={report.projects.current_overdue_projects > 0} />
                <Metric label="Progress updates in period" value={report.projects.progress_updates_in_period} />
              </div>
              <div className="grid gap-4 xl:grid-cols-2">
                <Breakdown title="Projects by current status" rows={report.projects.status_breakdown} />
                <Breakdown title="Projects by priority" rows={report.projects.priority_breakdown} />
              </div>
              <ProjectTrend points={report.projects.creation_trend} />
              <Card className="overflow-hidden">
                <div className="border-b border-slate-200 px-5 py-4">
                  <h3 className="text-sm font-semibold text-slate-900">Project portfolio</h3>
                  <p className="mt-1 text-xs text-slate-500">Latest matching projects, with current status and progress.</p>
                </div>
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-slate-200 text-sm">
                    <thead className="bg-slate-50 text-left text-xs text-slate-500">
                      <tr>
                        <th className="px-4 py-3 font-semibold">Project</th>
                        <th className="px-4 py-3 font-semibold">Status</th>
                        <th className="px-4 py-3 font-semibold">Priority</th>
                        <th className="px-4 py-3 font-semibold">Progress</th>
                        <th className="px-4 py-3 font-semibold">Deadline</th>
                        <th className="px-4 py-3 font-semibold">BOM shortage lines</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {report.projects.items.map((item) => (
                        <tr key={item.id}>
                          <td className="px-4 py-3">
                            <p className="font-medium text-slate-900">{item.name}</p>
                            <p className="text-xs text-slate-500">{humanize(item.type)} · Created {formatDate(item.created_at)}</p>
                          </td>
                          <td className="px-4 py-3 text-xs text-slate-700">{humanize(item.status)}</td>
                          <td className="px-4 py-3 text-xs text-slate-700">{humanize(item.priority)}</td>
                          <td className="px-4 py-3">
                            <div className="flex min-w-24 items-center gap-2">
                              <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-slate-100">
                                <div className="h-full rounded-full bg-[#0f7185]" style={{ width: `${item.progress_percent}%` }} />
                              </div>
                              <span className="text-xs tabular-nums text-slate-600">{item.progress_percent}%</span>
                            </div>
                          </td>
                          <td className="px-4 py-3 text-xs text-slate-600">{formatDate(item.end_date)}</td>
                          <td className="px-4 py-3 text-xs tabular-nums text-slate-700">{item.shortage_lines}</td>
                        </tr>
                      ))}
                      {report.projects.items.length === 0 ? (
                        <tr><td colSpan={6} className="px-4 py-10 text-center text-sm text-slate-500">No projects match this period and filter selection.</td></tr>
                      ) : null}
                    </tbody>
                  </table>
                </div>
              </Card>
              <ScopeNote>{report.projects.scope_note}</ScopeNote>
            </section>
          ) : null}

          {tab === "inventory" ? (
            <section className="space-y-4">
              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                <Metric label="Inventory SKUs" value={report.inventory.total_items} />
                <Metric label="Zero-stock items" value={report.inventory.zero_stock_items} warning={report.inventory.zero_stock_items > 0} />
                <Metric label="Items required by active projects" value={report.inventory.items_with_active_project_demand} />
                <Metric label="Items with active-project shortage" value={report.inventory.items_with_active_project_shortage} warning={report.inventory.items_with_active_project_shortage > 0} />
              </div>
              <Card className="overflow-hidden">
                <div className="border-b border-slate-200 px-5 py-4">
                  <h3 className="text-sm font-semibold text-slate-900">Current stock by SKU</h3>
                  <p className="mt-1 text-xs text-slate-500">Available stock is shown separately for each item. No unlike SKU quantities are combined.</p>
                </div>
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-slate-200 text-sm">
                    <thead className="bg-slate-50 text-left text-xs text-slate-500">
                      <tr>
                        <th className="px-4 py-3 font-semibold">Item / SKU</th>
                        <th className="px-4 py-3 font-semibold">Available now</th>
                        <th className="px-4 py-3 font-semibold">Active project demand</th>
                        <th className="px-4 py-3 font-semibold">Allocated</th>
                        <th className="px-4 py-3 font-semibold">Shortage</th>
                        <th className="px-4 py-3 font-semibold">Active projects</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {report.inventory.items.map((item) => (
                        <tr key={item.id}>
                          <td className="px-4 py-3"><p className="font-medium text-slate-900">{item.name}</p><p className="text-xs text-slate-500">{item.sku}</p></td>
                          <td className="px-4 py-3 text-xs tabular-nums text-slate-700">{formatNumber(item.quantity_available)}</td>
                          <td className="px-4 py-3 text-xs tabular-nums text-slate-700">{formatNumber(item.active_project_required)}</td>
                          <td className="px-4 py-3 text-xs tabular-nums text-slate-700">{formatNumber(item.active_project_allocated)}</td>
                          <td className={`px-4 py-3 text-xs font-semibold tabular-nums ${item.active_project_shortage > 0 ? "text-amber-700" : "text-slate-700"}`}>{formatNumber(item.active_project_shortage)}</td>
                          <td className="px-4 py-3 text-xs tabular-nums text-slate-700">{item.active_project_count}</td>
                        </tr>
                      ))}
                      {report.inventory.items.length === 0 ? (
                        <tr><td colSpan={6} className="px-4 py-10 text-center text-sm text-slate-500">No inventory items found.</td></tr>
                      ) : null}
                    </tbody>
                  </table>
                </div>
              </Card>
              <ScopeNote>{report.inventory.scope_note}</ScopeNote>
            </section>
          ) : null}

          {tab === "purchases" ? (
            <section className="space-y-4">
              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                <Metric label="Purchase requests created" value={report.purchases.total_requests} />
                <Metric label="Average approval time" value={report.purchases.average_approval_hours === null ? "—" : `${formatNumber(report.purchases.average_approval_hours, 1)} hrs`} />
                <Metric label="Average delivery time" value={report.purchases.average_delivery_days === null ? "—" : `${formatNumber(report.purchases.average_delivery_days, 1)} days`} />
              </div>
              <div className="grid gap-4 xl:grid-cols-2">
                <Breakdown title="Requests by current status" rows={report.purchases.status_breakdown} />
                <Card className="p-5">
                  <h3 className="text-sm font-semibold text-slate-900">Requested quantity by SKU</h3>
                  <p className="mt-1 text-xs text-slate-500">Quantities are grouped by item and not added across unlike SKUs.</p>
                  {report.purchases.by_item.length === 0 ? (
                    <p className="mt-4 text-sm text-slate-500">No purchase requests in this selection.</p>
                  ) : (
                    <div className="mt-4 space-y-3">
                      {report.purchases.by_item.map((item) => (
                        <div key={item.sku} className="flex items-center justify-between gap-4 border-b border-slate-100 pb-2 last:border-0">
                          <div><p className="text-sm font-medium text-slate-800">{item.item_name}</p><p className="text-xs text-slate-500">{item.sku} · {item.request_count} request(s)</p></div>
                          <p className="text-sm font-semibold tabular-nums text-slate-900">{formatNumber(item.requested_quantity)}</p>
                        </div>
                      ))}
                    </div>
                  )}
                </Card>
              </div>
              <Card className="overflow-hidden">
                <div className="border-b border-slate-200 px-5 py-4">
                  <h3 className="text-sm font-semibold text-slate-900">Purchase-request register</h3>
                </div>
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-slate-200 text-sm">
                    <thead className="bg-slate-50 text-left text-xs text-slate-500">
                      <tr>
                        <th className="px-4 py-3 font-semibold">Project / item</th>
                        <th className="px-4 py-3 font-semibold">Quantity</th>
                        <th className="px-4 py-3 font-semibold">Status</th>
                        <th className="px-4 py-3 font-semibold">Requested by</th>
                        <th className="px-4 py-3 font-semibold">Requested</th>
                        <th className="px-4 py-3 font-semibold">Delivered</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {report.purchases.items.map((item) => (
                        <tr key={item.id}>
                          <td className="px-4 py-3"><p className="font-medium text-slate-900">{item.project_name}</p><p className="text-xs text-slate-500">{item.item_name} · {item.sku}</p></td>
                          <td className="px-4 py-3 text-xs tabular-nums text-slate-700">{formatNumber(item.quantity)}</td>
                          <td className="px-4 py-3 text-xs text-slate-700">{humanize(item.status)}</td>
                          <td className="px-4 py-3 text-xs text-slate-700">{item.requester_name}</td>
                          <td className="px-4 py-3 text-xs text-slate-600">{formatDate(item.created_at)}</td>
                          <td className="px-4 py-3 text-xs text-slate-600">{formatDate(item.delivered_at)}</td>
                        </tr>
                      ))}
                      {report.purchases.items.length === 0 ? (
                        <tr><td colSpan={6} className="px-4 py-10 text-center text-sm text-slate-500">No purchase requests match this period and filter selection.</td></tr>
                      ) : null}
                    </tbody>
                  </table>
                </div>
              </Card>
              <ScopeNote>{report.purchases.scope_note}</ScopeNote>
            </section>
          ) : null}
        </>
      ) : null}
    </div>
  );
}
