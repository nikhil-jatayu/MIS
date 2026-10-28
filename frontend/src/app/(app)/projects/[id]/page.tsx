"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  CalendarClock,
  CheckCircle2,
  Circle,
  ClipboardCheck,
  Download,
  FileText,
  History,
  PackageCheck,
  Paperclip,
  Pencil,
  Play,
  Plus,
  RefreshCw,
  ShieldCheck,
  ShoppingCart,
  TriangleAlert,
  Upload,
  Users,
} from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useRef, useState, type ChangeEvent, type ReactNode } from "react";
import { toast } from "sonner";

import {
  MemberRoleBadge,
  PriorityBadge,
  ProjectStatusBadge,
  ProjectTypeBadge,
  PurchaseStatusBadge,
  TestResultBadge,
} from "@/components/badges";
import {
  AlertBanner,
  Avatar,
  Badge,
  Button,
  Card,
  CardHeader,
  EmptyState,
  PageHeader,
  ProgressBar,
  Skeleton,
  Modal,
} from "@/components/ui";
import { apiFetch, apiUrl, errorMessage } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { loadAllInventory } from "@/lib/loaders";
import type {
  Attachment,
  Page,
  ProgressLog,
  Project,
  PurchaseRequest,
  UserSummary,
} from "@/lib/types";
import {
  cn,
  formatBytes,
  formatDate,
  formatDateTime,
  isPastDate,
  pluralise,
  PROJECT_STATUS_LABELS,
} from "@/lib/utils";

import {
  BomModal,
  CompleteProjectModal,
  EditProjectModal,
  MembersModal,
  ProgressModal,
  SubmitTestingModal,
  TestResultModal,
} from "./project-modals";

const FLOW = [
  "PENDING_INVENTORY",
  "READY_FOR_PRODUCTION",
  "IN_PRODUCTION",
  "IN_TESTING",
  "COMPLETED",
] as const;

