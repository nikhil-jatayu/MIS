"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Check, Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import {
  Button,
  Field,
  Input,
  Modal,
  Select,
  Textarea,
} from "@/components/ui";
import { apiFetch, errorMessage } from "@/lib/api";
import type {
  InventoryItem,
  Project,
  ProjectMemberRole,
  TestResult,
  UserSummary,
} from "@/lib/types";
import {
  MEMBER_ROLE_LABELS,
  PRIORITY_LABELS,
  TEST_RESULT_LABELS,
} from "@/lib/utils";

function useRefreshProject(projectId: string) {
  const queryClient = useQueryClient();
  return () => {
    void queryClient.invalidateQueries({ queryKey: ["project", projectId] });
    void queryClient.invalidateQueries({ queryKey: ["projects"] });
    void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    void queryClient.invalidateQueries({ queryKey: ["purchase-requests"] });
    void queryClient.invalidateQueries({ queryKey: ["progress", projectId] });
    void queryClient.invalidateQueries({ queryKey: ["attachments", projectId] });
  };
}

export function EditProjectModal({
  project,
  onClose,
}: {
  project: Project;
  onClose: () => void;
}) {
  const refresh = useRefreshProject(project.id);
  const [name, setName] = useState(project.name);
  const [description, setDescription] = useState(project.description ?? "");
  const [priority, setPriority] = useState(project.priority);
  const [startDate, setStartDate] = useState(project.start_date ?? "");
  const [endDate, setEndDate] = useState(project.end_date ?? "");
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () =>
      apiFetch<Project>(`/projects/${project.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          name,
          description: description || null,
          priority,
          start_date: startDate || null,
          end_date: endDate || null,
        }),
      }),
    onSuccess: () => {
      refresh();
      toast.success("Project updated");
      onClose();
    },
    onError: (mutationError) => {
      setError(errorMessage(mutationError));
      toast.error(errorMessage(mutationError));
    },
  });

  function submit() {
    setError(null);
    if (name.trim().length < 2) {
      setError("Project name must be at least 2 characters.");
      return;
    }
    if (startDate && endDate && endDate < startDate) {
      setError("Deadline must be on or after the start date.");
      return;
    }
    mutation.mutate();
  }

  return (
    <Modal
      open
      onClose={onClose}
      title="Edit project"
      description="Deadline changes are recorded as a distinct audit event."
      footer={
        <>
          <Button variant="outline" onClick={onClose} disabled={mutation.isPending}>
            Cancel
          </Button>
          <Button onClick={submit} loading={mutation.isPending}>
            Save changes
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <Field label="Project name" htmlFor="edit-project-name" required>
          <Input
            id="edit-project-name"
            value={name}
            onChange={(event) => setName(event.target.value)}
          />
        </Field>
        <Field label="Description" htmlFor="edit-project-description">
          <Textarea
            id="edit-project-description"
            value={description}
            onChange={(event) => setDescription(event.target.value)}
          />
        </Field>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Priority" htmlFor="edit-project-priority">
            <Select
              id="edit-project-priority"
              value={priority}
              onChange={(event) =>
                setPriority(event.target.value as Project["priority"])
              }
            >
              {Object.entries(PRIORITY_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </Select>
          </Field>
          <div />
          <Field label="Start date" htmlFor="edit-project-start">
            <Input
              id="edit-project-start"
              type="date"
              value={startDate}
              onChange={(event) => setStartDate(event.target.value)}
            />
          </Field>
          <Field label="Deadline" htmlFor="edit-project-end">
            <Input
              id="edit-project-end"
              type="date"
              value={endDate}
              onChange={(event) => setEndDate(event.target.value)}
            />
          </Field>
        </div>
        {error ? (
          <p className="rounded-lg bg-red-50 px-3 py-2 text-xs font-medium text-red-700">
            {error}
          </p>
        ) : null}
      </div>
    </Modal>
  );
}

export function MembersModal({
  project,
  users,
  onClose,
}: {
  project: Project;
  users: UserSummary[];
  onClose: () => void;
}) {
  const refresh = useRefreshProject(project.id);
  const [rows, setRows] = useState<
    { user_id: string; role_in_project: ProjectMemberRole }[]
  >(
    project.members.length
      ? project.members.map((member) => ({
          user_id: member.user.id,
          role_in_project: member.role_in_project,
        }))
      : [{ user_id: "", role_in_project: "DEVELOPER" }],
  );
  const [error, setError] = useState<string | null>(null);

  const activeIds = new Set(users.map((user) => user.id));
  const options = [
    ...users,
    ...project.members
      .map((member) => member.user)
      .filter((memberUser) => !activeIds.has(memberUser.id)),
  ];

  const mutation = useMutation({
    mutationFn: () =>
      apiFetch<Project>(`/projects/${project.id}/members`, {
        method: "PUT",
        body: JSON.stringify({ members: rows }),
      }),
    onSuccess: () => {
      refresh();
      toast.success("Project team updated");
      onClose();
    },
    onError: (mutationError) => {
      setError(errorMessage(mutationError));
      toast.error(errorMessage(mutationError));
    },
  });

  function submit() {
    setError(null);
    if (rows.length === 0) {
      setError("Assign at least one person.");
      return;
    }
    if (rows.some((row) => !row.user_id)) {
      setError("Select a person for every row.");
      return;
    }
    if (new Set(rows.map((row) => row.user_id)).size !== rows.length) {
      setError("Each person can only be assigned once.");
      return;
    }
    mutation.mutate();
  }

  return (
    <Modal
      open
      onClose={onClose}
      title="Manage project team"
      description="Admins can update members at any workflow stage."
      size="lg"
      footer={
        <>
          <Button variant="outline" onClick={onClose} disabled={mutation.isPending}>
            Cancel
          </Button>
          <Button onClick={submit} loading={mutation.isPending}>
            Save team
          </Button>
        </>
      }
    >
      <div className="space-y-3">
        {rows.map((row, index) => {
          const selectedIds = rows.map((item) => item.user_id);
          return (
            <div
              key={index}
              className="grid gap-3 rounded-xl border border-slate-200 bg-slate-50/50 p-3 sm:grid-cols-[1fr_180px_36px]"
            >
              <Field label="Person" htmlFor={`member-existing-${index}`}>
                <Select
                  id={`member-existing-${index}`}
                  value={row.user_id}
                  onChange={(event) =>
                    setRows((current) =>
                      current.map((item, itemIndex) =>
                        itemIndex === index
                          ? { ...item, user_id: event.target.value }
                          : item,
                      ),
                    )
                  }
                >
                  <option value="">Select a person</option>
                  {options.map((person) => (
                    <option
                      key={person.id}
                      value={person.id}
                      disabled={
                        selectedIds.includes(person.id) &&
                        selectedIds.indexOf(person.id) !== index
                      }
                    >
                      {person.name} · {person.email}
                    </option>
                  ))}
                </Select>
              </Field>
              <Field label="Project role" htmlFor={`member-existing-role-${index}`}>
                <Select
                  id={`member-existing-role-${index}`}
                  value={row.role_in_project}
                  onChange={(event) =>
                    setRows((current) =>
                      current.map((item, itemIndex) =>
                        itemIndex === index
                          ? {
                              ...item,
                              role_in_project: event.target
                                .value as ProjectMemberRole,
                            }
                          : item,
                      ),
                    )
                  }
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
                  variant="ghost"
                  size="icon"
                  onClick={() => setRows((current) => current.filter((_, i) => i !== index))}
                  disabled={rows.length === 1}
                  title="Remove member"
                >
                  <Trash2 className="h-4 w-4 text-red-500" />
                </Button>
              </div>
            </div>
          );
        })}
        <Button
          variant="outline"
          size="sm"
          onClick={() =>
            setRows((current) => [
              ...current,
              { user_id: "", role_in_project: "DEVELOPER" },
            ])
          }
        >
          <Plus className="h-3.5 w-3.5" />
          Add member
        </Button>
        {error ? (
          <p className="rounded-lg bg-red-50 px-3 py-2 text-xs font-medium text-red-700">
            {error}
          </p>
        ) : null}
      </div>
    </Modal>
  );
}

export function BomModal({
  project,
  inventory,
  onClose,
}: {
  project: Project;
  inventory: InventoryItem[];
  onClose: () => void;
}) {
  const refresh = useRefreshProject(project.id);
  const [rows, setRows] = useState(
    project.bom_lines.map((line) => ({
      item_id: line.item.id,
      quantity_required: line.quantity_required,
    })),
  );
  const [error, setError] = useState<string | null>(null);
  const inventoryMap = new Map(inventory.map((item) => [item.id, item]));

  const mutation = useMutation({
    mutationFn: () =>
      apiFetch<Project>(`/projects/${project.id}/bom`, {
        method: "PUT",
        body: JSON.stringify({ lines: rows }),
      }),
    onSuccess: () => {
      refresh();
      toast.success("Bill of materials updated and inventory re-checked");
      onClose();
    },
    onError: (mutationError) => {
      setError(errorMessage(mutationError));
      toast.error(errorMessage(mutationError));
    },
  });

  function submit() {
    setError(null);
    if (rows.some((row) => !row.item_id)) {
      setError("Select an inventory item for every row.");
      return;
    }
    if (rows.some((row) => !Number.isInteger(row.quantity_required) || row.quantity_required < 1)) {
      setError("Every quantity must be a whole number of at least 1.");
      return;
    }
    if (new Set(rows.map((row) => row.item_id)).size !== rows.length) {
      setError("Each inventory item can only appear once.");
      return;
    }
    mutation.mutate();
  }

  return (
    <Modal
      open
      onClose={onClose}
      title="Edit bill of materials"
      description="Saving releases previous allocations and re-runs the inventory check."
      size="lg"
      footer={
        <>
          <Button variant="outline" onClick={onClose} disabled={mutation.isPending}>
            Cancel
          </Button>
          <Button onClick={submit} loading={mutation.isPending}>
            Save BOM
          </Button>
        </>
      }
    >
      <div className="space-y-3">
        {rows.length === 0 ? (
          <p className="rounded-xl border border-dashed border-slate-300 bg-slate-50 px-4 py-6 text-center text-xs text-slate-500">
            No material required. Saving will mark the project ready for production.
          </p>
        ) : null}
        {rows.map((row, index) => {
          const selected = inventoryMap.get(row.item_id);
          const selectedIds = rows.map((item) => item.item_id);
          return (
            <div
              key={index}
              className="rounded-xl border border-slate-200 bg-slate-50/50 p-3"
            >
              <div className="grid gap-3 sm:grid-cols-[1fr_120px_36px]">
                <Field label="Inventory item" htmlFor={`bom-edit-item-${index}`}>
                  <Select
                    id={`bom-edit-item-${index}`}
                    value={row.item_id}
                    onChange={(event) =>
                      setRows((current) =>
                        current.map((item, itemIndex) =>
                          itemIndex === index
                            ? { ...item, item_id: event.target.value }
                            : item,
                        ),
                      )
                    }
                  >
                    <option value="">Select an item</option>
                    {inventory.map((item) => (
                      <option
                        key={item.id}
                        value={item.id}
                        disabled={
                          selectedIds.includes(item.id) &&
                          selectedIds.indexOf(item.id) !== index
                        }
                      >
                        {item.sku} · {item.name} ({item.quantity_available} available)
                      </option>
                    ))}
                  </Select>
                </Field>
                <Field label="Quantity" htmlFor={`bom-edit-qty-${index}`}>
                  <Input
                    id={`bom-edit-qty-${index}`}
                    type="number"
                    min={1}
                    step={1}
                    value={row.quantity_required}
                    onChange={(event) =>
                      setRows((current) =>
                        current.map((item, itemIndex) =>
                          itemIndex === index
                            ? {
                                ...item,
                                quantity_required: Number(event.target.value),
                              }
                            : item,
                        ),
                      )
                    }
                  />
                </Field>
                <div className="flex items-end">
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => setRows((current) => current.filter((_, i) => i !== index))}
                    title="Remove item"
                  >
                    <Trash2 className="h-4 w-4 text-red-500" />
                  </Button>
                </div>
              </div>
              {selected ? (
                <p className="mt-2 text-[11px] text-slate-500">
                  Available: <strong>{selected.quantity_available}</strong> units
                  {row.quantity_required > selected.quantity_available ? (
                    <span className="ml-2 font-semibold text-amber-700">
                      Shortage of {row.quantity_required - selected.quantity_available}
                    </span>
                  ) : null}
                </p>
              ) : null}
            </div>
          );
        })}
        <Button
          variant="outline"
          size="sm"
          onClick={() =>
            setRows((current) => [...current, { item_id: "", quantity_required: 1 }])
          }
        >
          <Plus className="h-3.5 w-3.5" />
          Add item
        </Button>
        {error ? (
          <p className="rounded-lg bg-red-50 px-3 py-2 text-xs font-medium text-red-700">
            {error}
          </p>
        ) : null}
      </div>
    </Modal>
  );
}

export function ProgressModal({
  project,
  onClose,
}: {
  project: Project;
  onClose: () => void;
}) {
  const refresh = useRefreshProject(project.id);
  const [percent, setPercent] = useState(project.progress_percent);
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () =>
      apiFetch(`/projects/${project.id}/progress-logs`, {
        method: "POST",
        body: JSON.stringify({ note, progress_percent: percent }),
      }),
    onSuccess: () => {
      refresh();
      toast.success("Progress logged");
      onClose();
    },
    onError: (mutationError) => {
      setError(errorMessage(mutationError));
      toast.error(errorMessage(mutationError));
    },
  });

  function submit() {
    setError(null);
    if (note.trim().length < 3) {
      setError("Add a note of at least 3 characters.");
      return;
    }
    if (percent < project.progress_percent) {
      setError(`Progress cannot be below the current ${project.progress_percent}%.`);
      return;
    }
    if (percent >= 100) {
      setError("100% is set only at Admin sign-off.");
      return;
    }
    mutation.mutate();
  }

  return (
    <Modal
      open
      onClose={onClose}
      title="Log progress"
      description="Progress history is append-only. Notes cannot be edited after saving."
      footer={
        <>
          <Button variant="outline" onClick={onClose} disabled={mutation.isPending}>
            Cancel
          </Button>
          <Button onClick={submit} loading={mutation.isPending}>
            Save progress
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
          <div className="flex items-center justify-between text-xs">
            <span className="text-slate-500">Current progress</span>
            <span className="font-bold text-slate-900">
              {project.progress_percent}%
            </span>
          </div>
        </div>
        <Field
          label="New progress"
          htmlFor="progress-percent"
          hint="Must be equal to or higher than the current value, and below 100%."
          required
        >
          <Input
            id="progress-percent"
            type="number"
            min={project.progress_percent}
            max={99}
            step={1}
            value={percent}
            onChange={(event) => setPercent(Number(event.target.value))}
          />
        </Field>
        <Field label="Progress note" htmlFor="progress-note" required>
          <Textarea
            id="progress-note"
            value={note}
            onChange={(event) => setNote(event.target.value)}
            placeholder="What was completed since the last update?"
          />
        </Field>
        {error ? (
          <p className="rounded-lg bg-red-50 px-3 py-2 text-xs font-medium text-red-700">
            {error}
          </p>
        ) : null}
      </div>
    </Modal>
  );
}

export function SubmitTestingModal({
  project,
  users,
  onClose,
}: {
  project: Project;
  users: UserSummary[];
  onClose: () => void;
}) {
  const refresh = useRefreshProject(project.id);
  const currentTester =
    project.members.find((member) => member.role_in_project === "TESTER")?.user.id ??
    "";
  const [testerId, setTesterId] = useState(currentTester);
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () =>
      apiFetch<Project>(`/projects/${project.id}/submit-testing`, {
        method: "POST",
        body: JSON.stringify({ tester_id: testerId }),
      }),
    onSuccess: () => {
      refresh();
      toast.success("Project submitted for testing");
      onClose();
    },
    onError: (mutationError) => {
      setError(errorMessage(mutationError));
      toast.error(errorMessage(mutationError));
    },
  });

  return (
    <Modal
      open
      onClose={onClose}
      title="Submit for testing"
      description="Select the QA Tester who will record the pass or fail result."
      size="sm"
      footer={
        <>
          <Button variant="outline" onClick={onClose} disabled={mutation.isPending}>
            Cancel
          </Button>
          <Button
            onClick={() => {
              if (!testerId) {
                setError("Select a Tester.");
                return;
              }
              mutation.mutate();
            }}
            loading={mutation.isPending}
          >
            Submit for testing
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <Field label="Tester" htmlFor="tester-select" required>
          <Select
            id="tester-select"
            value={testerId}
            onChange={(event) => setTesterId(event.target.value)}
          >
            <option value="">Select a Tester</option>
            {users.map((person) => (
              <option key={person.id} value={person.id}>
                {person.name} · {person.email}
              </option>
            ))}
          </Select>
        </Field>
        <p className="text-xs leading-5 text-slate-500">
          The selected person is added as a Tester if they are not already on the
          project. The project moves to In Testing.
        </p>
        {error ? (
          <p className="rounded-lg bg-red-50 px-3 py-2 text-xs font-medium text-red-700">
            {error}
          </p>
        ) : null}
      </div>
    </Modal>
  );
}

export function TestResultModal({
  project,
  onClose,
}: {
  project: Project;
  onClose: () => void;
}) {
  const refresh = useRefreshProject(project.id);
  const [result, setResult] = useState<TestResult>("PASS");
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () =>
      apiFetch<Project>(`/projects/${project.id}/test-result`, {
        method: "POST",
        body: JSON.stringify({ result, note }),
      }),
    onSuccess: () => {
      refresh();
      toast.success(
        result === "PASS"
          ? "Test result recorded. Awaiting Admin sign-off."
          : "Test failed. Project returned to In Production.",
      );
      onClose();
    },
    onError: (mutationError) => {
      setError(errorMessage(mutationError));
      toast.error(errorMessage(mutationError));
    },
  });

  return (
    <Modal
      open
      onClose={onClose}
      title="Record test result"
      description="Only the assigned Tester can record this result."
      size="sm"
      footer={
        <>
          <Button variant="outline" onClick={onClose} disabled={mutation.isPending}>
            Cancel
          </Button>
          <Button
            variant={result === "PASS" ? "success" : "danger"}
            onClick={() => {
              if (note.trim().length < 3) {
                setError("Add a test note of at least 3 characters.");
                return;
              }
              mutation.mutate();
            }}
            loading={mutation.isPending}
          >
            <Check className="h-4 w-4" />
            Record {TEST_RESULT_LABELS[result].toLowerCase()}
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <Field label="Result" htmlFor="test-result">
          <Select
            id="test-result"
            value={result}
            onChange={(event) => setResult(event.target.value as TestResult)}
          >
            <option value="PASS">Passed</option>
            <option value="FAIL">Failed</option>
          </Select>
        </Field>
        <Field label="Test note" htmlFor="test-note" required>
          <Textarea
            id="test-note"
            value={note}
            onChange={(event) => setNote(event.target.value)}
            placeholder="Summarise the test outcome, evidence, or failure details."
          />
        </Field>
        {result === "FAIL" ? (
          <p className="rounded-lg bg-amber-50 px-3 py-2 text-xs font-medium text-amber-800">
            A failed test returns the project to In Production for rework.
          </p>
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

export function CompleteProjectModal({
  project,
  onClose,
}: {
  project: Project;
  onClose: () => void;
}) {
  const refresh = useRefreshProject(project.id);
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () =>
      apiFetch<Project>(`/projects/${project.id}/complete`, {
        method: "POST",
        body: JSON.stringify({ note: note || null }),
      }),
    onSuccess: () => {
      refresh();
      toast.success("Project signed off as completed");
      onClose();
    },
    onError: (mutationError) => {
      setError(errorMessage(mutationError));
      toast.error(errorMessage(mutationError));
    },
  });

  return (
    <Modal
      open
      onClose={onClose}
      title="Sign off project"
      description="The project will be marked Completed and progress set to 100%."
      size="sm"
      footer={
        <>
          <Button variant="outline" onClick={onClose} disabled={mutation.isPending}>
            Cancel
          </Button>
          <Button variant="success" onClick={() => mutation.mutate()} loading={mutation.isPending}>
            Complete project
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-xs leading-5 text-emerald-800">
          <p className="font-semibold">{project.name} passed testing.</p>
          <p className="mt-0.5">Sign-off closes the project and makes it read-only.</p>
        </div>
        <Field label="Sign-off note (optional)" htmlFor="signoff-note">
          <Textarea
            id="signoff-note"
            value={note}
            onChange={(event) => setNote(event.target.value)}
            placeholder="Final acceptance notes, handover reference, etc."
          />
        </Field>
        {error ? (
          <p className="rounded-lg bg-red-50 px-3 py-2 text-xs font-medium text-red-700">
            {error}
          </p>
        ) : null}
      </div>
    </Modal>
  );
}
