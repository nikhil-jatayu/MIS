import { Badge } from "@/components/ui";
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
import {
  ALERT_TYPE_LABELS,
  MEMBER_ROLE_LABELS,
  PRIORITY_CLASSES,
  PRIORITY_LABELS,
  PROJECT_STATUS_CLASSES,
  PROJECT_STATUS_LABELS,
  PROJECT_TYPE_LABELS,
  PURCHASE_STATUS_CLASSES,
  PURCHASE_STATUS_LABELS,
  ROLE_LABELS,
  TEST_RESULT_LABELS,
} from "@/lib/utils";

export function ProjectStatusBadge({ status }: { status: ProjectStatus }) {
  return <Badge className={PROJECT_STATUS_CLASSES[status]}>{PROJECT_STATUS_LABELS[status]}</Badge>;
}

export function PriorityBadge({ priority }: { priority: Priority }) {
  return <Badge className={PRIORITY_CLASSES[priority]}>{PRIORITY_LABELS[priority]}</Badge>;
}

export function ProjectTypeBadge({ type }: { type: ProjectType }) {
  return (
    <Badge className="border-slate-200 bg-slate-50 text-slate-700">
      {PROJECT_TYPE_LABELS[type]}
    </Badge>
  );
}

export function PurchaseStatusBadge({ status }: { status: PurchaseRequestStatus }) {
  return (
    <Badge className={PURCHASE_STATUS_CLASSES[status]}>
      {PURCHASE_STATUS_LABELS[status]}
    </Badge>
  );
}

export function AlertTypeBadge({ type }: { type: AlertType }) {
  return (
    <Badge
      className={
        type === "ESCALATED"
          ? "border-red-200 bg-red-50 text-red-700"
          : "border-amber-200 bg-amber-50 text-amber-700"
      }
    >
      {ALERT_TYPE_LABELS[type]}
    </Badge>
  );
}

export function MemberRoleBadge({ role }: { role: ProjectMemberRole }) {
  return (
    <Badge className="border-slate-200 bg-slate-50 text-slate-600">
      {MEMBER_ROLE_LABELS[role]}
    </Badge>
  );
}

export function TestResultBadge({ result }: { result: TestResult }) {
  return (
    <Badge
      className={
        result === "PASS"
          ? "border-emerald-200 bg-emerald-50 text-emerald-700"
          : "border-red-200 bg-red-50 text-red-700"
      }
    >
      {TEST_RESULT_LABELS[result]}
    </Badge>
  );
}

export function RoleBadge({ role }: { role: UserRole }) {
  const classes: Record<UserRole, string> = {
    SUPER_ADMIN: "border-violet-200 bg-violet-50 text-violet-700",
    ADMIN: "border-sky-200 bg-sky-50 text-sky-700",
    USER: "border-slate-200 bg-slate-50 text-slate-600",
  };
  return <Badge className={classes[role]}>{ROLE_LABELS[role]}</Badge>;
}
