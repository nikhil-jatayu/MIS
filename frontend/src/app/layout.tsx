import type { Metadata } from "next";

import { Providers } from "@/components/providers";

import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "MIS",
    template: "%s · MIS",
  },
  description:
    "MIS — Management Information System for project, inventory, purchasing and production operations. Designed, developed and managed by JES Electronic Systems Pvt Ltd.",
  applicationName: "MIS",
  icons: {
    icon: "/mis-logo.svg",
  },
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full bg-slate-50 text-slate-900">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
