import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Dashboard | AI Finland Platform",
};

export default function DashboardPage() {
  return (
    <div className="flex flex-col items-center justify-center py-3xl">
      <svg
        width="48"
        height="48"
        viewBox="0 0 48 48"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden="true"
        className="mb-md text-[#49454f] opacity-40"
      >
        <path
          d="M8 24L24 8L40 24M12 20V38C12 39.1 12.9 40 14 40H20V30H28V40H34C35.1 40 36 39.1 36 38V20"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
      <h1 className="mb-sm text-[22px] font-semibold text-[#2c1f2e]">
        Welcome to AI Finland Platform
      </h1>
      <p className="text-[14px] text-[#49454f]">
        Your dashboard is ready. Content will appear here as data becomes available.
      </p>
    </div>
  );
}
