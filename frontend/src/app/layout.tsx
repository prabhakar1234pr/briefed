import type { Metadata } from "next";
import { AuthKitProvider } from "@workos-inc/authkit-nextjs/components";
import { Shell } from "@/components/Shell";
import "./globals.css";

export const metadata: Metadata = {
  title: "Briefed — AI Meeting Intelligence",
  description: "Your AI agent that joins meetings, answers questions, and never lets context slip.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className="h-full">
      <body className="min-h-full flex flex-col">
        <div className="orb orb-blue" />
        <div className="orb orb-teal" />
        <AuthKitProvider>
          <Shell>{children}</Shell>
        </AuthKitProvider>
      </body>
    </html>
  );
}
