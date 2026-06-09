import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";
import { apiClient } from "@/lib/api";
import { useAuth } from "@/auth/AuthProvider";
import { useLang } from "@/i18n/LanguageProvider";
import { 
  Plus, Search, User, Users, FileText, ArrowLeft, Loader2, 
  DollarSign, Package, AlertTriangle, TrendingUp, Calendar, Trash2 
} from "lucide-react";
import { 
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer 
} from "recharts";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";

export const Route = createFileRoute("/app/")({
  component: DashboardPage,
});

type TabType = "dashboard" | "inventory" | "staff" | "activity";

function DashboardPage() {
  const { user } = useAuth();
  const { t } = useLang();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<TabType>("dashboard");
  const [searchQuery, setSearchQuery] = useState("");
  const [isAddMedOpen, setIsAddMedOpen] = useState(false);

  // Fetch Dashboard KPIs
  const { data: dashData, isLoading: isDashLoading } = useQuery({
    queryKey: ["dashboardData"],
    queryFn: async () => {
      const res = await apiClient.get("/dashboard");
      return res.data;
    },
    retry: 1,
  });

  // Fetch Medicines
  const { data: medicines, isLoading: isMedsLoading, refetch: refetchMeds } = useQuery({
    queryKey: ["medicinesList"],
    queryFn: async () => {
      const res = await apiClient.get("/medicines");
      return res.data;
    },
    retry: 1,
  });

  // Fetch Staff
  const { data: staff, isLoading: isStaffLoading } = useQuery({
    queryKey: ["staffList"],
    queryFn: async () => {
      const res = await apiClient.get("/staff");
      return res.data;
    },
    retry: 1,
  });

  // Add Medicine Mutation
  const addMedicineMutation = useMutation({
    mutationFn: async (payload: any) => {
      const res = await apiClient.post("/medicines", payload);
      return res.data;
    },
    onSuccess: () => {
      toast.success("Medicine successfully added to inventory!");
      setIsAddMedOpen(false);
      refetchMeds();
      queryClient.invalidateQueries({ queryKey: ["dashboardData"] });
    },
  });

  const handleAddMedicineSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    
    // Compile nested location object
    const location = {
      rack: String(fd.get("rack") || "Shelf A"),
      shelf: String(fd.get("shelf") || "Row 1"),
      warehouse: String(fd.get("warehouse") || "Main Store")
    };

    const payload = {
      id: crypto.randomUUID(),
      name: String(fd.get("name") || ""),
      genericName: String(fd.get("genericName") || ""),
      brand: String(fd.get("brand") || "Generic"),
      category: String(fd.get("category") || "Analgesic"),
      barcode: String(fd.get("barcode") || `BAR-${Date.now()}`),
      sku: String(fd.get("sku") || `SKU-${Date.now()}`),
      batchNumber: String(fd.get("batchNumber") || "BATCH-001"),
      manufactureDate: String(fd.get("manufactureDate") || new Date().toISOString().split("T")[0]),
      expiryDate: String(fd.get("expiryDate") || new Date(Date.now() + 365 * 24 * 60 * 60 * 1000).toISOString().split("T")[0]),
      quantity: Number(fd.get("quantity") || 100),
      unit: String(fd.get("unit") || "tablets"),
      purchasePrice: Number(fd.get("purchasePrice") || 5.0),
      sellingPrice: Number(fd.get("sellingPrice") || 10.0),
      discount: 0.0,
      taxRate: 5.0,
      lowStockThreshold: Number(fd.get("lowStockThreshold") || 10),
      location,
      status: "active",
      controlled: false,
      prescriptionRequired: false,
      supplierId: crypto.randomUUID(), // Simulated supplier link
      description: String(fd.get("description") || "Standard medicine item"),
      sideEffects: [],
      interactions: [],
      dosage: "As directed",
      storage: "Store at room temp"
    };

    addMedicineMutation.mutate(payload);
  };

  // Filter medicines by search query
  const filteredMeds = medicines
    ? medicines.filter((m: any) => 
        m.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        m.generic_name.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : [];

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      {/* Top Navigation */}
      <header className="border-b border-white/10 bg-background/50 backdrop-blur-md sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link to="/" className="text-muted-foreground hover:text-white transition">
              <ArrowLeft className="size-5" />
            </Link>
            <div className="h-4 w-px bg-white/15" />
            <h1 className="text-lg font-bold text-white tracking-tight">
              {user?.pharmacyName} <span className="text-xs font-normal text-muted-foreground ml-1">Portal</span>
            </h1>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-xs font-medium text-muted-foreground bg-white/5 border border-white/10 rounded-full px-3 py-1">
              Active User: {user?.email}
            </span>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 flex-1 flex flex-col lg:flex-row gap-8">
        {/* Sidebar Nav */}
        <aside className="w-full lg:w-64 flex-shrink-0 flex flex-col gap-2">
          <SidebarButton active={activeTab === "dashboard"} onClick={() => setActiveTab("dashboard")} icon={TrendingUp} label="KPIs & Chart" />
          <SidebarButton active={activeTab === "inventory"} onClick={() => setActiveTab("inventory")} icon={Package} label="Medicine Inventory" />
          <SidebarButton active={activeTab === "staff"} onClick={() => setActiveTab("staff")} icon={Users} label="Staff Directory" />
          <SidebarButton active={activeTab === "activity"} onClick={() => setActiveTab("activity")} icon={FileText} label="Activity Logs" />
        </aside>

        {/* Dashboard Content Panel */}
        <main className="flex-1 space-y-6">
          {/* TAB 1: DASHBOARD STATS */}
          {activeTab === "dashboard" && (
            <div className="space-y-6">
              {isDashLoading ? (
                <div className="flex items-center justify-center py-20">
                  <Loader2 className="size-8 animate-spin text-muted-foreground" />
                </div>
              ) : dashData ? (
                <>
                  {/* KPI Cards Grid */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                    <KpiCard icon={DollarSign} title="Today's Revenue" value={`IQD ${dashData.stats.today_revenue.toLocaleString()}`} subtitle="Sales processed today" glow="emerald" />
                    <KpiCard icon={TrendingUp} title="Monthly Revenue" value={`IQD ${dashData.stats.month_revenue.toLocaleString()}`} subtitle="Sales processed this month" glow="blue" />
                    <KpiCard icon={Package} title="Low Stock Alerts" value={`${dashData.stats.low_stock} items`} subtitle="Requires urgent reorder" glow="amber" />
                    <KpiCard icon={AlertTriangle} title="Expired Medicines" value={`${dashData.stats.expired} items`} subtitle="Removed from dispensing" glow="rose" />
                  </div>

                  {/* Recharts Analytics Chart */}
                  <div className="glass rounded-2xl border border-white/10 p-5 space-y-4">
                    <div>
                      <h3 className="text-base font-semibold text-white">Revenue & Profit History</h3>
                      <p className="text-xs text-muted-foreground">30-day business timeline</p>
                    </div>
                    <div className="h-72 w-full">
                      <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={dashData.revenue_series} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                          <defs>
                            <linearGradient id="colorRev" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.2}/>
                              <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                            </linearGradient>
                            <linearGradient id="colorProf" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="5%" stopColor="#10b981" stopOpacity={0.2}/>
                              <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                            </linearGradient>
                          </defs>
                          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                          <XAxis dataKey="day" stroke="rgba(255,255,255,0.4)" fontSize={11} tickLine={false} />
                          <YAxis stroke="rgba(255,255,255,0.4)" fontSize={11} tickLine={false} />
                          <Tooltip contentStyle={{ backgroundColor: "#121212", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px" }} />
                          <Area type="monotone" dataKey="revenue" stroke="#3b82f6" strokeWidth={2} fillOpacity={1} fill="url(#colorRev)" name="Revenue" />
                          <Area type="monotone" dataKey="profit" stroke="#10b981" strokeWidth={2} fillOpacity={1} fill="url(#colorProf)" name="Profit" />
                        </AreaChart>
                      </ResponsiveContainer>
                    </div>
                  </div>

                  {/* Top Sold Drugs List */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="glass rounded-2xl border border-white/10 p-5 space-y-4">
                      <h3 className="text-sm font-semibold text-white">Top Performing Medicines</h3>
                      <div className="space-y-3">
                        {dashData.top_sold && dashData.top_sold.length > 0 ? (
                          dashData.top_sold.map((drug: any, i: number) => (
                            <div key={i} className="flex items-center justify-between text-xs py-2 border-b border-white/5 last:border-0">
                              <div className="font-medium text-foreground">{drug.name}</div>
                              <div className="flex gap-4 text-muted-foreground">
                                <span>{drug.qty} sold</span>
                                <span className="text-white font-semibold">IQD {drug.revenue.toLocaleString()}</span>
                              </div>
                            </div>
                          ))
                        ) : (
                          <div className="text-xs text-muted-foreground py-4 text-center">No sales logged yet.</div>
                        )}
                      </div>
                    </div>

                    <div className="glass rounded-2xl border border-white/10 p-5 space-y-4">
                      <h3 className="text-sm font-semibold text-white">Category Value Breakdown</h3>
                      <div className="space-y-3">
                        {dashData.category_breakdown && dashData.category_breakdown.length > 0 ? (
                          dashData.category_breakdown.map((cat: any, i: number) => (
                            <div key={i} className="flex items-center justify-between text-xs py-2 border-b border-white/5 last:border-0">
                              <div className="font-medium text-foreground">{cat.name}</div>
                              <div className="text-white font-semibold">IQD {cat.value.toLocaleString()}</div>
                            </div>
                          ))
                        ) : (
                          <div className="text-xs text-muted-foreground py-4 text-center">No inventory items.</div>
                        )}
                      </div>
                    </div>
                  </div>
                </>
              ) : (
                <div className="text-center py-20 text-muted-foreground">Unable to load dashboard metrics.</div>
              )}
            </div>
          )}

          {/* TAB 2: INVENTORY */}
          {activeTab === "inventory" && (
            <div className="space-y-4">
              <div className="flex items-center justify-between flex-wrap gap-3">
                {/* Search */}
                <div className="relative w-full max-w-xs">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
                  <Input 
                    type="text" 
                    placeholder="Search medicines..." 
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-9 h-10 rounded-xl border-white/15 bg-white/5 text-foreground placeholder:text-muted-foreground focus-visible:ring-white/20"
                  />
                </div>

                {/* Add Button */}
                <Button 
                  onClick={() => setIsAddMedOpen(true)}
                  className="h-10 rounded-xl bg-white text-background hover:bg-white/90 gap-2 font-semibold"
                >
                  <Plus className="size-4" />
                  Add Medicine
                </Button>
              </div>

              {/* Table */}
              <div className="glass rounded-2xl border border-white/10 overflow-hidden">
                {isMedsLoading ? (
                  <div className="flex justify-center py-20">
                    <Loader2 className="size-8 animate-spin text-muted-foreground" />
                  </div>
                ) : filteredMeds.length > 0 ? (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse text-xs">
                      <thead>
                        <tr className="border-b border-white/10 bg-white/[0.02] text-muted-foreground font-semibold">
                          <th className="p-4">Name</th>
                          <th className="p-4">Generic Name</th>
                          <th className="p-4">Category</th>
                          <th className="p-4">Qty</th>
                          <th className="p-4">Selling Price</th>
                          <th className="p-4">Expiry Date</th>
                          <th className="p-4">Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {filteredMeds.map((med: any) => (
                          <tr key={med.id} className="border-b border-white/5 hover:bg-white/[0.01] transition-colors">
                            <td className="p-4 font-semibold text-white">{med.name}</td>
                            <td className="p-4 text-muted-foreground">{med.generic_name}</td>
                            <td className="p-4 text-muted-foreground">{med.category}</td>
                            <td className={`p-4 font-semibold ${med.quantity <= med.low_stock_threshold ? "text-amber-400" : "text-foreground"}`}>
                              {med.quantity} {med.unit}
                            </td>
                            <td className="p-4 font-medium">IQD {Math.round(med.selling_price).toLocaleString()}</td>
                            <td className="p-4 text-muted-foreground">{med.expiry_date || "N/A"}</td>
                            <td className="p-4">
                              <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase ${
                                med.status === "active" 
                                  ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" 
                                  : "bg-red-500/10 text-red-400 border border-red-500/20"
                              }`}>
                                {med.status}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="text-center py-20 text-muted-foreground">No medicines found in the inventory.</div>
                )}
              </div>
            </div>
          )}

          {/* TAB 3: STAFF */}
          {activeTab === "staff" && (
            <div className="glass rounded-2xl border border-white/10 overflow-hidden">
              {isStaffLoading ? (
                <div className="flex justify-center py-20">
                  <Loader2 className="size-8 animate-spin text-muted-foreground" />
                </div>
              ) : staff && staff.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse text-xs">
                    <thead>
                      <tr className="border-b border-white/10 bg-white/[0.02] text-muted-foreground font-semibold">
                        <th className="p-4">Name</th>
                        <th className="p-4">Email</th>
                        <th className="p-4">Role</th>
                        <th className="p-4">Shift</th>
                        <th className="p-4">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {staff.map((member: any) => (
                        <tr key={member.id} className="border-b border-white/5 hover:bg-white/[0.01] transition-colors">
                          <td className="p-4 font-semibold text-white flex items-center gap-2">
                            <span className="grid size-7 place-items-center rounded-full bg-white/10 text-[10px] font-bold text-white">
                              {member.name[0].toUpperCase()}
                            </span>
                            {member.name}
                          </td>
                          <td className="p-4 text-muted-foreground">{member.email}</td>
                          <td className="p-4 text-muted-foreground capitalize">{member.role}</td>
                          <td className="p-4 text-muted-foreground capitalize">{member.shift}</td>
                          <td className="p-4">
                            <span className="rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-0.5 text-[10px] font-semibold uppercase">
                              {member.status}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="text-center py-20 text-muted-foreground">No staff directory records.</div>
              )}
            </div>
          )}

          {/* TAB 4: ACTIVITY LOGS */}
          {activeTab === "activity" && (
            <div className="glass rounded-2xl border border-white/10 p-5 space-y-4">
              <h3 className="text-base font-semibold text-white">Platform Activity Stream</h3>
              <div className="space-y-4">
                {dashData?.recent_activity && dashData.recent_activity.length > 0 ? (
                  dashData.recent_activity.map((act: any) => (
                    <div key={act.id} className="flex gap-4 items-start text-xs border-b border-white/5 pb-3 last:border-0 last:pb-0">
                      <div className={`grid size-8 place-items-center rounded-full flex-shrink-0 ${
                        act.severity === "high" || act.severity === "error"
                          ? "bg-rose-500/15 text-rose-400"
                          : act.severity === "warning"
                          ? "bg-amber-500/15 text-amber-400"
                          : "bg-blue-500/15 text-blue-400"
                      }`}>
                        <FileText className="size-4" />
                      </div>
                      <div className="flex-1 space-y-1">
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-white">{act.actor}</span>
                          <span className="text-[10px] text-muted-foreground">{new Date(act.at).toLocaleString()}</span>
                        </div>
                        <p className="text-muted-foreground text-[11px] leading-relaxed">{act.message}</p>
                        <span className="inline-block text-[9px] uppercase tracking-wider text-muted-foreground font-semibold">
                          Type: {act.type}
                        </span>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="text-center py-20 text-muted-foreground">No activity history recorded.</div>
                )}
              </div>
            </div>
          )}
        </main>
      </div>

      {/* Add Medicine Dialog */}
      <Dialog open={isAddMedOpen} onOpenChange={setIsAddMedOpen}>
        <DialogContent className="glass-strong max-w-xl rounded-2xl border-white/10 bg-background/90 p-6 text-foreground shadow-2xl overflow-y-auto max-h-[85vh]">
          <DialogHeader className="text-start">
            <DialogTitle className="text-xl">Add New Medicine</DialogTitle>
            <DialogDescription className="text-muted-foreground">
              Submit medicine details to provision stock to the pharmacy database.
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleAddMedicineSubmit} className="space-y-4 mt-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label htmlFor="name">Medicine Name</Label>
                <Input id="name" name="name" required placeholder="e.g. Panadol Extra" className="h-10 rounded-xl border-white/10 bg-white/5" />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="genericName">Generic/Chemical Name</Label>
                <Input id="genericName" name="genericName" required placeholder="e.g. Paracetamol" className="h-10 rounded-xl border-white/10 bg-white/5" />
              </div>
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-1.5">
                <Label htmlFor="brand">Brand</Label>
                <Input id="brand" name="brand" placeholder="e.g. GSK" className="h-10 rounded-xl border-white/10 bg-white/5" />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="category">Category</Label>
                <Input id="category" name="category" required placeholder="e.g. Analgesic" className="h-10 rounded-xl border-white/10 bg-white/5" />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="batchNumber">Batch Code</Label>
                <Input id="batchNumber" name="batchNumber" placeholder="e.g. BAT-2026A" className="h-10 rounded-xl border-white/10 bg-white/5" />
              </div>
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-1.5">
                <Label htmlFor="quantity">Stock Quantity</Label>
                <Input id="quantity" name="quantity" type="number" required placeholder="100" className="h-10 rounded-xl border-white/10 bg-white/5" />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="unit">Unit Type</Label>
                <Input id="unit" name="unit" required placeholder="e.g. tablets" className="h-10 rounded-xl border-white/10 bg-white/5" />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="lowStockThreshold">Low Stock Alarm</Label>
                <Input id="lowStockThreshold" name="lowStockThreshold" type="number" placeholder="10" className="h-10 rounded-xl border-white/10 bg-white/5" />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label htmlFor="purchasePrice">Purchase Price (IQD)</Label>
                <Input id="purchasePrice" name="purchasePrice" type="number" step="0.01" placeholder="500" className="h-10 rounded-xl border-white/10 bg-white/5" />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="sellingPrice">Selling Price (IQD)</Label>
                <Input id="sellingPrice" name="sellingPrice" type="number" step="0.01" placeholder="1000" className="h-10 rounded-xl border-white/10 bg-white/5" />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label htmlFor="manufactureDate">Manufacture Date</Label>
                <Input id="manufactureDate" name="manufactureDate" type="date" className="h-10 rounded-xl border-white/10 bg-white/5" />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="expiryDate">Expiry Date</Label>
                <Input id="expiryDate" name="expiryDate" type="date" required className="h-10 rounded-xl border-white/10 bg-white/5" />
              </div>
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-1.5">
                <Label htmlFor="rack">Rack location</Label>
                <Input id="rack" name="rack" placeholder="A1" className="h-10 rounded-xl border-white/10 bg-white/5" />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="shelf">Shelf location</Label>
                <Input id="shelf" name="shelf" placeholder="Row 2" className="h-10 rounded-xl border-white/10 bg-white/5" />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="warehouse">Store warehouse</Label>
                <Input id="warehouse" name="warehouse" placeholder="Store 1" className="h-10 rounded-xl border-white/10 bg-white/5" />
              </div>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="description">Item Description</Label>
              <Input id="description" name="description" placeholder="Optional details..." className="h-10 rounded-xl border-white/10 bg-white/5" />
            </div>

            <Button 
              type="submit" 
              disabled={addMedicineMutation.isPending}
              className="mt-4 h-11 w-full rounded-full bg-white text-background hover:bg-white/90 font-semibold"
            >
              {addMedicineMutation.isPending ? (
                <Loader2 className="size-4 animate-spin text-current" />
              ) : (
                "Save Medicine"
              )}
            </Button>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function SidebarButton({ active, onClick, icon: Icon, label }: { active: boolean; onClick: () => void; icon: any; label: string }) {
  return (
    <button
      onClick={onClick}
      className={`flex w-full items-center gap-3 rounded-xl px-4 py-3 text-xs font-semibold tracking-wide transition ${
        active 
          ? "bg-white text-background shadow-md" 
          : "text-foreground/70 hover:bg-white/5 hover:text-white"
      }`}
    >
      <Icon className="size-4" />
      {label}
    </button>
  );
}

function KpiCard({ icon: Icon, title, value, subtitle, glow }: { icon: any; title: string; value: string; subtitle: string; glow: "emerald" | "blue" | "amber" | "rose" }) {
  const glowClasses = {
    emerald: "shadow-[0_15px_40px_-15px_rgba(16,185,129,0.15)] border-emerald-500/10",
    blue: "shadow-[0_15px_40px_-15px_rgba(59,130,246,0.15)] border-blue-500/10",
    amber: "shadow-[0_15px_40px_-15px_rgba(245,158,11,0.15)] border-amber-500/10",
    rose: "shadow-[0_15px_40px_-15px_rgba(244,63,94,0.15)] border-rose-500/10",
  };

  const iconGlow = {
    emerald: "bg-emerald-500/10 text-emerald-400",
    blue: "bg-blue-500/10 text-blue-400",
    amber: "bg-amber-500/10 text-amber-400",
    rose: "bg-rose-500/10 text-rose-400",
  };

  return (
    <div className={`glass rounded-2xl border p-5 flex flex-col justify-between min-h-[120px] ${glowClasses[glow]}`}>
      <div className="flex justify-between items-start">
        <span className="text-[10px] uppercase font-bold tracking-wider text-muted-foreground">{title}</span>
        <div className={`p-2 rounded-xl ${iconGlow[glow]}`}>
          <Icon className="size-4" />
        </div>
      </div>
      <div className="space-y-1 mt-3">
        <div className="text-xl font-bold text-white tracking-tight leading-none">{value}</div>
        <p className="text-[10px] text-muted-foreground">{subtitle}</p>
      </div>
    </div>
  );
}
