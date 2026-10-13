import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Preluma | Light Up Before Class",
  description:
    "Prepare before class. Understand more during class. Yunnan University pre-class learning.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <a className="skip-link" href="#main">
          Skip to content
        </a>
        <div className="app-shell">
          <aside className="sidebar" aria-label="Preluma navigation">
            <div className="sidebar-shade" />
            <div className="sidebar-content">
              <Link className="brand" href="/" aria-label="Preluma home">
                <strong>Preluma</strong>
                <span>Light Up Before Class</span>
              </Link>
              <p className="sidebar-kicker">Yunnan University</p>
              <nav aria-label="Primary">
                <Link href="/">Home</Link>
                <Link href="/courses">Courses</Link>
              </nav>
              <p className="sidebar-note">
                Your full learning workspace remains available in the existing
                Streamlit app while this web experience is built.
              </p>
            </div>
          </aside>
          <main id="main" className="main-content">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
