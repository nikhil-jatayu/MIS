"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  Boxes,
  CirclePlus,
  ClipboardCheck,
  Info,
  Plus,
  Trash2,
  UserRound,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo } from "react";
import { useFieldArray, useForm, useWatch } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { RequireRole } from "@/components/auth-gate";
import {
  AlertBanner,
  Button,
  Card,
  CardHeader,
  Field,
  Input,
  PageHeader,
  Select,
  Spinner,
  Textarea,
} from "@/components/ui";
import { apiFetch, errorMessage } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { loadAllInventory } from "@/lib/loaders";
import type { Project, UserSummary } from "@/lib/types";
import {
  buttonClass,
  MEMBER_ROLE_LABELS,
  PRIORITY_LABELS,
  PROJECT_TYPE_LABELS,
} from "@/lib/utils";

const memberSchema = z.object({
  user_id: z.string().min(1, "Select a person"),
  role_in_project: z.enum(["DEVELOPER", "PRODUCER", "TESTER"]),
});

const bomLineSchema = z.object({
  item_id: z.string().min(1, "Select an inventory item"),
  quantity_required: z
    .number({ error: "Enter a quantity" })
    .int("Use a whole number")
    .min(1, "Minimum quantity is 1")
    .max(1_000_000, "Quantity is too large"),
});

const projectSchema = z
  .object({
    name: z.string().trim().min(2, "Name must be at least 2 characters").max(200),
    description: z.string().max(5000, "Description is too long"),
    type: z.enum(["RND", "PRODUCTION"]),
    priority: z.enum(["LOW", "MEDIUM", "HIGH", "CRITICAL"]),
    start_date: z.string(),
    end_date: z.string(),
    members: z.array(memberSchema).min(1, "Assign at least one person"),
    bom: z.array(bomLineSchema),
  })
  .superRefine((values, context) => {
    if (
      values.start_date &&
      values.end_date &&
      values.end_date < values.start_date
    ) {
      context.addIssue({
        code: "custom",
        path: ["end_date"],
        message: "Deadline must be on or after the start date",
      });
    }
    const userIds = values.members.map((member) => member.user_id);
    if (new Set(userIds).size !== userIds.length) {
      context.addIssue({
        code: "custom",
        path: ["members"],
        message: "Each person can only be assigned once",
      });
    }
    const itemIds = values.bom.map((line) => line.item_id);
    if (new Set(itemIds).size !== itemIds.length) {
      context.addIssue({
        code: "custom",
        path: ["bom"],
        message: "Each inventory item can only appear once in the BOM",
      });
    }
  });

type ProjectFormValues = z.infer<typeof projectSchema>;

export default function NewProjectPage() {
  return (
    <RequireRole roles={["ADMIN", "SUPER_ADMIN"]}>
      <NewProjectContent />
    </RequireRole>
  );
}

