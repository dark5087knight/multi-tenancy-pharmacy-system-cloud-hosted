import { motion } from "motion/react";
import { Check, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { useLang } from "@/i18n/LanguageProvider";
import { useAuth } from "@/auth/AuthProvider";
import { Button } from "@/components/ui/button";
import type { TranslationKey } from "@/i18n/translations";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";

type RenderPlan = {
  id?: string;
  name: TranslationKey;
  rawName?: string;
  desc: TranslationKey;
  rawDesc?: string;
  price: string;
  features: TranslationKey[];
  highlighted?: boolean;
};

const staticPlans: RenderPlan[] = [
  {
    name: "pricing.starter.name",
    desc: "pricing.starter.desc",
    price: "$29",
    features: ["pricing.f.inventory", "pricing.f.reports", "pricing.f.support"],
  },
  {
    name: "pricing.pro.name",
    desc: "pricing.pro.desc",
    price: "$79",
    features: [
      "pricing.f.inventory",
      "pricing.f.branches",
      "pricing.f.advanced",
      "pricing.f.priority",
    ],
    highlighted: true,
  },
  {
    name: "pricing.enterprise.name",
    desc: "pricing.enterprise.desc",
    price: "$199",
    features: [
      "pricing.f.sso",
      "pricing.f.sla",
      "pricing.f.manager",
      "pricing.f.priority",
    ],
  },
];

export function Pricing() {
  const { t } = useLang();
  const { user, openAuth } = useAuth();
  const queryClient = useQueryClient();

  // Fetch plans from backend
  const { data: dbPlans, isLoading: isPlansLoading } = useQuery({
    queryKey: ["plans"],
    queryFn: async () => {
      const res = await apiClient.get("/billing/plans");
      return res.data;
    },
    retry: 1,
  });

  // Checkout mutation
  const checkoutMutation = useMutation({
    mutationFn: async (planId: string) => {
      const res = await apiClient.post("/billing/checkout", { plan_id: planId });
      return res.data;
    },
    onSuccess: (data) => {
      toast.success(`Successfully upgraded to the ${data.plan_name || "selected"} plan!`);
      queryClient.invalidateQueries({ queryKey: ["subscription"] });
    },
  });

  const subscribe = (p: RenderPlan) => {
    if (!user) {
      openAuth();
      return;
    }
    if (p.id) {
      checkoutMutation.mutate(p.id);
    } else {
      toast.error("Invalid plan selection. Please refresh.");
    }
  };

  // Map backend plans or fallback to static list
  const plansToRender: RenderPlan[] = dbPlans && dbPlans.length > 0
    ? dbPlans.map((p: any) => {
        const slug = p.slug.toLowerCase();
        let nameKey: TranslationKey = "pricing.starter.name";
        let descKey: TranslationKey = "pricing.starter.desc";
        let features: TranslationKey[] = [];

        if (slug === "starter" || slug === "free") {
          nameKey = "pricing.starter.name";
          descKey = "pricing.starter.desc";
          features = ["pricing.f.inventory", "pricing.f.reports", "pricing.f.support"];
        } else if (slug === "pro") {
          nameKey = "pricing.pro.name";
          descKey = "pricing.pro.desc";
          features = [
            "pricing.f.inventory",
            "pricing.f.branches",
            "pricing.f.advanced",
            "pricing.f.priority",
          ];
        } else if (slug === "enterprise") {
          nameKey = "pricing.enterprise.name";
          descKey = "pricing.enterprise.desc";
          features = [
            "pricing.f.sso",
            "pricing.f.sla",
            "pricing.f.manager",
            "pricing.f.priority",
          ];
        }

        return {
          id: p.id,
          name: nameKey,
          rawName: p.name,
          desc: descKey,
          rawDesc: p.description,
          price: `$${Math.round(p.price_monthly)}`,
          features,
          highlighted: slug === "pro",
        };
      })
    : staticPlans;

  return (
    <section id="pricing" className="relative py-20 sm:py-28">
      {/* ambient glow */}
      <div aria-hidden className="pointer-events-none absolute inset-0 -z-10">
        <div className="absolute left-1/2 bottom-0 size-[500px] -translate-x-1/2 rounded-full bg-white/[0.02] blur-3xl" />
      </div>

      <div className="mx-auto max-w-6xl px-4">
        <div className="mx-auto max-w-2xl text-center">
          <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">{t("pricing.eyebrow")}</p>
          <h2 className="mt-3 text-3xl font-semibold tracking-tight sm:text-4xl">{t("pricing.title")}</h2>
          <p className="mt-3 text-muted-foreground">{t("pricing.subtitle")}</p>
        </div>

        {isPlansLoading ? (
          <div className="mt-16 flex justify-center">
            <Loader2 className="size-8 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <div className="mt-12 grid gap-4 lg:grid-cols-3">
            {plansToRender.map((p, i) => (
              <motion.div
                key={p.id || i}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-60px" }}
                transition={{ duration: 0.4, delay: i * 0.07 }}
                className={`relative flex flex-col rounded-2xl p-6 transition duration-300 hover:-translate-y-1 ${
                  p.highlighted
                    ? "glass-strong border-white/20 ring-1 ring-white/20"
                    : "glass"
                }`}
              >
                {p.highlighted && (
                  <span className="absolute -top-3 start-6 rounded-full bg-white px-3 py-1 text-[10px] font-semibold uppercase tracking-wider text-background">
                    {t("pricing.popular")}
                  </span>
                )}
                <h3 className="text-lg font-semibold">{t(p.name)}</h3>
                <p className="mt-1 text-sm text-muted-foreground">{t(p.desc)}</p>
                <div className="mt-6 flex items-baseline gap-1">
                  <span className="text-4xl font-semibold tracking-tight">{p.price}</span>
                  <span className="text-sm text-muted-foreground">{t("pricing.per")}</span>
                </div>
                <ul className="mt-6 flex-1 space-y-2.5">
                  {p.features.map((f) => (
                    <li key={f} className="flex items-center gap-2 text-sm text-foreground/90">
                      <Check className="size-4 text-foreground/80" strokeWidth={2} />
                      {t(f)}
                    </li>
                  ))}
                </ul>
                <Button
                  onClick={() => subscribe(p)}
                  disabled={checkoutMutation.isPending && checkoutMutation.variables === p.id}
                  className={`mt-8 h-11 rounded-full ${
                    p.highlighted
                      ? "bg-white text-background hover:bg-white/90"
                      : "border border-white/15 bg-white/5 text-foreground hover:bg-white/10"
                  }`}
                >
                  {checkoutMutation.isPending && checkoutMutation.variables === p.id ? (
                    <Loader2 className="size-4 animate-spin text-current" />
                  ) : (
                    t("pricing.cta")
                  )}
                </Button>
              </motion.div>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}