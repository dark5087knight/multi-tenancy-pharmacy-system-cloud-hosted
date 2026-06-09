import { Globe } from "lucide-react";
import { useLang } from "@/i18n/LanguageProvider";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

export function LanguageSwitcher() {
  const { lang, setLang } = useLang();
  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs font-medium text-foreground/90 transition hover:bg-white/10 hover:-translate-y-0.5"
        aria-label="Language"
      >
        <Globe className="size-3.5" />
        <span className="uppercase tracking-wider">{lang}</span>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="glass min-w-36">
        <DropdownMenuItem onClick={() => setLang("en")} className="gap-2">
          <span>🇺🇸</span> English
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => setLang("ar")} className="gap-2">
          <span>🇸🇦</span> العربية
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}