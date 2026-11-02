"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { AlertBanner, Badge, Button, Card, EmptyState, Field, PageHeader, Pagination, Select, Textarea, Input } from "@/components/ui";
import { apiFetch, errorMessage } from "@/lib/api";
import type { Page, ProductionAction, ProductionActionCreate, ProductionActionStatus, Project, ProductionAssignee } from "@/lib/types";

const today = () => {
  const value = new Date();
  return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, "0")}-${String(value.getDate()).padStart(2, "0")}`;
};

export default function ProductionActionsPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState("");
  const [form, setForm] = useState<ProductionActionCreate>({
    date_raised: today(),
    issue_observation: "",
    corrective_action: "",
    responsible_user_id: "",
    deadline: today(),
    remarks: "",
  });
  const [formError, setFormError] = useState<string | null>(null);
  const projectsQuery = useQuery({
    queryKey: ["production-project-options"],
    queryFn: () => apiFetch<Page<Project>>("/projects?page=1&page_size=100"),
  });
  const actionsQuery = useQuery({
    queryKey: ["production-actions", page, statusFilter],
    queryFn: () => apiFetch<Page<ProductionAction>>(`/production/actions?page=${page}&page_size=20${statusFilter ? `&status=${statusFilter}` : ""}`),
  });
  const usersQuery = useQuery({
    queryKey: ["active-users-for-production-actions"],
    queryFn: () => apiFetch<ProductionAssignee[]>("/production/assignees"),
  });
  const createAction = useMutation({
    mutationFn: () => apiFetch<ProductionAction>("/production/actions", { method: "POST", body: JSON.stringify(form) }),
    onSuccess: async () => {
      setForm({ date_raised: today(), issue_observation: "", corrective_action: "", responsible_user_id: "", deadline: today(), remarks: "" });
      setFormError(null);
      await queryClient.invalidateQueries({ queryKey: ["production-actions"] });
      await queryClient.invalidateQueries({ queryKey: ["production-summary"] });
    },
    onError: (error) => setFormError(errorMessage(error)),
  });
  const updateAction = useMutation({
    mutationFn: ({ id, status }: { id: string; status: ProductionActionStatus }) => apiFetch<ProductionAction>(`/production/actions/${id}`, { method: "PATCH", body: JSON.stringify({ status }) }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["production-actions"] });
      await queryClient.invalidateQueries({ queryKey: ["production-summary"] });
    },
  });

  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Production" title="Production action tracker" description="Log production issues, assign an owner, set a deadline and track corrective actions through closure." />
      <Card className="overflow-hidden">
        <div className="border-b border-slate-100 px-5 py-4">
          <h2 className="font-semibold text-slate-900">Raise a production action</h2>
          <p className="mt-1 text-xs text-slate-500">Give every issue an accountable owner and a realistic due date.</p>
        </div>
        <form className="space-y-4 p-5" onSubmit={(event) => { event.preventDefault(); setFormError(null); createAction.mutate(); }}>
          {formError ? <AlertBanner tone="danger">{formError}</AlertBanner> : null}
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            <Field label="Date raised" required><Input type="date" value={form.date_raised} onChange={(e) => setForm((v) => ({ ...v, date_raised: e.target.value }))} required /></Field>
            <Field label="Deadline" required><Input type="date" value={form.deadline} onChange={(e) => setForm((v) => ({ ...v, deadline: e.target.value }))} required /></Field>
            <Field label="Responsible person">
              <Select value={form.responsible_user_id} required onChange={(e) => setForm((v) => ({ ...v, responsible_user_id: e.target.value }))}>
                <option value="" disabled>Choose responsible person</option>
                {usersQuery.data?.map((user) => <option key={user.id} value={user.id}>{user.name}</option>)}
              </Select>
            </Field>
            <Field label="MIS project (optional)">
              <Select value={form.project_id ?? ""} onChange={(e) => setForm((v) => ({ ...v, project_id: e.target.value || null }))}>
                <option value="">Not linked to a project</option>
                {projectsQuery.data?.items.filter((project) => project.type === "PRODUCTION").map((project) => <option key={project.id} value={project.id}>{project.name}</option>)}
              </Select>
            </Field>
          </div>
          <Field label="Issue / observation" required><Textarea rows={3} value={form.issue_observation} onChange={(e) => setForm((v) => ({ ...v, issue_observation: e.target.value }))} minLength={3} required placeholder="Describe the production issue, defect, delay or constraint…" /></Field>
          <Field label="Corrective / preventive action" required><Textarea rows={3} value={form.corrective_action} onChange={(e) => setForm((v) => ({ ...v, corrective_action: e.target.value }))} minLength={3} required placeholder="Describe the action required to resolve or prevent recurrence…" /></Field>
          <Field label="Remarks / evidence"><Textarea rows={2} value={form.remarks ?? ""} onChange={(e) => setForm((v) => ({ ...v, remarks: e.target.value }))} /></Field>
          <div className="flex justify-end"><Button type="submit" loading={createAction.isPending} disabled={!form.responsible_user_id}>Create action</Button></div>
        </form>
      </Card>

      <Card className="overflow-hidden">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 px-5 py-4">
          <div><h2 className="font-semibold text-slate-900">Production actions</h2><p className="mt-1 text-xs text-slate-500">{actionsQuery.data?.total ?? 0} actions</p></div>
          <label className="flex items-center gap-2 text-sm text-slate-600">Status
            <Select value={statusFilter} onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}>
              <option value="">All statuses</option><option value="OPEN">Open</option><option value="IN_PROGRESS">In progress</option><option value="ON_HOLD">On hold</option><option value="CLOSED">Closed</option>
            </Select>
          </label>
        </div>
        {actionsQuery.isError ? <div className="p-5"><AlertBanner tone="danger">{errorMessage(actionsQuery.error)}</AlertBanner></div> : null}
        {actionsQuery.isLoading ? <p className="p-5 text-sm text-slate-500">Loading actions…</p> : null}
        {actionsQuery.data && actionsQuery.data.items.length === 0 ? <EmptyState title="No production actions found" description="Raise an action above when an issue needs an owner and deadline." /> : null}
        {actionsQuery.data && actionsQuery.data.items.length > 0 ? (
          <>
            <div className="divide-y divide-slate-100">
              {actionsQuery.data.items.map((action) => (
                <div key={action.id} className="grid gap-3 p-5 lg:grid-cols-[1fr_180px_150px] lg:items-start">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2"><span className="text-xs font-semibold text-slate-500">{action.action_number}</span><StatusBadge status={action.status} />{action.is_overdue ? <Badge className="border-amber-200 bg-amber-50 text-amber-800">Overdue</Badge> : null}</div>
                    <h3 className="mt-2 font-semibold text-slate-900">{action.issue_observation}</h3>
                    <p className="mt-1 text-sm text-slate-600">Action: {action.corrective_action}</p>
                    {action.remarks ? <p className="mt-1 text-xs text-slate-500">{action.remarks}</p> : null}
                  </div>
                  <div className="text-sm"><p className="text-xs text-slate-500">Responsible</p><p className="mt-1 font-medium text-slate-800">{action.responsible_user?.name ?? "Unassigned"}</p><p className="mt-2 text-xs text-slate-500">Deadline</p><p className="mt-1 text-slate-800">{action.deadline}</p></div>
                  <div className="flex flex-col gap-2">
                    {action.status !== "CLOSED" ? (
                      <Select aria-label={`Update status for ${action.action_number}`} value={action.status} disabled={updateAction.isPending} onChange={(e) => updateAction.mutate({ id: action.id, status: e.target.value as ProductionActionStatus })}>
                        <option value="OPEN">Open</option><option value="IN_PROGRESS">In progress</option><option value="ON_HOLD">On hold</option><option value="CLOSED">Closed</option>
                      </Select>
                    ) : <span className="text-xs text-slate-500">Closed {action.closed_at ? new Date(action.closed_at).toLocaleDateString() : ""}</span>}
                    {action.closed_at && action.closed_by ? <span className="text-xs text-slate-500">By {action.closed_by.name}</span> : null}
                  </div>
                </div>
              ))}
            </div>
            <Pagination page={actionsQuery.data.page} pages={actionsQuery.data.pages} total={actionsQuery.data.total} onPageChange={setPage} />
          </>
        ) : null}
        {updateAction.isError ? <div className="p-5"><AlertBanner tone="danger">{errorMessage(updateAction.error)}</AlertBanner></div> : null}
      </Card>
    </div>
  );
}

function StatusBadge({ status }: { status: ProductionActionStatus }) {
  const styles: Record<ProductionActionStatus, string> = {
    OPEN: "border-sky-200 bg-sky-50 text-sky-800",
    IN_PROGRESS: "border-indigo-200 bg-indigo-50 text-indigo-800",
    ON_HOLD: "border-amber-200 bg-amber-50 text-amber-800",
    CLOSED: "border-emerald-200 bg-emerald-50 text-emerald-800",
  };
  const labels: Record<ProductionActionStatus, string> = { OPEN: "Open", IN_PROGRESS: "In progress", ON_HOLD: "On hold", CLOSED: "Closed" };
  return <Badge className={styles[status]}>{labels[status]}</Badge>;
}
