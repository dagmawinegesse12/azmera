import type { Metadata } from "next";
import { ValidationDashboard } from "@/features/validation/ValidationDashboard";

export const metadata: Metadata = {
  title: "Validation · Azmera",
};

export default function ValidationPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl sm:text-2xl font-semibold text-text-primary">Model Validation</h1>
        <p className="text-text-muted text-sm mt-1">
          Rolling-origin Heidke Skill Scores and release tier assignments for all 13 regions.
        </p>
      </div>
      <ValidationDashboard />
    </div>
  );
}