export default function ProjectDetailPage() {
  const params = useParams<{ id: string }>();
  const projectId = params.id;
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [progressPage, setProgressPage] = useState(1);
  const [editOpen, setEditOpen] = useState(false);
  const [membersOpen, setMembersOpen] = useState(false);
  const [bomOpen, setBomOpen] = useState(false);
  const [progressOpen, setProgressOpen] = useState(false);
  const [testingOpen, setTestingOpen] = useState(false);
  const [resultOpen, setResultOpen] = useState(false);
  const [completeOpen, setCompleteOpen] = useState(false);
  const [startConfirmOpen, setStartConfirmOpen] = useState(false);

  const projectQuery = useQuery({
    queryKey: ["project", projectId],
    queryFn: () => apiFetch<Project>(`/projects/${projectId}`),
    enabled: Boolean(projectId),
  });

  const project = projectQuery.data;
  const isAdmin = user?.role === "ADMIN" || user?.role === "SUPER_ADMIN";
  const isMember = Boolean(
    user && project?.members.some((member) => member.user.id === user.id),
  );
  const canAct = Boolean(isAdmin || isMember);
  const isTester = Boolean(
    user &&
      project?.members.some(
        (member) =>
          member.user.id === user.id && member.role_in_project === "TESTER",
      ),
  );

  const usersQuery = useQuery({
    queryKey: ["users", "options"],
    queryFn: () => apiFetch<UserSummary[]>("/users/options"),
    enabled: isAdmin,
  });

  const inventoryQuery = useQuery({
    queryKey: ["inventory", "all-options"],
    queryFn: loadAllInventory,
    enabled: isAdmin,
  });

  const attachmentsQuery = useQuery({
    queryKey: ["attachments", projectId],
    queryFn: () => apiFetch<Attachment[]>(`/projects/${projectId}/attachments`),
    enabled: Boolean(project) && canAct,
  });

  const progressQuery = useQuery({
    queryKey: ["progress", projectId, progressPage],
    queryFn: () =>
      apiFetch<Page<ProgressLog>>(
        `/projects/${projectId}/progress-logs?page=${progressPage}&page_size=10`,
      ),
    enabled: Boolean(project),
  });

  const purchasesQuery = useQuery({
    queryKey: ["purchase-requests", { projectId, page: 1 }],
    queryFn: () =>
      apiFetch<Page<PurchaseRequest>>(
        `/purchase-requests?project_id=${projectId}&page=1&page_size=100`,
      ),
    enabled: Boolean(project),
  });

  const startProduction = useMutation({
    mutationFn: () =>
      apiFetch<Project>(`/projects/${projectId}/start-production`, {
        method: "POST",
      }),
    onSuccess: () => {
      refreshProject();
      setStartConfirmOpen(false);
      toast.success("Production started");
    },
    onError: (error) => toast.error(errorMessage(error)),
  });

  const createRequest = useMutation({
    mutationFn: (itemId: string) =>
      apiFetch<PurchaseRequest>(`/projects/${projectId}/purchase-requests`, {
        method: "POST",
        body: JSON.stringify({ item_id: itemId }),
      }),
    onSuccess: () => {
      refreshProject();
      void queryClient.invalidateQueries({ queryKey: ["purchase-requests"] });
      toast.success("Purchase request raised for the full remaining shortage");
    },
    onError: (error) => toast.error(errorMessage(error)),
  });

  const upload = useMutation({
    mutationFn: (file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      return apiFetch<Attachment>(`/projects/${projectId}/attachments`, {
        method: "POST",
        body: formData,
      });
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ["attachments", projectId],
      });
      toast.success("Attachment uploaded");
      if (fileInputRef.current) fileInputRef.current.value = "";
    },
    onError: (error) => {
      toast.error(errorMessage(error));
      if (fileInputRef.current) fileInputRef.current.value = "";
    },
  });

  function refreshProject() {
    void queryClient.invalidateQueries({ queryKey: ["project", projectId] });
    void queryClient.invalidateQueries({ queryKey: ["projects"] });
    void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    void queryClient.invalidateQueries({ queryKey: ["inventory"] });
    void queryClient.invalidateQueries({ queryKey: ["progress", projectId] });
    void queryClient.invalidateQueries({
      queryKey: ["purchase-requests"],
    });
  }

  function performRefresh() {
    refreshProject();
    void queryClient.invalidateQueries({
      queryKey: ["attachments", projectId],
    });
    toast.success("Project data refreshed");
  }

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (file) upload.mutate(file);
  }

  if (projectQuery.isLoading) {
    return (
      <div>
        <Skeleton className="h-5 w-32" />
        <Skeleton className="mt-4 h-9 w-96" />
        <Skeleton className="mt-2 h-4 w-[32rem]" />
        <div className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <Skeleton key={index} className="h-28" />
          ))}
        </div>
        <Skeleton className="mt-6 h-96" />
      </div>
    );
  }

  if (projectQuery.isError || !project) {
    return (
      <div>
        <Link
          href="/projects"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-slate-900"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to projects
        </Link>
        <AlertBanner
          tone="danger"
          title="Project unavailable"
          action={
            <Button variant="outline" size="sm" onClick={() => projectQuery.refetch()}>
              <RefreshCw className="h-3.5 w-3.5" />
              Retry
            </Button>
          }
        >
          {errorMessage(projectQuery.error, "This project could not be loaded.")}
        </AlertBanner>
      </div>
    );
  }

  const canEditBom =
    isAdmin &&
    project.status === "PENDING_INVENTORY" &&
    (purchasesQuery.data?.total ?? 0) === 0;
  const canLogProgress =
    canAct && project.status !== "COMPLETED" && Boolean(user);
  const canRecordResult =
    isTester && project.status === "IN_TESTING" && !project.test_result;
  const canComplete =
    isAdmin &&
    project.status === "IN_TESTING" &&
    project.test_result === "PASS";
  const openRequestsByItem = new Map<string, number>();
  for (const request of purchasesQuery.data?.items ?? []) {
    if (["PENDING", "APPROVED", "ORDERED"].includes(request.status)) {
      openRequestsByItem.set(
        request.item_id,
        (openRequestsByItem.get(request.item_id) ?? 0) + request.quantity,
      );
    }
  }
  const flowStatus =
    project.status === "AWAITING_DELIVERY"
      ? (project.paused_from_status ?? "READY_FOR_PRODUCTION")
      : project.status;
  const flowIndex = FLOW.indexOf(flowStatus as (typeof FLOW)[number]);

  return (
    <div className="animate-rise-in">
      <Link
        href="/projects"
        className="mb-4 inline-flex items-center gap-1.5 text-xs font-semibold text-slate-500 transition hover:text-slate-900"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        Back to projects
      </Link>

      <PageHeader
        eyebrow={
          <span className="flex flex-wrap items-center gap-1.5">
            <ProjectTypeBadge type={project.type} />
            <PriorityBadge priority={project.priority} />
            <ProjectStatusBadge status={project.status} />
          </span>
        }
        title={project.name}
        description={project.description || "No project description."}
        actions={
          <>
            <Button variant="ghost" size="icon" onClick={performRefresh} title="Refresh">
              <RefreshCw className="h-4 w-4" />
            </Button>
            {isAdmin ? (
              <>
                <Button variant="outline" onClick={() => setMembersOpen(true)}>
                  <Users className="h-4 w-4" />
                  Manage team
                </Button>
                <Button onClick={() => setEditOpen(true)}>
                  <Pencil className="h-4 w-4" />
                  Edit project
                </Button>
              </>
            ) : null}
          </>
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <SummaryCard
          icon={ClipboardCheck}
          label="Progress"
          value={`${project.progress_percent}%`}
          hint={`${pluralise(project.pending_days, "day")} since status update`}
        >
          <ProgressBar value={project.progress_percent} className="mt-3" />
        </SummaryCard>
        <SummaryCard
          icon={CalendarClock}
          label="Deadline"
          value={formatDate(project.end_date, "Not set")}
          hint={
            project.end_date
              ? isPastDate(project.end_date) && project.status !== "COMPLETED"
                ? "Deadline has passed"
                : `Starts ${formatDate(project.start_date, "not set")}`
              : "Add a deadline from Edit project"
          }
          tone={
            isPastDate(project.end_date) && project.status !== "COMPLETED"
              ? "bg-red-50 text-red-700"
              : "bg-sky-50 text-sky-700"
          }
        />
        <SummaryCard
          icon={PackageCheck}
          label="Inventory"
          value={project.is_inventory_ready ? "Ready" : "Shortages"}
          hint={
            project.is_inventory_ready
              ? "All BOM lines allocated"
              : `${pluralise(project.shortage_count, "BOM line")} short`
          }
          tone={
            project.is_inventory_ready
              ? "bg-emerald-50 text-emerald-700"
              : "bg-amber-50 text-amber-700"
          }
        />
        <SummaryCard
          icon={Users}
          label="Team"
          value={String(project.members.length)}
          hint={`Created by ${project.creator.name}`}
          tone="bg-violet-50 text-violet-700"
        />
      </div>

      {project.status === "AWAITING_DELIVERY" ? (
        <AlertBanner
          tone="warning"
          title="Production paused — awaiting delivery"
          action={
            <Link
              href="/purchases?status=ORDERED"
              className="text-xs font-semibold underline"
            >
              View ordered requests
            </Link>
          }
        >
          {project.delay_reason || "No delay reason recorded."} The project will
          resume automatically when ordered material is delivered and allocated.
        </AlertBanner>
      ) : null}

      <div className="mt-5 grid gap-6 xl:grid-cols-[1.55fr_1fr]">
        <div className="space-y-6">
          <Card>
            <CardHeader
              title="Bill of materials & inventory"
              description={
                project.is_inventory_ready
                  ? "Every required item is fully allocated."
                  : "Raise a purchase request for each remaining shortage."
              }
              action={
                isAdmin ? (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setBomOpen(true)}
                    disabled={!canEditBom || inventoryQuery.isLoading}
                    title={
                      canEditBom
                        ? "Edit BOM"
                        : "BOM is locked after production starts or a purchase request is raised"
                    }
                  >
                    <Pencil className="h-3.5 w-3.5" />
                    Edit BOM
                  </Button>
                ) : null
              }
            />
            {project.bom_lines.length === 0 ? (
              <EmptyState
                icon={<PackageCheck className="h-5 w-5" />}
                title="No material required"
                description="This project has no BOM lines, so it is treated as inventory-ready."
              />
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[640px] text-left text-sm">
                  <thead className="bg-slate-50 text-[10px] font-semibold tracking-wide text-slate-500 uppercase">
                    <tr>
                      <th className="px-5 py-3">Item</th>
                      <th className="px-3 py-3 text-right">Required</th>
                      <th className="px-3 py-3 text-right">Allocated</th>
                      <th className="px-3 py-3 text-right">Shortage</th>
                      <th className="px-5 py-3 text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {project.bom_lines.map((line) => {
                      const openQty = openRequestsByItem.get(line.item.id) ?? 0;
                      const remaining = Math.max(line.quantity_shortage - openQty, 0);
                      return (
                        <tr key={line.id} className="align-middle">
                          <td className="px-5 py-3">
                            <p className="font-medium text-slate-900">{line.item.name}</p>
                            <p className="mt-0.5 font-mono text-[10px] text-slate-500">
                              {line.item.sku} · {line.item.quantity_available} in stock
                            </p>
                          </td>
                          <td className="px-3 py-3 text-right text-slate-700">
                            {line.quantity_required}
                          </td>
                          <td className="px-3 py-3 text-right font-semibold text-slate-900">
                            {line.quantity_allocated}
                          </td>
                          <td className="px-3 py-3 text-right">
                            {line.quantity_shortage > 0 ? (
                              <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-0.5 text-[11px] font-bold text-amber-700">
                                <TriangleAlert className="h-3 w-3" />
                                {line.quantity_shortage}
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-700">
                                <CheckCircle2 className="h-3.5 w-3.5" />
                                None
                              </span>
                            )}
                          </td>
                          <td className="px-5 py-3 text-right">
                            {openQty > 0 ? (
                              <span className="text-[10px] font-medium text-slate-500">
                                {openQty} requested
                              </span>
                            ) : null}
                            {remaining > 0 && canAct ? (
                              <Button
                                variant="outline"
                                size="sm"
                                className="ml-2"
                                onClick={() => createRequest.mutate(line.item.id)}
                                loading={
                                  createRequest.isPending &&
                                  createRequest.variables === line.item.id
                                }
                                disabled={purchasesQuery.isLoading}
                              >
                                <ShoppingCart className="h-3.5 w-3.5" />
                                Request {remaining}
                              </Button>
                            ) : remaining > 0 ? (
                              <span className="text-[11px] text-slate-400">
                                Assigned team only
                              </span>
                            ) : null}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </Card>

          <Card>
            <CardHeader
              title="Progress log"
              description="Append-only history of project updates"
              action={
                canLogProgress ? (
                  <Button variant="outline" size="sm" onClick={() => setProgressOpen(true)}>
                    <Plus className="h-3.5 w-3.5" />
                    Log progress
                  </Button>
                ) : null
              }
            />
            {progressQuery.isLoading ? (
              <div className="space-y-3 p-5">
                <Skeleton className="h-14" />
                <Skeleton className="h-14" />
              </div>
            ) : progressQuery.isError ? (
              <div className="p-5">
                <AlertBanner tone="danger">
                  {errorMessage(progressQuery.error)}
                </AlertBanner>
              </div>
            ) : !progressQuery.data?.items.length ? (
              <EmptyState
                icon={<History className="h-5 w-5" />}
                title="No progress updates yet"
                description="Assigned team members can append notes and percentage progress."
              />
            ) : (
              <>
                <div className="p-5">
                  {progressQuery.data.items.map((log, index) => (
                    <div key={log.id} className="relative flex gap-3 pb-5 last:pb-0">
                      {index < progressQuery.data.items.length - 1 ? (
                        <span className="absolute top-8 bottom-0 left-4 w-px bg-slate-200" />
                      ) : null}
                      <Avatar name={log.user.name} className="relative z-10" />
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <div>
                            <p className="text-xs font-semibold text-slate-900">
                              {log.user.name}
                            </p>
                            <p className="text-[10px] text-slate-400">
                              {formatDateTime(log.created_at)}
                            </p>
                          </div>
                          <Badge className="border-teal-200 bg-teal-50 text-teal-700">
                            {log.progress_percent}%
                          </Badge>
                        </div>
                        <p className="mt-1.5 text-xs leading-5 whitespace-pre-wrap text-slate-600">
                          {log.note}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
                {progressQuery.data.pages > 1 ? (
                  <div className="flex items-center justify-between border-t border-slate-100 px-5 py-3">
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={progressPage <= 1}
                      onClick={() => setProgressPage((current) => current - 1)}
                    >
                      Previous
                    </Button>
                    <span className="text-[11px] text-slate-500">
                      Page {progressQuery.data.page} of {progressQuery.data.pages}
                    </span>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={progressPage >= progressQuery.data.pages}
                      onClick={() => setProgressPage((current) => current + 1)}
                    >
                      Next
                    </Button>
                  </div>
                ) : null}
              </>
            )}
          </Card>

          {canAct ? (
            <Card>
              <CardHeader
                title="Attachments"
                description="Files are stored locally on the server with configured size and type limits."
                action={
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => fileInputRef.current?.click()}
                    loading={upload.isPending}
                  >
                    <Upload className="h-3.5 w-3.5" />
                    Upload file
                  </Button>
                }
              />
              <input
                ref={fileInputRef}
                type="file"
                className="hidden"
                onChange={handleFileChange}
                aria-label="Upload attachment"
              />
              {attachmentsQuery.isLoading ? (
                <div className="space-y-2 p-5">
                  <Skeleton className="h-10" />
                  <Skeleton className="h-10" />
                </div>
              ) : attachmentsQuery.isError ? (
                <div className="p-5">
                  <AlertBanner tone="danger">
                    {errorMessage(attachmentsQuery.error)}
                  </AlertBanner>
                </div>
              ) : !attachmentsQuery.data?.length ? (
                <EmptyState
                  icon={<Paperclip className="h-5 w-5" />}
                  title="No attachments"
                  description="Upload specifications, test evidence, or handover documents."
                />
              ) : (
                <div className="divide-y divide-slate-100">
                  {attachmentsQuery.data.map((attachment) => (
                    <div
                      key={attachment.id}
                      className="flex flex-wrap items-center gap-3 px-5 py-3"
                    >
                      <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-slate-100 text-slate-500">
                        <FileText className="h-4 w-4" />
                      </span>
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-xs font-semibold text-slate-900">
                          {attachment.filename}
                        </p>
                        <p className="text-[10px] text-slate-400">
                          {formatBytes(attachment.size_bytes)} ·{" "}
                          {attachment.uploader.name} ·{" "}
                          {formatDateTime(attachment.created_at)}
                        </p>
                      </div>
                      <a
                        href={apiUrl(attachment.download_url)}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1 rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-[11px] font-semibold text-slate-700 shadow-sm hover:bg-slate-50"
                      >
                        <Download className="h-3.5 w-3.5" />
                        Download
                      </a>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          ) : null}
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader
              title="Workflow"
              description={PROJECT_STATUS_LABELS[project.status]}
            />
            <div className="p-5">
              <ol className="space-y-0">
                {FLOW.map((step, index) => {
                  const active = index === flowIndex;
                  const complete =
                    index < flowIndex || project.status === "COMPLETED";
                  return (
                    <li key={step} className="relative flex gap-3 pb-5 last:pb-0">
                      {index < FLOW.length - 1 ? (
                        <span
                          className={cn(
                            "absolute top-6 bottom-0 left-[11px] w-px",
                            complete ? "bg-teal-300" : "bg-slate-200",
                          )}
                        />
                      ) : null}
                      <span
                        className={cn(
                          "relative z-10 flex h-6 w-6 shrink-0 items-center justify-center rounded-full border-2",
                          complete
                            ? "border-teal-500 bg-teal-500 text-white"
                            : active
                              ? "border-[#0f5c73] bg-white text-[#0f5c73] ring-4 ring-teal-50"
                              : "border-slate-300 bg-white text-slate-300",
                        )}
                      >
                        {complete ? (
                          <CheckCircle2 className="h-3.5 w-3.5" />
                        ) : (
                          <Circle className="h-2 w-2 fill-current" />
                        )}
                      </span>
                      <div className="pt-0.5">
                        <p
                          className={cn(
                            "text-xs font-semibold",
                            active
                              ? "text-slate-900"
                              : complete
                                ? "text-slate-700"
                                : "text-slate-400",
                          )}
                        >
                          {PROJECT_STATUS_LABELS[step]}
                        </p>
                        {active && project.status === "AWAITING_DELIVERY" ? (
                          <p className="mt-0.5 text-[10px] font-medium text-orange-600">
                            Paused · awaiting delivery
                          </p>
                        ) : null}
                      </div>
                    </li>
                  );
                })}
              </ol>

              <div className="mt-4 space-y-2 border-t border-slate-100 pt-4">
                {isAdmin && project.status === "READY_FOR_PRODUCTION" ? (
                  <Button
                    className="w-full"
                    onClick={() => setStartConfirmOpen(true)}
                    loading={startProduction.isPending}
                  >
                    <Play className="h-4 w-4" />
                    Start production
                  </Button>
                ) : null}
                {isAdmin && project.status === "IN_PRODUCTION" ? (
                  <Button className="w-full" onClick={() => setTestingOpen(true)}>
                    <ClipboardCheck className="h-4 w-4" />
                    Submit for testing
                  </Button>
                ) : null}
                {project.status === "IN_TESTING" && !project.test_result ? (
                  canRecordResult ? (
                    <Button
                      className="w-full"
                      variant="success"
                      onClick={() => setResultOpen(true)}
                    >
                      <ClipboardCheck className="h-4 w-4" />
                      Record test result
                    </Button>
                  ) : (
                    <AlertBanner tone="info">
                      Waiting for the assigned Tester to record a result.
                    </AlertBanner>
                  )
                ) : null}
                {canComplete ? (
                  <Button
                    className="w-full"
                    variant="success"
                    onClick={() => setCompleteOpen(true)}
                  >
                    <ShieldCheck className="h-4 w-4" />
                    Sign off as completed
                  </Button>
                ) : null}
                {project.status === "COMPLETED" ? (
                  <div className="flex items-center gap-2 rounded-lg bg-emerald-50 px-3 py-2 text-xs font-semibold text-emerald-800">
                    <CheckCircle2 className="h-4 w-4" />
                    Project completed
                  </div>
                ) : null}
                {!isAdmin && project.status === "IN_PRODUCTION" ? (
                  <p className="text-[11px] leading-5 text-slate-500">
                    An Admin must submit this project for testing.
                  </p>
                ) : null}
                {!isAdmin && project.status === "READY_FOR_PRODUCTION" ? (
                  <p className="text-[11px] leading-5 text-slate-500">
                    An Admin will start production when the team is ready.
                  </p>
                ) : null}
              </div>
            </div>
          </Card>

          {project.test_result ? (
            <Card>
              <CardHeader
                title="Testing"
                description={
                  project.tested_at
                    ? `Recorded ${formatDateTime(project.tested_at)}`
                    : undefined
                }
                action={<TestResultBadge result={project.test_result} />}
              />
              <div className="space-y-3 p-5">
                <p className="text-xs leading-5 whitespace-pre-wrap text-slate-600">
                  {project.test_note}
                </p>
                {project.tester ? (
                  <p className="text-[11px] text-slate-400">
                    Tester: {project.tester.name}
                  </p>
                ) : null}
                {project.test_result === "FAIL" &&
                project.status === "IN_PRODUCTION" ? (
                  <AlertBanner tone="warning">
                    Rework required. An Admin can resubmit for testing once ready.
                  </AlertBanner>
                ) : null}
              </div>
            </Card>
          ) : null}

          <Card>
            <CardHeader
              title="Team"
              description={`${project.members.length} assigned`}
              action={
                isAdmin ? (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setMembersOpen(true)}
                  >
                    Manage
                  </Button>
                ) : null
              }
            />
            <div className="divide-y divide-slate-100">
              {project.members.map((member) => (
                <div key={member.id} className="flex items-center gap-3 px-5 py-3">
                  <Avatar name={member.user.name} />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-xs font-semibold text-slate-900">
                      {member.user.name}
                    </p>
                    <p className="truncate text-[10px] text-slate-400">
                      {member.user.email}
                    </p>
                  </div>
                  <MemberRoleBadge role={member.role_in_project} />
                </div>
              ))}
            </div>
          </Card>

          <Card>
            <CardHeader
              title="Purchase requests"
              description={`${purchasesQuery.data?.total ?? 0} raised for this project`}
              action={
                <Link
                  href="/purchases"
                  className="text-[11px] font-semibold text-[#0f5c73] hover:underline"
                >
                  View all
                </Link>
              }
            />
            {purchasesQuery.isLoading ? (
              <div className="space-y-2 p-5">
                <Skeleton className="h-10" />
                <Skeleton className="h-10" />
              </div>
            ) : !purchasesQuery.data?.items.length ? (
              <EmptyState
                icon={<ShoppingCart className="h-5 w-5" />}
                title="No purchase requests"
                description="Shortages can be raised directly from the BOM table."
              />
            ) : (
              <div className="divide-y divide-slate-100">
                {purchasesQuery.data.items.slice(0, 5).map((request) => (
                  <div key={request.id} className="px-5 py-3">
                    <div className="flex items-center justify-between gap-3">
                      <p className="truncate text-xs font-semibold text-slate-900">
                        {request.item.name}
                      </p>
                      <PurchaseStatusBadge status={request.status} />
                    </div>
                    <p className="mt-0.5 text-[10px] text-slate-400">
                      Qty {request.quantity} · {formatDate(request.created_at)}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </Card>

          <Card>
            <CardHeader title="Project record" />
            <dl className="space-y-2.5 p-5 text-xs">
              <RecordRow label="Created by" value={project.creator.name} />
              <RecordRow label="Created" value={formatDateTime(project.created_at)} />
              <RecordRow label="Start date" value={formatDate(project.start_date, "Not set")} />
              <RecordRow label="Deadline" value={formatDate(project.end_date, "Not set")} />
              <RecordRow
                label="Last status change"
                value={formatDateTime(project.status_changed_at)}
              />
              <RecordRow label="Project ID" value={project.id} mono />
            </dl>
          </Card>
        </div>
      </div>

      {editOpen ? (
        <EditProjectModal project={project} onClose={() => setEditOpen(false)} />
      ) : null}
      {membersOpen ? (
        <MembersModal
          project={project}
          users={usersQuery.data ?? []}
          onClose={() => setMembersOpen(false)}
        />
      ) : null}
      {bomOpen ? (
        <BomModal
          project={project}
          inventory={inventoryQuery.data ?? []}
          onClose={() => setBomOpen(false)}
        />
      ) : null}
      {progressOpen ? (
        <ProgressModal project={project} onClose={() => setProgressOpen(false)} />
      ) : null}
      {testingOpen ? (
        <SubmitTestingModal
          project={project}
          users={usersQuery.data ?? []}
          onClose={() => setTestingOpen(false)}
        />
      ) : null}
      {resultOpen ? (
        <TestResultModal project={project} onClose={() => setResultOpen(false)} />
      ) : null}
      {completeOpen ? (
        <CompleteProjectModal
          project={project}
          onClose={() => setCompleteOpen(false)}
        />
      ) : null}
      <StartProductionModal
        open={startConfirmOpen}
        onClose={() => setStartConfirmOpen(false)}
        onConfirm={() => startProduction.mutate()}
        loading={startProduction.isPending}
        project={project}
      />
    </div>
  );
}

function SummaryCard({
  icon: Icon,
  label,
  value,
  hint,
  tone = "bg-slate-100 text-slate-700",
  children,
}: {
  icon: typeof ClipboardCheck;
  label: string;
  value: string;
  hint: string;
  tone?: string;
  children?: ReactNode;
}) {
  return (
    <Card className="p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-[11px] font-medium text-slate-500">{label}</p>
          <p className="mt-1 truncate text-xl font-bold text-slate-900">{value}</p>
          <p className="mt-0.5 text-[10px] text-slate-400">{hint}</p>
        </div>
        <span className={cn("flex h-9 w-9 items-center justify-center rounded-lg", tone)}>
          <Icon className="h-4 w-4" />
        </span>
      </div>
      {children}
    </Card>
  );
}

function RecordRow({
  label,
  value,
  mono,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div className="flex items-start justify-between gap-4">
      <dt className="text-slate-500">{label}</dt>
      <dd
        className={cn(
          "max-w-[65%] text-right font-medium text-slate-800",
          mono && "truncate font-mono text-[10px]",
        )}
        title={mono ? value : undefined}
      >
        {value}
      </dd>
    </div>
  );
}

function StartProductionModal({
  open,
  onClose,
  onConfirm,
  loading,
  project,
}: {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  loading: boolean;
  project: Project;
}) {
  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Start production"
      description={project.name}
      size="sm"
      footer={
        <>
          <Button variant="outline" onClick={onClose} disabled={loading}>
            Cancel
          </Button>
          <Button onClick={onConfirm} loading={loading}>
            <Play className="h-4 w-4" />
            Start production
          </Button>
        </>
      }
    >
      <div className="space-y-3 text-sm leading-6 text-slate-600">
        <p>
          The project will move to <strong>In Production</strong>. All BOM
          inventory must remain fully allocated.
        </p>
        <p className="rounded-lg bg-slate-50 px-3 py-2 text-xs">
          Progress logging remains available to the assigned team. An Admin can
          submit the project for testing when production is complete.
        </p>
      </div>
    </Modal>
  );
}
