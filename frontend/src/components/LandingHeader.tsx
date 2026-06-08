"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import styles from "@/app/page.module.css";

const navItems = [
  { label: "Features", href: "/#features" },
  { label: "Pricing", href: "/#pricing" },
  { label: "Docs", href: "/#docs" },
];

export default function LandingHeader() {
  const [isScrolled, setIsScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => {
      setIsScrolled(window.scrollY > 28);
    };

    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      className={`${styles.pageHeader} ${
        isScrolled ? styles.pageHeaderScrolled : styles.pageHeaderTop
      } anim-0`}
    >
      <Link href="/" className={styles.brand} style={{ textDecoration: "none" }}>
        <span className={styles.brandIconBox}>
          <Image
            src="/assets/logo-b.png"
            alt="Agent Bora logo"
            width={40}
            height={40}
            unoptimized
            priority
            className={styles.brandIcon}
          />
        </span>
        <span>
          Agent <span className={styles.brandB}>Bora</span>
        </span>
      </Link>

      <div className={styles.headerRight}>
        <nav className={styles.flowTopNav}>
          {navItems.map((item) => (
            <Link key={item.label} href={item.href} className={styles.flowTopLink}>
              {item.label}
            </Link>
          ))}
        </nav>
        <Link href="/auth?mode=signin" className={styles.buttonSecondary}>
          Login
        </Link>
      </div>
    </header>
  );
}
