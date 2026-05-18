import type { Metadata } from "next";
import { ThemeProvider } from "next-themes";
import HealthCheck from "@/components/health-check";
import { StorageErrorHandler } from "@/components/storage-error-handler";
import { XsltWorkspaceProvider } from "@/lib/xslt-workspace-context";
import "./globals.css";
import { Plus_Jakarta_Sans } from 'next/font/google';

const defaultUrl = process.env.VERCEL_URL
  ? `https://${process.env.VERCEL_URL}`
  : "http://localhost:3000";

export const metadata: Metadata = {
  metadataBase: new URL(defaultUrl),
  title: "Invoice Rule Engine",
  description: "This is a Invoice Rule Engine",
};


const plusJakartaSans = Plus_Jakarta_Sans({
  subsets: ['latin'],
  variable: '--font-plus-jakarta',
  display: 'swap',
  weight: ['400', '500', '600', '700'],
});

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${plusJakartaSans.className} antialiased overflow-x-hidden`} suppressHydrationWarning>
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          <StorageErrorHandler />
          <XsltWorkspaceProvider>{children}</XsltWorkspaceProvider>
          <HealthCheck />
        </ThemeProvider>
      </body>
    </html>
  );
}
