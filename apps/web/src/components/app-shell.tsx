"use client";

import { useState, useCallback } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useSession } from "@/hooks/use-session";

interface NavItem {
  label: string;
  href: string;
  icon: React.ReactNode;
  adminOnly?: boolean;
}

const navItems: NavItem[] = [
  {
    label: "Dashboard",
    href: "/",
    icon: (
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
        <path d="M3 10L10 3L17 10M5 8.5V16C5 16.55 5.45 17 6 17H8.5V12.5H11.5V17H14C14.55 17 15 16.55 15 16V8.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
      </svg>
    ),
  },
  {
    label: "Needs",
    href: "/needs",
    icon: (
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
        <path d="M10 3V17M3 10H17" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
      </svg>
    ),
  },
  {
    label: "Products",
    href: "/products",
    icon: (
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
        <rect x="3" y="3" width="14" height="14" rx="2" stroke="currentColor" strokeWidth="1.5"/>
        <path d="M3 8H17" stroke="currentColor" strokeWidth="1.5"/>
      </svg>
    ),
  },
  {
    label: "Matches",
    href: "/matches",
    icon: (
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
        <path d="M7 10L9 12L13 8M10 17C13.866 17 17 13.866 17 10C17 6.134 13.866 3 10 3C6.134 3 3 6.134 3 10C3 13.866 6.134 17 10 17Z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
      </svg>
    ),
  },
  {
    label: "Admin",
    href: "/admin",
    adminOnly: true,
    icon: (
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
        <path d="M10 3L3 7V13L10 17L17 13V7L10 3Z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round"/>
        <circle cx="10" cy="10" r="2" stroke="currentColor" strokeWidth="1.5"/>
      </svg>
    ),
  },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const [collapsed, setCollapsed] = useState(false);
  const pathname = usePathname();
  const { user, logout } = useSession();

  const toggleSidebar = useCallback(() => {
    setCollapsed((prev) => !prev);
  }, []);

  const isAdmin = user?.roles.some(
    (r) => r === "admin" || r === "super_admin"
  );

  const filteredNavItems = navItems.filter(
    (item) => !item.adminOnly || isAdmin
  );

  const isActive = (href: string) => {
    if (href === "/") return pathname === "/";
    return pathname.startsWith(href);
  };

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <aside
        className="flex flex-col border-r bg-[#f7f5f7] transition-all duration-200"
        style={{
          width: collapsed ? 64 : 240,
          borderColor: "rgba(0,0,0,0.08)",
        }}
      >
        {/* Sidebar header with collapse toggle */}
        <div className="flex h-[56px] items-center justify-between px-[16px]">
          {!collapsed && (
            <span className="text-[14px] font-semibold text-[#2c1f2e]">
              AI Finland
            </span>
          )}
          <button
            onClick={toggleSidebar}
            className="flex h-[32px] w-[32px] items-center justify-center rounded-md hover:bg-[rgba(0,0,0,0.04)] focus:outline-none focus:ring-2 focus:ring-primary"
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 16 16"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
              aria-hidden="true"
            >
              {collapsed ? (
                <path d="M6 3L11 8L6 13" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
              ) : (
                <path d="M11 3L6 8L11 13" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
              )}
            </svg>
          </button>
        </div>

        {/* Navigation items */}
        <nav className="flex flex-1 flex-col gap-[4px] px-[8px] py-[8px]" aria-label="Main navigation">
          {filteredNavItems.map((item) => {
            const active = isActive(item.href);
            return (
              <div key={item.href} className="relative group">
                <Link
                  href={item.href}
                  className={`flex items-center gap-[12px] rounded-md px-[12px] py-[8px] text-[14px] font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-primary ${
                    active
                      ? "bg-[#f2e1f4] text-[#2c1f2e]"
                      : "text-[#49454f] hover:bg-[rgba(0,0,0,0.04)]"
                  } ${collapsed ? "justify-center px-0" : ""}`}
                  aria-current={active ? "page" : undefined}
                >
                  <span className="flex h-[20px] w-[20px] shrink-0 items-center justify-center">
                    {item.icon}
                  </span>
                  {!collapsed && <span>{item.label}</span>}
                </Link>
                {/* Tooltip for collapsed state */}
                {collapsed && (
                  <div
                    role="tooltip"
                    className="pointer-events-none absolute left-[64px] top-1/2 z-50 -translate-y-1/2 rounded-md bg-[#2c1f2e] px-[8px] py-[4px] text-[12px] text-white opacity-0 shadow-md transition-opacity group-hover:opacity-100"
                  >
                    {item.label}
                  </div>
                )}
              </div>
            );
          })}
        </nav>
      </aside>

      {/* Main content area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Top bar */}
        <header
          className="flex h-[56px] items-center justify-end gap-[16px] border-b px-[24px]"
          style={{ borderColor: "rgba(0,0,0,0.08)" }}
        >
          <div className="flex items-center gap-[12px]">
            {user?.orgName && (
              <span className="text-[12px] font-medium text-[#49454f]">
                {user.orgName}
              </span>
            )}
            <span className="text-[14px] font-medium text-[#2c1f2e]">
              {user?.displayName ?? "User"}
            </span>
            <button
              onClick={logout}
              className="rounded-md px-[12px] py-[6px] text-[14px] font-medium text-[#49454f] hover:bg-[rgba(0,0,0,0.04)] focus:outline-none focus:ring-2 focus:ring-primary"
            >
              Logout
            </button>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-auto bg-surface p-lg">
          {children}
        </main>
      </div>
    </div>
  );
}
