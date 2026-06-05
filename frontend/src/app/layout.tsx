import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";
import { QueryProvider } from "@/lib/query-provider";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "AI Flywheel",
  description: "AI Flywheel — Personal Venture Operating System",
};

const navItems = [
  { href: "/", label: "Dashboard", icon: "⌂" },
  { href: "/ventures", label: "Ventures", icon: "◆" },
  { href: "/thesis", label: "Thesis", icon: "△" },
  { href: "/discovery", label: "Discovery", icon: "◎" },
  { href: "/market", label: "Market Intel", icon: "⟁" },
  { href: "/offers", label: "Offers", icon: "◈" },
  { href: "/agents", label: "Agents", icon: "⚙" },
  { href: "/experiments", label: "Experiments", icon: "⚗" },
  { href: "/reviews", label: "Reviews", icon: "✓" },
  { href: "/costs", label: "Costs", icon: "$" },
];

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} h-full`}>
      <body className="h-full flex">
        <QueryProvider>
          {/* Sidebar */}
          <aside className="fixed inset-y-0 left-0 w-64 bg-gray-900 text-white flex flex-col">
            <div className="h-16 flex items-center px-6 border-b border-gray-700">
              <h1 className="text-xl font-bold">AI Flywheel</h1>
            </div>
            <nav className="flex-1 px-4 py-4 space-y-1">
              {navItems.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className="flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium text-gray-300 hover:bg-gray-800 hover:text-white transition-colors"
                >
                  <span className="text-lg">{item.icon}</span>
                  {item.label}
                </Link>
              ))}
            </nav>
            <div className="px-4 py-3 border-t border-gray-700">
              <p className="text-xs text-gray-500">v0.1.0 | Dev Mode</p>
            </div>
          </aside>

          {/* Main content */}
          <div className="ml-64 flex-1 flex flex-col min-h-screen">
            <header className="h-16 bg-white border-b border-gray-200 flex items-center justify-between px-8">
              <h2 className="text-lg font-semibold text-gray-800">AI Flywheel Platform</h2>
              <div className="flex items-center gap-3">
                <span className="text-sm text-gray-500">Dev User</span>
                <div className="w-8 h-8 rounded-full bg-indigo-500 flex items-center justify-center text-white text-sm font-medium">D</div>
              </div>
            </header>
            <main className="flex-1 p-8 bg-gray-50">
              {children}
            </main>
          </div>
        </QueryProvider>
      </body>
    </html>
  );
}
