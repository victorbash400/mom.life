import type { Metadata } from "next";
import { DM_Sans, Fraunces } from "next/font/google";
import "./globals.css";

const sans = DM_Sans({ subsets: ["latin"], variable: "--font-sans" });
const display = Fraunces({ subsets: ["latin"], variable: "--font-display" });

export const metadata: Metadata = {
  title: "mom.life",
  description: "The quiet operating layer for motherhood.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className={`${sans.variable} ${display.variable}`}>{children}</body>
    </html>
  );
}
