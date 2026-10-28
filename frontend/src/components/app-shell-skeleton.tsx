"use client";

import { Skeleton } from "@/components/ui";

export function AppShellSkeleton() {
  return (
    <div className="min-h-screen bg-slate-50 lg:pl-64">
      <div className="hidden" />
      <div className="mx-auto w-full max-w-[1500px] px-4 py-8 sm:px-6 lg:px-8">
        <Skeleton className="h-7 w-48" />
        <Skeleton className="mt-2 h-4 w-80" />
        <div className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <Skeleton key={index} className="h-28" />
          ))}
        </div>
        <Skeleton className="mt-6 h-80" />
      </div>
    </div>
  );
}
