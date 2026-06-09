import { motion } from "motion/react";
import { ArrowRight, Download } from "lucide-react";
import { useLang } from "@/i18n/LanguageProvider";
import { useAuth } from "@/auth/AuthProvider";
import { Button } from "@/components/ui/button";

export function Hero() {
  const { t } = useLang();
  const { openDownload } = useAuth();

  return (
    <section id="top" className="relative overflow-hidden pt-32 pb-20 sm:pt-40 sm:pb-28">
      {/* ambient gray glow */}
      <div aria-hidden className="pointer-events-none absolute inset-0 -z-10">
        <div className="absolute left-1/2 top-0 size-[640px] -translate-x-1/2 rounded-full bg-white/[0.04] blur-3xl" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_-20%,rgba(255,255,255,0.05),transparent_60%)]" />
      </div>

      <div className="mx-auto grid max-w-6xl items-center gap-12 px-4 lg:grid-cols-2">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: "easeOut" }}
        >
          <span className="inline-flex items-center rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-foreground/70">
            {t("hero.badge")}
          </span>
          <h1 className="mt-5 text-balance text-4xl font-semibold tracking-tight sm:text-5xl lg:text-6xl">
            {t("hero.title")}
          </h1>
          <p className="mt-5 max-w-xl text-pretty text-base text-muted-foreground sm:text-lg">
            {t("hero.subtitle")}
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-3">
            <Button onClick={openDownload} className="h-11 rounded-full bg-white px-5 text-background hover:bg-white/90">
              <Download className="size-4" />
              <span className="ms-2">{t("hero.cta.get")}</span>
            </Button>
            <a href="#pricing">
              <Button variant="ghost" className="h-11 rounded-full border border-white/15 bg-white/5 px-5 hover:bg-white/10">
                {t("hero.cta.pricing")}
                <ArrowRight className="ms-2 size-4 rtl:rotate-180" />
              </Button>
            </a>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, ease: "easeOut", delay: 0.1 }}
          className="relative"
        >
          <MockDashboard />
        </motion.div>
      </div>
    </section>
  );
}

function MockDashboard() {
  const { t } = useLang();
  return (
    <div className="glass-strong rounded-3xl p-3 shadow-[0_30px_80px_-20px_rgba(0,0,0,0.6)]">
      <div className="flex items-center gap-1.5 px-2 py-1.5">
        <span className="size-2.5 rounded-full bg-white/20" />
        <span className="size-2.5 rounded-full bg-white/20" />
        <span className="size-2.5 rounded-full bg-white/20" />
      </div>
      <div className="grid grid-cols-[140px_1fr] gap-3 rounded-2xl border border-white/10 bg-background/60 p-3">
        {/* sidebar */}
        <div className="hidden flex-col gap-1.5 rounded-xl bg-white/[0.03] p-2 sm:flex">
          {["Dashboard", "Inventory", "Orders", "Patients", "Reports"].map((l, i) => (
            <div key={l} className={`rounded-md px-2 py-1.5 text-[11px] ${i === 0 ? "bg-white text-background" : "text-foreground/70"}`}>{l}</div>
          ))}
        </div>
        {/* main */}
        <div className="flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <div className="text-xs text-muted-foreground">{t("dash.label")}</div>
            <div className="h-6 w-24 rounded-md bg-white/5" />
          </div>
          <div className="grid grid-cols-3 gap-2">
            {[t("dash.sales"), t("dash.orders"), t("dash.stock")].map((label, i) => (
              <div key={label} className="rounded-xl border border-white/10 bg-white/[0.03] p-3">
                <div className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</div>
                <div className="mt-2 text-lg font-semibold">{["$12.4k", "284", "9"][i]}</div>
              </div>
            ))}
          </div>
          <div className="rounded-xl border border-white/10 bg-white/[0.03] p-3">
            <div className="mb-3 text-[10px] uppercase tracking-wider text-muted-foreground">{t("dash.activity")}</div>
            <div className="flex h-28 items-end gap-1.5">
              {[35, 60, 42, 78, 55, 90, 68, 72, 50, 84, 62, 95].map((h, i) => (
                <div key={i} className="flex-1 rounded-sm bg-white/30" style={{ height: `${h}%` }} />
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}