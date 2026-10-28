"use client";

import { AlertTriangle } from "lucide-react";
import { useEffect } from "react";

import { Button, Card } from "@/components/ui";

export default function AppError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <Card className="mx-auto mt-10 max-w-lg p-8 text-center">
      <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-amber-50 text-amber-600">
        <AlertTriangle className="h-6 w-6" />
      </div>
      <h1 className="mt-4 text-lg font-bold text-slate-900">
        Something went wrong
      </h1>
      <p className="mt-1 text-sm text-slate-500">
        The page could not be loaded. Please try again, or contact support if
        the problem continues.
      </p>
      {error.digest ? (
        <p className="mt-2 font-mono text-[11px] text-slate-400">
          Reference: {error.digest}
        </p>
      ) : null}
      <Button className="mt-5" onClick={reset}>
        Try again
      </Button>
    </Card>
  );
}
