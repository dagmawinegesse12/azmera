"use client";

/**
 * MobileNav — fixed bottom tab bar, visible only on screens < md (768px).
 *
 * Mirrors the sidebar nav items. Each tab has an icon + label and satisfies
 * the 44×44px minimum touch-target recommendation. Safe-area padding is added
 * for iPhone home-indicator clearance.
 */

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

export function MobileNav() {
  const pathname = usePathname();
  const t = useLocale();

  const isActive = (href: string) =>
    href === "/" ? pathname === "/" : pathname.startsWith(href);

  return (
    <nav
      className="md:hidden fixed bottom-0 inset-x-0 z-50 bg-background-surface border-t border-background-border"
      style={{ paddingBottom: "env(safe-area-inset-bottom, 0px)" }}
      aria-label="Mobile navigation"
    >
      <div className="flex items-stretch h-14">
        {NAV_ITEMS.map(({ labelKey, href, icon: Icon }) => {
          const active = isActive(href);
          return (
            <Link
              key={href}
              href={href}
              className="flex-1 flex flex-col items-center justify-center gap-0.5 transition-colors"
              style={{ color: active ? "var(--accent-green)" : "var(--text-faint)" }}
              aria-current={active ? "page" : undefined}
            >
              <Icon
                className="h-[22px] w-[22px] shrink-0"
                strokeWidth={active ? 2.25 : 1.75}
                aria-hidden="true"
              />
              <span className="text-[10px] font-medium tracking-wide leading-none">
                {t.nav[labelKey]}
              </span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
