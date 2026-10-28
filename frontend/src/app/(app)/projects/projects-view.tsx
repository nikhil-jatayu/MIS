"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";
import {
  FolderKanban,
  Plus,
  RefreshCw,
  Search,
  SlidersHorizontal,
  X,
} from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useState } from "react";

import { ProjectCard } from "@/components/project-card";
import {
  AlertBanner,
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
import { useAuth } from "@/lib/auth";
import type { Page, Priority, Project, ProjectStatus, ProjectType } from "@/lib/types";
import { useDebouncedValue } from "@/lib/use-debounced";
import {
  buildQuery,
  buttonClass,
  PRIORITY_LABELS,
  PROJECT_STATUS_LABELS,
  PROJECT_TYPE_LABELS,
} from "@/lib/utils";

const STATUSES = Object.keys(PROJECT_STATUS_LABELS) as ProjectStatus[];
const PRIORITIES = Object.keys(PRIORITY_LABELS) as Priority[];
const TYPES = Object.keys(PROJECT_TYPE_LABELS) as ProjectType[];

const SORTS = {
  newest: { sort: "created_at", order: "desc", label: "Newest first" },
  deadline: { sort: "end_date", order: "asc", label: "Deadline (soonest)" },
  priority: { sort: "priority", order: "desc", label: "Priority (highest)" },
  status: { sort: "status", order: "asc", label: "Workflow status" },
  progress: { sort: "progress_percent", order: "desc", label: "Progress (highest)" },
  name: { sort: "name", order: "asc", label: "Name (A–Z)" },
} as const;

type SortKey = keyof typeof SORTS;

export function ProjectsView() {
  const { user } = useAuth();
  const searchParams = useSearchParams();
  const initialStatus = searchParams.get("status");
  const [search, setSearch] = useState("");
  const [type, setType] = useState<ProjectType | "">("");
  const [status, setStatus] = useState<ProjectStatus | "">(
    initialStatus && STATUSES.includes(initialStatus as ProjectStatus)
      ? (initialStatus as ProjectStatus)
      : "",
  );
  const [priority, setPriority] = useState<Priority | "">("");
  const [deadlineFrom, setDeadlineFrom] = useState("");
  const [deadlineTo, setDeadlineTo] = useState("");
  const [assignedToMe, setAssignedToMe] = useState(
    searchParams.get("assigned") === "1",
  );
  const [sortKey, setSortKey] = useState<SortKey>(
    searchParams.get("assigned") === "1" ? "deadline" : "newest",
  );
  const [page, setPage] = useState(1);
  const debouncedSearch = useDebouncedValue(search);

  const query = useQuery({
    queryKey: [
      "projects",
      {
        q: debouncedSearch,
        type,
        status,
        priority,
        deadlineFrom,
        deadlineTo,
        assignedToMe,
        sortKey,
        page,
      },
    ],
    queryFn: () => {
      const sort = SORTS[sortKey];
      const params = buildQuery({
        page,
        page_size: 12,
        q: debouncedSearch,
        type,
        status,
        priority,
        deadline_from: deadlineFrom,
        deadline_to: deadlineTo,
        assigned_to_me: assignedToMe || undefined,
        sort: sort.sort,
        order: sort.order,
      });
      return apiFetch<Page<Project>>(`/projects${params}`);
    },
    placeholderData: keepPreviousData,
  });

  const canCreate = user?.role === "ADMIN" || user?.role === "SUPER_ADMIN";
  const hasFilters = Boolean(
    search ||
      type ||
      status ||
      priority ||
      deadlineFrom ||
      deadlineTo ||
      assignedToMe,
  );

  function resetFilters() {
    setSearch("");
    setType("");
    setStatus("");
    setPriority("");
    setDeadlineFrom("");
    setDeadlineTo("");
    setAssignedToMe(false);
    setPage(1);
  }

  return (
    <div className="animate-rise-in">
      <PageHeader
        eyebrow="Portfolio"
        title="Projects"
        description="Every R&D and production project, with live inventory readiness, personnel, deadlines, and progress."
        actions={
          canCreate ? (
            <Link href="/projects/new" className={buttonClass("primary")}>
              <Plus className="h-4 w-4" />
              New project
            </Link>
          ) : null
        }
      />

      <Card className="mb-5 p-4">
        <div className="mb-3 flex items-center gap-2 text-xs font-semibold text-slate-500">
          <SlidersHorizontal className="h-4 w-4" />
          Filters and sorting
          {query.isFetching ? (
            <Spinner className="ml-1 h-3.5 w-3.5 text-[#0f5c73]" />
          ) : null}
        </div>
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <Field label="Search" htmlFor="project-search">
            <div className="relative">
              <Search className="pointer-events-none absolute top-3 left-3 h-4 w-4 text-slate-400" />
              <Input
                id="project-search"
                value={search}
                onChange={(event) => {
                  setSearch(event.target.value);
                  setPage(1);
                }}
                placeholder="Search name or description"
                className="pl-9"
              />
            </div>
          </Field>
          <Field label="Type" htmlFor="project-type">
            <Select
              id="project-type"
              value={type}
              onChange={(event) => {
                setType(event.target.value as ProjectType | "");
                setPage(1);
              }}
            >
              <option value="">All types</option>
              {TYPES.map((item) => (
                <option key={item} value={item}>
                  {PROJECT_TYPE_LABELS[item]}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Status" htmlFor="project-status-filter">
            <Select
              id="project-status-filter"
              value={status}
              onChange={(event) => {
                setStatus(event.target.value as ProjectStatus | "");
                setPage(1);
              }}
            >
              <option value="">All statuses</option>
              {STATUSES.map((item) => (
                <option key={item} value={item}>
                  {PROJECT_STATUS_LABELS[item]}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Priority" htmlFor="project-priority">
            <Select
              id="project-priority"
              value={priority}
              onChange={(event) => {
                setPriority(event.target.value as Priority | "");
                setPage(1);
              }}
            >
              <option value="">All priorities</option>
              {PRIORITIES.map((item) => (
                <option key={item} value={item}>
                  {PRIORITY_LABELS[item]}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Deadline from" htmlFor="deadline-from">
            <Input
              id="deadline-from"
              type="date"
              value={deadlineFrom}
              onChange={(event) => {
                setDeadlineFrom(event.target.value);
                setPage(1);
              }}
            />
          </Field>
          <Field label="Deadline to" htmlFor="deadline-to">
            <Input
              id="deadline-to"
              type="date"
              value={deadlineTo}
              onChange={(event) => {
                setDeadlineTo(event.target.value);
                setPage(1);
              }}
            />
          </Field>
          <Field label="Sort by" htmlFor="project-sort">
            <Select
              id="project-sort"
              value={sortKey}
              onChange={(event) => {
                setSortKey(event.target.value as SortKey);
                setPage(1);
              }}
            >
              {Object.entries(SORTS).map(([key, sort]) => (
                <option key={key} value={key}>
                  {sort.label}
                </option>
              ))}
            </Select>
          </Field>
          <div className="flex items-end gap-2">
            <label className="flex h-10 flex-1 cursor-pointer items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 text-xs font-medium text-slate-600 shadow-sm">
              <input
                type="checkbox"
                checked={assignedToMe}
                onChange={(event) => {
                  setAssignedToMe(event.target.checked);
                  setPage(1);
                }}
                className="h-3.5 w-3.5 rounded border-slate-300 accent-[#0f5c73]"
              />
              Assigned to me
            </label>
            {hasFilters ? (
              <Button
                variant="ghost"
                size="icon"
                onClick={resetFilters}
                title="Clear filters"
                aria-label="Clear filters"
              >
                <X className="h-4 w-4" />
              </Button>
            ) : null}
          </div>
        </div>
      </Card>

      {query.isError ? (
        <AlertBanner
          tone="danger"
          title="Unable to load projects"
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
        <div className="grid gap-4 sm:grid-cols-2 2xl:grid-cols-3">
          {Array.from({ length: 6 }).map((_, index) => (
            <Skeleton key={index} className="h-80" />
          ))}
        </div>
      ) : !query.data?.items.length ? (
        <Card>
          <EmptyState
            icon={<FolderKanban className="h-5 w-5" />}
            title={hasFilters ? "No projects match these filters" : "No projects yet"}
            description={
              hasFilters
                ? "Try widening the date range or clearing one of the filters."
                : canCreate
                  ? "Create the first project to start order intake and the inventory check."
                  : "You will see projects here once an Admin adds them."
            }
            action={
              hasFilters ? (
                <Button variant="outline" size="sm" onClick={resetFilters}>
                  Clear filters
                </Button>
              ) : canCreate ? (
                <Link href="/projects/new" className={buttonClass("primary", "sm")}>
                  <Plus className="h-3.5 w-3.5" />
                  Create project
                </Link>
              ) : undefined
            }
          />
        </Card>
      ) : (
        <>
          <div className="mb-3 flex items-center justify-between">
            <p className="text-xs text-slate-500">
              {query.data.total} project{query.data.total === 1 ? "" : "s"} found
            </p>
          </div>
          <div className="grid gap-4 sm:grid-cols-2 2xl:grid-cols-3">
            {query.data.items.map((project) => (
              <ProjectCard key={project.id} project={project} />
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
    </div>
  );
}
