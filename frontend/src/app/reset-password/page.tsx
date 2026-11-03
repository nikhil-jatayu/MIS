import { Suspense } from "react";

import { ResetPasswordForm } from "./reset-password-form";

export default function ResetPasswordPage() {
  return (
    <Suspense
      fallback={
        <main className="flex min-h-screen items-center justify-center bg-slate-100 px-4">
          <p className="text-sm text-slate-500">Loading password reset…</p>
        </main>
      }
    >
      <ResetPasswordForm />
    </Suspense>
  );
}
