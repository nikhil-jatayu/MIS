import { LoaderCircle } from "lucide-react";

import { MisBrand, OrganizationCredit } from "@/components/mis-brand";

interface BrandedLoadingScreenProps {
  title?: string;
  description?: string;
}

export function BrandedLoadingScreen({
  title = "Preparing your workspace",
  description = "Verifying your access and loading your MIS workspace.",
}: BrandedLoadingScreenProps) {
  return (
    <main
      aria-busy="true"
      aria-live="polite"
      className="relative flex min-h-screen items-center justify-center overflow-hidden bg-[#061f2a] px-4 py-12 text-white"
    >
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 opacity-70"
        style={{
          backgroundImage:
            "radial-gradient(circle at 18% 18%, rgba(45,212,191,0.22), transparent 34%), radial-gradient(circle at 82% 78%, rgba(14,116,144,0.34), transparent 42%)",
        }}
      />

      <section className="relative w-full max-w-lg rounded-[28px] border border-white/10 bg-white/[0.06] px-7 py-9 text-center shadow-2xl shadow-black/20 backdrop-blur-xl sm:px-12 sm:py-11">
        <div className="flex justify-center">
          <MisBrand variant="dark" size="lg" />
        </div>

        <div className="mt-10 flex flex-col items-center">
          <div className="flex h-16 w-16 items-center justify-center rounded-full border border-teal-300/20 bg-teal-300/5">
            <LoaderCircle
              aria-hidden="true"
              className="h-9 w-9 animate-spin text-teal-300"
              strokeWidth={1.8}
            />
          </div>
          <h1 className="mt-6 text-xl font-semibold tracking-tight sm:text-2xl">
            {title}
          </h1>
          <p className="mt-2 max-w-sm text-sm leading-6 text-slate-300">
            {description}
          </p>
        </div>

        <div className="mt-9 border-t border-white/10 pt-6">
          <OrganizationCredit variant="dark" />
        </div>
      </section>
    </main>
  );
}
