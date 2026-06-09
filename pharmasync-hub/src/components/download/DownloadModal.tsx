import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { useAuth } from "@/auth/AuthProvider";
import { useLang } from "@/i18n/LanguageProvider";
import { Apple, Monitor, Smartphone, Tablet } from "lucide-react";
import { toast } from "sonner";

const platforms = [
  { name: "Windows", icon: Monitor },
  { name: "macOS", icon: Apple },
  { name: "iOS", icon: Smartphone },
  { name: "Android", icon: Tablet },
];

export function DownloadModal() {
  const { downloadOpen, closeDownload } = useAuth();
  const { t } = useLang();

  return (
    <Dialog open={downloadOpen} onOpenChange={(o) => !o && closeDownload()}>
      <DialogContent className="glass-strong max-w-lg rounded-2xl border-white/10 bg-background/70 p-6 text-foreground">
        <DialogHeader className="text-start">
          <DialogTitle className="text-xl">{t("download.title")}</DialogTitle>
          <DialogDescription className="text-muted-foreground">{t("download.subtitle")}</DialogDescription>
        </DialogHeader>
        <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
          {platforms.map(({ name, icon: Icon }) => (
            <button
              key={name}
              onClick={() => toast.success(`${name} — ${t("download.toast")}`)}
              className="group flex items-center gap-3 rounded-xl border border-white/10 bg-white/5 p-4 text-start transition hover:-translate-y-0.5 hover:bg-white/10"
            >
              <span className="grid size-10 place-items-center rounded-lg bg-white/10">
                <Icon className="size-5" strokeWidth={1.6} />
              </span>
              <div>
                <div className="text-sm font-semibold">{name}</div>
                <div className="text-xs text-muted-foreground">Download</div>
              </div>
            </button>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  );
}