"use client";

import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import {
  ArrowRight,
  Check,
  Clock3,
  PackageCheck,
  RefreshCw,
  ShoppingCart,
  Truck,
  X,
} from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { PurchaseStatusBadge } from "@/components/badges";
import {
  AlertBanner,
  Button,
  Card,
  EmptyState,
  Field,
  Modal,
  PageHeader,
  Pagination,
  Select,
  Skeleton,
  Textarea,
} from "@/components/ui";
import { apiFetch, errorMessage } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Page, PurchaseRequest, PurchaseRequestStatus } from "@/lib/types";
import {
  buildQuery,
  formatDateTime,
  PURCHASE_STATUS_LABELS,
} from "@/lib/utils";

const STATUSES = Object.keys(PURCHASE_STATUS_LABELS) as PurchaseRequestStatus[];

type ActionKind = "approve" | "reject" | "order" | "deliver";

export function PurchasesView() {
  const { user } = useAuth();
  const searchParams = useSearchParams();
  const initialStatus = searchParams.get("status");
  const [status, setStatus] = useState<PurchaseRequestStatus | "">(
    initialStatus && STATUSES.includes(initialStatus as PurchaseRequestStatus)
      ? (initialStatus as PurchaseRequestStatus)
      : "",
  );
  const [page, setPage] = useState(1);
  const [action, setAction] = useState<{
    kind: ActionKind;
    request: PurchaseRequest;
  } | null>(null);

  const query = useQuery({
    queryKey: ["purchase-requests", { status, page }],
    queryFn: () =>
      apiFetch<Page<PurchaseRequest>>(
        `/purchase-requests${buildQuery({
          page,
          page_size: 20,
          status,
        })}`,
      ),
    placeholderData: keepPreviousData,
  });

  const canApprove = user?.role === "ADMIN" || user?.role === "SUPER_ADMIN";

  return (
    <div className="animate-rise-in">
      <PageHeader
        eyebrow="Procurement"
        title="Purchase requests"
        description="Shortage requests raised against project BOMs. Approval, ordering, and delivery update inventory and project status."
      />

      <AlertBanner tone="info" title="Procurement workflow">
        Pending → Approved → Ordered (project pauses as Awaiting Delivery) →
        Delivered (stock received and automatically allocated to the project).
      </AlertBanner>

      <Card className="mt-5 mb-5 p-4">
        <div className="grid gap-3 sm:grid-cols-[220px_1fr] sm:items-end">
          <Field label="Status" htmlFor="purchase-status">
            <Select
              id="purchase-status"
              value={status}
              onChange={(event) => {
                setStatus(event.target.value as PurchaseRequestStatus | "");
                setPage(1);
              }}
            >
              <option value="">All requests</option>
              {STATUSES.map((item) => (
                <option key={item} value={item}>
                  {PURCHASE_STATUS_LABELS[item]}
                </option>
              ))}
            </Select>
          </Field>
          <p className="hidden pb-2 text-right text-[11px] text-slate-400 sm:block">
            {canApprove
              ? "Admins can approve, reject, order, and receive requests."
              : "You can raise requests from a project page and track their status here."}
          </p>
        </div>
      </Card>

      {query.isError ? (
        <AlertBanner
          tone="danger"
          title="Unable to load purchase requests"
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
          {Array.from({ length: 6 }).map((_, index) => (
            <Skeleton key={index} className="h-20" />
          ))}
        </div>
      ) : !query.data?.items.length ? (
        <Card>
          <EmptyState
            icon={<ShoppingCart className="h-5 w-5" />}
            title="No purchase requests"
            description={
              status
                ? "No requests currently have this status."
                : "When a project BOM cannot be filled from stock, raise a request from the project page."
            }
            action={
              status ? (
                <Button variant="outline" size="sm" onClick={() => setStatus("")}>
                  Show all
                </Button>
              ) : undefined
            }
          />
        </Card>
      ) : (
        <Card className="overflow-hidden">
          <div className="flex items-center justify-between border-b border-slate-100 px-5 py-3">
            <p className="text-xs text-slate-500">
              {query.data.total} request{query.data.total === 1 ? "" : "s"}
            </p>
            <span className="hidden text-[11px] text-slate-400 sm:block">
              Newest first
            </span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[980px] text-left text-sm">
              <thead className="bg-slate-50 text-[10px] font-semibold tracking-wide text-slate-500 uppercase">
                <tr>
                  <th className="px-5 py-3">Item</th>
                  <th className="px-5 py-3">Project</th>
                  <th className="px-5 py-3 text-right">Qty</th>
                  <th className="px-5 py-3">Requested by</th>
                  <th className="px-5 py-3">Status</th>
                  <th className="px-5 py-3">Timeline</th>
                  {canApprove ? <th className="px-5 py-3 text-right">Actions</th> : null}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {query.data.items.map((request) => (
                  <tr key={request.id} className="align-top transition hover:bg-slate-50/80">
                    <td className="px-5 py-3.5">
                      <p className="font-medium text-slate-900">{request.item.name}</p>
                      <p className="mt-0.5 font-mono text-[10px] text-slate-500">
                        {request.item.sku} · {request.item.quantity_available} in stock
                      </p>
                      {request.reason ? (
                        <p className="mt-1 line-clamp-2 max-w-56 text-[11px] text-slate-500">
                          “{request.reason}”
                        </p>
                      ) : null}
                    </td>
                    <td className="px-5 py-3.5">
                      <Link
                        href={`/projects/${request.project_id}`}
                        className="inline-flex items-center gap-1 text-xs font-semibold text-[#0f5c73] hover:underline"
                      >
                        {request.project.name}
                        <ArrowRight className="h-3 w-3" />
                      </Link>
                      <p className="mt-0.5 text-[10px] text-slate-400">
                        {request.project.type === "RND" ? "R&D" : "Production"}
                      </p>
                    </td>
                    <td className="px-5 py-3.5 text-right font-semibold text-slate-900">
                      {request.quantity}
                    </td>
                    <td className="px-5 py-3.5">
                      <p className="text-xs text-slate-700">{request.requester.name}</p>
                      <p className="text-[10px] text-slate-400">
                        {formatDateTime(request.created_at)}
                      </p>
                    </td>
                    <td className="px-5 py-3.5">
                      <PurchaseStatusBadge status={request.status} />
                      {request.review_note &&
                      (request.status === "REJECTED" || request.status === "ORDERED") ? (
                        <p className="mt-1 max-w-44 text-[10px] text-slate-500">
                          {request.review_note}
                        </p>
                      ) : null}
                    </td>
                    <td className="px-5 py-3.5">
                      <div className="space-y-1 text-[10px] text-slate-500">
                        <p>Raised {formatDateTime(request.created_at)}</p>
                        {request.approved_at ? (
                          <p>Approved {formatDateTime(request.approved_at)}</p>
                        ) : null}
                        {request.ordered_at ? (
                          <p>Ordered {formatDateTime(request.ordered_at)}</p>
                        ) : null}
                        {request.delivered_at ? (
                          <p>Delivered {formatDateTime(request.delivered_at)}</p>
                        ) : null}
                      </div>
                    </td>
                    {canApprove ? (
                      <td className="px-5 py-3.5">
                        <div className="flex flex-wrap justify-end gap-1">
                          {request.status === "PENDING" ? (
                            <>
                              <Button
                                variant="success"
                                size="sm"
                                onClick={() =>
                                  setAction({ kind: "approve", request })
                                }
                              >
                                <Check className="h-3.5 w-3.5" />
                                Approve
                              </Button>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => setAction({ kind: "reject", request })}
                              >
                                <X className="h-3.5 w-3.5" />
                                Reject
                              </Button>
                            </>
                          ) : null}
                          {request.status === "APPROVED" ? (
                            <>
                              <Button
                                variant="primary"
                                size="sm"
                                onClick={() => setAction({ kind: "order", request })}
                              >
                                <Truck className="h-3.5 w-3.5" />
                                Mark ordered
                              </Button>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => setAction({ kind: "reject", request })}
                              >
                                <X className="h-3.5 w-3.5" />
                                Reject
                              </Button>
                            </>
                          ) : null}
                          {request.status === "ORDERED" ? (
                            <Button
                              variant="success"
                              size="sm"
                              onClick={() => setAction({ kind: "deliver", request })}
                            >
                              <PackageCheck className="h-3.5 w-3.5" />
                              Mark delivered
                            </Button>
                          ) : null}
                          {request.status === "DELIVERED" ? (
                            <span className="inline-flex items-center gap-1 text-[10px] font-medium text-emerald-700">
                              <PackageCheck className="h-3.5 w-3.5" />
                              Complete
                            </span>
                          ) : null}
                          {request.status === "REJECTED" ? (
                            <span className="inline-flex items-center gap-1 text-[10px] font-medium text-slate-400">
                              <Clock3 className="h-3.5 w-3.5" />
                              Closed
                            </span>
                          ) : null}
                        </div>
                      </td>
                    ) : null}
                  </tr>
                ))}
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

      <PurchaseActionModal
        state={action}
        onClose={() => setAction(null)}
      />
    </div>
  );
}

