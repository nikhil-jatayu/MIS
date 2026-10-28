import {
  ArrowUpRight,
  CalendarDays,
  CheckCircle2,
  Clock3,
  PackageCheck,
  TriangleAlert,
  Users,
} from "lucide-react";
import Link from "next/link";

import {
  PriorityBadge,
  ProjectStatusBadge,
  ProjectTypeBadge,
} from "@/components/badges";
import { Avatar, Card, ProgressBar } from "@/components/ui";
import type { Project } from "@/lib/types";
import {
  cn,
  formatDate,
  isPastDate,
  pluralise,
  PROJECT_STATUS_LABELS,
} from "@/lib/utils";

export function ProjectCard({ project }: { project: Project }) {
  const overdue =
    isPastDate(project.end_date) && project.status !== "COMPLETED";
  const allocated = project.bom_lines.reduce(
    (sum, line) => sum + line.quantity_allocated,
    0,
  );
  const required = project.bom_lines.reduce(
    (sum, line) => sum + line.quantity_required,
    0,
  );

  return (
    <Link href={`/projects/${project.id}`} className="group block">
      <Card className="h-full p-5 transition duration-200 group-hover:-translate-y-0.5 group-hover:border-teal-300 group-hover:shadow-md">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="mb-2 flex flex-wrap items-center gap-1.5">
              <ProjectTypeBadge type={project.type} />
              <PriorityBadge priority={project.priority} />
            </div>
            <h3 className="line-clamp-1 text-base font-bold text-slate-900 group-hover:text-[#0f5c73]">
              {project.name}
            </h3>
            <p className="mt-1 line-clamp-2 min-h-9 text-xs leading-5 text-slate-500">
              {project.description || "No description provided."}
            </p>
          </div>
          <ProjectStatusBadge status={project.status} />
        </div>

        <div className="mt-4">
          <div className="mb-1.5 flex items-center justify-between text-[11px]">
            <span className="font-medium text-slate-500">Progress</span>
            <span className="font-bold text-slate-700">
              {project.progress_percent}%
            </span>
          </div>
          <ProgressBar value={project.progress_percent} />
        </div>

        <div className="mt-4 grid grid-cols-2 gap-3 text-[11px]">
          <div className="flex items-center gap-1.5 text-slate-600">
            <CalendarDays className="h-3.5 w-3.5 text-slate-400" />
            <span className={cn(overdue && "font-semibold text-red-600")}>
              {formatDate(project.end_date, "No deadline")}
            </span>
          </div>
          <div className="flex items-center gap-1.5 text-slate-600">
            <Clock3 className="h-3.5 w-3.5 text-slate-400" />
            <span>
              {project.pending_days === 0
                ? "Updated today"
                : `${pluralise(project.pending_days, "day")} since update`}
            </span>
          </div>
          <div className="flex items-center gap-1.5 text-slate-600">
            <Users className="h-3.5 w-3.5 text-slate-400" />
            <span className="truncate">
              {pluralise(project.members.length, "member")}
            </span>
          </div>
          <div
            className={cn(
              "flex items-center gap-1.5",
              project.is_inventory_ready ? "text-emerald-700" : "text-amber-700",
            )}
          >
            {project.is_inventory_ready ? (
              <PackageCheck className="h-3.5 w-3.5" />
            ) : (
              <TriangleAlert className="h-3.5 w-3.5" />
            )}
            <span>
              {project.is_inventory_ready
                ? "Inventory ready"
                : `${pluralise(project.shortage_count, "shortage")}`}
            </span>
          </div>
        </div>

        {project.bom_lines.length > 0 ? (
          <div className="mt-4 rounded-lg border border-slate-100 bg-slate-50/70 px-3 py-2">
            <div className="flex items-center justify-between text-[10px] font-semibold tracking-wide text-slate-500 uppercase">
              <span>Inventory checklist</span>
              <span>
                {allocated}/{required} units
              </span>
            </div>
            <div className="mt-1.5 space-y-1">
              {project.bom_lines.slice(0, 3).map((line) => (
                <div
                  key={line.id}
                  className="flex items-center justify-between gap-2 text-[11px]"
                >
                  <span className="truncate text-slate-600">
                    {line.item.sku} · {line.item.name}
                  </span>
                  <span
                    className={cn(
                      "flex shrink-0 items-center gap-0.5 font-semibold",
                      line.quantity_shortage > 0
                        ? "text-amber-700"
                        : "text-emerald-700",
                    )}
                  >
                    {line.quantity_shortage > 0 ? (
                      <TriangleAlert className="h-3 w-3" />
                    ) : (
                      <CheckCircle2 className="h-3 w-3" />
                    )}
                    {line.quantity_allocated}/{line.quantity_required}
                  </span>
                </div>
              ))}
              {project.bom_lines.length > 3 ? (
                <p className="text-[10px] text-slate-400">
                  +{project.bom_lines.length - 3} more item(s)
                </p>
              ) : null}
            </div>
          </div>
        ) : null}

        <div className="mt-4 flex items-center justify-between border-t border-slate-100 pt-3">
          <div className="flex -space-x-1.5">
            {project.members.slice(0, 4).map((member) => (
              <Avatar
                key={member.id}
                name={member.user.name}
                className="h-7 w-7 border-2 border-white bg-slate-100 text-[10px]"
              />
            ))}
            {project.members.length > 4 ? (
              <span className="flex h-7 w-7 items-center justify-center rounded-full border-2 border-white bg-slate-100 text-[9px] font-bold text-slate-600">
                +{project.members.length - 4}
              </span>
            ) : null}
          </div>
          <span className="inline-flex items-center gap-0.5 text-[11px] font-semibold text-[#0f5c73]">
            {PROJECT_STATUS_LABELS[project.status]}
            <ArrowUpRight className="h-3.5 w-3.5" />
          </span>
        </div>
      </Card>
    </Link>
  );
}
