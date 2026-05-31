"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuthStore } from "@/stores/auth-store";

const PROTECTED_PREFIXES = ["/tasks", "/reports", "/settings"];

export function AuthRouteGuard() {
  const pathname = usePathname();
  const router = useRouter();
  const status = useAuthStore((state) => state.status);
  const refresh = useAuthStore((state) => state.refresh);

  const protectedRoute = PROTECTED_PREFIXES.some((prefix) =>
    pathname.startsWith(prefix),
  );

  useEffect(() => {
    if (!protectedRoute || status !== "idle") return;
    void refresh();
  }, [protectedRoute, refresh, status]);

  useEffect(() => {
    if (!protectedRoute || status !== "anonymous") return;
    router.replace(`/login?next=${encodeURIComponent(pathname)}`);
  }, [pathname, protectedRoute, router, status]);

  return null;
}
