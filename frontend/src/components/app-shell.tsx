"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Bell,
  Boxes,
  CheckCheck,
  ChevronDown,
  FolderKanban,
  LayoutDashboard,
  LogOut,
  Menu,
  Plus,
  ScrollText,
  Settings,
  ShoppingCart,
  Users,
  X,
  type LucideIcon,
} from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { toast } from "sonner";

import { AppShellSkeleton } from "@/components/app-shell-skeleton";
import { AuthGate } from "@/components/auth-gate";
import { Avatar, Badge } from "@/components/ui";
import { apiFetch, errorMessage } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Alert, MessageResponse, Page, UserRole } from "@/lib/types";
import {
  ALERT_TYPE_LABELS,
  buttonClass,
  cn,
  formatDateTime,
  ROLE_LABELS,
} from "@/lib/utils";

interface NavigationItem {
  href: string;
  label: string;
  icon: LucideIcon;
  roles?: UserRole[];
}

const NAVIGATION: NavigationItem[] = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/projects", label: "Projects", icon: FolderKanban },
  { href: "/inventory", label: "Inventory", icon: Boxes },
  { href: "/purchases", label: "Purchase requests", icon: ShoppingCart },
  { href: "/alerts", label: "Alerts", icon: Bell },
  { href: "/users", label: "Users", icon: Users, roles: ["SUPER_ADMIN"] },
  {
    href: "/settings",
    label: "Time Counter",
    icon: Settings,
    roles: ["SUPER_ADMIN"],
  },
  {
    href: "/audit",
    label: "Audit trail",
    icon: ScrollText,
    roles: ["SUPER_ADMIN"],
  },
];

const PAGE_TITLES: Record<string, string> = {
  "/dashboard": "Dashboard",
  "/projects": "Projects",
  "/projects/new": "New project",
  "/inventory": "Inventory",
  "/purchases": "Purchase requests",
  "/alerts": "Alerts",
  "/users": "Users",
  "/settings": "Time Counter",
  "/audit": "Audit trail",
};

function isActive(pathname: string, href: string) {
  if (href === "/dashboard") return pathname === href;
  return pathname === href || pathname.startsWith(`${href}/`);
}

function pageTitle(pathname: string) {
  if (PAGE_TITLES[pathname]) return PAGE_TITLES[pathname];
  if (pathname.startsWith("/projects/")) return "Project details";
  return "MIS";
}

