import { Suspense } from "react";

import { AppShellSkeleton } from "@/components/app-shell-skeleton";

import { LoginForm } from "./login-form";

export const metadata = {
  title: "Sign in",
};

export default function LoginPage() {
  return (
    <Suspense
      fallback={<AppShellSkeleton />}
    >
      <LoginForm />
    </Suspense>
  );
}
