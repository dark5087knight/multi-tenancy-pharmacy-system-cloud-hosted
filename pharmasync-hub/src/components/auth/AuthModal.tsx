import { useState, type FormEvent } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/auth/AuthProvider";
import { useLang } from "@/i18n/LanguageProvider";

export function AuthModal() {
  const { authOpen, closeAuth, signIn, signUp } = useAuth();
  const { t } = useLang();
  const [tab, setTab] = useState<"signin" | "signup">("signin");
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const onSignIn = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setErr(null);
    const fd = new FormData(e.currentTarget);
    const email = String(fd.get("email") || "");
    const password = String(fd.get("password") || "");
    if (!email.trim() || password.length < 6) { setErr(t("auth.error.invalid")); return; }
    setLoading(true);
    try {
      await signIn(email, password);
      closeAuth();
    } catch (err: any) {
      setErr(err.message || "Sign in failed.");
    } finally {
      setLoading(false);
    }
  };

  const onSignUp = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setErr(null);
    const fd = new FormData(e.currentTarget);
    const pharmacy = String(fd.get("pharmacy") || "").trim();
    const email = String(fd.get("email") || "");
    const password = String(fd.get("password") || "");
    const confirm = String(fd.get("confirm") || "");
    if (!pharmacy) { setErr(t("auth.error.pharmacy")); return; }
    if (!email.trim() || password.length < 6) { setErr(t("auth.error.invalid")); return; }
    if (password !== confirm) { setErr(t("auth.error.mismatch")); return; }
    setLoading(true);
    try {
      await signUp(pharmacy, email, password);
      closeAuth();
    } catch (err: any) {
      setErr(err.message || "Registration failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={authOpen} onOpenChange={(o) => !o && closeAuth()}>
      <DialogContent className="glass-strong max-w-md rounded-2xl border-white/10 bg-background/70 p-6 text-foreground shadow-[0_30px_80px_-20px_rgba(0,0,0,0.7)]">
        <DialogHeader className="text-start">
          <DialogTitle className="text-xl">{t("auth.title")}</DialogTitle>
          <DialogDescription className="text-muted-foreground">{t("auth.subtitle")}</DialogDescription>
        </DialogHeader>

        <Tabs value={tab} onValueChange={(v) => { setTab(v as "signin" | "signup"); setErr(null); }} className="mt-2">
          <TabsList className="grid w-full grid-cols-2 rounded-full bg-white/5">
            <TabsTrigger value="signin" className="rounded-full data-[state=active]:bg-white data-[state=active]:text-background">{t("auth.tab.signin")}</TabsTrigger>
            <TabsTrigger value="signup" className="rounded-full data-[state=active]:bg-white data-[state=active]:text-background">{t("auth.tab.signup")}</TabsTrigger>
          </TabsList>

          <TabsContent value="signin" className="mt-5">
            <form onSubmit={onSignIn} className="space-y-3">
              <Field id="email" type="text" label={t("auth.email")} placeholder="e.g. admin or admin@pharmacy.com" />
              <Field id="password" type="password" label={t("auth.password")} />
              {err && (
                <div className="rounded-xl bg-red-500/10 border border-red-500/20 p-3 text-xs text-red-400 font-medium leading-relaxed">
                  {err}
                </div>
              )}
              <Button type="submit" disabled={loading} className="mt-2 h-11 w-full rounded-full bg-white text-background hover:bg-white/90">
                {t("auth.signin.cta")}
              </Button>
            </form>
          </TabsContent>

          <TabsContent value="signup" className="mt-5">
            <form onSubmit={onSignUp} className="space-y-3">
              <Field id="pharmacy" type="text" label={t("auth.pharmacy")} placeholder="e.g. Caduceus Pharmacy" />
              <Field id="email" type="text" label={t("auth.email")} placeholder="e.g. admin or admin@pharmacy.com" />
              <Field id="password" type="password" label={t("auth.password")} />
              <Field id="confirm" type="password" label={t("auth.confirm")} />
              {err && (
                <div className="rounded-xl bg-red-500/10 border border-red-500/20 p-3 text-xs text-red-400 font-medium leading-relaxed">
                  {err}
                </div>
              )}
              <Button type="submit" disabled={loading} className="mt-2 h-11 w-full rounded-full bg-white text-background hover:bg-white/90">
                {t("auth.signup.cta")}
              </Button>
            </form>
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}

function Field({ id, type, label, placeholder }: { id: string; type: string; label: string; placeholder?: string }) {
  return (
    <div className="space-y-1.5">
      <Label htmlFor={id} className="text-xs text-muted-foreground">{label}</Label>
      <Input
        id={id}
        name={id}
        type={type}
        required
        placeholder={placeholder}
        className="h-11 rounded-xl border-white/10 bg-white/5 text-foreground placeholder:text-muted-foreground focus-visible:ring-white/20"
      />
    </div>
  );
}