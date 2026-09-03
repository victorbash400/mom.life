import type { Metadata } from "next";
import { Bodoni_Moda, Cormorant_Garamond, DM_Sans } from "next/font/google";
import "./globals.css";

const sans = DM_Sans({ subsets: ["latin"], variable: "--font-sans" });
const display = Bodoni_Moda({ subsets: ["latin"], variable: "--font-display", weight: ["400", "500", "600"] });
const life = Cormorant_Garamond({ subsets: ["latin"], variable: "--font-life", style: ["italic"], weight: ["400", "500"] });

export const metadata: Metadata = {
  title: "mom.life",
  description: "The quiet operating layer for motherhood.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className={`${sans.variable} ${display.variable} ${life.variable}`}>{children}</body>
    </html>
  );
}
