"use client";

import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import { usePathname } from "next/navigation";

export default function Navbar() {
  const { token, logout } = useAuth();
  const pathname = usePathname();

  const navLinkClass = (path: string) => {
    return `nav-link ${pathname === path ? "active" : ""}`;
  };

  return (
    <nav className="navbar">
      <div className="navbar-container">
        <Link href="/" className="navbar-brand">
          Inboxio
        </Link>
        <div className="navbar-links">
          {token ? (
            <>
              <Link href="/chat" className={navLinkClass("/chat")}>
                Chat
              </Link>
              <Link href="/profile" className={navLinkClass("/profile")}>
                Profile
              </Link>
              <Link href="/cold-email" className={navLinkClass("/cold-email")}>
                Cold Email
              </Link>
              <button onClick={logout} className="nav-link btn-logout">
                Logout
              </button>
            </>
          ) : (
            <>
              <Link href="/login" className={navLinkClass("/login")}>
                Login
              </Link>
              <Link href="/signup" className={navLinkClass("/signup")}>
                Signup
              </Link>
            </>
          )}
        </div>
      </div>
    </nav>
  );
}
