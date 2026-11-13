"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useMemo, useState, type FormEvent, type ReactNode } from "react";

import { apiFetch, errorMessage } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Page, Project, UserSummary } from "@/lib/types";
import type {
  AlertReportRow,
  AlertsReportSection,
  AuditReportRow,
  AuditReportSection,
  ReportCountBreakdown,
} from "@/lib/alerts-audit-reporting-types";

const ACTIONS = [
  "CREATE",
  "UPDATE",
  "DELETE",
  "STATUS_CHANGED",
  "DEADLINE_CHANGED",
  "MEMBERS_CHANGED",
  "BOM_CHANGED",
  "INVENTORY_ALLOCATED",
  "INVENTORY_RELEASED",
  "INVENTORY_ADJUSTED",
  "INVENTORY_RECEIVED",
  "APPROVE",
  "REJECT",
  "ORDER",
  "DELIVER",
  "TEST_RESULT",
  "PASSWORD_CHANGED",
  "PASSWORD_RESET",
];

const ENTITIES = [
  "project",
  "inventory_item",
  "purchase_request",
  "progress_log",
  "attachment",
  "user",
  "settings",
  "production_entry",
  "production_action",
  "production_monthly_review",
  "alert",
];

type Tab = "alerts" | "audit";

function isoDate(value: Date): string {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function initialRange() {
  const today = new Date();
  const start = new Date(today);
  start.setDate(today.getDate() - 29);
  return { from: isoDate(start), to: isoDate(today) };
}

function dateLabel(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(new Date(`${value.slice(0, 10)}T00:00:00`));
}

function dateTimeLabel(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function humanize(value: string): string {
  return value.toLowerCase().split("_").map((part) => part.charAt(0).toUpperCase() + part.slice(1)).join(" ");
}

function makeQuery(values: Record<string, string>): string {
  const params = new URLSearchParams();
  Object.entries(values).forEach(([key, value]) => {
    if (value !== "") params.set(key, value);
  });
  return params.toString();
}

function Metric({ label, value, detail }: { label: string; value: ReactNode; detail?: string }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <p className="text-xs font-medium text-slate-500">{label}</p>
      <p className="mt-2 text-2xl font-bold tracking-tight text-slate-900">{value}</p>
      {detail ? <p className="mt-1 text-xs text-slate-500">{detail}</p> : null}
    </div>
  );
}

function Breakdown({ title, rows }: { title: string; rows: ReportCountBreakdown[] }) {
  const maximum = Math.max(1, ...rows.map((row) => row.count));
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="text-sm font-semibold text-slate-900">{title}</h2>
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
                <div className="h-full rounded-full bg-[#0f7185]" style={{ width: `${(row.count / maximum) * 100}%` }} />
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

type TrendPoint = { period: string; alerts_created?: number; events?: number };

function Trend({
  title,
  points,
  valueKey,
}: {
  title: string;
  points: TrendPoint[];
  valueKey: "alerts_created" | "events";
}) {
  const maximum = Math.max(1, ...points.map((point) => Number(point[valueKey] ?? 0)));
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="text-sm font-semibold text-slate-900">{title}</h2>
      {points.length === 0 ? (
        <p className="mt-4 text-sm text-slate-500">No trend data in this selection.</p>
      ) : (
        <div className="mt-4 space-y-3">
          {points.map((point) => {
            const value = Number(point[valueKey] ?? 0);
            return (
              <div key={point.period}>
                <div className="mb-1 flex items-center justify-between gap-3 text-xs">
                  <span className="font-medium text-slate-700">{dateLabel(point.period)}</span>
                  <span className="tabular-nums text-slate-500">{value}</span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-slate-100">
                  <div className="h-full rounded-full bg-[#0f7185]" style={{ width: `${(value / maximum) * 100}%` }} />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}

function ScopeNote({ children }: { children: string }) {
  return <p className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-xs leading-5 text-slate-600">{children}</p>;
}

function AlertTable({ rows }: { rows: AlertReportRow[] }) {
  return (
    <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
      <table className="min-w-full divide-y divide-slate-200 text-sm">
        <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
          <tr>
            <th className="px-4 py-3">Alert</th><th className="px-4 py-3">Project</th><th className="px-4 py-3">Type</th><th className="px-4 py-3">Read state</th><th className="px-4 py-3">Alert date</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {rows.map((row) => (
            <tr key={row.id} className="align-top">
              <td className="max-w-xl px-4 py-3 text-slate-700">{row.message}</td>
              <td className="whitespace-nowrap px-4 py-3 font-medium text-slate-800">{row.project_name}</td>
              <td className="whitespace-nowrap px-4 py-3"><span className={`rounded-full px-2 py-1 text-xs font-semibold ${row.alert_type === "ESCALATED" ? "bg-rose-50 text-rose-700" : "bg-sky-50 text-sky-700"}`}>{humanize(row.alert_type)}</span></td>
              <td className="whitespace-nowrap px-4 py-3 text-slate-600">{row.is_read ? "Read" : "Unread"}</td>
              <td className="whitespace-nowrap px-4 py-3 text-slate-600">{dateLabel(row.alert_date)}</td>
            </tr>
          ))}
          {rows.length === 0 ? <tr><td colSpan={5} className="px-4 py-10 text-center text-sm text-slate-500">No alerts match these filters.</td></tr> : null}
        </tbody>
      </table>
    </div>
  );
}

function AuditTable({ rows }: { rows: AuditReportRow[] }) {
  return (
    <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
      <table className="min-w-full divide-y divide-slate-200 text-sm">
        <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
          <tr><th className="px-4 py-3">Timestamp</th><th className="px-4 py-3">Actor</th><th className="px-4 py-3">Action</th><th className="px-4 py-3">Entity</th><th className="px-4 py-3">Entity ID</th></tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {rows.map((row) => (
            <tr key={row.id}>
              <td className="whitespace-nowrap px-4 py-3 text-slate-600">{dateTimeLabel(row.created_at)}</td>
              <td className="whitespace-nowrap px-4 py-3 font-medium text-slate-800">{row.actor_name}</td>
              <td className="whitespace-nowrap px-4 py-3 text-slate-700">{humanize(row.action)}</td>
              <td className="whitespace-nowrap px-4 py-3 text-slate-700">{humanize(row.entity)}</td>
              <td className="max-w-48 truncate px-4 py-3 font-mono text-xs text-slate-500">{row.entity_id ?? "—"}</td>
            </tr>
          ))}
          {rows.length === 0 ? <tr><td colSpan={5} className="px-4 py-10 text-center text-sm text-slate-500">No audit events match these filters.</td></tr> : null}
        </tbody>
      </table>
    </div>
  );
}

export default function AlertsAuditReportsPage() {
  const { user } = useAuth();
  const isSuperAdmin = user?.role === "SUPER_ADMIN";
  const initial = useMemo(() => initialRange(), []);
  const [tab, setTab] = useState<Tab>("alerts");
  const [dateFrom, setDateFrom] = useState(initial.from);
  const [dateTo, setDateTo] = useState(initial.to);
  const [projectId, setProjectId] = useState("");
  const [alertType, setAlertType] = useState("");
  const [readState, setReadState] = useState("");
  const [actorId, setActorId] = useState("");
  const [action, setAction] = useState("");
  const [entity, setEntity] = useState("");
  const [filterError, setFilterError] = useState<string | null>(null);
  const [applied, setApplied] = useState({
    dateFrom: initial.from,
    dateTo: initial.to,
    projectId: "",
    alertType: "",
    readState: "",
    actorId: "",
    action: "",
    entity: "",
  });

  const projectOptions = useQuery({
    queryKey: ["alerts-audit-report-projects"],
    queryFn: () => apiFetch<Page<Project>>("/projects?page=1&page_size=100"),
  });
  const userOptions = useQuery({
    queryKey: ["alerts-audit-report-users"],
    queryFn: () => apiFetch<UserSummary[]>("/users/options"),
    enabled: isSuperAdmin,
  });

  const alertsQueryString = useMemo(() => makeQuery({
    date_from: applied.dateFrom,
    date_to: applied.dateTo,
    project_id: applied.projectId,
    alert_type: applied.alertType,
    is_read: applied.readState,
  }), [applied]);
  const auditQueryString = useMemo(() => makeQuery({
    date_from: applied.dateFrom,
    date_to: applied.dateTo,
    actor_id: applied.actorId,
    action: applied.action,
    entity: applied.entity,
  }), [applied]);

  const alertsQuery = useQuery({
    queryKey: ["alerts-audit-report", "alerts", alertsQueryString],
    queryFn: () => apiFetch<AlertsReportSection>(`/reports/alerts-audit/alerts?${alertsQueryString}`),
    enabled: tab === "alerts",
    placeholderData: keepPreviousData,
  });
  const auditQuery = useQuery({
    queryKey: ["alerts-audit-report", "audit", auditQueryString],
    queryFn: () => apiFetch<AuditReportSection>(`/reports/alerts-audit/audit?${auditQueryString}`),
    enabled: tab === "audit" && isSuperAdmin,
    placeholderData: keepPreviousData,
  });

  function applyFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!dateFrom || !dateTo || dateFrom > dateTo) {
      setFilterError("The start date must be on or before the end date.");
      return;
    }
    const days = (new Date(`${dateTo}T00:00:00`).getTime() - new Date(`${dateFrom}T00:00:00`).getTime()) / 86_400_000;
    if (days > 365) {
      setFilterError("Choose a reporting period of 366 days or less.");
      return;
    }
    setFilterError(null);
    setApplied({ dateFrom, dateTo, projectId, alertType, readState, actorId, action, entity });
  }

  function clearFilters() {
    setDateFrom(initial.from);
    setDateTo(initial.to);
    setProjectId("");
    setAlertType("");
    setReadState("");
    setActorId("");
    setAction("");
    setEntity("");
    setFilterError(null);
    setApplied({ dateFrom: initial.from, dateTo: initial.to, projectId: "", alertType: "", readState: "", actorId: "", action: "", entity: "" });
  }

  const isLoading = tab === "alerts" ? alertsQuery.isLoading : auditQuery.isLoading;
  const queryError = tab === "alerts" ? alertsQuery.error : auditQuery.error;
  const hasAppliedFilters = Boolean(applied.projectId || applied.alertType || applied.readState || applied.actorId || applied.action || applied.entity);

  return (
    <div className="animate-rise-in space-y-5">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#0f7185]">Reports</p>
        <h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-900">Alerts &amp; Audit Reports</h1>
        <p className="mt-1 max-w-3xl text-sm text-slate-500">Review notification activity and, for Super Admins, operational audit activity across MIS.</p>
      </div>

      <div className="flex flex-wrap gap-2 border-b border-slate-200">
        <button type="button" onClick={() => setTab("alerts")} className={`border-b-2 px-4 py-2 text-sm font-semibold ${tab === "alerts" ? "border-[#0f7185] text-[#0f7185]" : "border-transparent text-slate-500 hover:text-slate-900"}`}>Alerts</button>
        {isSuperAdmin ? <button type="button" onClick={() => setTab("audit")} className={`border-b-2 px-4 py-2 text-sm font-semibold ${tab === "audit" ? "border-[#0f7185] text-[#0f7185]" : "border-transparent text-slate-500 hover:text-slate-900"}`}>Audit</button> : null}
      </div>

      <form onSubmit={applyFilters} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <label className="text-xs font-semibold text-slate-600">From date<input type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} className="mt-1 block h-10 w-full rounded-lg border border-slate-300 px-3 text-sm font-normal text-slate-800 outline-none focus:border-[#0f7185] focus:ring-2 focus:ring-[#0f7185]/15" /></label>
          <label className="text-xs font-semibold text-slate-600">To date<input type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} className="mt-1 block h-10 w-full rounded-lg border border-slate-300 px-3 text-sm font-normal text-slate-800 outline-none focus:border-[#0f7185] focus:ring-2 focus:ring-[#0f7185]/15" /></label>
          {tab === "alerts" ? (
            <>
              <label className="text-xs font-semibold text-slate-600">Project<select value={projectId} onChange={(event) => setProjectId(event.target.value)} className="mt-1 block h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm font-normal text-slate-800"><option value="">All visible projects</option>{projectOptions.data?.items.map((project) => <option key={project.id} value={project.id}>{project.name}</option>)}</select></label>
              <label className="text-xs font-semibold text-slate-600">Alert type<select value={alertType} onChange={(event) => setAlertType(event.target.value)} className="mt-1 block h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm font-normal text-slate-800"><option value="">All types</option><option value="STANDARD">Standard</option><option value="ESCALATED">Escalated</option></select></label>
              <label className="text-xs font-semibold text-slate-600">Read state<select value={readState} onChange={(event) => setReadState(event.target.value)} className="mt-1 block h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm font-normal text-slate-800"><option value="">All</option><option value="false">Unread</option><option value="true">Read</option></select></label>
            </>
          ) : isSuperAdmin ? (
            <>
              <label className="text-xs font-semibold text-slate-600">Actor<select value={actorId} onChange={(event) => setActorId(event.target.value)} className="mt-1 block h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm font-normal text-slate-800"><option value="">All actors</option>{userOptions.data?.map((person) => <option key={person.id} value={person.id}>{person.name} · {person.email}</option>)}</select></label>
              <label className="text-xs font-semibold text-slate-600">Action<select value={action} onChange={(event) => setAction(event.target.value)} className="mt-1 block h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm font-normal text-slate-800"><option value="">All actions</option>{ACTIONS.map((value) => <option key={value} value={value}>{humanize(value)}</option>)}</select></label>
              <label className="text-xs font-semibold text-slate-600">Entity<select value={entity} onChange={(event) => setEntity(event.target.value)} className="mt-1 block h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm font-normal text-slate-800"><option value="">All entities</option>{ENTITIES.map((value) => <option key={value} value={value}>{humanize(value)}</option>)}</select></label>
            </>
          ) : null}
        </div>
        {filterError ? <p className="mt-3 text-sm text-rose-700">{filterError}</p> : null}
        <div className="mt-4 flex flex-wrap justify-end gap-2">
          {hasAppliedFilters ? <button type="button" onClick={clearFilters} className="rounded-lg px-3 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-100">Clear filters</button> : null}
          <button type="submit" className="rounded-lg bg-[#0f5c73] px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-[#0a4d61]">Apply filters</button>
        </div>
      </form>

      {queryError ? <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">Unable to load this report: {errorMessage(queryError)}</div> : isLoading ? <div className="rounded-xl border border-slate-200 bg-white p-8 text-sm text-slate-500">Loading report…</div> : tab === "alerts" && alertsQuery.data ? (
        <AlertsContent report={alertsQuery.data} />
      ) : tab === "audit" && isSuperAdmin && auditQuery.data ? (
        <AuditContent report={auditQuery.data} />
      ) : null}
    </div>
  );
}

function AlertsContent({ report }: { report: AlertsReportSection }) {
  return (
    <div className="space-y-5">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        <Metric label="Total alerts" value={report.total_alerts} />
        <Metric label="Unread" value={report.unread_alerts} />
        <Metric label="Read" value={report.read_alerts} />
        <Metric label="Escalated" value={report.escalated_alerts} />
        <Metric label="Projects with alerts" value={report.projects_with_alerts} />
      </div>
      <div className="grid gap-4 xl:grid-cols-2">
        <Breakdown title="Alerts by type" rows={report.type_breakdown} />
        <Trend title="Alert creation trend" points={report.trend} valueKey="alerts_created" />
      </div>
      <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="text-sm font-semibold text-slate-900">Projects with the most alerts</h2>
        {report.project_breakdown.length === 0 ? <p className="mt-4 text-sm text-slate-500">No project alert activity.</p> : <div className="mt-4 overflow-x-auto"><table className="min-w-full text-sm"><thead className="text-left text-xs uppercase text-slate-500"><tr><th className="py-2 pr-4">Project</th><th className="py-2 pr-4">Total</th><th className="py-2 pr-4">Unread</th><th className="py-2">Escalated</th></tr></thead><tbody className="divide-y divide-slate-100">{report.project_breakdown.map((row) => <tr key={row.project_id}><td className="py-3 pr-4 font-medium text-slate-800">{row.project_name}</td><td className="py-3 pr-4 tabular-nums">{row.total_alerts}</td><td className="py-3 pr-4 tabular-nums">{row.unread_alerts}</td><td className="py-3 tabular-nums">{row.escalated_alerts}</td></tr>)}</tbody></table></div>}
      </section>
      <section className="space-y-3"><h2 className="text-sm font-semibold text-slate-900">Alert details</h2><AlertTable rows={report.items} /></section>
      <ScopeNote>{report.scope_note}</ScopeNote>
    </div>
  );
}

function AuditContent({ report }: { report: AuditReportSection }) {
  return (
    <div className="space-y-5">
      <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-xs leading-5 text-amber-900">Super Admin report. It shows audit metadata only and does not expose before/after payloads. Use the Audit Trail page for authorized record-level inspection.</div>
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        <Metric label="Total audit events" value={report.total_events} />
        <Metric label="Unique actors" value={report.unique_actors} />
        <Metric label="Entity references affected" value={report.unique_entity_references} />
      </div>
      <div className="grid gap-4 xl:grid-cols-2">
        <Breakdown title="Events by action" rows={report.action_breakdown} />
        <Breakdown title="Events by entity" rows={report.entity_breakdown} />
        <Trend title="Audit activity trend" points={report.trend} valueKey="events" />
        <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"><h2 className="text-sm font-semibold text-slate-900">Most active actors</h2>{report.actor_breakdown.length === 0 ? <p className="mt-4 text-sm text-slate-500">No audit activity in this selection.</p> : <div className="mt-4 space-y-3">{report.actor_breakdown.map((row) => <div key={row.actor_id ?? row.actor_name} className="flex items-center justify-between gap-3 text-sm"><span className="truncate font-medium text-slate-700">{row.actor_name}</span><span className="tabular-nums text-slate-500">{row.events}</span></div>)}</div>}</section>
      </div>
      <section className="space-y-3"><h2 className="text-sm font-semibold text-slate-900">Audit event details</h2><AuditTable rows={report.items} /></section>
      <ScopeNote>{report.scope_note}</ScopeNote>
    </div>
  );
}
