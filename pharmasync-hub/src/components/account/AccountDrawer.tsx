import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/auth/AuthProvider";
import { useLang } from "@/i18n/LanguageProvider";
import { CreditCard, LogOut, Settings, User, Wallet, Loader2, LayoutDashboard, ShieldAlert } from "lucide-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import { toast } from "sonner";
import { Link } from "@tanstack/react-router";

function initials(name: string) {
  return name.split(/\s+/).map((w) => w[0]).filter(Boolean).slice(0, 2).join("").toUpperCase();
}

export function AccountDrawer() {
  const { drawerOpen, closeDrawer, user, signOut, openAuth } = useAuth();
  const { t, dir } = useLang();
  const queryClient = useQueryClient();

  // Fetch subscription from backend
  const { data: sub, isLoading: isSubLoading } = useQuery({
    queryKey: ["subscription"],
    queryFn: async () => {
      const res = await apiClient.get("/billing/subscription");
      return res.data;
    },
    enabled: !!user && drawerOpen,
    retry: false,
  });

  // Cancel subscription mutation
  const cancelMutation = useMutation({
    mutationFn: async () => {
      const res = await apiClient.post("/billing/subscription/cancel");
      return res.data;
    },
    onSuccess: () => {
      toast.success("Subscription successfully cancelled.");
      queryClient.invalidateQueries({ queryKey: ["subscription"] });
    },
  });

  const handleCancel = () => {
    if (confirm("Are you sure you want to cancel your subscription? You will lose access to premium features at the end of the billing period.")) {
      cancelMutation.mutate();
    }
  };

  return (
    <Sheet open={drawerOpen} onOpenChange={(o) => !o && closeDrawer()}>
      <SheetContent
        side={dir === "rtl" ? "left" : "right"}
        className="glass-strong w-full border-white/10 bg-background/80 p-0 text-foreground sm:max-w-sm"
      >
        <SheetHeader className="sr-only">
          <SheetTitle>Account</SheetTitle>
          <SheetDescription>Account drawer</SheetDescription>
        </SheetHeader>

        {user ? (
          <div className="flex h-full flex-col">
            <div className="p-6">
              <div className="flex items-center gap-3">
                <span className="grid size-12 place-items-center rounded-full bg-white text-sm font-semibold text-background">
                  {initials(user.pharmacyName)}
                </span>
                <div className="min-w-0">
                  <div className="truncate text-sm font-semibold">{user.pharmacyName}</div>
                  <div className="truncate text-xs text-muted-foreground">{user.email}</div>
                </div>
              </div>
            </div>
            
            <div className="h-px bg-white/10" />

            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {/* Dashboard access button */}
              <Link
                to="/app"
                onClick={closeDrawer}
                className="flex w-full items-center gap-3 rounded-xl px-4 py-3 text-sm font-medium text-foreground bg-white/5 border border-white/10 transition hover:bg-white/10"
              >
                <LayoutDashboard className="size-4 text-foreground/80" />
                Go to Dashboard
              </Link>

              {/* Subscription details card */}
              <div className="rounded-xl border border-white/10 bg-white/[0.03] p-4 space-y-3">
                <div className="flex items-center gap-2">
                  <Wallet className="size-4 text-muted-foreground" />
                  <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    {t("drawer.menu.plan")}
                  </span>
                </div>

                {isSubLoading ? (
                  <div className="flex items-center justify-center py-4">
                    <Loader2 className="size-5 animate-spin text-muted-foreground" />
                  </div>
                ) : sub ? (
                  <div className="space-y-3">
                    <div className="flex items-baseline justify-between">
                      <div className="text-lg font-bold tracking-tight text-white">
                        {sub.plan_name || "Pro Plan"}
                      </div>
                      <span className={`rounded-full px-2.5 py-0.5 text-[10px] font-semibold uppercase ${
                        sub.status === "active" 
                          ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" 
                          : "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                      }`}>
                        {sub.status}
                      </span>
                    </div>

                    <div className="text-xs text-muted-foreground space-y-1">
                      <div>Billing: <span className="text-foreground capitalize">{sub.billing_cycle}</span></div>
                      <div>
                        {sub.status === "active" ? "Renews on: " : "Ends on: "}
                        <span className="text-foreground">
                          {new Date(sub.current_period_end).toLocaleDateString()}
                        </span>
                      </div>
                      {sub.cancelled_at && (
                        <div className="flex items-center gap-1 mt-2 text-amber-400">
                          <ShieldAlert className="size-3" />
                          <span>Cancelled on {new Date(sub.cancelled_at).toLocaleDateString()}</span>
                        </div>
                      )}
                    </div>

                    {sub.status === "active" && (
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={handleCancel}
                        disabled={cancelMutation.isPending}
                        className="w-full mt-2 h-9 rounded-lg bg-red-950/40 text-red-400 border border-red-900/30 hover:bg-red-900/40"
                      >
                        {cancelMutation.isPending ? (
                          <Loader2 className="size-3 animate-spin" />
                        ) : (
                          "Cancel Subscription"
                        )}
                      </Button>
                    )}
                  </div>
                ) : (
                  <div className="text-xs text-muted-foreground">
                    No active subscription found. Upgrade below!
                  </div>
                )}
              </div>

              {/* Standard menu items */}
              <nav className="space-y-1">
                <MenuItem icon={User} label={t("drawer.menu.account")} />
                <MenuItem icon={CreditCard} label={t("drawer.menu.billing")} />
                <MenuItem icon={Settings} label={t("drawer.menu.settings")} />
              </nav>
            </div>

            <div className="border-t border-white/10 p-4">
              <Button
                variant="ghost"
                onClick={async () => { await signOut(); closeDrawer(); }}
                className="w-full justify-start gap-2 rounded-xl text-muted-foreground hover:bg-white/5 hover:text-foreground"
              >
                <LogOut className="size-4" />
                {t("drawer.logout")}
              </Button>
            </div>
          </div>
        ) : (
          <div className="flex h-full flex-col items-center justify-center gap-4 p-8 text-center">
            <div className="grid size-14 place-items-center rounded-full border border-white/10 bg-white/5">
              <User className="size-6 text-foreground/80" />
            </div>
            <p className="text-sm text-muted-foreground">{t("auth.subtitle")}</p>
            <Button
              onClick={() => { closeDrawer(); openAuth(); }}
              className="h-11 w-full rounded-full bg-white text-background hover:bg-white/90"
            >
              {t("drawer.login.cta")}
            </Button>
          </div>
        )}
      </SheetContent>
    </Sheet>
  );
}

function MenuItem({ icon: Icon, label }: { icon: React.ComponentType<{ className?: string }>; label: string }) {
  return (
    <button className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-foreground/90 transition hover:bg-white/5">
      <Icon className="size-4 text-foreground/70" />
      {label}
    </button>
  );
}