"use client";

// ── Zustand store hydration trigger ───────────────────────────────
// Because the selection store uses skipHydration: true, it won't read
// from localStorage during SSR. This component runs a single useEffect
// on the client after mount to pull in the persisted values — at that
// point the React tree has already committed and there is no hydration
// mismatch to trigger.

import { useEffect } from "react";
import { useSelectionStore } from "@/store/selectionStore";

export function StoreHydration() {
  useEffect(() => {
    // Trigger localStorage rehydration on the client only.
    // This is a no-op if there is nothing in storage yet.
    useSelectionStore.persist.rehydrate();
  }, []);

  // Renders nothing — pure side-effect component.
  return null;
}