function PurchaseActionModal({
  state,
  onClose,
}: {
  state: { kind: ActionKind; request: PurchaseRequest } | null;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () => {
      if (!state) throw new Error("No request selected");
      if (state.kind === "approve") {
        return apiFetch<PurchaseRequest>(
          `/purchase-requests/${state.request.id}/approve`,
          { method: "POST" },
        );
      }
      if (state.kind === "reject") {
        return apiFetch<PurchaseRequest>(
          `/purchase-requests/${state.request.id}/reject`,
          {
            method: "POST",
            body: JSON.stringify({ reason: note || null }),
          },
        );
      }
      if (state.kind === "order") {
        return apiFetch<PurchaseRequest>(
          `/purchase-requests/${state.request.id}/order`,
          {
            method: "POST",
            body: JSON.stringify({ delay_reason: note }),
          },
        );
      }
      return apiFetch<PurchaseRequest>(
        `/purchase-requests/${state.request.id}/deliver`,
        { method: "POST" },
      );
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["purchase-requests"] });
      void queryClient.invalidateQueries({ queryKey: ["projects"] });
      void queryClient.invalidateQueries({ queryKey: ["inventory"] });
      void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      toast.success(successMessage(state?.kind));
      close();
    },
    onError: (mutationError) => {
      const message = errorMessage(mutationError);
      setError(message);
      toast.error(message);
    },
  });

  function close() {
    setNote("");
    setError(null);
    onClose();
  }

  function submit() {
    setError(null);
    if (state?.kind === "order" && note.trim().length < 5) {
      setError("A delay reason of at least 5 characters is required.");
      return;
    }
    mutation.mutate();
  }

  const copy = state ? modalCopy[state.kind] : modalCopy.approve;

  return (
    <Modal
      open={Boolean(state)}
      onClose={close}
      title={copy.title}
      description={state ? `${state.request.item.name} · ${state.request.project.name}` : ""}
      size="sm"
      footer={
        <>
          <Button variant="outline" onClick={close} disabled={mutation.isPending}>
            Cancel
          </Button>
          <Button
            variant={copy.buttonVariant}
            onClick={submit}
            loading={mutation.isPending}
          >
            {copy.button}
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <p className="text-sm leading-6 text-slate-600">{copy.body}</p>
        {state?.kind === "order" ? (
          <Field
            label="Delay reason"
            htmlFor="delay-reason"
            hint="Recorded on the project and shown as Awaiting Delivery."
            required
          >
            <Textarea
              id="delay-reason"
              value={note}
              onChange={(event) => setNote(event.target.value)}
              placeholder="e.g. Supplier lead time for the power module"
            />
          </Field>
        ) : null}
        {state?.kind === "reject" ? (
          <Field label="Reason (optional)" htmlFor="reject-reason">
            <Textarea
              id="reject-reason"
              value={note}
              onChange={(event) => setNote(event.target.value)}
              placeholder="Why is this request being rejected?"
            />
          </Field>
        ) : null}
        {error ? (
          <p className="rounded-lg bg-red-50 px-3 py-2 text-xs font-medium text-red-700">
            {error}
          </p>
        ) : null}
      </div>
    </Modal>
  );
}

