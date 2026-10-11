import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { AuthBoundary } from "@/components/auth/AuthBoundary";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Brasaland Talent Pipeline Tracker",
  description: "Internal People and Culture recruitment tracker for Brasaland.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full bg-slate-50 text-slate-900 flex flex-col"><AuthBoundary>{children}</AuthBoundary></body>
    </html>
  );
}