export function AppShell({ children }: { children: ReactNode }) {
  const { user, isLoading } = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [mobileOpen, setMobileOpen] = useState(false);

  if (isLoading || !user) {
    return (
      <AuthGate>
        <AppShellSkeleton />
      </AuthGate>
    );
  }

  const navigation = NAVIGATION.filter(
    (item) => !item.roles || item.roles.includes(user.role),
  );
  const canCreateProjects =
    user.role === "ADMIN" || user.role === "SUPER_ADMIN";

  async function handleLogout() {
    try {
      await apiFetch<MessageResponse>("/auth/logout", { method: "POST" });
      queryClient.clear();
      router.replace("/login");
      toast.success("Signed out");
    } catch (error) {
      toast.error(errorMessage(error, "Unable to sign out."));
    }
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 flex-col border-r border-slate-200 bg-[#082f3d] text-slate-200 lg:flex">
        <SidebarContent
          navigation={navigation}
          pathname={pathname}
          canCreateProjects={canCreateProjects}
          onLogout={handleLogout}
        />
      </aside>

      {mobileOpen ? (
        <div className="fixed inset-0 z-40 lg:hidden">
          <button
            aria-label="Close navigation"
            className="absolute inset-0 bg-slate-950/60"
            onClick={() => setMobileOpen(false)}
          />
          <aside className="relative flex h-full w-72 max-w-[85vw] flex-col bg-[#082f3d] text-slate-200 shadow-2xl">
            <button
              className="absolute top-4 right-4 rounded-lg p-2 text-slate-400 hover:bg-white/10 hover:text-white"
              onClick={() => setMobileOpen(false)}
              aria-label="Close menu"
            >
              <X className="h-5 w-5" />
            </button>
            <SidebarContent
              navigation={navigation}
              pathname={pathname}
              canCreateProjects={canCreateProjects}
              onLogout={handleLogout}
              onNavigate={() => setMobileOpen(false)}
            />
          </aside>
        </div>
      ) : null}

      <div className="flex min-h-screen flex-col lg:pl-64">
        <header className="sticky top-0 z-20 flex h-16 items-center justify-between gap-3 border-b border-slate-200 bg-white/90 px-4 backdrop-blur sm:px-6 lg:px-8">
          <div className="flex min-w-0 items-center gap-3">
            <button
              className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 lg:hidden"
              onClick={() => setMobileOpen(true)}
              aria-label="Open menu"
            >
              <Menu className="h-5 w-5" />
            </button>
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-slate-900">
                {pageTitle(pathname)}
              </p>
              <p className="hidden text-[11px] text-slate-500 sm:block">
                R&D and Production Management Information System
              </p>
            </div>
          </div>
          <div className="flex items-center gap-1.5 sm:gap-2">
            {canCreateProjects ? (
              <Link
                href="/projects/new"
                className={buttonClass(
                  "outline",
                  "sm",
                  "hidden sm:inline-flex",
                )}
              >
                <Plus className="h-3.5 w-3.5" />
                New project
              </Link>
            ) : null}
            <NotificationBell />
            <div className="ml-1 hidden items-center gap-2 border-l border-slate-200 pl-3 sm:flex">
              <Avatar name={user.name} />
              <div className="max-w-36">
                <p className="truncate text-xs font-semibold text-slate-900">
                  {user.name}
                </p>
                <p className="truncate text-[10px] text-slate-500">
                  {ROLE_LABELS[user.role]}
                </p>
              </div>
            </div>
          </div>
        </header>

        <main className="mx-auto w-full max-w-[1500px] flex-1 px-4 py-6 sm:px-6 lg:px-8">
          {children}
        </main>

        <footer className="border-t border-slate-200 bg-white px-4 py-4 text-center text-xs text-slate-500 sm:px-6 lg:px-8">
          Made and managed by JES Electronics Systems Pvt Ltd
        </footer>
      </div>
    </div>
  );
}

function SidebarContent({
  navigation,
  pathname,
  canCreateProjects,
  onLogout,
  onNavigate,
}: {
  navigation: NavigationItem[];
  pathname: string;
  canCreateProjects: boolean;
  onLogout: () => void;
  onNavigate?: () => void;
}) {
  const { user } = useAuth();
  return (
    <>
      <div className="flex h-20 items-center gap-3 border-b border-white/10 px-5">
        <div className="flex h-10 w-10 items-center justify-center overflow-hidden rounded-xl bg-white p-1.5">
          <Image
            src="/jes-logo.png"
            alt="JES Electronics Systems logo"
            width={36}
            height={36}
            priority
          />
        </div>
        <div className="min-w-0">
          <p className="truncate text-sm font-bold tracking-wide text-white">
            JES Electronics
          </p>
          <p className="text-[10px] tracking-[0.14em] text-teal-200/80 uppercase">
            Systems Pvt Ltd · MIS
          </p>
        </div>
      </div>

      <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
        {navigation.map((item) => {
          const Icon = item.icon;
          const active = isActive(pathname, item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={onNavigate}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition",
                active
                  ? "bg-white/12 text-white shadow-inner"
                  : "text-slate-300 hover:bg-white/8 hover:text-white",
              )}
            >
              <Icon
                className={cn(
                  "h-[18px] w-[18px]",
                  active ? "text-teal-300" : "text-slate-400",
                )}
              />
              <span className="flex-1">{item.label}</span>
              {item.href === "/alerts" ? <AlertCountBadge /> : null}
            </Link>
          );
        })}

        {canCreateProjects ? (
          <div className="pt-3">
            <Link
              href="/projects/new"
              onClick={onNavigate}
              className="flex items-center justify-center gap-2 rounded-lg border border-teal-300/30 bg-teal-400/10 px-3 py-2.5 text-sm font-semibold text-teal-100 transition hover:bg-teal-400/20"
            >
              <Plus className="h-4 w-4" />
              Create project
            </Link>
          </div>
        ) : null}
      </nav>

      <div className="border-t border-white/10 p-3">
        {user ? (
          <div className="rounded-xl bg-white/6 p-3">
            <div className="flex items-center gap-2.5">
              <Avatar
                name={user.name}
                className="bg-teal-400/15 text-teal-200"
              />
              <div className="min-w-0 flex-1">
                <p className="truncate text-xs font-semibold text-white">
                  {user.name}
                </p>
                <p className="text-[10px] text-slate-400">
                  {ROLE_LABELS[user.role]}
                </p>
              </div>
              <button
                onClick={onLogout}
                title="Sign out"
                aria-label="Sign out"
                className="rounded-lg p-1.5 text-slate-400 transition hover:bg-white/10 hover:text-white"
              >
                <LogOut className="h-4 w-4" />
              </button>
            </div>
          </div>
        ) : null}
      </div>
    </>
  );
}

