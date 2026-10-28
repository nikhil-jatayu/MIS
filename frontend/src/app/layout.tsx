import type { Metadata } from "next";

import { Providers } from "@/components/providers";

import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "JES MIS",
    template: "%s · JES MIS",
  },
  description:
    "R&D and Production Management Information System for JES Electronics Systems Pvt Ltd.",
  applicationName: "JES MIS",
  icons: {
    icon: "/jes-logo.png",
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
