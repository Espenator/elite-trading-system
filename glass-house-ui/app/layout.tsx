import type { Metadata } from "next";
import "../src/app/aurora.css";

export const metadata: Metadata = {
  title: "Elite Trading Glass House",
  description: "Real-time Signal Intelligence System",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">
        {children}
      </body>
    </html>
  );
}
