"use client";

import { ShieldAlert } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";

import { BrandedLoadingScreen } from "@/components/branded-loading-screen";
import { Button, Card } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import type { UserRole } from "@/lib/types";
import { buttonClass, ROLE_LABELS } from "@/lib/utils";

function safeNextPath(pathname: string) {
  return pathname.startsWith("/") && !pathname.startsWith("//")
    ? pathname
    : "/dashboard";
}

export function AuthGate({
  children,
  requirePasswordChanged = true,
}: {
  children: ReactNode;
  requirePasswordChanged?: boolean;
}) {
  const { user, isLoading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (isLoading) return;
    if (!user) {
      const next = safeNextPath(pathname);
      router.replace(`/login?next=${encodeURIComponent(next)}`);
      return;
    }
    if (requirePasswordChanged && user.must_change_password) {
      router.replace("/change-password");
    }
  }, [isLoading, user, requirePasswordChanged, router, pathname]);

  if (isLoading) {
    return (
      <BrandedLoadingScreen
        title="Verifying your session"
        description="Checking your account and preparing your MIS workspace."
      />
    );
  }
  if (!user) {
    return (
      <BrandedLoadingScreen
        title="Opening secure sign-in"
        description="Redirecting you to the MIS sign-in page."
      />
    );
  }
  if (requirePasswordChanged && user.must_change_password) {
    return (
      <BrandedLoadingScreen
        title="One more security step"
        description="Taking you to the required password update."
      />
    );
  }
  return <>{children}</>;
}

export function RequireRole({
  roles,
  children,
}: {
  roles: UserRole[];
  children: ReactNode;
}) {
  const { user } = useAuth();
  if (!user) return null;
  if (!roles.includes(user.role)) {
    return (
      <Card className="mx-auto mt-10 max-w-lg p-8 text-center">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-red-50 text-red-600">
          <ShieldAlert className="h-6 w-6" />
        </div>
        <h1 className="mt-4 text-lg font-bold text-slate-900">
          Access restricted
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          This area is available to{" "}
          {roles.map((role) => ROLE_LABELS[role]).join(" and ")} users only. Your
          current role is {ROLE_LABELS[user.role]}.
        </p>
        <Link href="/dashboard" className={buttonClass("primary", "md", "mt-5")}>
          Back to dashboard
        </Link>
      </Card>
    );
  }
  return <>{children}</>;
}

export function AccessDenied() {
  return (
    <Card className="mx-auto mt-10 max-w-lg p-8 text-center">
      <ShieldAlert className="mx-auto h-10 w-10 text-red-500" />
      <h1 className="mt-3 text-lg font-bold text-slate-900">
        You do not have access to this page
      </h1>
      <p className="mt-1 text-sm text-slate-500">
        Contact a Super Admin if you believe this is a mistake.
      </p>
      <Button className="mt-5" onClick={() => window.history.back()}>
        Go back
      </Button>
    </Card>
  );
}