function NewProjectContent() {
  const { user } = useAuth();
  const router = useRouter();
  const queryClient = useQueryClient();

  const peopleQuery = useQuery({
    queryKey: ["users", "options"],
    queryFn: () => apiFetch<UserSummary[]>("/users/options"),
  });
  const inventoryQuery = useQuery({
    queryKey: ["inventory", "all-options"],
    queryFn: loadAllInventory,
  });

  const today = useMemo(() => new Date().toISOString().slice(0, 10), []);

  const {
    register,
    control,
    handleSubmit,
    formState: { errors },
  } = useForm<ProjectFormValues>({
    resolver: zodResolver(projectSchema),
    defaultValues: {
      name: "",
      description: "",
      type: "RND",
      priority: "MEDIUM",
      start_date: today,
      end_date: "",
      members: [{ user_id: "", role_in_project: "DEVELOPER" }],
      bom: [],
    },
  });

  const members = useFieldArray({ control, name: "members" });
  const bom = useFieldArray({ control, name: "bom" });
  const watchedBom = useWatch({ control, name: "bom" }) ?? [];
  const inventory = inventoryQuery.data ?? [];
  const inventoryMap = new Map(inventory.map((item) => [item.id, item]));

  const createProject = useMutation({
    mutationFn: (values: ProjectFormValues) =>
      apiFetch<Project>("/projects", {
        method: "POST",
        body: JSON.stringify({
          name: values.name,
          description: values.description || null,
          type: values.type,
          priority: values.priority,
          start_date: values.start_date || null,
          end_date: values.end_date || null,
          members: values.members,
          bom: values.bom.map((line) => ({
            item_id: line.item_id,
            quantity_required: line.quantity_required,
          })),
        }),
      }),
    onSuccess: (project) => {
      void queryClient.invalidateQueries({ queryKey: ["projects"] });
      void queryClient.invalidateQueries({ queryKey: ["inventory"] });
      void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      toast.success(
        project.is_inventory_ready
          ? "Project created. All inventory was allocated."
          : "Project created. Inventory shortages were flagged.",
      );
      router.push(`/projects/${project.id}`);
    },
    onError: (error) => toast.error(errorMessage(error, "Unable to create project.")),
  });

  const watchedMembers = useWatch({ control, name: "members" }) ?? [];
  const selectedUserIds = watchedMembers.map((member) => member.user_id);
  const selectedItemIds = watchedBom.map((line) => line.item_id);

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
        eyebrow="Order intake"
        title="Create project"
        description="Define the work, assign the team, and add the bill of materials. Inventory is checked and allocated automatically on creation."
        actions={
          <span className="rounded-full border border-slate-200 bg-white px-3 py-1 text-[11px] font-medium text-slate-500">
            Created by {user?.name ?? "Admin"}
          </span>
        }
      />

      <form
        onSubmit={handleSubmit((values) => createProject.mutate(values))}
        className="grid gap-6 xl:grid-cols-[1.45fr_1fr]"
        noValidate
      >
        <div className="space-y-6">
          <Card>
            <CardHeader
              title="Project details"
              description="Core information used across dashboards and alerts"
            />
            <div className="space-y-4 p-5">
              <Field
                label="Project name"
                htmlFor="name"
                error={errors.name?.message}
                required
              >
                <Input
                  id="name"
                  placeholder="e.g. Battery management controller — Rev B"
                  {...register("name")}
                />
              </Field>
              <Field
                label="Description"
                htmlFor="description"
                error={errors.description?.message}
                hint="Optional scope, customer context, or delivery notes."
              >
                <Textarea
                  id="description"
                  placeholder="What is being built, and for whom?"
                  {...register("description")}
                />
              </Field>
              <div className="grid gap-4 sm:grid-cols-2">
                <Field label="Type" htmlFor="type" error={errors.type?.message} required>
                  <Select id="type" {...register("type")}>
                    {Object.entries(PROJECT_TYPE_LABELS).map(([value, label]) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ))}
                  </Select>
                </Field>
                <Field
                  label="Priority"
                  htmlFor="priority"
                  error={errors.priority?.message}
                  required
                >
                  <Select id="priority" {...register("priority")}>
                    {Object.entries(PRIORITY_LABELS).map(([value, label]) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ))}
                  </Select>
                </Field>
                <Field
                  label="Start date"
                  htmlFor="start_date"
                  error={errors.start_date?.message}
                >
                  <Input id="start_date" type="date" {...register("start_date")} />
                </Field>
                <Field
                  label="Deadline"
                  htmlFor="end_date"
                  error={errors.end_date?.message}
                  hint="Drives the Time Counter reminder window."
                >
                  <Input id="end_date" type="date" {...register("end_date")} />
                </Field>
              </div>
            </div>
          </Card>

          <Card>
            <CardHeader
              title="Assigned personnel"
              description="At least one person is required. Testers can be assigned here or when testing begins."
              action={
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() =>
                    members.append({ user_id: "", role_in_project: "DEVELOPER" })
                  }
                >
                  <Plus className="h-3.5 w-3.5" />
                  Add person
                </Button>
              }
            />
            <div className="space-y-3 p-5">
              {members.fields.map((field, index) => (
                <div
                  key={field.id}
                  className="grid gap-3 rounded-xl border border-slate-200 bg-slate-50/50 p-3 sm:grid-cols-[1fr_170px_36px]"
                >
                  <Field label="Person" htmlFor={`member-${index}`}>
                    <Select
                      id={`member-${index}`}
                      {...register(`members.${index}.user_id`)}
                    >
                      <option value="">Select a person</option>
                      {peopleQuery.data?.map((person) => (
                        <option
                          key={person.id}
                          value={person.id}
                          disabled={
                            selectedUserIds.includes(person.id) &&
                            selectedUserIds.indexOf(person.id) !== index
                          }
                        >
                          {person.name} · {person.email}
                        </option>
                      ))}
                    </Select>
                  </Field>
                  <Field label="Project role" htmlFor={`member-role-${index}`}>
                    <Select
                      id={`member-role-${index}`}
                      {...register(`members.${index}.role_in_project`)}
                    >
                      {Object.entries(MEMBER_ROLE_LABELS).map(([value, label]) => (
                        <option key={value} value={value}>
                          {label}
                        </option>
                      ))}
                    </Select>
                  </Field>
                  <div className="flex items-end">
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      onClick={() => members.remove(index)}
                      disabled={members.fields.length === 1}
                      title="Remove person"
                    >
                      <Trash2 className="h-4 w-4 text-red-500" />
                    </Button>
                  </div>
                  {errors.members?.[index]?.user_id?.message ? (
                    <p className="text-xs text-red-600 sm:col-span-3">
                      {errors.members[index]?.user_id?.message}
                    </p>
                  ) : null}
                </div>
              ))}
              {errors.members?.root?.message || errors.members?.message ? (
                <p className="text-xs font-medium text-red-600">
                  {errors.members.root?.message ?? errors.members.message}
                </p>
              ) : null}
              {peopleQuery.isLoading ? (
                <p className="flex items-center gap-2 text-xs text-slate-500">
                  <Spinner className="h-3.5 w-3.5" /> Loading people…
                </p>
              ) : null}
            </div>
          </Card>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader
              title="Bill of materials"
              description="Optional. Each item is checked against live inventory."
              action={
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => bom.append({ item_id: "", quantity_required: 1 })}
                  disabled={inventoryQuery.isLoading}
                >
                  <CirclePlus className="h-3.5 w-3.5" />
                  Add item
                </Button>
              }
            />
            <div className="space-y-3 p-5">
              {bom.fields.length === 0 ? (
                <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 px-4 py-6 text-center">
                  <Boxes className="mx-auto h-7 w-7 text-slate-300" />
                  <p className="mt-2 text-xs font-semibold text-slate-600">
                    No material required
                  </p>
                  <p className="mt-1 text-[11px] leading-5 text-slate-500">
                    The project will be marked ready for production immediately.
                    Add an item if stock must be allocated.
                  </p>
                </div>
              ) : null}

              {bom.fields.map((field, index) => {
                const selected = inventoryMap.get(watchedBom[index]?.item_id ?? "");
                return (
                  <div
                    key={field.id}
                    className="rounded-xl border border-slate-200 bg-slate-50/50 p-3"
                  >
                    <div className="grid gap-3 sm:grid-cols-[1fr_120px_36px]">
                      <Field label="Inventory item" htmlFor={`bom-item-${index}`}>
                        <Select
                          id={`bom-item-${index}`}
                          {...register(`bom.${index}.item_id`)}
                        >
                          <option value="">Select an item</option>
                          {inventory.map((item) => (
                            <option
                              key={item.id}
                              value={item.id}
                              disabled={
                                selectedItemIds.includes(item.id) &&
                                selectedItemIds.indexOf(item.id) !== index
                              }
                            >
                              {item.sku} · {item.name}
                            </option>
                          ))}
                        </Select>
                      </Field>
                      <Field label="Quantity" htmlFor={`bom-qty-${index}`}>
                        <Input
                          id={`bom-qty-${index}`}
                          type="number"
                          min={1}
                          step={1}
                          {...register(`bom.${index}.quantity_required`, {
                            valueAsNumber: true,
                          })}
                        />
                      </Field>
                      <div className="flex items-end">
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon"
                          onClick={() => bom.remove(index)}
                          title="Remove item"
                        >
                          <Trash2 className="h-4 w-4 text-red-500" />
                        </Button>
                      </div>
                    </div>
                    {errors.bom?.[index]?.item_id?.message ||
                    errors.bom?.[index]?.quantity_required?.message ? (
                      <p className="mt-2 text-xs text-red-600">
                        {errors.bom[index]?.item_id?.message ??
                          errors.bom[index]?.quantity_required?.message}
                      </p>
                    ) : selected ? (
                      <div className="mt-2 flex flex-wrap items-center justify-between gap-2 rounded-lg bg-white px-3 py-2 text-[11px]">
                        <span className="text-slate-500">
                          Available now:{" "}
                          <strong className="text-slate-800">
                            {selected.quantity_available} units
                          </strong>
                        </span>
                        {(watchedBom[index]?.quantity_required || 0) >
                        selected.quantity_available ? (
                          <span className="font-semibold text-amber-700">
                            Shortage of{" "}
                            {(watchedBom[index]?.quantity_required || 0) -
                              selected.quantity_available}{" "}
                            units
                          </span>
                        ) : (
                          <span className="font-semibold text-emerald-700">
                            Available to allocate
                          </span>
                        )}
                      </div>
                    ) : null}
                  </div>
                );
              })}

              {errors.bom?.root?.message || errors.bom?.message ? (
                <p className="text-xs font-medium text-red-600">
                  {errors.bom.root?.message ?? errors.bom.message}
                </p>
              ) : null}
              {inventoryQuery.isError ? (
                <AlertBanner tone="warning" title="Inventory could not be loaded">
                  {errorMessage(inventoryQuery.error)}
                </AlertBanner>
              ) : null}
            </div>
          </Card>

          <AlertBanner tone="info" title="What happens on save?">
            <ul className="mt-1 space-y-1.5 text-xs leading-5">
              <li className="flex gap-2">
                <ClipboardCheck className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                Stock is allocated atomically when every BOM line is available.
              </li>
              <li className="flex gap-2">
                <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                Any shortage keeps the project in Pending Inventory so the team
                can raise purchase requests.
              </li>
              <li className="flex gap-2">
                <UserRound className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                Assigned users can log progress as soon as the project exists.
              </li>
            </ul>
          </AlertBanner>

          <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
            <Link href="/projects" className={buttonClass("outline")}>
              Cancel
            </Link>
            <Button type="submit" loading={createProject.isPending}>
              Create project
            </Button>
          </div>
        </div>
      </form>
    </div>
  );
}
