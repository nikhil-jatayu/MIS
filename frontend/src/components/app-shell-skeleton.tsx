import { Skeleton } from "@/components/ui";

const SIDEBAR_ITEMS = Array.from({ length: 9 });
const KPI_ITEMS = Array.from({ length: 4 });
const TABLE_ROWS = Array.from({ length: 5 });

export function AppShellSkeleton() {
  return (
    <div
      className="min-h-screen bg-slate-50"
      aria-busy="true"
      aria-label="Loading MIS workspace"
      role="status"
    >
      <span className="sr-only">Loading workspace</span>

      <aside className="fixed inset-y-0 left-0 z-20 hidden w-64 flex-col border-r border-slate-200 bg-white p-5 lg:flex">
        <div className="flex h-16 items-center gap-3 border-b border-slate-100 pb-5">
          <Skeleton className="h-10 w-10 rounded-xl" />
          <div className="min-w-0 flex-1 space-y-2">
            <Skeleton className="h-3 w-20" />
            <Skeleton className="h-2.5 w-32 max-w-full" />
          </div>
        </div>

        <nav aria-hidden="true" className="mt-7 flex-1 space-y-2">
          {SIDEBAR_ITEMS.map((_, index) => (
            <div key={index} className="flex h-10 items-center gap-3 rounded-lg px-2">
              <Skeleton className="h-5 w-5 rounded-md" />
              <Skeleton className="h-3 flex-1" />
            </div>
          ))}
        </nav>

        <div className="border-t border-slate-100 pt-4">
          <div className="flex items-center gap-3">
            <Skeleton className="h-9 w-9 rounded-full" />
            <div className="min-w-0 flex-1 space-y-2">
              <Skeleton className="h-3 w-24 max-w-full" />
              <Skeleton className="h-2.5 w-16" />
            </div>
            <Skeleton className="h-7 w-7 rounded-md" />
          </div>
        </div>
      </aside>

      <div className="min-h-screen lg:pl-64">
        <header className="flex h-16 items-center justify-between gap-4 border-b border-slate-200 bg-white px-4 sm:px-6 lg:px-8">
          <div className="flex min-w-0 items-center gap-3">
            <Skeleton className="h-8 w-8 rounded-lg lg:hidden" />
            <div className="min-w-0 space-y-2">
              <Skeleton className="h-3.5 w-28 max-w-full" />
              <Skeleton className="hidden h-2.5 w-44 sm:block" />
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Skeleton className="h-9 w-9 rounded-lg" />
            <Skeleton className="h-9 w-9 rounded-full" />
            <div className="hidden space-y-2 sm:block">
              <Skeleton className="h-3 w-24" />
              <Skeleton className="h-2.5 w-16" />
            </div>
          </div>
        </header>

        <main className="mx-auto w-full max-w-[1500px] space-y-6 px-4 py-6 sm:px-6 lg:px-8">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div className="min-w-0 flex-1 space-y-2">
              <Skeleton className="h-3 w-28" />
              <Skeleton className="h-8 w-56 max-w-full" />
              <Skeleton className="h-4 w-96 max-w-full" />
            </div>
            <Skeleton className="h-10 w-32 rounded-lg" />
          </div>

          <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4" aria-hidden="true">
            {KPI_ITEMS.map((_, index) => (
              <div key={index} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
                <Skeleton className="h-3 w-24" />
                <Skeleton className="mt-3 h-7 w-16" />
                <Skeleton className="mt-3 h-2.5 w-28 max-w-full" />
              </div>
            ))}
          </section>

          <section className="grid gap-6 xl:grid-cols-[1.45fr_1fr]" aria-hidden="true">
            <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
              <div className="border-b border-slate-100 px-5 py-4">
                <Skeleton className="h-4 w-40" />
                <Skeleton className="mt-2 h-3 w-60 max-w-full" />
              </div>
              <div className="grid gap-3 p-5 sm:grid-cols-3">
                {Array.from({ length: 3 }).map((_, index) => (
                  <div key={index} className="rounded-lg border border-slate-100 p-3">
                    <Skeleton className="h-3 w-20" />
                    <Skeleton className="mt-3 h-6 w-16" />
                    <Skeleton className="mt-2 h-2.5 w-24 max-w-full" />
                  </div>
                ))}
              </div>
              <div className="space-y-4 border-t border-slate-100 p-5">
                {TABLE_ROWS.map((_, index) => (
                  <div key={index} className="flex items-center gap-3">
                    <Skeleton className="h-8 w-8 rounded-md" />
                    <div className="min-w-0 flex-1 space-y-2">
                      <Skeleton className="h-3 w-2/3 max-w-full" />
                      <Skeleton className="h-2.5 w-1/2 max-w-full" />
                    </div>
                    <Skeleton className="h-3 w-16" />
                  </div>
                ))}
              </div>
            </div>

            <div className="space-y-6">
              <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
                <div className="border-b border-slate-100 px-5 py-4">
                  <Skeleton className="h-4 w-32" />
                  <Skeleton className="mt-2 h-3 w-48 max-w-full" />
                </div>
                <div className="space-y-4 p-5">
                  {Array.from({ length: 4 }).map((_, index) => (
                    <div key={index} className="space-y-2">
                      <Skeleton className="h-3 w-24" />
                      <Skeleton className="h-3 w-full" />
                      <Skeleton className="h-3 w-4/5 max-w-full" />
                    </div>
                  ))}
                </div>
              </div>
              <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                <Skeleton className="h-4 w-32" />
                <div className="mt-4 grid grid-cols-2 gap-3">
                  {Array.from({ length: 4 }).map((_, index) => (
                    <Skeleton key={index} className="h-16 rounded-lg" />
                  ))}
                </div>
              </div>
            </div>
          </section>

          <footer className="flex justify-center border-t border-slate-200 py-5">
            <Skeleton className="h-3 w-64 max-w-full" />
          </footer>
        </main>
      </div>
    </div>
  );
}
