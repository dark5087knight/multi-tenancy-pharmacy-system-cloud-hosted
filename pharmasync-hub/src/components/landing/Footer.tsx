import { useLang } from "@/i18n/LanguageProvider";

export function Footer() {
  const { t } = useLang();
  return (
    <footer className="border-t border-white/10 py-10">
      <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-3 px-4 sm:flex-row">
        <div className="flex items-center gap-2">
          <span className="grid size-6 place-items-center rounded-md bg-white text-background">
            <svg viewBox="0 0 24 24" className="size-3.5" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 3v18M3 12h18" />
            </svg>
          </span>
          <span className="text-sm font-semibold">PharmaCloud</span>
          <span className="ms-2 text-xs text-muted-foreground">{t("footer.tagline")}</span>
        </div>
        <p className="text-xs text-muted-foreground">
          © {new Date().getFullYear()} PharmaCloud. {t("footer.rights")}
        </p>
      </div>
    </footer>
  );
}