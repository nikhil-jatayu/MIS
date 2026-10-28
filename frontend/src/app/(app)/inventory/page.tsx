"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import {
  Boxes,
  Pencil,
  Plus,
  RefreshCw,
  Search,
  Trash2,
  TriangleAlert,
} from "lucide-react";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import {
  AlertBanner,
  Button,
  Card,
  EmptyState,
  Field,
  Input,
  Modal,
  PageHeader,
  Pagination,
  Select,
  Skeleton,
  Spinner,
} from "@/components/ui";
import { apiFetch, errorMessage } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { InventoryItem, MessageResponse, Page } from "@/lib/types";
import { useDebouncedValue } from "@/lib/use-debounced";
import { buildQuery, formatDateTime } from "@/lib/utils";

const itemSchema = z.object({
  name: z.string().trim().min(2, "Name must be at least 2 characters").max(200),
  sku: z.string().trim().min(1, "SKU is required").max(100),
  quantity_available: z
    .number({ error: "Enter a quantity" })
    .int("Use a whole number")
    .min(0, "Quantity cannot be negative")
    .max(10_000_000, "Quantity is too large"),
});

type ItemValues = z.infer<typeof itemSchema>;

export default function InventoryPage() {
  const { user } = useAuth();
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState("name");
  const [order, setOrder] = useState<"asc" | "desc">("asc");
  const [page, setPage] = useState(1);
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<InventoryItem | null>(null);
  const [deleting, setDeleting] = useState<InventoryItem | null>(null);
  const debouncedSearch = useDebouncedValue(search);
  const canManage = user?.role === "SUPER_ADMIN";

  const query = useQuery({
    queryKey: ["inventory", { q: debouncedSearch, sort, order, page }],
    queryFn: () =>
      apiFetch<Page<InventoryItem>>(
        `/inventory${buildQuery({
          page,
          page_size: 20,
          q: debouncedSearch,
          sort,
          order,
        })}`,
      ),
    placeholderData: keepPreviousData,
  });

  function openCreate() {
    setEditing(null);
    setFormOpen(true);
  }

  function openEdit(item: InventoryItem) {
    setEditing(item);
    setFormOpen(true);
  }

  return (
    <div className="animate-rise-in">
      <PageHeader
        eyebrow="Stock control"
        title="Inventory"
        description="Shared component and material stock. Project BOM allocation reduces available quantity automatically."
        actions={
          canManage ? (
            <Button onClick={openCreate}>
              <Plus className="h-4 w-4" />
              New inventory item
            </Button>
          ) : (
            <span className="rounded-full border border-slate-200 bg-white px-3 py-1 text-[11px] text-slate-500">
              Read-only · managed by Super Admin
            </span>
          )
        }
      />

      <Card className="mb-5 p-4">
        <div className="grid gap-3 sm:grid-cols-[1fr_200px_160px]">
          <Field label="Search inventory" htmlFor="inventory-search">
            <div className="relative">
              <Search className="pointer-events-none absolute top-3 left-3 h-4 w-4 text-slate-400" />
              <Input
                id="inventory-search"
                value={search}
                onChange={(event) => {
                  setSearch(event.target.value);
                  setPage(1);
                }}
                placeholder="Search by name or SKU"
                className="pl-9"
              />
            </div>
          </Field>
          <Field label="Sort by" htmlFor="inventory-sort">
            <Select
              id="inventory-sort"
              value={sort}
              onChange={(event) => {
                setSort(event.target.value);
                setPage(1);
              }}
            >
              <option value="name">Name</option>
              <option value="sku">SKU</option>
              <option value="quantity_available">Quantity available</option>
              <option value="created_at">Recently added</option>
            </Select>
          </Field>
          <Field label="Direction" htmlFor="inventory-order">
            <Select
              id="inventory-order"
              value={order}
              onChange={(event) => {
                setOrder(event.target.value as "asc" | "desc");
                setPage(1);
              }}
            >
              <option value="asc">Ascending</option>
              <option value="desc">Descending</option>
            </Select>
          </Field>
        </div>
      </Card>

      {query.isError ? (
        <AlertBanner
          tone="danger"
          title="Unable to load inventory"
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
            <Skeleton key={index} className="h-14" />
          ))}
        </div>
      ) : !query.data?.items.length ? (
        <Card>
          <EmptyState
            icon={<Boxes className="h-5 w-5" />}
            title={debouncedSearch ? "No matching inventory items" : "No inventory yet"}
            description={
              debouncedSearch
                ? "Try a different name or SKU."
                : canManage
                  ? "Add the materials and components used by production projects."
                  : "A Super Admin has not added inventory yet."
            }
            action={
              canManage && !debouncedSearch ? (
                <Button size="sm" onClick={openCreate}>
                  <Plus className="h-3.5 w-3.5" />
                  Add item
                </Button>
              ) : undefined
            }
          />
        </Card>
      ) : (
        <Card className="overflow-hidden">
          <div className="flex items-center justify-between border-b border-slate-100 px-5 py-3">
            <p className="text-xs text-slate-500">
              {query.data.total} item{query.data.total === 1 ? "" : "s"}
              {query.isFetching ? (
                <Spinner className="ml-2 h-3 w-3 text-[#0f5c73]" />
              ) : null}
            </p>
            <p className="hidden text-[11px] text-slate-400 sm:block">
              Quantities change with allocations, deliveries, and adjustments.
            </p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[700px] text-left text-sm">
              <thead className="bg-slate-50 text-[10px] font-semibold tracking-wide text-slate-500 uppercase">
                <tr>
                  <th className="px-5 py-3">Item</th>
                  <th className="px-5 py-3">SKU</th>
                  <th className="px-5 py-3 text-right">Available</th>
                  <th className="px-5 py-3">Last updated</th>
                  {canManage ? <th className="px-5 py-3 text-right">Actions</th> : null}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {query.data.items.map((item) => (
                  <tr key={item.id} className="transition hover:bg-slate-50/80">
                    <td className="px-5 py-3">
                      <div className="flex items-center gap-2.5">
                        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-100 text-slate-500">
                          <Boxes className="h-4 w-4" />
                        </span>
                        <span className="font-medium text-slate-900">{item.name}</span>
                      </div>
                    </td>
                    <td className="px-5 py-3 font-mono text-xs text-slate-600">
                      {item.sku}
                    </td>
                    <td className="px-5 py-3 text-right">
                      <span
                        className={
                          item.quantity_available === 0
                            ? "inline-flex items-center gap-1 rounded-full bg-red-50 px-2 py-0.5 text-xs font-bold text-red-700"
                            : item.quantity_available < 5
                              ? "inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-0.5 text-xs font-bold text-amber-700"
                              : "text-sm font-semibold text-slate-900"
                        }
                      >
                        {item.quantity_available === 0 ? (
                          <TriangleAlert className="h-3 w-3" />
                        ) : null}
                        {item.quantity_available}
                      </span>
                    </td>
                    <td className="px-5 py-3 text-xs text-slate-500">
                      {formatDateTime(item.updated_at)}
                    </td>
                    {canManage ? (
                      <td className="px-5 py-3">
                        <div className="flex justify-end gap-1">
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => openEdit(item)}
                            title={`Edit ${item.name}`}
                          >
                            <Pencil className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => setDeleting(item)}
                            title={`Delete ${item.name}`}
                          >
                            <Trash2 className="h-4 w-4 text-red-500" />
                          </Button>
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

      <InventoryFormModal
        open={formOpen}
        item={editing}
        onClose={() => setFormOpen(false)}
      />
      <DeleteItemModal item={deleting} onClose={() => setDeleting(null)} />
    </div>
  );
}

function InventoryFormModal({
  open,
  item,
  onClose,
}: {
  open: boolean;
  item: InventoryItem | null;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<ItemValues>({
    resolver: zodResolver(itemSchema),
    defaultValues: { name: "", sku: "", quantity_available: 0 },
  });

  useEffect(() => {
    if (!open) return;
    reset(
      item
        ? {
            name: item.name,
            sku: item.sku,
            quantity_available: item.quantity_available,
          }
        : { name: "", sku: "", quantity_available: 0 },
    );
  }, [item, open, reset]);

  const mutation = useMutation({
    mutationFn: (values: ItemValues) =>
      item
        ? apiFetch<InventoryItem>(`/inventory/${item.id}`, {
            method: "PUT",
            body: JSON.stringify(values),
          })
        : apiFetch<InventoryItem>("/inventory", {
            method: "POST",
            body: JSON.stringify(values),
          }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["inventory"] });
      void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      toast.success(item ? "Inventory item updated" : "Inventory item created");
      onClose();
    },
    onError: (error) => toast.error(errorMessage(error)),
  });

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={item ? "Edit inventory item" : "New inventory item"}
      description="SKU values are normalised to uppercase and must be unique."
      footer={
        <>
          <Button variant="outline" onClick={onClose} disabled={mutation.isPending}>
            Cancel
          </Button>
          <Button
            onClick={handleSubmit((values) => mutation.mutate(values))}
            loading={mutation.isPending}
          >
            {item ? "Save changes" : "Create item"}
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <Field label="Item name" htmlFor="item-name" error={errors.name?.message} required>
          <Input id="item-name" placeholder="e.g. 10kΩ resistor, 1/4W" {...register("name")} />
        </Field>
        <Field
          label="SKU"
          htmlFor="item-sku"
          error={errors.sku?.message}
          hint="Use a stable internal part number."
          required
        >
          <Input id="item-sku" placeholder="e.g. RES-10K-025W" className="uppercase" {...register("sku")} />
        </Field>
        <Field
          label="Quantity available"
          htmlFor="item-quantity"
          error={errors.quantity_available?.message}
          hint="Adjustments are recorded in the audit trail."
          required
        >
          <Input
            id="item-quantity"
            type="number"
            min={0}
            step={1}
            {...register("quantity_available", { valueAsNumber: true })}
          />
        </Field>
      </div>
    </Modal>
  );
}

function DeleteItemModal({
  item,
  onClose,
}: {
  item: InventoryItem | null;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: () =>
      apiFetch<MessageResponse>(`/inventory/${item?.id}`, { method: "DELETE" }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["inventory"] });
      void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      toast.success("Inventory item deleted");
      onClose();
    },
    onError: (error) => toast.error(errorMessage(error)),
  });

  return (
    <Modal
      open={Boolean(item)}
      onClose={onClose}
      title="Delete inventory item?"
      description="This cannot be undone."
      size="sm"
      footer={
        <>
          <Button variant="outline" onClick={onClose} disabled={mutation.isPending}>
            Cancel
          </Button>
          <Button
            variant="danger"
            onClick={() => mutation.mutate()}
            loading={mutation.isPending}
          >
            Delete item
          </Button>
        </>
      }
    >
      <p className="text-sm text-slate-600">
        <strong className="text-slate-900">{item?.name}</strong> ({item?.sku}) will
        be removed from inventory. Items referenced by a project BOM or purchase
        request cannot be deleted.
      </p>
    </Modal>
  );
}