function AlertCountBadge() {
  const { data } = useQuery({
    queryKey: ["alerts", "unread-count"],
    queryFn: () =>
      apiFetch<{ unread: number }>("/alerts/unread-count").then(
        (data) => data.unread,
      ),
    refetchInterval: 30_000,
  });
  if (!data) return null;
  return (
    <span className="flex h-5 min-w-5 items-center justify-center rounded-full bg-red-500 px-1.5 text-[10px] font-bold text-white">
      {data > 99 ? "99+" : data}
    </span>
  );
}

function NotificationBell() {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const queryClient = useQueryClient();

  const unread = useQuery({
    queryKey: ["alerts", "unread-count"],
    queryFn: () =>
      apiFetch<{ unread: number }>("/alerts/unread-count").then(
        (data) => data.unread,
      ),
    refetchInterval: 30_000,
  });

  const recent = useQuery({
    queryKey: ["alerts", "recent"],
    queryFn: () => apiFetch<Page<Alert>>("/alerts?page=1&page_size=5"),
    enabled: open,
  });

  const markAll = useMutation({
    mutationFn: () =>
      apiFetch<MessageResponse>("/alerts/read-all", { method: "POST" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["alerts"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      toast.success("All alerts marked as read");
    },
    onError: (error) => toast.error(errorMessage(error)),
  });

  useEffect(() => {
    if (!open) return;
    const handlePointerDown = (event: PointerEvent) => {
      if (!containerRef.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("pointerdown", handlePointerDown);
    return () => document.removeEventListener("pointerdown", handlePointerDown);
  }, [open]);

  const count = unread.data ?? 0;

  return (
    <div className="relative" ref={containerRef}>
      <button
        onClick={() => setOpen((current) => !current)}
        className="relative rounded-lg p-2 text-slate-500 transition hover:bg-slate-100 hover:text-slate-900"
        aria-label={`Notifications${count ? `, ${count} unread` : ""}`}
        aria-expanded={open}
      >
        <Bell className="h-5 w-5" />
        {count > 0 ? (
          <span className="absolute top-0.5 right-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-500 px-1 text-[9px] font-bold text-white ring-2 ring-white">
            {count > 9 ? "9+" : count}
          </span>
        ) : null}
      </button>

      {open ? (
        <div className="absolute right-0 mt-2 w-[min(22rem,calc(100vw-2rem))] overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xl">
          <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
            <div>
              <p className="text-sm font-semibold text-slate-900">
                Notifications
              </p>
              <p className="text-[11px] text-slate-500">{count} unread</p>
            </div>
            <button
              className="inline-flex items-center gap-1 text-[11px] font-semibold text-[#0f5c73] hover:underline disabled:opacity-50"
              onClick={() => markAll.mutate()}
              disabled={markAll.isPending || count === 0}
            >
              <CheckCheck className="h-3.5 w-3.5" />
              Mark all read
            </button>
          </div>
          <div className="max-h-80 overflow-y-auto">
            {recent.isLoading ? (
              <p className="px-4 py-6 text-center text-xs text-slate-500">
                Loading notifications…
              </p>
            ) : recent.data?.items.length ? (
              recent.data.items.map((alert) => (
                <Link
                  key={alert.id}
                  href={`/projects/${alert.project_id}`}
                  onClick={() => setOpen(false)}
                  className={cn(
                    "block border-b border-slate-50 px-4 py-3 transition last:border-0 hover:bg-slate-50",
                    !alert.is_read && "bg-teal-50/40",
                  )}
                >
                  <div className="flex items-center justify-between gap-2">
                    <Badge
                      className={
                        alert.type === "ESCALATED"
                          ? "border-red-200 bg-red-50 text-red-700"
                          : "border-amber-200 bg-amber-50 text-amber-700"
                      }
                    >
                      {ALERT_TYPE_LABELS[alert.type]}
                    </Badge>
                    <span className="text-[10px] text-slate-400">
                      {formatDateTime(alert.created_at)}
                    </span>
                  </div>
                  <p className="mt-1.5 line-clamp-2 text-xs leading-5 text-slate-700">
                    {alert.message}
                  </p>
                </Link>
              ))
            ) : (
              <p className="px-4 py-8 text-center text-xs text-slate-500">
                You are all caught up.
              </p>
            )}
          </div>
          <Link
            href="/alerts"
            onClick={() => setOpen(false)}
            className="flex items-center justify-center gap-1 border-t border-slate-100 bg-slate-50 px-4 py-2.5 text-xs font-semibold text-[#0f5c73] hover:bg-slate-100"
          >
            View all alerts
            <ChevronDown className="h-3.5 w-3.5 -rotate-90" />
          </Link>
        </div>
      ) : null}
    </div>
  );
}
