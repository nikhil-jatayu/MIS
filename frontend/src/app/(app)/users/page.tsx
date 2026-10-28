"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import {
  KeyRound,
  Pencil,
  Plus,
  RefreshCw,
  Search,
  ShieldCheck,
  UserRound,
} from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { RequireRole } from "@/components/auth-gate";
import { RoleBadge } from "@/components/badges";
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
import type { Page, User, UserRole } from "@/lib/types";
import { useDebouncedValue } from "@/lib/use-debounced";
import {
  buildQuery,
  formatDate,
  formatDateTime,
  ROLE_LABELS,
} from "@/lib/utils";

const ROLES = Object.keys(ROLE_LABELS) as UserRole[];
const PASSWORD_PATTERN =
  /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,128}$/;

const createSchema = z.object({
  name: z.string().trim().min(2, "Name must be at least 2 characters").max(150),
  email: z.email("Enter a valid email address"),
  role: z.enum(["SUPER_ADMIN", "ADMIN", "USER"]),
  temporary_password: z
    .string()
    .regex(
      PASSWORD_PATTERN,
      "Use 8+ characters with uppercase, lowercase, a number, and a special character",
    ),
});

type CreateValues = z.infer<typeof createSchema>;

const editSchema = z.object({
  name: z.string().trim().min(2, "Name must be at least 2 characters").max(150),
  role: z.enum(["SUPER_ADMIN", "ADMIN", "USER"]),
  is_active: z.boolean(),
});

type EditValues = z.infer<typeof editSchema>;

const resetSchema = z
  .object({
    new_password: z
      .string()
      .regex(
        PASSWORD_PATTERN,
        "Use 8+ characters with uppercase, lowercase, a number, and a special character",
      ),
    confirm_password: z.string().min(1, "Confirm the new password"),
  })
  .refine((values) => values.new_password === values.confirm_password, {
    path: ["confirm_password"],
    message: "Passwords do not match",
  });

type ResetValues = z.infer<typeof resetSchema>;

type UserAction =
  | { type: "create" }
  | { type: "edit"; user: User }
  | { type: "reset"; user: User }
  | null;

export default function UsersPage() {
  return (
    <RequireRole roles={["SUPER_ADMIN"]}>
      <UsersContent />
    </RequireRole>
  );
}

