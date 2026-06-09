import { motion } from "motion/react";
import { Package, ShieldCheck, CreditCard, Building2, Users, RefreshCw, type LucideIcon } from "lucide-react";
import { useLang } from "@/i18n/LanguageProvider";
import type { TranslationKey } from "@/i18n/translations";

const items: { icon: LucideIcon; title: TranslationKey; desc: TranslationKey }[] = [
  { icon: Package, title: "feature.inventory.title", desc: "feature.inventory.desc" },
  { icon: ShieldCheck, title: "feature.safety.title", desc: "feature.safety.desc" },
  { icon: CreditCard, title: "feature.billing.title", desc: "feature.billing.desc" },
  { icon: Building2, title: "feature.tenant.title", desc: "feature.tenant.desc" },
  { icon: Users, title: "feature.rbac.title", desc: "feature.rbac.desc" },
  { icon: RefreshCw, title: "feature.sync.title", desc: "feature.sync.desc" },
];

export function Features() {
  const { t } = useLang();
  return (
    <section id="features" className="relative py-20 sm:py-28">
      <div className="mx-auto max-w-6xl px-4">
        <div className="mx-auto max-w-2xl text-center">
          <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">{t("features.eyebrow")}</p>
          <h2 className="mt-3 text-3xl font-semibold tracking-tight sm:text-4xl">{t("features.title")}</h2>
          <p className="mt-3 text-muted-foreground">{t("features.subtitle")}</p>
        </div>

        <div className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {items.map(({ icon: Icon, title, desc }, i) => (
            <motion.div
              key={title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-60px" }}
              transition={{ duration: 0.4, delay: i * 0.05 }}
              className="glass group rounded-2xl p-5 transition duration-300 hover:-translate-y-1 hover:bg-white/[0.07]"
            >
              <div className="grid size-10 place-items-center rounded-xl border border-white/10 bg-white/5">
                <Icon className="size-5 text-foreground" strokeWidth={1.6} />
              </div>
              <h3 className="mt-4 text-base font-semibold">{t(title)}</h3>
              <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">{t(desc)}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}