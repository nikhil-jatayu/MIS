import { Card, Skeleton } from "@/components/ui";

export function DashboardSkeleton() {
  return (
    <div className="space-y-6" aria-busy="true" aria-label="Loading dashboard">
      <div className="space-y-2">
        <Skeleton className="h-3 w-32" />
        <Skeleton className="h-8 w-64 max-w-full" />
        <Skeleton className="h-4 w-96 max-w-full" />
      </div>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 8 }).map((_, index) => (
          <Card key={index} className="flex items-start justify-between gap-3 p-4">
            <div className="min-w-0 flex-1 space-y-3">
              <Skeleton className="h-3 w-28 max-w-full" />
              <Skeleton className="h-7 w-16" />
              <Skeleton className="h-2.5 w-24 max-w-full" />
            </div>
            <Skeleton className="h-10 w-10 shrink-0 rounded-xl" />
          </Card>
        ))}
      </section>

      <Card className="overflow-hidden">
        <div className="border-b border-slate-100 px-5 py-4">
          <Skeleton className="h-4 w-40" />
          <Skeleton className="mt-2 h-3 w-64 max-w-full" />
        </div>
        <div className="grid gap-3 p-5 sm:grid-cols-3">
          {Array.from({ length: 3 }).map((_, index) => (
            <div key={index} className="flex items-center gap-3 rounded-lg border border-slate-100 p-3">
              <Skeleton className="h-9 w-9 shrink-0 rounded-lg" />
              <div className="flex-1 space-y-2">
                <Skeleton className="h-5 w-14" />
                <Skeleton className="h-3 w-24 max-w-full" />
              </div>
            </div>
          ))}
        </div>
        <div className="space-y-3 border-t border-slate-100 p-5">
          {Array.from({ length: 3 }).map((_, index) => (
            <Skeleton key={index} className="h-3 w-full" />
          ))}
        </div>
      </Card>

      <div className="grid gap-6 xl:grid-cols-[1.45fr_1fr]">
        <Card className="overflow-hidden">
          <div className="border-b border-slate-100 px-5 py-4">
            <Skeleton className="h-4 w-36" />
            <Skeleton className="mt-2 h-3 w-56 max-w-full" />
          </div>
          <div className="divide-y divide-slate-100">
            {Array.from({ length: 4 }).map((_, index) => (
              <div key={index} className="flex items-center gap-3 px-5 py-4">
                <Skeleton className="h-9 w-9 shrink-0 rounded-lg" />
                <div className="min-w-0 flex-1 space-y-2">
                  <Skeleton className="h-3.5 w-2/3 max-w-full" />
                  <Skeleton className="h-3 w-1/2 max-w-full" />
                </div>
                <Skeleton className="h-2 w-20 shrink-0" />
              </div>
            ))}
          </div>
        </Card>

        <div className="space-y-6">
          <Card className="overflow-hidden">
            <div className="border-b border-slate-100 px-5 py-4">
              <Skeleton className="h-4 w-28" />
              <Skeleton className="mt-2 h-3 w-44 max-w-full" />
            </div>
            <div className="divide-y divide-slate-100">
              {Array.from({ length: 3 }).map((_, index) => (
                <div key={index} className="space-y-2 px-5 py-4">
                  <Skeleton className="h-3 w-20" />
                  <Skeleton className="h-3 w-full" />
                  <Skeleton className="h-3 w-4/5" />
                </div>
              ))}
            </div>
          </Card>
          <Card className="p-5">
            <Skeleton className="h-4 w-28" />
            <div className="mt-4 grid grid-cols-2 gap-3">
              {Array.from({ length: 4 }).map((_, index) => (
                <Skeleton key={index} className="h-16 rounded-lg" />
              ))}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}