function UsersContent() {
  const [search, setSearch] = useState("");
  const [role, setRole] = useState<UserRole | "">("");
  const [active, setActive] = useState<"" | "true" | "false">("");
  const [page, setPage] = useState(1);
  const [action, setAction] = useState<UserAction>(null);
  const debouncedSearch = useDebouncedValue(search);

  const query = useQuery({
    queryKey: ["users", { q: debouncedSearch, role, active, page }],
    queryFn: () =>
      apiFetch<Page<User>>(
        `/users${buildQuery({
          page,
          page_size: 20,
          q: debouncedSearch,
          role,
          is_active: active || undefined,
        })}`,
      ),
    placeholderData: keepPreviousData,
  });

  return (
    <div className="animate-rise-in">
      <PageHeader
        eyebrow="Administration"
        title="Users"
        description="Create Office People IDs, assign roles, deactivate access, and reset temporary passwords."
        actions={
          <Button onClick={() => setAction({ type: "create" })}>
            <Plus className="h-4 w-4" />
            New user
          </Button>
        }
      />

      <Card className="mb-5 p-4">
        <div className="grid gap-3 sm:grid-cols-[1fr_180px_160px]">
          <Field label="Search users" htmlFor="user-search">
            <div className="relative">
              <Search className="pointer-events-none absolute top-3 left-3 h-4 w-4 text-slate-400" />
              <Input
                id="user-search"
                value={search}
                onChange={(event) => {
                  setSearch(event.target.value);
                  setPage(1);
                }}
                placeholder="Search by name or email"
                className="pl-9"
              />
            </div>
          </Field>
          <Field label="Role" htmlFor="user-role">
            <Select
              id="user-role"
              value={role}
              onChange={(event) => {
                setRole(event.target.value as UserRole | "");
                setPage(1);
              }}
            >
              <option value="">All roles</option>
              {ROLES.map((item) => (
                <option key={item} value={item}>
                  {ROLE_LABELS[item]}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Account status" htmlFor="user-active">
            <Select
              id="user-active"
              value={active}
              onChange={(event) => {
                setActive(event.target.value as "" | "true" | "false");
                setPage(1);
              }}
            >
              <option value="">All accounts</option>
              <option value="true">Active</option>
              <option value="false">Deactivated</option>
            </Select>
          </Field>
        </div>
      </Card>

      {query.isError ? (
        <AlertBanner
          tone="danger"
          title="Unable to load users"
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
            <Skeleton key={index} className="h-16" />
          ))}
        </div>
      ) : !query.data?.items.length ? (
        <Card>
          <EmptyState
            icon={<UserRound className="h-5 w-5" />}
            title="No users found"
            description="Adjust the filters or create a new user account."
            action={
              <Button size="sm" onClick={() => setAction({ type: "create" })}>
                <Plus className="h-3.5 w-3.5" />
                New user
              </Button>
            }
          />
        </Card>
      ) : (
        <Card className="overflow-hidden">
          <div className="flex items-center justify-between border-b border-slate-100 px-5 py-3">
            <p className="text-xs text-slate-500">
              {query.data.total} user{query.data.total === 1 ? "" : "s"}
              {query.isFetching ? (
                <Spinner className="ml-2 h-3 w-3 text-[#0f5c73]" />
              ) : null}
            </p>
            <p className="hidden text-[11px] text-slate-400 sm:block">
              Temporary passwords require a change at next sign-in.
            </p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[900px] text-left text-sm">
              <thead className="bg-slate-50 text-[10px] font-semibold tracking-wide text-slate-500 uppercase">
                <tr>
                  <th className="px-5 py-3">User</th>
                  <th className="px-5 py-3">Role</th>
                  <th className="px-5 py-3">Status</th>
                  <th className="px-5 py-3">Last sign-in</th>
                  <th className="px-5 py-3">Password</th>
                  <th className="px-5 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {query.data.items.map((user) => (
                  <tr key={user.id} className="transition hover:bg-slate-50/80">
                    <td className="px-5 py-3.5">
                      <p className="font-medium text-slate-900">{user.name}</p>
                      <p className="mt-0.5 text-[11px] text-slate-500">{user.email}</p>
                    </td>
                    <td className="px-5 py-3.5">
                      <RoleBadge role={user.role} />
                    </td>
                    <td className="px-5 py-3.5">
                      <span
                        className={
                          user.is_active
                            ? "inline-flex items-center gap-1.5 text-xs font-medium text-emerald-700"
                            : "inline-flex items-center gap-1.5 text-xs font-medium text-slate-400"
                        }
                      >
                        <span
                          className={
                            user.is_active
                              ? "h-1.5 w-1.5 rounded-full bg-emerald-500"
                              : "h-1.5 w-1.5 rounded-full bg-slate-300"
                          }
                        />
                        {user.is_active ? "Active" : "Deactivated"}
                      </span>
                    </td>
                    <td className="px-5 py-3.5 text-xs text-slate-500">
                      {user.last_login_at
                        ? formatDateTime(user.last_login_at)
                        : "Never"}
                      <p className="mt-0.5 text-[10px] text-slate-400">
                        Added {formatDate(user.created_at)}
                      </p>
                    </td>
                    <td className="px-5 py-3.5">
                      {user.must_change_password ? (
                        <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-semibold text-amber-700">
                          <ShieldCheck className="h-3 w-3" />
                          Change required
                        </span>
                      ) : (
                        <span className="text-[11px] text-slate-400">Set by user</span>
                      )}
                    </td>
                    <td className="px-5 py-3.5">
                      <div className="flex justify-end gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => setAction({ type: "edit", user })}
                          title={`Edit ${user.name}`}
                        >
                          <Pencil className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => setAction({ type: "reset", user })}
                          title={`Reset password for ${user.name}`}
                        >
                          <KeyRound className="h-4 w-4 text-amber-600" />
                        </Button>
                      </div>
                    </td>
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

      <UserActionModal action={action} onClose={() => setAction(null)} />
    </div>
  );
}

function UserActionModal({
  action,
  onClose,
}: {
  action: UserAction;
  onClose: () => void;
}) {
  if (action?.type === "create") {
    return <CreateUserModal onClose={onClose} />;
  }
  if (action?.type === "edit") {
    return <EditUserModal user={action.user} onClose={onClose} />;
  }
  if (action?.type === "reset") {
    return <ResetPasswordModal user={action.user} onClose={onClose} />;
  }
  return null;
}

function CreateUserModal({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient();
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<CreateValues>({
    resolver: zodResolver(createSchema),
    defaultValues: {
      name: "",
      email: "",
      role: "USER",
      temporary_password: "",
    },
  });

  const mutation = useMutation({
    mutationFn: (values: CreateValues) =>
      apiFetch<User>("/users", {
        method: "POST",
        body: JSON.stringify(values),
      }),
    onSuccess: (user) => {
      void queryClient.invalidateQueries({ queryKey: ["users"] });
      void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      toast.success(`${user.name} created. Share the temporary password securely.`);
      onClose();
    },
    onError: (error) => toast.error(errorMessage(error)),
  });

  return (
    <Modal
      open
      onClose={onClose}
      title="Create user"
      description="The user must replace the temporary password at first sign-in."
      footer={
        <>
          <Button variant="outline" onClick={onClose} disabled={mutation.isPending}>
            Cancel
          </Button>
          <Button
            onClick={handleSubmit((values) => mutation.mutate(values))}
            loading={mutation.isPending}
          >
            Create user
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <Field label="Full name" htmlFor="new-user-name" error={errors.name?.message} required>
          <Input id="new-user-name" placeholder="e.g. Priya Sharma" {...register("name")} />
        </Field>
        <Field
          label="Office People ID (email)"
          htmlFor="new-user-email"
          error={errors.email?.message}
          required
        >
          <Input
            id="new-user-email"
            type="email"
            placeholder="name@jatayues.com"
            {...register("email")}
          />
        </Field>
        <Field label="Role" htmlFor="new-user-role" error={errors.role?.message} required>
          <Select id="new-user-role" {...register("role")}>
            {ROLES.map((item) => (
              <option key={item} value={item}>
                {ROLE_LABELS[item]}
              </option>
            ))}
          </Select>
        </Field>
        <Field
          label="Temporary password"
          htmlFor="new-user-password"
          error={errors.temporary_password?.message}
          hint="8+ characters with uppercase, lowercase, number, and special character."
          required
        >
          <Input
            id="new-user-password"
            type="text"
            autoComplete="new-password"
            placeholder="e.g. Welcome@2026"
            {...register("temporary_password")}
          />
        </Field>
      </div>
    </Modal>
  );
}

function EditUserModal({
  user,
  onClose,
}: {
  user: User;
  onClose: () => void;
}) {
  const { user: currentUser } = useAuth();
  const queryClient = useQueryClient();
  const isSelf = currentUser?.id === user.id;

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<EditValues>({
    resolver: zodResolver(editSchema),
    defaultValues: {
      name: user.name,
      role: user.role,
      is_active: user.is_active,
    },
  });

  const mutation = useMutation({
    mutationFn: (values: EditValues) =>
      apiFetch<User>(`/users/${user.id}`, {
        method: "PATCH",
        body: JSON.stringify(values),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["users"] });
      void queryClient.invalidateQueries({ queryKey: ["users", "options"] });
      toast.success("User updated");
      onClose();
    },
    onError: (error) => toast.error(errorMessage(error)),
  });

  return (
    <Modal
      open
      onClose={onClose}
      title="Edit user"
      description={user.email}
      footer={
        <>
          <Button variant="outline" onClick={onClose} disabled={mutation.isPending}>
            Cancel
          </Button>
          <Button
            onClick={handleSubmit((values) => mutation.mutate(values))}
            loading={mutation.isPending}
          >
            Save changes
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <Field label="Full name" htmlFor="edit-user-name" error={errors.name?.message} required>
          <Input id="edit-user-name" {...register("name")} />
        </Field>
        <Field
          label="Role"
          htmlFor="edit-user-role"
          error={errors.role?.message}
          hint={isSelf ? "You cannot change your own role." : undefined}
          required
        >
          <Select id="edit-user-role" disabled={isSelf} {...register("role")}>
            {ROLES.map((item) => (
              <option key={item} value={item}>
                {ROLE_LABELS[item]}
              </option>
            ))}
          </Select>
        </Field>
        <label className="flex items-start gap-3 rounded-xl border border-slate-200 bg-slate-50 p-3">
          <input
            type="checkbox"
            disabled={isSelf}
            className="mt-0.5 h-4 w-4 rounded border-slate-300 accent-[#0f5c73]"
            {...register("is_active")}
          />
          <span>
            <span className="block text-sm font-medium text-slate-800">
              Account is active
            </span>
            <span className="mt-0.5 block text-[11px] leading-5 text-slate-500">
              Deactivated users cannot sign in. They remain in project history and
              audit records.
              {isSelf ? " You cannot deactivate your own account." : ""}
            </span>
          </span>
        </label>
      </div>
    </Modal>
  );
}

function ResetPasswordModal({
  user,
  onClose,
}: {
  user: User;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ResetValues>({
    resolver: zodResolver(resetSchema),
    defaultValues: { new_password: "", confirm_password: "" },
  });

  const mutation = useMutation({
    mutationFn: (values: ResetValues) =>
      apiFetch<User>(`/users/${user.id}/reset-password`, {
        method: "POST",
        body: JSON.stringify({ new_password: values.new_password }),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["users"] });
      toast.success("Password reset. The user must change it at next sign-in.");
      onClose();
    },
    onError: (error) => toast.error(errorMessage(error)),
  });

  return (
    <Modal
      open
      onClose={onClose}
      title="Reset password"
      description={`${user.name} · ${user.email}`}
      size="sm"
      footer={
        <>
          <Button variant="outline" onClick={onClose} disabled={mutation.isPending}>
            Cancel
          </Button>
          <Button
            variant="danger"
            onClick={handleSubmit((values) => mutation.mutate(values))}
            loading={mutation.isPending}
          >
            Reset password
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <AlertBanner tone="warning">
          The existing password will stop working immediately. The user will be
          forced to set a new password when they next sign in.
        </AlertBanner>
        <Field
          label="New temporary password"
          htmlFor="reset-password"
          error={errors.new_password?.message}
          required
        >
          <Input
            id="reset-password"
            type="text"
            autoComplete="new-password"
            placeholder="e.g. Reset@2026"
            {...register("new_password")}
          />
        </Field>
        <Field
          label="Confirm password"
          htmlFor="reset-password-confirm"
          error={errors.confirm_password?.message}
          required
        >
          <Input
            id="reset-password-confirm"
            type="text"
            autoComplete="new-password"
            {...register("confirm_password")}
          />
        </Field>
      </div>
    </Modal>
  );
}
