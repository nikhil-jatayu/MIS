import { clsx, type ClassValue } from "clsx";
import { format, formatDistanceToNow, isValid, parseISO } from "date-fns";
import { twMerge } from "tailwind-merge";

import type {
  AlertType,
  Priority,
  ProjectMemberRole,
  ProjectStatus,
  ProjectType,
  PurchaseRequestStatus,
  TestResult,
  UserRole,
} from "@/lib/types";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export type ButtonVariant =
  | "primary"
  | "secondary"
  | "outline"
  | "ghost"
  | "danger"
  | "success";
export type ButtonSize = "sm" | "md" | "lg" | "icon";

const buttonVariants: Record<ButtonVariant, string> = {
  primary:
    "bg-[#0f5c73] text-white shadow-sm hover:bg-[#0b4b5e] focus-visible:outline-[#0f5c73]",
  secondary:
    "bg-slate-900 text-white shadow-sm hover:bg-slate-800 focus-visible:outline-slate-900",
  outline:
    "border border-slate-300 bg-white text-slate-700 shadow-sm hover:border-slate-400 hover:bg-slate-50 focus-visible:outline-slate-500",
  ghost:
    "text-slate-600 hover:bg-slate-100 hover:text-slate-900 focus-visible:outline-slate-400",
  danger:
    "bg-red-600 text-white shadow-sm hover:bg-red-700 focus-visible:outline-red-600",
  success:
    "bg-emerald-600 text-white shadow-sm hover:bg-emerald-700 focus-visible:outline-emerald-600",
};

const buttonSizes: Record<ButtonSize, string> = {
  sm: "h-8 px-3 text-xs",
  md: "h-10 px-4 text-sm",
  lg: "h-11 px-5 text-sm",
  icon: "h-9 w-9",
};

export function buttonClass(
  variant: ButtonVariant = "primary",
  size: ButtonSize = "md",
  className?: string,
) {
  return cn(
    "inline-flex shrink-0 items-center justify-center gap-2 rounded-lg font-semibold transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 disabled:pointer-events-none disabled:opacity-50",
    buttonVariants[variant],
    buttonSizes[size],
    className,
  );
}

function toDate(value: string | null | undefined): Date | null {
  if (!value) return null;
  const date = /^\d{4}-\d{2}-\d{2}$/.test(value)
    ? parseISO(value)
    : new Date(value);
  return isValid(date) ? date : null;
}

export function formatDate(value: string | null | undefined, fallback = "—") {
  const date = toDate(value);
  return date ? format(date, "dd MMM yyyy") : fallback;
}

export function formatDateTime(
  value: string | null | undefined,
  fallback = "—",
) {
  const date = toDate(value);
  return date ? format(date, "dd MMM yyyy, HH:mm") : fallback;
}

export function fromNow(value: string | null | undefined, fallback = "—") {
  const date = toDate(value);
  return date ? formatDistanceToNow(date, { addSuffix: true }) : fallback;
}

export function isPastDate(value: string | null | undefined) {
  const date = toDate(value);
  if (!date) return false;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return date.getTime() < today.getTime();
}

export function initials(name: string) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");
}

export function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function pluralise(count: number, singular: string, plural?: string) {
  return `${count} ${count === 1 ? singular : (plural ?? `${singular}s`)}`;
}

export function buildQuery(
  values: Record<string, string | number | boolean | null | undefined>,
) {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(values)) {
    if (value === undefined || value === null || value === "") continue;
    params.set(key, String(value));
  }
  const query = params.toString();
  return query ? `?${query}` : "";
}

export const ROLE_LABELS: Record<UserRole, string> = {
  SUPER_ADMIN: "Super Admin",
  ADMIN: "Admin",
  USER: "User",
};

export const PROJECT_TYPE_LABELS: Record<ProjectType, string> = {
  RND: "R&D",
  PRODUCTION: "Production",
};

export const PROJECT_STATUS_LABELS: Record<ProjectStatus, string> = {
  PENDING_INVENTORY: "Pending inventory",
  READY_FOR_PRODUCTION: "Ready for production",
  AWAITING_DELIVERY: "Awaiting delivery",
  IN_PRODUCTION: "In production",
  IN_TESTING: "In testing",
  COMPLETED: "Completed",
};

export const PRIORITY_LABELS: Record<Priority, string> = {
  LOW: "Low",
  MEDIUM: "Medium",
  HIGH: "High",
  CRITICAL: "Critical",
};

export const MEMBER_ROLE_LABELS: Record<ProjectMemberRole, string> = {
  DEVELOPER: "Developer",
  PRODUCER: "Producer",
  TESTER: "Tester",
};

export const PURCHASE_STATUS_LABELS: Record<PurchaseRequestStatus, string> = {
  PENDING: "Pending approval",
  APPROVED: "Approved",
  REJECTED: "Rejected",
  ORDERED: "Ordered",
  DELIVERED: "Delivered",
};

export const TEST_RESULT_LABELS: Record<TestResult, string> = {
  PASS: "Passed",
  FAIL: "Failed",
};

export const ALERT_TYPE_LABELS: Record<AlertType, string> = {
  STANDARD: "Standard",
  ESCALATED: "Escalated",
};

export const PROJECT_STATUS_CLASSES: Record<ProjectStatus, string> = {
  PENDING_INVENTORY: "border-amber-200 bg-amber-50 text-amber-800",
  READY_FOR_PRODUCTION: "border-sky-200 bg-sky-50 text-sky-800",
  AWAITING_DELIVERY: "border-orange-200 bg-orange-50 text-orange-800",
  IN_PRODUCTION: "border-indigo-200 bg-indigo-50 text-indigo-800",
  IN_TESTING: "border-violet-200 bg-violet-50 text-violet-800",
  COMPLETED: "border-emerald-200 bg-emerald-50 text-emerald-800",
};

export const PRIORITY_CLASSES: Record<Priority, string> = {
  LOW: "border-slate-200 bg-slate-50 text-slate-700",
  MEDIUM: "border-blue-200 bg-blue-50 text-blue-700",
  HIGH: "border-orange-200 bg-orange-50 text-orange-700",
  CRITICAL: "border-red-200 bg-red-50 text-red-700",
};

export const PURCHASE_STATUS_CLASSES: Record<PurchaseRequestStatus, string> = {
  PENDING: "border-amber-200 bg-amber-50 text-amber-800",
  APPROVED: "border-sky-200 bg-sky-50 text-sky-800",
  REJECTED: "border-red-200 bg-red-50 text-red-700",
  ORDERED: "border-indigo-200 bg-indigo-50 text-indigo-800",
  DELIVERED: "border-emerald-200 bg-emerald-50 text-emerald-800",
};

export const PROJECT_STATUS_ORDER: ProjectStatus[] = [
  "PENDING_INVENTORY",
  "READY_FOR_PRODUCTION",
  "IN_PRODUCTION",
  "IN_TESTING",
  "COMPLETED",
];
