import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { QueryProvider } from "@/components/providers/QueryProvider";
import { StoreHydration } from "@/components/providers/StoreHydration";

const inter = Inter({
  variable: "--font-sans",
  subsets: ["latin"],
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "Azmera — Ethiopian Seasonal Rainfall Forecast",
  description:
    "Probabilistic seasonal rainfall forecasts for Ethiopia's 13 administrative regions, built on statistically validated logistic regression models and CHIRPS satellite rainfall data.",
  keywords: ["Ethiopia", "rainfall forecast", "seasonal climate", "ENSO", "Kiremt", "Belg"],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body
        className={`${inter.variable} ${jetbrainsMono.variable} antialiased bg-background text-text-primary`}
      >
        <QueryProvider>
          <StoreHydration />
          {children}
        </QueryProvider>
      </body>
    </html>
  );
}
