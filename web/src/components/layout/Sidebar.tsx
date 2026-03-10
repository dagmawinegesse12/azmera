"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Home, BarChart2, Map, FlaskConical } from "lucide-react";
import { useLocale } from "@/hooks/useLocale";

interface NavItem {
  labelKey: "home" | "forecast" | "riskMap" | "validation";
  href: string;
  icon: React.ElementType;
}

const NAV_ITEMS: NavItem[] = [
  { labelKey: "home",       href: "/",           icon: Home          },
  { labelKey: "forecast",   href: "/forecast",   icon: BarChart2     },
  { labelKey: "riskMap",    href: "/map",        icon: Map           },
  { labelKey: "validation", href: "/validation", icon: FlaskConical  },
];

export function Sidebar() {
  const pathname = usePathname();
  const t = useLocale();

  const isActive = (href: string) =>
    href === "/" ? pathname === "/" : pathname.startsWith(href);

  return (
    <aside className="hidden md:flex w-56 shrink-0 flex-col border-r border-background-border bg-background-surface">
      {/* Logo */}
      <div className="flex flex-col gap-0.5 px-5 py-5">
        <span className="text-lg font-semibold tracking-tight text-text-primary">
          Azmera
        </span>
        <span className="text-xs text-text-muted">{t.nav.seasonalForecasts}</span>
      </div>

      <div className="mx-3 h-px bg-background-border" />

      {/* Navigation */}
      <nav className="flex flex-1 flex-col gap-1 px-3 py-4">
        {NAV_ITEMS.map(({ labelKey, href, icon: Icon }) => {
          const active = isActive(href);
          return (
            <Link
              key={href}
              href={href}
              className={[
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                active
                  ? "bg-background-elevated text-text-primary"
                  : "text-text-muted hover:bg-background-elevated/50 hover:text-text-secondary",
              ].join(" ")}
            >
              <Icon className="h-4 w-4 shrink-0" strokeWidth={1.75} />
              {t.nav[labelKey]}
            </Link>
          );
        })}
      </nav>

      {/* Version footer */}
      <div className="px-5 py-4">
        <span className="text-xs text-text-faint">{t.nav.version}</span>
      </div>
    </aside>
  );
}
