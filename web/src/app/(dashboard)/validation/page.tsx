import type { Metadata } from "next";
import { ValidationDashboard } from "@/features/validation/ValidationDashboard";
import { ValidationPageHeading } from "@/features/validation/ValidationPageHeading";

export const metadata: Metadata = {
  title: "Validation · Azmera",
};

export default function ValidationPage() {
  return (
    <div className="space-y-6">
      <ValidationPageHeading />
      <ValidationDashboard />
    </div>
  );
}
