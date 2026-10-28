import { Suspense } from "react";

import { PurchasesView } from "./purchases-view";

export const metadata = {
  title: "Purchase requests",
};

export default function PurchasesPage() {
  return (
    <Suspense
      fallback={
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, index) => (
            <div key={index} className="h-16 animate-pulse rounded-xl bg-slate-200/70" />
          ))}
        </div>
      }
    >
      <PurchasesView />
    </Suspense>
  );
}
