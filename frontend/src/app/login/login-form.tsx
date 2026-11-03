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
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { BrandedLoadingScreen } from "@/components/branded-loading-screen";
import { MisBrand, OrganizationCredit } from "@/components/mis-brand";
import { Button, Field, Input } from "@/components/ui";
import { errorMessage } from "@/lib/api";
import { useAuth } from "@/lib/auth";

const loginSchema = z.object({
  email: z.email("Enter a valid email address"),
  password: z.string().min(1, "Enter your password").max(128),
});

type LoginValues = z.infer<typeof loginSchema>;

const POST_LOGIN_BRAND_DURATION_MS = 1800;

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
  const [isRedirecting, setIsRedirecting] = useState(false);
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
    // While a submitted login is running, its submit handler owns navigation.
    // isSubmitting remains true through the branded hand-off, preventing a
    // competing redirect from the session-change effect.
    if (isLoading || !user || isSubmitting || isRedirecting) return;
    router.replace(user.must_change_password ? "/change-password" : nextPath);
  }, [isLoading, user, isSubmitting, isRedirecting, router, nextPath]);

  if (isLoading || user || isRedirecting) {
    return (
      <BrandedLoadingScreen
        title={user || isRedirecting ? "Opening your workspace" : "Verifying your session"}
        description={
          user || isRedirecting
            ? "Your sign-in is complete. Loading your MIS workspace and access permissions."
            : "Checking whether you already have an active MIS session."
        }
      />
    );
  }

  async function onSubmit(values: LoginValues) {
    try {
      const signedIn = await login({
        email: values.email.trim(),
        password: values.password,
      });
      setIsRedirecting(true);
      toast.success(`Welcome, ${signedIn.name}`);
      // Keep the branded hand-off visible long enough to read, without adding
      // a long or artificial wait to the sign-in process.
      await new Promise<void>((resolve) => {
        window.setTimeout(resolve, POST_LOGIN_BRAND_DURATION_MS);
      });
      router.replace(
        signedIn.must_change_password ? "/change-password" : nextPath,
      );
    } catch (error) {
      setIsRedirecting(false);
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
            <MisBrand variant="dark" size="lg" />
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

          <div className="relative">
            <p className="text-[11px] text-slate-500">
              Authorised personnel only. All activity is recorded in the audit
              trail.
            </p>
            <OrganizationCredit variant="dark" className="mt-3" />
          </div>
        </section>

        <section className="flex items-center justify-center bg-slate-50 px-5 py-10 sm:px-10">
          <div className="w-full max-w-md">
            <div className="mb-8 lg:hidden">
              <MisBrand size="md" />
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
                  Sign in using your registered email address and password.
                </p>
              </div>

              <form
                className="mt-6 space-y-4"
                onSubmit={handleSubmit(onSubmit)}
                noValidate
              >
                <Field
                  label="Email Address"
                  htmlFor="email"
                  error={errors.email?.message}
                >
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

                <div className="-mt-1 flex justify-end">
                  <Link
                    href="/forgot-password"
                    className="text-xs font-semibold text-[#0f5c73] hover:underline"
                  >
                    Forgot password?
                  </Link>
                </div>

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
      <footer className="border-t border-slate-800 bg-slate-950 px-4 py-4 text-center">
        <div className="mx-auto flex w-full max-w-sm justify-center">
          <span className="inline-flex items-center rounded-full border border-slate-700/70 bg-slate-900/80 px-4 py-2 text-[10px] font-semibold tracking-[0.14em] text-slate-300 uppercase">
            Management Information System
          </span>
        </div>
        <OrganizationCredit variant="dark" className="mx-auto mt-3 max-w-sm lg:hidden" />
      </footer>
    </div>
  );
}
