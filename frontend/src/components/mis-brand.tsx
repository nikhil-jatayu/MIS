import { cn } from "@/lib/utils";

interface MisBrandProps {
  variant?: "light" | "dark";
  size?: "sm" | "md" | "lg";
  className?: string;
}

export function MisBrand({
  variant = "light",
  size = "md",
  className,
}: MisBrandProps) {
  const dark = variant === "dark";
  const dimensions = {
    sm: { mark: "h-9 w-9 rounded-lg text-sm", title: "text-sm", subtitle: "text-[8px]" },
    md: { mark: "h-10 w-10 rounded-xl text-base", title: "text-sm", subtitle: "text-[9px]" },
    lg: { mark: "h-12 w-12 rounded-2xl text-lg", title: "text-lg", subtitle: "text-[10px]" },
  }[size];

  return (
    <div className={cn("flex min-w-0 items-center gap-3", className)}>
      <div
        aria-hidden="true"
        className={cn(
          "flex shrink-0 items-center justify-center font-black tracking-tight shadow-sm",
          dimensions.mark,
          dark ? "bg-white text-[#082f3d]" : "bg-[#082f3d] text-white",
        )}
      >
        MIS
      </div>
      <div className="min-w-0">
        <p
          className={cn(
            "truncate font-bold tracking-wide",
            dimensions.title,
            dark ? "text-white" : "text-slate-900",
          )}
        >
          MIS
        </p>
        <p
          className={cn(
            "truncate font-semibold tracking-[0.08em] uppercase",
            dimensions.subtitle,
            dark ? "text-teal-200/80" : "text-slate-500",
          )}
        >
          Management Information System
        </p>
      </div>
    </div>
  );
}


interface OrganizationCreditProps {
  variant?: "light" | "dark";
  className?: string;
}

/** Identifies the organization responsible for building and managing MIS. */
export function OrganizationCredit({
  variant = "light",
  className,
}: OrganizationCreditProps) {
  const dark = variant === "dark";

  return (
    <div className={cn("leading-5", className)}>
      <p
        className={cn(
          "text-[10px] font-bold tracking-[0.15em] uppercase",
          dark ? "text-teal-200" : "text-[#0f5c73]",
        )}
      >
        Designed, developed and managed by
      </p>
      <p
        className={cn(
          "mt-0.5 text-sm font-bold tracking-tight sm:text-[15px]",
          dark ? "text-white" : "text-slate-900",
        )}
      >
        JES Electronic Systems Pvt Ltd
      </p>
    </div>
  );
}
