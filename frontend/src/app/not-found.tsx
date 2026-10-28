import Link from "next/link";

import { buttonClass } from "@/lib/utils";

export default function NotFound() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
      <div className="w-full max-w-lg rounded-2xl border border-slate-200 bg-white p-10 text-center shadow-sm">
        <p className="text-sm font-bold tracking-[0.2em] text-[#0f5c73] uppercase">
          404
        </p>
        <h1 className="mt-3 text-2xl font-bold text-slate-900">
          Page not found
        </h1>
        <p className="mt-2 text-sm text-slate-500">
          The page you requested does not exist or may have moved.
        </p>
        <Link href="/dashboard" className={buttonClass("primary", "md", "mt-6")}>
          Go to dashboard
        </Link>
      </div>
    </div>
  );
}
