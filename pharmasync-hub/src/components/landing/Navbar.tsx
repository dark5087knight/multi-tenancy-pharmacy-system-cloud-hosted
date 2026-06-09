import { Download, Menu } from "lucide-react";
import { useState } from "react";
import { useLang } from "@/i18n/LanguageProvider";
import { useAuth } from "@/auth/AuthProvider";
import { LanguageSwitcher } from "@/components/common/LanguageSwitcher";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";

function initials(name: string) {
  return name
    .split(/\s+/)
    .map((w) => w[0])
    .filter(Boolean)
    .slice(0, 2)
    .join("")
    .toUpperCase();
}

export function Navbar() {
  const { t } = useLang();
  const { user, openAuth, openDrawer, openDownload } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);

  const navLinks = (
    <>
      <a href="#features" className="text-sm text-foreground/80 transition hover:text-foreground">
        {t("nav.features")}
      </a>
      <a href="#pricing" className="text-sm text-foreground/80 transition hover:text-foreground">
        {t("nav.pricing")}
      </a>
    </>
  );

  const accountArea = user ? (
    <button
      onClick={openDrawer}
      className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 py-1 ps-1 pe-3 text-sm text-foreground transition hover:bg-white/10 hover:-translate-y-0.5"
      aria-label="Account"
    >
      <span className="grid size-7 place-items-center rounded-full bg-white text-[10px] font-semibold text-background">
        {initials(user.pharmacyName)}
      </span>
      <span className="hidden max-w-[160px] truncate sm:inline">{user.pharmacyName}</span>
    </button>
  ) : (
    <Button
      variant="ghost"
      onClick={openAuth}
      className="rounded-full border border-white/10 bg-white/5 px-4 text-sm hover:bg-white/10"
    >
      {t("nav.login")}
    </Button>
  );

  return (
    <header className="fixed inset-x-0 top-0 z-40">
      <div className="mx-auto mt-3 max-w-6xl px-4">
        <div className="glass flex h-14 items-center justify-between rounded-2xl px-3 sm:px-4">
          <a href="#top" className="flex items-center gap-2 ps-1">
            <span className="grid size-7 place-items-center rounded-md bg-white text-background">
              <svg viewBox="0 0 24 24" className="size-4" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 3v18M3 12h18" />
              </svg>
            </span>
            <span className="text-sm font-semibold tracking-tight">PharmaCloud</span>
          </a>

          <nav className="hidden items-center gap-6 md:flex">{navLinks}</nav>

          <div className="flex items-center gap-2">
            <div className="hidden sm:block"><LanguageSwitcher /></div>
            <div className="hidden sm:block">{accountArea}</div>
            <Button
              onClick={openDownload}
              className="hidden rounded-full bg-white px-4 text-background hover:bg-white/90 sm:inline-flex"
            >
              <Download className="size-4" />
              <span className="ms-2">{t("nav.download")}</span>
            </Button>

            <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
              <SheetTrigger asChild>
                <Button variant="ghost" size="icon" className="md:hidden">
                  <Menu className="size-5" />
                </Button>
              </SheetTrigger>
              <SheetContent side="top" className="glass-strong border-white/10 bg-background/80">
                <div className="mt-6 flex flex-col gap-4">
                  <a href="#features" onClick={() => setMobileOpen(false)} className="text-base">{t("nav.features")}</a>
                  <a href="#pricing" onClick={() => setMobileOpen(false)} className="text-base">{t("nav.pricing")}</a>
                  <div className="flex items-center gap-3 pt-2">
                    <LanguageSwitcher />
                    {accountArea}
                  </div>
                  <Button onClick={() => { setMobileOpen(false); openDownload(); }} className="mt-2 rounded-full bg-white text-background hover:bg-white/90">
                    <Download className="size-4" />
                    <span className="ms-2">{t("nav.download")}</span>
                  </Button>
                </div>
              </SheetContent>
            </Sheet>
          </div>
        </div>
      </div>
    </header>
  );
}