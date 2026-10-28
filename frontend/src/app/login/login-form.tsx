"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import {
  ArrowRight,
  Eye,
  EyeOff,
  LockKeyhole,
  Mail,
  ShieldCheck,
} from "lucide-react";
import Image from "next/image";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { Button, Field, Input } from "@/components/ui";
import { errorMessage } from "@/lib/api";
import { useAuth } from "@/lib/auth";

const loginSchema = z.object({
  email: z.email("Enter a valid email address"),
  password: z.string().min(1, "Enter your password").max(128),
});

type LoginValues = z.infer<typeof loginSchema>;

function safeNext(value: string | null) {
  if (!value || !value.startsWith("/") || value.startsWith("//")) {
    return "/dashboard";
  }
  return value;
}

export function LoginForm() {
  const { login, user, isLoading } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [showPassword, setShowPassword] = useState(false);
  const nextPath = safeNext(searchParams.get("next"));

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "" },
  });

  useEffect(() => {
    if (isLoading || !user) return;
    router.replace(user.must_change_password ? "/change-password" : nextPath);
  }, [isLoading, user, router, nextPath]);

  async function onSubmit(values: LoginValues) {
    try {
      const signedIn = await login({
        email: values.email.trim(),
        password: values.password,
      });
      toast.success(`Welcome, ${signedIn.name}`);
      router.replace(
        signedIn.must_change_password ? "/change-password" : nextPath,
      );
    } catch (error) {
      toast.error(errorMessage(error, "Unable to sign in."));
    }
  }

  return (
    <div className="flex min-h-screen flex-col bg-slate-950">
      <div className="grid flex-1 lg:grid-cols-[1.1fr_1fr]">
        <section className="relative hidden overflow-hidden bg-[#082f3d] p-12 text-white lg:flex lg:flex-col lg:justify-between">
          <div
            className="pointer-events-none absolute inset-0 opacity-40"
            style={{
              backgroundImage:
                "radial-gradient(circle at 18% 18%, rgba(45,212,191,0.28), transparent 34%), radial-gradient(circle at 85% 70%, rgba(14,116,144,0.45), transparent 40%), linear-gradient(135deg, rgba(255,255,255,0.04) 1px, transparent 1px)",
              backgroundSize: "auto, auto, 28px 28px",
            }}
          />
          <div className="relative">
            <div className="flex items-center gap-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-white p-2 shadow-lg">
                <Image
                  src="/jes-logo.png"
                  alt="JES Electronics Systems logo"
                  width={40}
                  height={40}
                  priority
                />
              </div>
              <div>
                <p className="text-lg font-bold tracking-wide">
                  JES Electronics Systems
                </p>
                <p className="text-[10px] font-semibold tracking-[0.22em] text-teal-200/80 uppercase">
                  Pvt Ltd · Management Information System
                </p>
              </div>
            </div>
          </div>

          <div className="relative max-w-xl">
            <p className="mb-4 inline-flex items-center gap-2 rounded-full border border-teal-300/20 bg-teal-300/10 px-3 py-1 text-[11px] font-semibold tracking-wide text-teal-200 uppercase">
              <ShieldCheck className="h-3.5 w-3.5" />
              Secure internal workspace
            </p>
            <h1 className="text-4xl leading-[1.15] font-bold tracking-tight xl:text-5xl">
              From order intake to production sign-off, in one place.
            </h1>
            <p className="mt-5 max-w-lg text-sm leading-6 text-slate-300">
              Track project readiness, inventory allocation, purchase requests,
              progress, testing, and Time Counter alerts across the R&amp;D and
              production pipeline.
            </p>
            <div className="mt-8 grid grid-cols-3 gap-3">
              {[
                ["Projects", "End-to-end"],
                ["Inventory", "Live allocation"],
                ["Audit", "Full traceability"],
              ].map(([label, value]) => (
                <div
                  key={label}
                  className="rounded-xl border border-white/10 bg-white/5 px-4 py-3 backdrop-blur"
                >
                  <p className="text-[10px] tracking-wider text-slate-400 uppercase">
                    {label}
                  </p>
                  <p className="mt-1 text-xs font-semibold text-white">
                    {value}
                  </p>
                </div>
              ))}
            </div>
          </div>

          <p className="relative text-[11px] text-slate-500">
            Authorised personnel only. All activity is recorded in the audit
            trail.
          </p>
        </section>

        <section className="flex items-center justify-center bg-slate-50 px-5 py-10 sm:px-10">
          <div className="w-full max-w-md">
            <div className="mb-8 flex items-center gap-3 lg:hidden">
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-[#082f3d] p-1.5">
                <Image
                  src="/jes-logo.png"
                  alt="JES Electronics Systems logo"
                  width={36}
                  height={36}
                  priority
                />
              </div>
              <div>
                <p className="text-sm font-bold text-slate-900">
                  JES Electronics Systems
                </p>
                <p className="text-[9px] font-semibold tracking-[0.18em] text-slate-500 uppercase">
                  Pvt Ltd · MIS
                </p>
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-xl shadow-slate-200/50 sm:p-8">
              <div>
                <p className="text-xs font-semibold tracking-[0.16em] text-[#0f5c73] uppercase">
                  Welcome back
                </p>
                <h2 className="mt-1 text-2xl font-bold tracking-tight text-slate-900">
                  Sign in to your workspace
                </h2>
                <p className="mt-1 text-sm text-slate-500">
                  Use your Office People ID (email address) and password.
                </p>
              </div>

              <form
                className="mt-6 space-y-4"
                onSubmit={handleSubmit(onSubmit)}
                noValidate
              >
                <Field
                  label="Office People ID"
                  htmlFor="email"
                  error={errors.email?.message}
                >
                  <div className="relative">
                    <Mail className="pointer-events-none absolute top-3 left-3 h-4 w-4 text-slate-400" />
                    <Input
                      id="email"
                      type="email"
                      autoComplete="username"
                      placeholder="name@jatayues.com"
                      className="pl-9"
                      {...register("email")}
                    />
                  </div>
                </Field>

                <Field
                  label="Password"
                  htmlFor="password"
                  error={errors.password?.message}
                >
                  <div className="relative">
                    <LockKeyhole className="pointer-events-none absolute top-3 left-3 h-4 w-4 text-slate-400" />
                    <Input
                      id="password"
                      type={showPassword ? "text" : "password"}
                      autoComplete="current-password"
                      placeholder="Enter your password"
                      className="pr-10 pl-9"
                      {...register("password")}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword((visible) => !visible)}
                      className="absolute top-0 right-0 flex h-10 w-10 items-center justify-center text-slate-400 transition hover:text-slate-700"
                      aria-label={
                        showPassword ? "Hide password" : "Show password"
                      }
                    >
                      {showPassword ? (
                        <EyeOff className="h-4 w-4" />
                      ) : (
                        <Eye className="h-4 w-4" />
                      )}
                    </button>
                  </div>
                </Field>

                <Button
                  type="submit"
                  className="w-full"
                  size="lg"
                  loading={isSubmitting}
                >
                  Sign in
                  {!isSubmitting ? <ArrowRight className="h-4 w-4" /> : null}
                </Button>
              </form>

              <p className="mt-5 text-center text-[11px] leading-5 text-slate-400">
                First-time users are prompted to replace their temporary
                password before continuing.
              </p>
            </div>

            <p className="mt-6 text-center text-[11px] text-slate-500">
              Need access? Contact a Super Admin to have your account created.
            </p>
          </div>
        </section>
      </div>
      <footer className="border-t border-slate-800 bg-slate-950 px-4 py-3 text-center text-[11px] text-slate-500">
        Made and managed by JES Electronics Systems Pvt Ltd
      </footer>
    </div>
  );
}
