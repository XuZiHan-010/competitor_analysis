import { cn } from "@/lib/utils";

interface PageContainerProps {
  children: React.ReactNode;
  className?: string;
  /** narrow: form-like pages (creation, single-column). wide: dashboards. */
  width?: "narrow" | "wide";
}

/**
 * Centered content shell with editorial side margins.
 * narrow = 720px max (single-column form / scoping flow)
 * wide   = 1280px max (DAG, reports)
 */
export function PageContainer({
  children,
  className,
  width = "narrow",
}: PageContainerProps) {
  return (
    <div
      className={cn(
        "mx-auto w-full px-4 py-8 sm:px-6 sm:py-12 md:px-8 md:py-16",
        width === "narrow" && "max-w-[720px]",
        width === "wide" && "max-w-[1280px]",
        className,
      )}
    >
      {children}
    </div>
  );
}
