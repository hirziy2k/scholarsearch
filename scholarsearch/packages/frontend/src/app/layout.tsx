import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ScholarSearch",
  description: "Academic literature search engine with transparent ranking and regional clinical elevation",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-50 text-gray-900 antialiased">
        <header className="border-b border-gray-200 bg-white">
          <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
            <div className="flex items-center gap-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600 text-sm font-bold text-white">
                S
              </div>
              <span className="text-xl font-semibold text-gray-900">
                ScholarSearch
              </span>
            </div>
            <nav className="flex items-center gap-6 text-sm text-gray-600">
              <a href="/" className="hover:text-gray-900">Search</a>
              <a href="/saved" className="hover:text-gray-900">Saved</a>
              <a href="/history" className="hover:text-gray-900">History</a>
            </nav>
          </div>
        </header>
        <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
          {children}
        </main>
      </body>
    </html>
  );
}
