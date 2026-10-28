import { Suspense } from "react";

import { ProjectsView } from "./projects-view";

export const metadata = {
  title: "Projects",
};

export default function ProjectsPage() {
  return (
    <Suspense
      fallback={
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="h-72 animate-pulse rounded-xl bg-slate-200/70" />
          <div className="h-72 animate-pulse rounded-xl bg-slate-200/70" />
        </div>
      }
    >
      <ProjectsView />
    </Suspense>
  );
}
