import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Palona Chat",
  description: "Minimal chat UI with product grid",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
