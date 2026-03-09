"use client";

import { type ReactNode } from "react";
import { Sidebar } from "./Sidebar";
import { TopNav } from "./TopNav";
import { MobileNav } from "./MobileNav";

interface DashboardShellProps {
  children: ReactNode;
}

export function DashboardShell({ children }: DashboardShellProps) {
  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* Sidebar — desktop/tablet only (hidden on mobile, see Sidebar.tsx) */}
      <Sidebar />

      {/* Content column — takes full width on mobile, remaining width on md+ */}
      <div className="flex flex-1 flex-col overflow-hidden min-w-0">
        <TopNav />

        {/*
         * Main scrollable area.
         * Mobile  (< md): p-4; bottom padding clears the 56px fixed bottom nav
         *                  + iPhone home indicator via env(safe-area-inset-bottom).
         * Desktop (≥ md): p-6; no bottom nav needed.
         */}
        <main className="flex-1 overflow-y-auto p-4 md:p-6 pb-[calc(3.5rem+env(safe-area-inset-bottom,0px))] md:pb-6">
          {children}
        </main>
      </div>

      {/* Bottom tab bar — rendered only on < md via CSS */}
      <MobileNav />
    </div>
  );
}