function successMessage(kind?: ActionKind) {
  if (kind === "approve") return "Purchase request approved";
  if (kind === "reject") return "Purchase request rejected";
  if (kind === "order") return "Request marked as ordered. Project is awaiting delivery.";
  return "Delivery recorded. Inventory received and allocation re-checked.";
}

const modalCopy: Record<
  ActionKind,
  {
    title: string;
    body: string;
    button: string;
    buttonVariant: "primary" | "danger" | "success";
  }
> = {
  approve: {
    title: "Approve purchase request",
    body: "Approval confirms the shortage is valid. The request can then be marked as ordered.",
    button: "Approve request",
    buttonVariant: "success",
  },
  reject: {
    title: "Reject purchase request",
    body: "Rejection closes the request. The project will remain in Pending Inventory until the shortage is resolved.",
    button: "Reject request",
    buttonVariant: "danger",
  },
  order: {
    title: "Mark as ordered",
    body: "The project will pause as Awaiting Delivery and record the delay reason below. This is reversed when stock is delivered.",
    button: "Confirm order",
    buttonVariant: "primary",
  },
  deliver: {
    title: "Confirm delivery",
    body: "Received quantity is added to inventory, then automatically allocated against the project BOM. The project may return to Ready, Production, or Testing.",
    button: "Confirm delivery",
    buttonVariant: "success",
  },
};
