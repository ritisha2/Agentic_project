import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "ESP APM — AI Diagnostic Platform",
  description: "ESP Agentic Performance Management — AI-driven ESP well diagnostics for production operations.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="antialiased bg-[#f8f9fa] text-[#191c1d] min-h-screen flex flex-col dot-grid-bg">{children}</body>
    </html>
  );
}
