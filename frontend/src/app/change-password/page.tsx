"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import {
  ArrowLeft,
  CheckCircle2,
  Eye,
  EyeOff,
  KeyRound,
  ShieldAlert,
} from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { AuthGate } from "@/components/auth-gate";
import { Button, Field, Input } from "@/components/ui";
import { errorMessage } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { buttonClass, ROLE_LABELS } from "@/lib/utils";

const passwordSchema = z
  .object({
    current_password: z.string().min(1, "Enter your current password"),
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
  })
  .refine((values) => values.current_password !== values.new_password, {
    path: ["new_password"],
    message: "Choose a password different from your current one",
  });

type PasswordValues = z.infer<typeof passwordSchema>;

export default function ChangePasswordPage() {
  return (
    <AuthGate requirePasswordChanged={false}>
      <ChangePasswordContent />
    </AuthGate>
  );
}

function ChangePasswordContent() {
  const { user, changePassword } = useAuth();
  const router = useRouter();
  const [showCurrent, setShowCurrent] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  const {
    register,
    control,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<PasswordValues>({
    resolver: zodResolver(passwordSchema),
    defaultValues: {
      current_password: "",
      new_password: "",
      confirm_password: "",
    },
  });

  const newPassword = useWatch({ control, name: "new_password" }) ?? "";
  const checks = [
    { label: "At least 8 characters", valid: newPassword.length >= 8 },
    {
      label: "Uppercase and lowercase letters",
      valid: /[A-Z]/.test(newPassword) && /[a-z]/.test(newPassword),
    },
    { label: "At least one number", valid: /\d/.test(newPassword) },
    {
      label: "At least one special character",
      valid: /[^A-Za-z0-9]/.test(newPassword),
    },
  ];

  async function onSubmit(values: PasswordValues) {
    try {
      await changePassword({
        current_password: values.current_password,
        new_password: values.new_password,
      });
      toast.success("Password updated. Welcome to JES MIS.");
      router.replace("/dashboard");
    } catch (error) {
      toast.error(errorMessage(error, "Unable to update your password."));
    }
  }

  const forced = Boolean(user?.must_change_password);

  return (
    <div className="flex min-h-screen flex-col bg-slate-100">
      <div className="flex flex-1 items-center justify-center px-4 py-10 sm:px-6">
        <div className="grid w-full max-w-4xl overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl shadow-slate-300/40 lg:grid-cols-[0.85fr_1.15fr]">
          <aside className="relative hidden flex-col justify-between overflow-hidden bg-[#082f3d] p-8 text-white lg:flex">
            <div
              className="pointer-events-none absolute inset-0 opacity-40"
              style={{
                backgroundImage:
                  "radial-gradient(circle at 20% 20%, rgba(45,212,191,0.3), transparent 38%), radial-gradient(circle at 80% 80%, rgba(14,116,144,0.45), transparent 42%)",
              }}
            />
            <div className="relative">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-white p-2">
                <Image
                  src="/jes-logo.png"
                  alt="JES Electronics Systems logo"
                  width={40}
                  height={40}
                  priority
                />
              </div>
              <p className="mt-4 text-lg font-bold">JES Electronics Systems</p>
              <p className="text-[10px] tracking-[0.2em] text-teal-200/80 uppercase">
                Pvt Ltd · MIS
              </p>
            </div>

            <div className="relative">
              <KeyRound className="h-7 w-7 text-teal-300" />
              <h2 className="mt-3 text-2xl leading-tight font-bold">
                Keep your account secure.
              </h2>
              <p className="mt-2 text-sm leading-6 text-slate-300">
                Passwords are stored using bcrypt hashing. Choose a unique
                password that you do not use for personal accounts.
              </p>
            </div>

            <p className="relative text-[11px] text-slate-500">
              Session: {user?.email}
            </p>
          </aside>

          <section className="p-6 sm:p-9">
            <div className="flex items-center justify-between gap-3">
              <div className="lg:hidden">
                <Image
                  src="/jes-logo.png"
                  alt="JES Electronics Systems logo"
                  width={40}
                  height={40}
                  priority
                />
              </div>
              {!forced ? (
                <Link
                  href="/dashboard"
                  className={buttonClass("ghost", "sm", "ml-auto")}
                >
                  <ArrowLeft className="h-3.5 w-3.5" />
                  Back
                </Link>
              ) : null}
            </div>

            <div className="mt-3">
              <p className="text-xs font-semibold tracking-[0.16em] text-[#0f5c73] uppercase">
                Account security
              </p>
              <h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-900">
                {forced ? "Set a new password" : "Change your password"}
              </h1>
              <p className="mt-1 text-sm text-slate-500">
                {forced
                  ? "Your temporary password must be changed before you can use the MIS."
                  : "Enter your current password, then choose a new one."}
              </p>
            </div>

            {forced ? (
              <div className="mt-5 flex gap-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0" />
                <p>
                  Signed in as <strong>{user?.name}</strong> (
                  {user ? ROLE_LABELS[user.role] : ""}). This is a one-time
                  password change.
                </p>
              </div>
            ) : null}

            <form
              className="mt-6 space-y-4"
              onSubmit={handleSubmit(onSubmit)}
              noValidate
            >
              <Field
                label="Current password"
                htmlFor="current_password"
                error={errors.current_password?.message}
              >
                <div className="relative">
                  <Input
                    id="current_password"
                    type={showCurrent ? "text" : "password"}
                    autoComplete="current-password"
                    className="pr-10"
                    {...register("current_password")}
                  />
                  <PasswordToggle
                    visible={showCurrent}
                    onToggle={() => setShowCurrent((value) => !value)}
                  />
                </div>
              </Field>

              <Field
                label="New password"
                htmlFor="new_password"
                error={errors.new_password?.message}
              >
                <div className="relative">
                  <Input
                    id="new_password"
                    type={showNew ? "text" : "password"}
                    autoComplete="new-password"
                    className="pr-10"
                    {...register("new_password")}
                  />
                  <PasswordToggle
                    visible={showNew}
                    onToggle={() => setShowNew((value) => !value)}
                  />
                </div>
              </Field>

              <div className="grid gap-2 rounded-lg bg-slate-50 p-3 sm:grid-cols-2">
                {checks.map((check) => (
                  <div
                    key={check.label}
                    className={
                      check.valid
                        ? "flex items-center gap-1.5 text-[11px] font-medium text-emerald-700"
                        : "flex items-center gap-1.5 text-[11px] text-slate-500"
                    }
                  >
                    <CheckCircle2
                      className={
                        check.valid
                          ? "h-3.5 w-3.5 text-emerald-600"
                          : "h-3.5 w-3.5 text-slate-300"
                      }
                    />
                    {check.label}
                  </div>
                ))}
              </div>

              <Field
                label="Confirm new password"
                htmlFor="confirm_password"
                error={errors.confirm_password?.message}
              >
                <div className="relative">
                  <Input
                    id="confirm_password"
                    type={showConfirm ? "text" : "password"}
                    autoComplete="new-password"
                    className="pr-10"
                    {...register("confirm_password")}
                  />
                  <PasswordToggle
                    visible={showConfirm}
                    onToggle={() => setShowConfirm((value) => !value)}
                  />
                </div>
              </Field>

              <Button
                type="submit"
                className="w-full"
                size="lg"
                loading={isSubmitting}
              >
                Update password
              </Button>
            </form>
          </section>
        </div>
      </div>
      <footer className="border-t border-slate-200 bg-white px-4 py-3 text-center text-[11px] text-slate-500">
        Made and managed by JES Electronics Systems Pvt Ltd
      </footer>
    </div>
  );
}

function PasswordToggle({
  visible,
  onToggle,
}: {
  visible: boolean;
  onToggle: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onToggle}
      className="absolute top-0 right-0 flex h-10 w-10 items-center justify-center text-slate-400 transition hover:text-slate-700"
      aria-label={visible ? "Hide password" : "Show password"}
    >
      {visible ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
    </button>
  );
}
