export type Lang = "en" | "ar";

export const translations = {
  en: {
    "nav.features": "Features",
    "nav.pricing": "Pricing",
    "nav.download": "Download",
    "nav.login": "Login",
    "nav.language": "Language",

    "hero.title": "Modern Pharmacy SaaS Platform",
    "hero.subtitle":
      "Run your pharmacy with confidence. Inventory, prescriptions, billing and team access — unified in one secure, multi-tenant cloud platform.",
    "hero.cta.get": "Get App",
    "hero.cta.pricing": "View Pricing",
    "hero.badge": "Built for modern pharmacies",

    "dash.label": "Today",
    "dash.sales": "Sales",
    "dash.orders": "Orders",
    "dash.stock": "Low stock",
    "dash.activity": "Activity",

    "features.eyebrow": "Features",
    "features.title": "Everything your pharmacy needs",
    "features.subtitle":
      "A focused toolkit that scales from a single counter to a multi-branch network.",
    "feature.inventory.title": "Inventory Management",
    "feature.inventory.desc":
      "Track stock in real time across locations with smart reorder thresholds and expiry alerts.",
    "feature.safety.title": "Drug Safety Checks",
    "feature.safety.desc":
      "Built-in interaction, allergy and dosage warnings to keep every dispense safe.",
    "feature.billing.title": "Subscription Billing",
    "feature.billing.desc":
      "Flexible plans, automated invoicing and seat management for growing teams.",
    "feature.tenant.title": "Multi-Tenant Architecture",
    "feature.tenant.desc":
      "Isolated, secure workspaces for every pharmacy with shared admin tooling.",
    "feature.rbac.title": "Role-Based Access",
    "feature.rbac.desc":
      "Fine-grained permissions for pharmacists, cashiers, managers and owners.",
    "feature.sync.title": "Real-time Sync",
    "feature.sync.desc":
      "Every device stays in sync — instantly, with offline-safe writes.",

    "pricing.eyebrow": "Pricing",
    "pricing.title": "Simple, transparent plans",
    "pricing.subtitle": "Start free, upgrade when you grow.",
    "pricing.per": "/month",
    "pricing.popular": "Most popular",
    "pricing.cta": "Subscribe",
    "pricing.starter.name": "Starter",
    "pricing.starter.desc": "For independent pharmacies getting started.",
    "pricing.pro.name": "Pro",
    "pricing.pro.desc": "For growing pharmacies with multiple staff.",
    "pricing.enterprise.name": "Enterprise",
    "pricing.enterprise.desc": "For multi-branch networks and chains.",
    "pricing.f.users": "users",
    "pricing.f.inventory": "Inventory & POS",
    "pricing.f.reports": "Standard reports",
    "pricing.f.support": "Email support",
    "pricing.f.branches": "Multi-branch",
    "pricing.f.advanced": "Advanced analytics",
    "pricing.f.priority": "Priority support",
    "pricing.f.sso": "SSO & audit logs",
    "pricing.f.sla": "Custom SLA",
    "pricing.f.manager": "Dedicated manager",

    "download.title": "Download PharmaCloud",
    "download.subtitle": "Available on every platform your team uses.",
    "download.toast": "Download starting…",

    "auth.title": "Welcome to PharmaCloud",
    "auth.subtitle": "Sign in or create your pharmacy account.",
    "auth.tab.signin": "Sign In",
    "auth.tab.signup": "Sign Up",
    "auth.email": "Email / Username",
    "auth.password": "Password",
    "auth.confirm": "Confirm password",
    "auth.pharmacy": "Pharmacy name",
    "auth.signin.cta": "Login",
    "auth.signup.cta": "Create account",
    "auth.error.invalid": "Please enter your email/username and a password with at least 6 characters.",
    "auth.error.mismatch": "Passwords do not match.",
    "auth.error.pharmacy": "Please enter your pharmacy name.",

    "drawer.login.cta": "Login / Sign in",
    "drawer.menu.account": "Account Information",
    "drawer.menu.plan": "Subscription Plan",
    "drawer.menu.billing": "Billing / Payments",
    "drawer.menu.settings": "Settings",
    "drawer.logout": "Log out",

    "footer.rights": "All rights reserved.",
    "footer.tagline": "Modern pharmacy software.",
  },
  ar: {
    "nav.features": "المزايا",
    "nav.pricing": "الأسعار",
    "nav.download": "تحميل",
    "nav.login": "تسجيل الدخول",
    "nav.language": "اللغة",

    "hero.title": "منصة SaaS حديثة لإدارة الصيدليات",
    "hero.subtitle":
      "أدر صيدليتك بثقة كاملة. المخزون والوصفات والفوترة وصلاحيات الفريق — كل ذلك في منصة سحابية آمنة ومتعددة المستأجرين.",
    "hero.cta.get": "احصل على التطبيق",
    "hero.cta.pricing": "عرض الأسعار",
    "hero.badge": "مصممة للصيدليات الحديثة",

    "dash.label": "اليوم",
    "dash.sales": "المبيعات",
    "dash.orders": "الطلبات",
    "dash.stock": "نفاد المخزون",
    "dash.activity": "النشاط",

    "features.eyebrow": "المزايا",
    "features.title": "كل ما تحتاجه صيدليتك",
    "features.subtitle":
      "أدوات مركّزة تنمو معك من صيدلية واحدة إلى شبكة فروع متكاملة.",
    "feature.inventory.title": "إدارة المخزون",
    "feature.inventory.desc":
      "تتبّع المخزون لحظيًا في جميع الفروع مع تنبيهات إعادة الطلب وتواريخ الانتهاء.",
    "feature.safety.title": "فحوصات سلامة الدواء",
    "feature.safety.desc":
      "تنبيهات مدمجة للتفاعلات الدوائية والحساسية والجرعات لضمان كل عملية صرف.",
    "feature.billing.title": "نظام اشتراكات وفوترة",
    "feature.billing.desc":
      "خطط مرنة وفوترة آلية وإدارة المقاعد للفرق المتنامية.",
    "feature.tenant.title": "بنية متعددة المستأجرين",
    "feature.tenant.desc":
      "مساحات عمل آمنة ومعزولة لكل صيدلية مع لوحة إدارة مشتركة.",
    "feature.rbac.title": "صلاحيات حسب الدور",
    "feature.rbac.desc":
      "صلاحيات دقيقة للصيادلة وأمناء الصندوق والمديرين والمالكين.",
    "feature.sync.title": "مزامنة لحظية",
    "feature.sync.desc":
      "جميع الأجهزة متزامنة فورًا، مع كتابة آمنة حتى دون اتصال.",

    "pricing.eyebrow": "الأسعار",
    "pricing.title": "خطط واضحة وبسيطة",
    "pricing.subtitle": "ابدأ مجانًا وارقَ خطّتك عندما تنمو.",
    "pricing.per": "/شهريًا",
    "pricing.popular": "الأكثر شيوعًا",
    "pricing.cta": "اشترك الآن",
    "pricing.starter.name": "المبتدئ",
    "pricing.starter.desc": "للصيدليات المستقلة في بداياتها.",
    "pricing.pro.name": "المحترف",
    "pricing.pro.desc": "للصيدليات المتنامية بعدة موظفين.",
    "pricing.enterprise.name": "المؤسسات",
    "pricing.enterprise.desc": "للسلاسل والشبكات متعددة الفروع.",
    "pricing.f.users": "مستخدمين",
    "pricing.f.inventory": "المخزون ونقاط البيع",
    "pricing.f.reports": "التقارير الأساسية",
    "pricing.f.support": "دعم عبر البريد",
    "pricing.f.branches": "دعم تعدد الفروع",
    "pricing.f.advanced": "تحليلات متقدمة",
    "pricing.f.priority": "دعم ذو أولوية",
    "pricing.f.sso": "SSO وسجلات تدقيق",
    "pricing.f.sla": "اتفاقية SLA مخصصة",
    "pricing.f.manager": "مدير حساب مخصص",

    "download.title": "تحميل PharmaCloud",
    "download.subtitle": "متوفر على جميع المنصات التي يستخدمها فريقك.",
    "download.toast": "بدأ التحميل…",

    "auth.title": "مرحبًا بك في PharmaCloud",
    "auth.subtitle": "سجّل دخولك أو أنشئ حسابًا جديدًا لصيدليتك.",
    "auth.tab.signin": "تسجيل الدخول",
    "auth.tab.signup": "إنشاء حساب",
    "auth.email": "البريد الإلكتروني / اسم المستخدم",
    "auth.password": "كلمة المرور",
    "auth.confirm": "تأكيد كلمة المرور",
    "auth.pharmacy": "اسم الصيدلية",
    "auth.signin.cta": "دخول",
    "auth.signup.cta": "إنشاء الحساب",
    "auth.error.invalid": "يرجى إدخال البريد الإلكتروني/اسم المستخدم وكلمة مرور لا تقل عن 6 أحرف.",
    "auth.error.mismatch": "كلمتا المرور غير متطابقتين.",
    "auth.error.pharmacy": "يرجى إدخال اسم الصيدلية.",

    "drawer.login.cta": "تسجيل الدخول",
    "drawer.menu.account": "معلومات الحساب",
    "drawer.menu.plan": "خطة الاشتراك",
    "drawer.menu.billing": "الفوترة والمدفوعات",
    "drawer.menu.settings": "الإعدادات",
    "drawer.logout": "تسجيل الخروج",

    "footer.rights": "جميع الحقوق محفوظة.",
    "footer.tagline": "برنامج صيدلية حديث.",
  },
} as const;

export type TranslationKey = keyof (typeof translations)["en"];