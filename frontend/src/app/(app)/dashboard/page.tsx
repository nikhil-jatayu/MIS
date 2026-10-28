"use client";

import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  BellRing,
  Boxes,
  CheckCircle2,
  CircleDashed,
  ClipboardList,
  Clock3,
  FolderKanban,
  PackageOpen,
  Plus,
  Settings,
  ShieldAlert,
  ShoppingCart,
  Users,
  Wrench,
  type LucideIcon,
} from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";

import { AlertTypeBadge, ProjectStatusBadge } from "@/components/badges";
import {
  AlertBanner,
  Button,
  Card,
  CardHeader,
  EmptyState,
  PageHeader,
  ProgressBar,
  Skeleton,
} from "@/components/ui";
import { apiFetch, errorMessage } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { DashboardSummary } from "@/lib/types";
import {
  buttonClass,
  cn,
  formatDate,
  formatDateTime,
  PROJECT_STATUS_LABELS,
  ROLE_LABELS,
} from "@/lib/utils";

interface StatDefinition {
  label: string;
  value: number;
  icon: LucideIcon;
  tone: string;
  hint?: string;
  href?: string;
}

export default function DashboardPage() {
  const { user } = useAuth();
  const query = useQuery({
    queryKey: ["dashboard"],
    queryFn: () => apiFetch<DashboardSummary>("/dashboard"),
    enabled: Boolean(user),
    refetchInterval: 60_000,
  });

  if (!user) return null;

  if (query.isLoading) {
    return (
      <div>
        <Skeleton className="h-8 w-60" />
        <Skeleton className="mt-2 h-4 w-96" />
        <div className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 8 }).map((_, index) => (
            <Skeleton key={index} className="h-28" />
          ))}
        </div>
        <Skeleton className="mt-6 h-80" />
      </div>
    );
  }

  if (query.isError || !query.data) {
    return (
      <div>
        <PageHeader title="Dashboard" />
        <AlertBanner
          tone="danger"
          title="Dashboard unavailable"
          action={
            <Button variant="outline" size="sm" onClick={() => query.refetch()}>
              Retry
            </Button>
          }
        >
          {errorMessage(query.error)}
        </AlertBanner>
      </div>
    );
  }

  const { stats, recent_projects, recent_alerts } = query.data;
  const roleCopy = {
    SUPER_ADMIN: {
      eyebrow: "Executive overview",
      title: `Good to see you, ${user.name.split(" ")[0]}`,
      description:
        "System-wide health across projects, inventory, purchasing, and Time Counter escalations.",
    },
    ADMIN: {
      eyebrow: "Operations overview",
      title: `Good to see you, ${user.name.split(" ")[0]}`,
      description:
        "Track project readiness, inventory constraints, purchase approvals, and production flow.",
    },
    USER: {
      eyebrow: "My workspace",
      title: `Welcome, ${user.name.split(" ")[0]}`,
      description:
        "Your assigned projects, progress updates, purchase requests, and deadline alerts.",
    },
  }[user.role];

  const commonStats: StatDefinition[] = [
    {
      label: "Total projects",
      value: stats.projects_total,
      icon: FolderKanban,
      tone: "bg-sky-50 text-sky-700",
      href: "/projects",
    },
    {
      label: "Active projects",
      value: stats.projects_active,
      icon: Activity,
      tone: "bg-teal-50 text-teal-700",
      href: "/projects",
    },
    {
      label: "Completed",
      value: stats.projects_completed,
      icon: CheckCircle2,
      tone: "bg-emerald-50 text-emerald-700",
      href: "/projects?status=COMPLETED",
    },
    {
      label: "Unread alerts",
      value: stats.unread_alerts,
      icon: BellRing,
      tone: "bg-amber-50 text-amber-700",
      href: "/alerts",
    },
  ];

  const roleStats: Record<typeof user.role, StatDefinition[]> = {
    SUPER_ADMIN: [
      ...commonStats,
      {
        label: "Escalated alerts",
        value: stats.escalated_alerts,
        icon: ShieldAlert,
        tone: "bg-red-50 text-red-700",
        href: "/alerts",
      },
      {
        label: "Pending purchases",
        value: stats.pending_purchase_requests,
        icon: ShoppingCart,
        tone: "bg-orange-50 text-orange-700",
        href: "/purchases?status=PENDING",
      },
      {
        label: "Active users",
        value: stats.users_total,
        icon: Users,
        tone: "bg-violet-50 text-violet-700",
        href: "/users",
      },
      {
        label: "Inventory items",
        value: stats.inventory_items,
        icon: Boxes,
        tone: "bg-slate-100 text-slate-700",
        href: "/inventory",
      },
    ],
    ADMIN: [
      ...commonStats,
      {
        label: "Pending inventory",
        value: stats.pending_inventory,
        icon: Clock3,
        tone: "bg-amber-50 text-amber-700",
        href: "/projects?status=PENDING_INVENTORY",
      },
      {
        label: "Pending purchases",
        value: stats.pending_purchase_requests,
        icon: ShoppingCart,
        tone: "bg-orange-50 text-orange-700",
        href: "/purchases?status=PENDING",
      },
      {
        label: "In testing",
        value: stats.in_testing,
        icon: ClipboardList,
        tone: "bg-violet-50 text-violet-700",
        href: "/projects?status=IN_TESTING",
      },
      {
        label: "Awaiting delivery",
        value: stats.awaiting_delivery,
        icon: PackageOpen,
        tone: "bg-indigo-50 text-indigo-700",
        href: "/projects?status=AWAITING_DELIVERY",
      },
    ],
    USER: [
      {
        label: "Assigned to me",
        value: stats.projects_assigned,
        icon: FolderKanban,
        tone: "bg-sky-50 text-sky-700",
        href: "/projects?assigned=1",
      },
      {
        label: "Active projects",
        value: stats.projects_active,
        icon: Activity,
        tone: "bg-teal-50 text-teal-700",
        href: "/projects",
      },
      {
        label: "Unread alerts",
        value: stats.unread_alerts,
        icon: BellRing,
        tone: "bg-amber-50 text-amber-700",
        href: "/alerts",
      },
      {
        label: "Pending purchases",
        value: stats.pending_purchase_requests,
        icon: ShoppingCart,
        tone: "bg-orange-50 text-orange-700",
        href: "/purchases?status=PENDING",
      },
      {
        label: "In production",
        value: stats.in_production,
        icon: Wrench,
        tone: "bg-indigo-50 text-indigo-700",
        href: "/projects?status=IN_PRODUCTION",
      },
      {
        label: "In testing",
        value: stats.in_testing,
        icon: ClipboardList,
        tone: "bg-violet-50 text-violet-700",
        href: "/projects?status=IN_TESTING",
      },
      {
        label: "Ready for production",
        value: stats.ready_for_production,
        icon: PackageOpen,
        tone: "bg-emerald-50 text-emerald-700",
        href: "/projects?status=READY_FOR_PRODUCTION",
      },
      {
        label: "Completed",
        value: stats.projects_completed,
        icon: CheckCircle2,
        tone: "bg-slate-100 text-slate-700",
        href: "/projects?status=COMPLETED",
      },
    ],
  };

  const quickLinks: Record<typeof user.role, { href: string; label: string; description: string; icon: LucideIcon }[]> = {
    SUPER_ADMIN: [
      { href: "/projects/new", label: "Create project", description: "Order intake and BOM check", icon: Plus },
      { href: "/users", label: "Manage users", description: "Roles and access", icon: Users },
      { href: "/settings", label: "Time Counter", description: "Alert thresholds", icon: Settings },
      { href: "/audit", label: "Audit trail", description: "Trace all changes", icon: ShieldAlert },
    ],
    ADMIN: [
      { href: "/projects/new", label: "Create project", description: "Order intake and BOM check", icon: Plus },
      { href: "/purchases?status=PENDING", label: "Approve purchases", description: "Review pending requests", icon: ShoppingCart },
      { href: "/projects?status=IN_PRODUCTION", label: "Production queue", description: "Move projects forward", icon: Wrench },
      { href: "/projects?status=IN_TESTING", label: "Testing queue", description: "QA and sign-off", icon: ClipboardList },
    ],
    USER: [
      { href: "/projects?assigned=1", label: "My projects", description: "Log progress and updates", icon: FolderKanban },
      { href: "/purchases", label: "My requests", description: "Track purchase requests", icon: ShoppingCart },
      { href: "/alerts", label: "My alerts", description: "Deadline notifications", icon: BellRing },
      { href: "/inventory", label: "Inventory", description: "Check availability", icon: Boxes },
    ],
  };

  return (
    <div className="animate-rise-in">
      <PageHeader
        eyebrow={roleCopy.eyebrow}
        title={roleCopy.title}
        description={roleCopy.description}
        actions={
          user.role === "USER" ? (
            <Link href="/projects?assigned=1" className={buttonClass("primary")}>
              View my projects
              <ArrowRight className="h-4 w-4" />
            </Link>
          ) : (
            <Link href="/projects/new" className={buttonClass("primary")}>
              <Plus className="h-4 w-4" />
              New project
            </Link>
          )
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {roleStats[user.role].map((stat) => (
          <StatCard key={stat.label} stat={stat} />
        ))}
      </div>

      <div className="mt-6 grid gap-6 xl:grid-cols-[1.45fr_1fr]">
        <Card>
          <CardHeader
            title="Recent projects"
            description="Latest project activity across the portfolio"
            action={
              <Link
                href="/projects"
                className="inline-flex items-center gap-1 text-xs font-semibold text-[#0f5c73] hover:underline"
              >
                View all
                <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            }
          />
          {recent_projects.length === 0 ? (
            <EmptyState
              icon={<FolderKanban className="h-5 w-5" />}
              title="No projects yet"
              description={
                user.role === "USER"
                  ? "Projects you are assigned to will appear here."
                  : "Create the first project to start the order-intake workflow."
              }
              action={
                user.role !== "USER" ? (
                  <Link href="/projects/new" className={buttonClass("primary", "sm")}>
                    <Plus className="h-3.5 w-3.5" />
                    Create project
                  </Link>
                ) : undefined
              }
            />
          ) : (
            <div className="divide-y divide-slate-100">
              {recent_projects.map((project) => (
                <Link
                  key={project.id}
                  href={`/projects/${project.id}`}
                  className="group flex flex-wrap items-center gap-3 px-5 py-3.5 transition hover:bg-slate-50"
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="truncate text-sm font-semibold text-slate-900 group-hover:text-[#0f5c73]">
                        {project.name}
                      </p>
                      <ProjectStatusBadge status={project.status} />
                    </div>
                    <p className="mt-1 text-[11px] text-slate-500">
                      {project.members.length} assigned ·{" "}
                      {project.end_date ? `Due ${formatDate(project.end_date)}` : "No deadline"}
                    </p>
                  </div>
                  <div className="w-28">
                    <div className="mb-1 flex items-center justify-between text-[10px] text-slate-500">
                      <span>{project.progress_percent}%</span>
                      <span>{project.shortage_count ? "Shortage" : "Ready"}</span>
                    </div>
                    <ProgressBar value={project.progress_percent} />
                  </div>
                  <ArrowRight className="h-4 w-4 text-slate-300 group-hover:text-[#0f5c73]" />
                </Link>
              ))}
            </div>
          )}
        </Card>

        <div className="space-y-6">
          <Card>
            <CardHeader
              title="Recent alerts"
              description="Time Counter notifications for you"
              action={
                <Link
                  href="/alerts"
                  className="text-xs font-semibold text-[#0f5c73] hover:underline"
                >
                  View all
                </Link>
              }
            />
            {recent_alerts.length === 0 ? (
              <EmptyState
                icon={<BellRing className="h-5 w-5" />}
                title="No alerts"
                description="Your Time Counter notifications will appear here."
              />
            ) : (
              <div className="divide-y divide-slate-100">
                {recent_alerts.map((alert) => (
                  <Link
                    key={alert.id}
                    href={`/projects/${alert.project_id}`}
                    className={cn(
                      "block px-5 py-3 transition hover:bg-slate-50",
                      !alert.is_read && "bg-teal-50/40",
                    )}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <AlertTypeBadge type={alert.type} />
                      <span className="text-[10px] text-slate-400">
                        {formatDateTime(alert.created_at)}
                      </span>
                    </div>
                    <p className="mt-1.5 line-clamp-2 text-xs leading-5 text-slate-600">
                      {alert.message}
                    </p>
                  </Link>
                ))}
              </div>
            )}
          </Card>

          <Card>
            <CardHeader title="Quick actions" description={`Signed in as ${ROLE_LABELS[user.role]}`} />
            <div className="grid gap-2 p-4 sm:grid-cols-2">
              {quickLinks[user.role].map((link) => {
                const Icon = link.icon;
                return (
                  <Link
                    key={`${link.href}-${link.label}`}
                    href={link.href}
                    className="rounded-lg border border-slate-200 p-3 transition hover:border-teal-300 hover:bg-teal-50/40"
                  >
                    <Icon className="h-4 w-4 text-[#0f5c73]" />
                    <p className="mt-2 text-xs font-semibold text-slate-900">
                      {link.label}
                    </p>
                    <p className="mt-0.5 text-[10px] leading-4 text-slate-500">
                      {link.description}
                    </p>
                  </Link>
                );
              })}
            </div>
          </Card>
        </div>
      </div>

      <Card className="mt-6">
        <CardHeader
          title="Project pipeline"
          description="Snapshot of projects by current workflow stage"
        />
        <div className="grid gap-3 p-4 sm:grid-cols-2 lg:grid-cols-5">
          {(
            [
              { status: "PENDING_INVENTORY", count: stats.pending_inventory, icon: CircleDashed },
              { status: "READY_FOR_PRODUCTION", count: stats.ready_for_production, icon: PackageOpen },
              { status: "AWAITING_DELIVERY", count: stats.awaiting_delivery, icon: AlertTriangle },
              { status: "IN_PRODUCTION", count: stats.in_production, icon: Wrench },
              { status: "IN_TESTING", count: stats.in_testing, icon: ClipboardList },
            ] as const
          ).map(({ status, count, icon: Icon }) => (
            <Link
              key={status}
              href={`/projects?status=${status}`}
              className="flex items-center gap-3 rounded-lg border border-slate-100 bg-slate-50/60 px-3 py-3 transition hover:border-teal-200 hover:bg-teal-50/40"
            >
              <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-white text-slate-500 shadow-sm">
                <Icon className="h-4 w-4" />
              </span>
              <div>
                <p className="text-lg leading-5 font-bold text-slate-900">
                  {count}
                </p>
                <p className="text-[10px] text-slate-500">
                  {PROJECT_STATUS_LABELS[status]}
                </p>
              </div>
            </Link>
          ))}
        </div>
      </Card>
    </div>
  );
}

function StatCard({ stat }: { stat: StatDefinition }) {
  const Icon = stat.icon;
  const content: ReactNode = (
    <Card className="h-full p-4 transition hover:border-teal-300 hover:shadow-md">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-[11px] font-medium text-slate-500">{stat.label}</p>
          <p className="mt-1 text-2xl font-bold tracking-tight text-slate-900">
            {stat.value}
          </p>
          {stat.hint ? <p className="mt-0.5 text-[10px] text-slate-400">{stat.hint}</p> : null}
        </div>
        <span className={cn("flex h-9 w-9 items-center justify-center rounded-lg", stat.tone)}>
          <Icon className="h-4 w-4" />
        </span>
      </div>
    </Card>
  );

  return stat.href ? <Link href={stat.href}>{content}</Link> : content;
}
