import type { Metadata } from "next";
import { AuthProvider } from "@/context/AuthContext";
import Navbar from "@/components/Navbar";
import "./globals.css";

export const metadata: Metadata = {
  title: "Inboxio",
  description: "Personal Gmail Intelligence Agent",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>
          <Navbar />
          <main className="main-content">
            {children}
          </main>
        </AuthProvider>
      </body>
    </html>
  );
}
