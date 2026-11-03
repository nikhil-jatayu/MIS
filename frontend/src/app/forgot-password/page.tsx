"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowLeft, Mail } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { MisBrand, OrganizationCredit } from "@/components/mis-brand";
import { Button, Field, Input } from "@/components/ui";
import { apiFetch, errorMessage } from "@/lib/api";
import type { MessageResponse } from "@/lib/types";

const requestSchema = z.object({
  email: z.email("Enter a valid email address"),
});

type RequestValues = z.infer<typeof requestSchema>;

export default function ForgotPasswordPage() {
  const [submitted, setSubmitted] = useState(false);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RequestValues>({
    resolver: zodResolver(requestSchema),
    defaultValues: { email: "" },
  });

  async function onSubmit(values: RequestValues) {
    try {
      await apiFetch<MessageResponse>("/auth/forgot-password", {
        method: "POST",
        body: JSON.stringify({ email: values.email.trim() }),
      });
      setSubmitted(true);
    } catch (error) {
      toast.error(errorMessage(error, "Unable to submit the reset request."));
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-100 px-4 py-10">
      <div className="w-full max-w-md">
        <div className="mb-6 flex justify-center">
          <MisBrand size="lg" />
        </div>
        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-xl shadow-slate-200/60 sm:p-8">
          {submitted ? (
            <div className="text-center">
              <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-teal-50 text-teal-700">
                <Mail className="h-5 w-5" />
              </div>
              <h1 className="mt-4 text-xl font-bold text-slate-900">
                Check your email
              </h1>
              <p className="mt-2 text-sm leading-6 text-slate-600">
                If an account with that email address exists, password-reset
                instructions will be sent. Check your inbox and spam folder.
              </p>
              <Link
                href="/login"
                className="mt-6 inline-flex items-center gap-2 text-sm font-semibold text-[#0f5c73] hover:underline"
              >
                <ArrowLeft className="h-4 w-4" />
                Back to sign in
              </Link>
            </div>
          ) : (
            <>
              <p className="text-xs font-semibold tracking-[0.16em] text-[#0f5c73] uppercase">
                Account recovery
              </p>
              <h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-900">
                Forgot your password?
              </h1>
              <p className="mt-2 text-sm leading-6 text-slate-500">
                Enter the email address registered with your MIS account. We’ll
                send a one-time password-reset link when an active account is
                associated with that address.
              </p>
              <form className="mt-6 space-y-4" onSubmit={handleSubmit(onSubmit)} noValidate>
                <Field label="Email Address" htmlFor="email" error={errors.email?.message}>
                  <div className="relative">
                    <Mail className="pointer-events-none absolute top-3 left-3 h-4 w-4 text-slate-400" />
                    <Input
                      id="email"
                      type="email"
                      autoComplete="email"
                      placeholder="name@company.com"
                      className="pl-9"
                      {...register("email")}
                    />
                  </div>
                </Field>
                <Button type="submit" className="w-full" size="lg" loading={isSubmitting}>
                  Send reset link
                </Button>
              </form>
              <div className="mt-6 text-center">
                <Link
                  href="/login"
                  className="inline-flex items-center gap-2 text-xs font-semibold text-slate-500 hover:text-[#0f5c73]"
                >
                  <ArrowLeft className="h-3.5 w-3.5" />
                  Back to sign in
                </Link>
              </div>
            </>
          )}
        </section>
        <div className="mt-5 text-center">
          <p className="text-[11px] text-slate-400">
            MIS · Management Information System
          </p>
          <OrganizationCredit className="mt-1" />
        </div>
      </div>
    </main>
  );
}
