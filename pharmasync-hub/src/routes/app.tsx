import { createFileRoute, Outlet } from "@tanstack/react-router";
import { useAuth } from "@/auth/AuthProvider";
import { useEffect } from "react";
import { Loader2 } from "lucide-react";

export const Route = createFileRoute("/app")({
  component: AppLayout,
});

function AppLayout() {
  const { user, initialLoading, openAuth } = useAuth();

  useEffect(() => {
    if (!initialLoading && !user) {
      openAuth();
    }
  }, [initialLoading, user, openAuth]);

  if (initialLoading) {
    return (
      <div className="flex h-screen w-screen flex-col items-center justify-center bg-background text-foreground">
        <div className="text-center space-y-4">
          <Loader2 className="size-10 animate-spin text-white/80 mx-auto" />
          <p className="text-sm text-muted-foreground tracking-wide">Resolving secure session...</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="flex h-screen w-screen flex-col items-center justify-center bg-background text-foreground text-center px-4">
        <div className="max-w-md space-y-4">
          <h1 className="text-2xl font-bold tracking-tight">Access Restricted</h1>
          <p className="text-sm text-muted-foreground">
            Please log in or register your pharmacy account to access the operations dashboard.
          </p>
          <button
            onClick={openAuth}
            className="inline-flex h-11 items-center justify-center rounded-full bg-white px-6 text-sm font-semibold text-background transition hover:bg-white/90"
          >
            Sign In to PharmaCloud
          </button>
        </div>
      </div>
    );
  }

  return <Outlet />;
}
