export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-surface p-md">
      <div className="w-full max-w-[440px] rounded-lg bg-surface p-lg shadow-md">
        {children}
      </div>
    </div>
  );
}
