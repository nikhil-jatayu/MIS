"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";
import {
  ChevronDown,
  ChevronRight,
  History,
  RefreshCw,
  Search,
  ShieldCheck,
  X,
} from "lucide-react";
import { useState } from "react";

import { RequireRole } from "@/components/auth-gate";
import {
  AlertBanner,
  Badge,
  Button,
  Card,
  EmptyState,
  Field,
  Input,
  PageHeader,
  Pagination,
  Select,
  Skeleton,
  Spinner,
} from "@/components/ui";
import { apiFetch, errorMessage } from "@/lib/api";
import type { AuditLog, Page, UserSummary } from "@/lib/types";
import { useDebouncedValue } from "@/lib/use-debounced";
import { buildQuery, formatDateTime } from "@/lib/utils";

const ENTITIES = [
  "project",
  "inventory_item",
  "purchase_request",
  "progress_log",
  "attachment",
  "user",
  "settings",
];

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

export default function AuditPage() {
  return (
    <RequireRole roles={["SUPER_ADMIN"]}>
      <AuditContent />
    </RequireRole>
  );
}

function AuditContent() {
  const [actorId, setActorId] = useState("");
  const [action, setAction] = useState("");
  const [entity, setEntity] = useState("");
  const [entityId, setEntityId] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [page, setPage] = useState(1);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const debouncedEntityId = useDebouncedValue(entityId);

  const usersQuery = useQuery({
    queryKey: ["users", "options"],
    queryFn: () => apiFetch<UserSummary[]>("/users/options"),
  });

  const query = useQuery({
    queryKey: [
      "audit-logs",
      { actorId, action, entity, entityId: debouncedEntityId, dateFrom, dateTo, page },
    ],
    queryFn: () =>
      apiFetch<Page<AuditLog>>(
        `/audit-logs${buildQuery({
          page,
          page_size: 25,
          actor_id: actorId,
          action,
          entity,
          entity_id: debouncedEntityId,
          date_from: dateFrom,
          date_to: dateTo,
        })}`,
      ),
    placeholderData: keepPreviousData,
  });

  const hasFilters = Boolean(
    actorId || action || entity || entityId || dateFrom || dateTo,
  );

  function resetFilters() {
    setActorId("");
    setAction("");
    setEntity("");
    setEntityId("");
    setDateFrom("");
    setDateTo("");
    setPage(1);
  }

  function toggle(id: string) {
    setExpanded((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  return (
    <div className="animate-rise-in">
      <PageHeader
        eyebrow="Read-only governance"
        title="Audit trail"
        description="Append-only record of creates, updates, status changes, inventory movements, password events, and configuration changes."
      />

      <AlertBanner tone="info" title="Immutable history">
        Audit entries cannot be edited or deleted through the application. Payloads
        show before and after snapshots where applicable.
      </AlertBanner>

      <Card className="mt-5 mb-5 p-4">
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          <Field label="Actor" htmlFor="audit-actor">
            <Select
              id="audit-actor"
              value={actorId}
              onChange={(event) => {
                setActorId(event.target.value);
                setPage(1);
              }}
            >
              <option value="">All actors</option>
              {usersQuery.data?.map((user) => (
                <option key={user.id} value={user.id}>
                  {user.name} · {user.email}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Action" htmlFor="audit-action">
            <Select
              id="audit-action"
              value={action}
              onChange={(event) => {
                setAction(event.target.value);
                setPage(1);
              }}
            >
              <option value="">All actions</option>
              {ACTIONS.map((item) => (
                <option key={item} value={item}>
                  {item.replaceAll("_", " ")}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Entity" htmlFor="audit-entity">
            <Select
              id="audit-entity"
              value={entity}
              onChange={(event) => {
                setEntity(event.target.value);
                setPage(1);
              }}
            >
              <option value="">All entities</option>
              {ENTITIES.map((item) => (
                <option key={item} value={item}>
                  {item.replaceAll("_", " ")}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Entity ID" htmlFor="audit-entity-id">
            <div className="relative">
              <Search className="pointer-events-none absolute top-3 left-3 h-4 w-4 text-slate-400" />
              <Input
                id="audit-entity-id"
                value={entityId}
                onChange={(event) => {
                  setEntityId(event.target.value);
                  setPage(1);
                }}
                placeholder="Exact UUID"
                className="pl-9"
              />
            </div>
          </Field>
          <Field label="From date" htmlFor="audit-from">
            <Input
              id="audit-from"
              type="date"
              value={dateFrom}
              onChange={(event) => {
                setDateFrom(event.target.value);
                setPage(1);
              }}
            />
          </Field>
          <Field label="To date" htmlFor="audit-to">
            <Input
              id="audit-to"
              type="date"
              value={dateTo}
              onChange={(event) => {
                setDateTo(event.target.value);
                setPage(1);
              }}
            />
          </Field>
        </div>
        {hasFilters ? (
          <div className="mt-3 flex justify-end">
            <Button variant="ghost" size="sm" onClick={resetFilters}>
              <X className="h-3.5 w-3.5" />
              Clear filters
            </Button>
          </div>
        ) : null}
      </Card>

      {query.isError ? (
        <AlertBanner
          tone="danger"
          title="Unable to load audit logs"
          action={
            <Button variant="outline" size="sm" onClick={() => query.refetch()}>
              <RefreshCw className="h-3.5 w-3.5" />
              Retry
            </Button>
          }
        >
          {errorMessage(query.error)}
        </AlertBanner>
      ) : query.isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 8 }).map((_, index) => (
            <Skeleton key={index} className="h-14" />
          ))}
        </div>
      ) : !query.data?.items.length ? (
        <Card>
          <EmptyState
            icon={<History className="h-5 w-5" />}
            title="No audit entries match"
            description="Adjust the filters to widen the search."
            action={
              hasFilters ? (
                <Button variant="outline" size="sm" onClick={resetFilters}>
                  Clear filters
                </Button>
              ) : undefined
            }
          />
        </Card>
      ) : (
        <Card className="overflow-hidden">
          <div className="flex items-center justify-between border-b border-slate-100 px-5 py-3">
            <p className="text-xs text-slate-500">
              {query.data.total} entr{query.data.total === 1 ? "y" : "ies"}
              {query.isFetching ? (
                <Spinner className="ml-2 h-3 w-3 text-[#0f5c73]" />
              ) : null}
            </p>
            <span className="hidden items-center gap-1 text-[11px] text-slate-400 sm:flex">
              <ShieldCheck className="h-3.5 w-3.5" />
              Append-only
            </span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[920px] text-left text-sm">
              <thead className="bg-slate-50 text-[10px] font-semibold tracking-wide text-slate-500 uppercase">
                <tr>
                  <th className="w-8 px-3 py-3" aria-label="Expand" />
                  <th className="px-3 py-3">Timestamp</th>
                  <th className="px-3 py-3">Actor</th>
                  <th className="px-3 py-3">Action</th>
                  <th className="px-3 py-3">Entity</th>
                  <th className="px-3 py-3">Entity ID</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {query.data.items.map((log) => {
                  const isExpanded = expanded.has(log.id);
                  const hasPayload = Boolean(log.before || log.after);
                  return (
                    <AuditRow
                      key={log.id}
                      log={log}
                      expanded={isExpanded}
                      hasPayload={hasPayload}
                      onToggle={() => toggle(log.id)}
                    />
                  );
                })}
              </tbody>
            </table>
          </div>
          <Pagination
            page={query.data.page}
            pages={query.data.pages}
            total={query.data.total}
            onPageChange={setPage}
          />
        </Card>
      )}
    </div>
  );
}

function AuditRow({
  log,
  expanded,
  hasPayload,
  onToggle,
}: {
  log: AuditLog;
  expanded: boolean;
  hasPayload: boolean;
  onToggle: () => void;
}) {
  return (
    <>
      <tr
        className={
          hasPayload
            ? "cursor-pointer transition hover:bg-slate-50/80"
            : "transition hover:bg-slate-50/80"
        }
        onClick={hasPayload ? onToggle : undefined}
      >
        <td className="px-3 py-3 text-slate-400">
          {hasPayload ? (
            expanded ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronRight className="h-4 w-4" />
            )
          ) : null}
        </td>
        <td className="px-3 py-3 text-xs whitespace-nowrap text-slate-600">
          {formatDateTime(log.created_at)}
        </td>
        <td className="px-3 py-3">
          <p className="text-xs font-medium text-slate-800">
            {log.actor?.name ?? "System"}
          </p>
          {log.actor ? (
            <p className="text-[10px] text-slate-400">{log.actor.email}</p>
          ) : null}
        </td>
        <td className="px-3 py-3">
          <Badge className="border-sky-200 bg-sky-50 font-mono text-[10px] text-sky-800">
            {log.action}
          </Badge>
        </td>
        <td className="px-3 py-3 text-xs text-slate-600">{log.entity}</td>
        <td className="px-3 py-3">
          <span
            className="block max-w-40 truncate font-mono text-[10px] text-slate-400"
            title={log.entity_id ?? undefined}
          >
            {log.entity_id ?? "—"}
          </span>
        </td>
      </tr>
      {expanded && hasPayload ? (
        <tr className="bg-slate-50/80">
          <td colSpan={6} className="px-5 py-4">
            <div className="grid gap-3 lg:grid-cols-2">
              <PayloadPanel title="Before" value={log.before} />
              <PayloadPanel title="After" value={log.after} />
            </div>
          </td>
        </tr>
      ) : null}
    </>
  );
}

function PayloadPanel({
  title,
  value,
}: {
  title: string;
  value: Record<string, unknown> | null;
}) {
  return (
    <div>
      <p className="mb-1.5 text-[10px] font-semibold tracking-wide text-slate-500 uppercase">
        {title}
      </p>
      <pre className="max-h-72 overflow-auto rounded-lg border border-slate-200 bg-white p-3 font-mono text-[10px] leading-5 text-slate-700">
        {value ? JSON.stringify(value, null, 2) : "No data"}
      </pre>
    </div>
  );
}
