import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "AgriDoctor — Crop Disease Detection",
  description: "SIH26131: Early detection and management of crop diseases"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-green-50 text-gray-900">{children}</body>
    </html>
  );
}
