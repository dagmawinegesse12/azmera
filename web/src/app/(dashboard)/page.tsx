import { redirect } from "next/navigation";

// Dashboard root → redirect to the forecast page
export default function DashboardIndexPage() {
  redirect("/forecast");
}
