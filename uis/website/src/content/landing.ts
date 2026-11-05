import type { LandingContent } from "@/types/content";

export const landingContent: LandingContent = {
  header: {
    brandInitials: "BR",
    brandName: "Brasaland Digital",
    tagline: "14 locations | Colombia + Florida",
    navLinks: [
      { label: "Solution", href: "#solution" },
      { label: "Departments", href: "#departments" },
      { label: "Impact", href: "#impact" },
    ],
    applyCta: {
      label: "Apply now",
      href: "/application",
      ariaLabel: "Open digital transformation application form",
    },
  },
  hero: {
    eyebrow: "Established company, digital growth phase",
    headline: "Keep the Brasaland flavor.",
    highlight: "Modernize every operation.",
    description:
      "Brasaland has grown from one family location to a two-country chain. Brasaland Digital unifies location sales, ingredient planning, loyalty data, and executive reporting so decisions are based on live metrics, not delayed PDFs.",
    primaryCta: { label: "Start your department request", href: "/application" },
    secondaryCta: { label: "See expected outcomes", href: "#impact" },
    imageUrl:
      "https://images.unsplash.com/photo-1555992336-fb0d29498b13?auto=format&fit=crop&w=1200&q=80",
    imageAlt: "Restaurant team coordinating orders and kitchen service during peak hours",
  },
  solution: {
    id: "solution",
    title: "What Brasaland Digital Delivers",
    description:
      "A mobile-first, data-first operating layer for the entire chain: from location supervisors and procurement to marketing and executive leadership.",
    items: [
      {
        title: "Real-time Operations Visibility",
        description:
          "Live sales by location, inactivity alerts during opening hours, and centralized view of COP and USD performance.",
      },
      {
        title: "Smarter Supplier Decisions",
        description:
          "Historical price tracking, purchase consolidation, and warning signals when material costs rise unexpectedly.",
      },
      {
        title: "Executive AI Insights",
        description:
          "Natural-language business questions, weekly auto-reports, and actionable summaries for growth decisions.",
        spanClassName: "sm:col-span-2 lg:col-span-1",
      },
    ],
  },
  departments: {
    id: "departments",
    title: "Built for Brasaland Departments",
    items: [
      {
        title: "Restaurant Operations + Technology",
        description:
          "Connect location-level POS events and telemetry to one API so supervisors can react to service disruptions, sales drops, and stock risks in real time.",
      },
      {
        title: "Marketing + Executive Direction",
        description:
          "Replace anonymous stamp-card behavior with digital customer intelligence that powers campaign decisions and personalized product recommendations.",
      },
    ],
  },
  impact: {
    id: "impact",
    title: "How It Works",
    items: [
      {
        label: "Step 1",
        title: "Department Application",
        description:
          "Each team submits a request with location, challenge type, urgency, and expected business impact.",
      },
      {
        label: "Step 2",
        title: "AI-Prioritized Backlog",
        description:
          "Requests are validated and grouped to maximize multi-location impact across Colombia and Florida.",
      },
      {
        label: "Step 3",
        title: "Measurable Deployment",
        description:
          "Dashboards, automations, and alerts launch with clear KPIs for adoption, speed, and revenue effect.",
      },
    ],
  },
  footer: {
    name: "Brasaland Digital",
    offices: "Medellin HQ + Miami Operations Office",
    email: "digital@brasaland.example",
    phone: "+57 300 111 2233",
    phoneHref: "tel:+573001112233",
  },
};
