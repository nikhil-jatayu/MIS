"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowLeft, CheckCircle2, Eye, EyeOff, KeyRound } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { MisBrand } from "@/components/mis-brand";
import { Button, Field, Input } from "@/components/ui";
import { apiFetch, errorMessage } from "@/lib/api";
import type { MessageResponse } from "@/lib/types";

const resetSchema = z
  .object({
    new_password: z
      .string()
      .min(8, "Use at least 8 characters")
      .max(128, "Use at most 128 characters")
      .regex(/[A-Z]/, "Add an uppercase letter")
      .regex(/[a-z]/, "Add a lowercase letter")
      .regex(/\d/, "Add a number")
      .regex(/[^A-Za-z0-9]/, "Add a special character"),
    confirm_password: z.string().min(1, "Confirm your new password"),
  })
  .refine((values) => values.new_password === values.confirm_password, {
    path: ["confirm_password"],
    message: "Passwords do not match",
  });

type ResetValues = z.infer<typeof resetSchema>;

export function ResetPasswordForm() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const token = searchParams.get("token") ?? "";
  const [showPassword, setShowPassword] = useState(false);
  const {
    register,
    control,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ResetValues>({
    resolver: zodResolver(resetSchema),
    defaultValues: { new_password: "", confirm_password: "" },
  });

  const newPassword = useWatch({ control, name: "new_password" }) ?? "";
  const checks = [
    { label: "At least 8 characters", valid: newPassword.length >= 8 },
    {
      label: "Uppercase and lowercase letters",
      valid: /[A-Z]/.test(newPassword) && /[a-z]/.test(newPassword),
    },
    { label: "At least one number", valid: /\d/.test(newPassword) },
    { label: "At least one special character", valid: /[^A-Za-z0-9]/.test(newPassword) },
  ];

  async function onSubmit(values: ResetValues) {
    if (!token) {
      toast.error("This reset link is missing its token. Request a new link.");
      return;
    }
    try {
      await apiFetch<MessageResponse>("/auth/reset-password", {
        method: "POST",
        body: JSON.stringify({ token, new_password: values.new_password }),
      });
      toast.success("Password updated. You can now sign in.");
      router.replace("/login");
    } catch (error) {
      toast.error(errorMessage(error, "Unable to reset your password."));
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-100 px-4 py-10">
      <div className="w-full max-w-md">
        <div className="mb-6 flex justify-center">
          <MisBrand size="lg" />
        </div>
        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-xl shadow-slate-200/60 sm:p-8">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-teal-50 text-teal-700">
            <KeyRound className="h-5 w-5" />
          </div>
          <p className="mt-5 text-xs font-semibold tracking-[0.16em] text-[#0f5c73] uppercase">
            Account recovery
          </p>
          <h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-900">
            Set a new password
          </h1>
          <p className="mt-2 text-sm leading-6 text-slate-500">
            Choose a new password for your MIS account. This reset link can only
            be used once and expires after 30 minutes.
          </p>

          {!token ? (
            <div className="mt-5 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
              The reset token is missing. Request a new password-reset link.
              <Link href="/forgot-password" className="mt-2 block font-semibold underline">
                Request another link
              </Link>
            </div>
          ) : (
            <form className="mt-6 space-y-4" onSubmit={handleSubmit(onSubmit)} noValidate>
              <Field label="New password" htmlFor="new_password" error={errors.new_password?.message}>
                <div className="relative">
                  <Input
                    id="new_password"
                    type={showPassword ? "text" : "password"}
                    autoComplete="new-password"
                    className="pr-10"
                    {...register("new_password")}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((visible) => !visible)}
                    className="absolute top-0 right-0 flex h-10 w-10 items-center justify-center text-slate-400 hover:text-slate-700"
                    aria-label={showPassword ? "Hide password" : "Show password"}
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </Field>
              <div className="grid gap-2 rounded-lg bg-slate-50 p-3 sm:grid-cols-2">
                {checks.map((check) => (
                  <div
                    key={check.label}
                    className={check.valid ? "flex items-center gap-1.5 text-[11px] font-medium text-emerald-700" : "flex items-center gap-1.5 text-[11px] text-slate-500"}
                  >
                    <CheckCircle2 className={check.valid ? "h-3.5 w-3.5 text-emerald-600" : "h-3.5 w-3.5 text-slate-300"} />
                    {check.label}
                  </div>
                ))}
              </div>
              <Field label="Confirm new password" htmlFor="confirm_password" error={errors.confirm_password?.message}>
                <Input
                  id="confirm_password"
                  type="password"
                  autoComplete="new-password"
                  {...register("confirm_password")}
                />
              </Field>
              <Button type="submit" className="w-full" size="lg" loading={isSubmitting}>
                Update password
              </Button>
            </form>
          )}
          <div className="mt-6 text-center">
            <Link
              href="/login"
              className="inline-flex items-center gap-2 text-xs font-semibold text-slate-500 hover:text-[#0f5c73]"
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              Back to sign in
            </Link>
          </div>
        </section>
        <p className="mt-5 text-center text-[11px] text-slate-400">
          MIS · Management Information System
        </p>
      </div>
    </main>
  );
}
