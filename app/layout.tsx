import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "mom.life",
  description: "The quiet operating layer for motherhood.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
