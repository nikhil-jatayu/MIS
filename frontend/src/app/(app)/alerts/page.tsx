"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  BellRing,
  CheckCheck,
  Play,
  RefreshCw,
  ShieldAlert,
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { toast } from "sonner";

import { AlertTypeBadge, ProjectStatusBadge } from "@/components/badges";
import {
  AlertBanner,
  Button,
  Card,
  EmptyState,
  PageHeader,
  Pagination,
  Skeleton,
} from "@/components/ui";
import { apiFetch, errorMessage } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Alert, AlertRunResult, MessageResponse, Page } from "@/lib/types";
import { cn, formatDate, formatDateTime } from "@/lib/utils";

export default function AlertsPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [page, setPage] = useState(1);

  const query = useQuery({
    queryKey: ["alerts", { unreadOnly, page }],
    queryFn: () =>
      apiFetch<Page<Alert>>(
        `/alerts?page=${page}&page_size=20&unread_only=${unreadOnly}`,
      ),
  });

  const markAll = useMutation({
    mutationFn: () =>
      apiFetch<MessageResponse>("/alerts/read-all", { method: "POST" }),
    onSuccess: (result) => {
      void queryClient.invalidateQueries({ queryKey: ["alerts"] });
      void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      toast.success(result.message);
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
        `Time Counter complete: ${result.alerts_created} alert(s) created, ${result.duplicates_skipped} duplicate(s) skipped.`,
      );
    },
    onError: (error) => toast.error(errorMessage(error)),
  });

  const markRead = useMutation({
    mutationFn: (id: string) =>
      apiFetch<MessageResponse>(`/alerts/${id}/read`, { method: "POST" }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["alerts"] });
      void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
    onError: (error) => toast.error(errorMessage(error)),
  });

  return (
    <div className="animate-rise-in">
      <PageHeader
        eyebrow="Time Counter"
        title="Alerts"
        description="Deadline and inactivity notifications. Standard alerts go to assigned users; escalated alerts go to Admins and, when severe, Super Admins."
        actions={
          <>
            <Button
              variant="outline"
              onClick={() => markAll.mutate()}
              disabled={markAll.isPending}
              loading={markAll.isPending}
            >
              <CheckCheck className="h-4 w-4" />
              Mark all read
            </Button>
            {user?.role === "SUPER_ADMIN" ? (
              <Button
                onClick={() => runCheck.mutate()}
                loading={runCheck.isPending}
              >
                <Play className="h-4 w-4" />
                Run check now
              </Button>
            ) : null}
          </>
        }
      />

      <AlertBanner tone="info" title="Alert policy">
        A standard reminder is raised when a project has no status or progress
        update beyond the safe threshold, or when its deadline enters the reminder
        window. Escalation replaces the user alert once the escalation threshold is
        crossed. Alerts are de-duplicated per project, type, recipient, and day.
      </AlertBanner>

      <div className="mt-5 mb-4 flex items-center justify-between gap-3">
        <div className="inline-flex rounded-lg border border-slate-200 bg-white p-1 shadow-sm">
          <button
            onClick={() => {
              setUnreadOnly(false);
              setPage(1);
            }}
            className={cn(
              "rounded-md px-3 py-1.5 text-xs font-semibold transition",
              !unreadOnly
                ? "bg-[#0f5c73] text-white"
                : "text-slate-500 hover:text-slate-900",
            )}
          >
            All alerts
          </button>
          <button
            onClick={() => {
              setUnreadOnly(true);
              setPage(1);
            }}
            className={cn(
              "rounded-md px-3 py-1.5 text-xs font-semibold transition",
              unreadOnly
                ? "bg-[#0f5c73] text-white"
                : "text-slate-500 hover:text-slate-900",
            )}
          >
            Unread only
          </button>
        </div>
        {query.data ? (
          <p className="text-xs text-slate-500">
            {query.data.total} alert{query.data.total === 1 ? "" : "s"}
          </p>
        ) : null}
      </div>

      {query.isError ? (
        <AlertBanner
          tone="danger"
          title="Unable to load alerts"
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
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, index) => (
            <Skeleton key={index} className="h-28" />
          ))}
        </div>
      ) : !query.data?.items.length ? (
        <Card>
          <EmptyState
            icon={<BellRing className="h-5 w-5" />}
            title={unreadOnly ? "No unread alerts" : "No alerts yet"}
            description={
              unreadOnly
                ? "You have read every alert. New alerts will appear here after the next Time Counter run."
                : "Alerts will appear when projects approach deadlines or remain inactive beyond the configured thresholds."
            }
          />
        </Card>
      ) : (
        <>
          <div className="space-y-3">
            {query.data.items.map((alert) => (
              <Card
                key={alert.id}
                className={cn(
                  "p-4 transition",
                  !alert.is_read && "border-l-4 border-l-amber-400",
                )}
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <AlertTypeBadge type={alert.type} />
                      {!alert.is_read ? (
                        <span className="inline-flex items-center gap-1 text-[10px] font-bold tracking-wide text-amber-700 uppercase">
                          <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
                          Unread
                        </span>
                      ) : null}
                      <span className="text-[10px] text-slate-400">
                        {formatDateTime(alert.created_at)} ·{" "}
                        Alert date {formatDate(alert.alert_date)}
                      </span>
                    </div>
                    <p className="mt-2 text-sm leading-6 text-slate-700">
                      {alert.message}
                    </p>
                    <Link
                      href={`/projects/${alert.project_id}`}
                      className="mt-2 inline-flex items-center gap-2 text-xs font-semibold text-[#0f5c73] hover:underline"
                    >
                      {alert.project.name}
                      <ProjectStatusBadge status={alert.project.status} />
                    </Link>
                  </div>
                  {!alert.is_read ? (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => markRead.mutate(alert.id)}
                      loading={markRead.isPending && markRead.variables === alert.id}
                    >
                      Mark read
                    </Button>
                  ) : null}
                </div>
              </Card>
            ))}
          </div>
          <div className="mt-5 overflow-hidden rounded-xl border border-slate-200 bg-white">
            <Pagination
              page={query.data.page}
              pages={query.data.pages}
              total={query.data.total}
              onPageChange={setPage}
            />
          </div>
        </>
      )}

      {user?.role === "SUPER_ADMIN" ? (
        <p className="mt-4 flex items-start gap-2 text-[11px] leading-5 text-slate-400">
          <ShieldAlert className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          The daily scheduler uses the thresholds in Time Counter settings. Manual
          runs are useful after changing thresholds or demonstrating the alert
          policy.
        </p>
      ) : null}
    </div>
  );
}