export function ProjectsGridSkeleton({ count = 6 }: { count?: number }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 2xl:grid-cols-3" aria-busy="true" aria-label="Loading projects">
      {Array.from({ length: count }).map((_, index) => (
        <Card key={index} className="overflow-hidden p-5">
          <div className="flex items-start justify-between gap-3">
            <Skeleton className="h-10 w-10 rounded-xl" />
            <Skeleton className="h-6 w-20 rounded-full" />
          </div>
          <div className="mt-5 space-y-2">
            <Skeleton className="h-4 w-3/4 max-w-full" />
            <Skeleton className="h-3 w-full" />
            <Skeleton className="h-3 w-5/6 max-w-full" />
          </div>
          <div className="mt-6 flex items-center gap-2">
            <Skeleton className="h-7 w-7 rounded-full" />
            <Skeleton className="h-3 w-28" />
          </div>
          <div className="mt-6 space-y-2 border-t border-slate-100 pt-4">
            <div className="flex justify-between gap-3">
              <Skeleton className="h-3 w-20" />
              <Skeleton className="h-3 w-12" />
            </div>
            <Skeleton className="h-2.5 w-full rounded-full" />
          </div>
        </Card>
      ))}
    </div>
  );
}

export function TableRowsSkeleton({
  rows = 6,
  columns = 5,
}: {
  rows?: number;
  columns?: number;
}) {
  const gridStyle = { gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))` };

  return (
    <div className="overflow-x-auto" aria-busy="true" aria-label="Loading table data">
      <div className="min-w-[720px]">
        <div className="grid gap-4 border-b border-slate-100 bg-slate-50 px-5 py-3" style={gridStyle}>
          {Array.from({ length: columns }).map((_, index) => (
            <Skeleton key={index} className="h-3 w-3/4 max-w-full" />
          ))}
        </div>
        <div className="divide-y divide-slate-100">
          {Array.from({ length: rows }).map((_, rowIndex) => (
            <div key={rowIndex} className="grid items-center gap-4 px-5 py-4" style={gridStyle}>
              {Array.from({ length: columns }).map((_, columnIndex) => (
                <Skeleton
                  key={columnIndex}
                  className={`h-3.5 ${columnIndex === 0 ? "w-4/5" : columnIndex === columns - 1 ? "w-1/2" : "w-3/4"} max-w-full`}
                />
              ))}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export function ProductionSummarySkeleton() {
  return (
    <div className="space-y-6" aria-busy="true" aria-label="Loading production summary">
      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }).map((_, index) => (
          <Card key={index} className="space-y-3 p-4">
            <Skeleton className="h-3 w-28" />
            <Skeleton className="h-7 w-20" />
            <Skeleton className="h-3 w-36 max-w-full" />
          </Card>
        ))}
      </section>

      <Card className="overflow-hidden">
        <div className="flex items-center justify-between gap-4 border-b border-slate-100 px-5 py-4">
          <div className="space-y-2">
            <Skeleton className="h-4 w-40" />
            <Skeleton className="h-3 w-56 max-w-full" />
          </div>
          <Skeleton className="h-7 w-16 rounded-full" />
        </div>
        <div className="grid gap-5 p-5 sm:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 8 }).map((_, index) => (
            <div key={index} className="space-y-2">
              <Skeleton className="h-3 w-28 max-w-full" />
              <Skeleton className="h-5 w-24 max-w-full" />
            </div>
          ))}
        </div>
      </Card>

      <Card className="space-y-4 p-5">
        <Skeleton className="h-4 w-56 max-w-full" />
        <Skeleton className="h-3 w-4/5 max-w-full" />
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-9 w-36" />
      </Card>
    </div>
  );
}

export function AlertListSkeleton({ count = 5 }: { count?: number }) {
  return (
    <div className="space-y-3" aria-busy="true" aria-label="Loading alerts">
      {Array.from({ length: count }).map((_, index) => (
        <Card key={index} className="flex items-start gap-3 p-4">
          <Skeleton className="h-9 w-9 shrink-0 rounded-full" />
          <div className="min-w-0 flex-1 space-y-2">
            <div className="flex items-center justify-between gap-3">
              <Skeleton className="h-5 w-24 rounded-full" />
              <Skeleton className="h-3 w-20" />
            </div>
            <Skeleton className="h-3 w-full" />
            <Skeleton className="h-3 w-4/5 max-w-full" />
          </div>
        </Card>
      ))}
    </div>
  );
}
