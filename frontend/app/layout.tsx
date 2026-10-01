import "./globals.css";
import type { Metadata } from "next";
import AppShell from "../components/AppShell";

export const metadata: Metadata = {
  title: "AgriDoctor — Crop Disease Detection",
  description: "Early detection and management of crop diseases using AI-powered image analysis.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-green-50 text-gray-900">
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
