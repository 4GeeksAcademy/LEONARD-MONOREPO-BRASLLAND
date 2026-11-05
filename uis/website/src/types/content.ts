export interface NavLink {
  label: string;
  href: string;
}

export interface FeatureItem {
  title: string;
  description: string;
  spanClassName?: string;
}

export interface StepItemData {
  label: string;
  title: string;
  description: string;
}

export interface HeroContent {
  eyebrow: string;
  headline: string;
  highlight: string;
  description: string;
  primaryCta: NavLink;
  secondaryCta: NavLink;
  imageUrl: string;
  imageAlt: string;
}

export interface FooterContent {
  name: string;
  offices: string;
  email: string;
  phone: string;
  phoneHref: string;
}

export interface SectionIntro {
  id: string;
  title: string;
  description?: string;
}

export interface HeaderContent {
  brandInitials: string;
  brandName: string;
  tagline: string;
  navLinks: readonly NavLink[];
  applyCta: NavLink & { ariaLabel: string };
}

export interface FeaturesSection extends SectionIntro {
  items: readonly FeatureItem[];
}

export interface DepartmentsSection extends SectionIntro {
  items: readonly FeatureItem[];
}

export interface StepsSection extends SectionIntro {
  items: readonly StepItemData[];
}

export interface LandingContent {
  header: HeaderContent;
  hero: HeroContent;
  solution: FeaturesSection;
  departments: DepartmentsSection;
  impact: StepsSection;
  footer: FooterContent;
}
