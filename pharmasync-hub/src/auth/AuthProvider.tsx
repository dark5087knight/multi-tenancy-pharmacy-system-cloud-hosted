import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { apiClient } from "@/lib/api";

export type User = { pharmacyName: string; email: string };

type Ctx = {
  user: User | null;
  initialLoading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (pharmacyName: string, email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
  openAuth: () => void;
  closeAuth: () => void;
  authOpen: boolean;
  openDrawer: () => void;
  closeDrawer: () => void;
  drawerOpen: boolean;
  openDownload: () => void;
  closeDownload: () => void;
  downloadOpen: boolean;
};

const AuthContext = createContext<Ctx | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [initialLoading, setInitialLoading] = useState(true);
  const [authOpen, setAuthOpen] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [downloadOpen, setDownloadOpen] = useState(false);

  useEffect(() => {
    const verifySession = async () => {
      // If we don't even have tokens in localStorage, skip verify Session to avoid unnecessary 401s
      if (!localStorage.getItem("access_token") && !localStorage.getItem("refresh_token")) {
        setInitialLoading(false);
        return;
      }
      try {
        const res = await apiClient.get("/auth/me");
        if (res.data) {
          setUser({
            pharmacyName: res.data.pharmacyName || res.data.pharmacy_name || "Al-Shifa Pharmacy",
            email: res.data.email,
          });
        }
      } catch (err) {
        // Session not active, user remains null
        setUser(null);
      } finally {
        setInitialLoading(false);
      }
    };
    verifySession();
  }, []);

  const signIn = async (email: string, password: string) => {
    try {
      const res = await apiClient.post("/auth/login", { email, password });
      const data = res.data;
      
      // Store tokens in localStorage for persistent sessions
      localStorage.setItem("access_token", data.access_token);
      localStorage.setItem("refresh_token", data.refresh_token);

      setUser({
        pharmacyName: data.user.pharmacyName || data.user.pharmacy_name || "Al-Shifa Pharmacy",
        email: data.user.email,
      });
    } catch (e: any) {
      let message = "Invalid email or password.";
      if (e.response?.data) {
        const errData = e.response.data;
        if (typeof errData.detail === "string") {
          message = errData.detail;
        } else if (Array.isArray(errData.detail)) {
          message = errData.detail.map((err: any) => err.msg).join(", ");
        } else {
          message = errData.errors?.[0]?.message || errData.detail || message;
        }
      }
      throw new Error(message);
    }
  };

  const signUp = async (pharmacyName: string, email: string, password: string) => {
    try {
      const res = await apiClient.post("/auth/register", { pharmacy_name: pharmacyName, email, password });
      const data = res.data;

      // Store tokens in localStorage for persistent sessions
      localStorage.setItem("access_token", data.access_token);
      localStorage.setItem("refresh_token", data.refresh_token);

      setUser({
        pharmacyName: data.user.pharmacyName || data.user.pharmacy_name || pharmacyName,
        email: data.user.email,
      });
    } catch (e: any) {
      let message = "Registration failed.";
      if (e.response?.data) {
        const errData = e.response.data;
        if (typeof errData.detail === "string") {
          message = errData.detail;
        } else if (Array.isArray(errData.detail)) {
          message = errData.detail.map((err: any) => err.msg).join(", ");
        } else {
          message = errData.errors?.[0]?.message || errData.detail || message;
        }
      }
      throw new Error(message);
    }
  };

  const signOut = async () => {
    try {
      await apiClient.post("/auth/logout");
    } catch (e) {
      // ignore
    } finally {
      // Clear tokens from localStorage
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      setUser(null);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        initialLoading,
        signIn,
        signUp,
        signOut,
        authOpen,
        openAuth: () => setAuthOpen(true),
        closeAuth: () => setAuthOpen(false),
        drawerOpen,
        openDrawer: () => setDrawerOpen(true),
        closeDrawer: () => setDrawerOpen(false),
        downloadOpen,
        openDownload: () => setDownloadOpen(true),
        closeDownload: () => setDownloadOpen(false),
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}