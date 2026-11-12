import type { Metadata } from "next";
import "./globals.css";
import { Navbar } from "@/components/Navbar";
import { SyntheticBanner } from "@/components/SyntheticBanner";
import { Providers } from "@/components/Providers";

export const metadata: Metadata = {
  title: "TerraWatch AI — Surface Change Detection",
  description: "Provider-agnostic surface change detection platform using calibrated SAR backscatter differencing",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-slate-950 text-slate-100 min-h-screen flex flex-col">
        <Providers>
          <SyntheticBanner />
          <Navbar />
          <main className="flex-1 flex flex-col">{children}</main>
        </Providers>
      </body>
    </html>
  );
}

