"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "@/hooks/use-session";
import { AppShell } from "@/components/app-shell";
import { MfaGate } from "@/components/mfa-gate";

export default function AuthenticatedLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { user, isAuthenticated, isLoading } = useSession();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [isLoading, isAuthenticated, router]);

  // Show loading state while checking auth
  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-surface">
        <span className="text-[14px] text-[#49454f]">Loading...</span>
      </div>
    );
  }

  // Not authenticated - will redirect
  if (!isAuthenticated) {
    return null;
  }

  // MFA gate for admin/super_admin without MFA
  const isAdminRole = user?.roles.some(
    (r) => r === "admin" || r === "super_admin"
  );
  if (isAdminRole && !user?.mfaEnabled) {
    return <MfaGate />;
  }

  return <AppShell>{children}</AppShell>;
}
