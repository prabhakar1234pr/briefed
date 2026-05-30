"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import styles from "@/app/page.module.css";

const navItems = ["Features", "Use Cases", "Pricing", "Docs", "Resources"];

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
      className={`${styles.flowTopHeader} ${styles.pageHeader} ${
        isScrolled ? styles.pageHeaderScrolled : styles.pageHeaderTop
      } anim-0`}
    >
      <div className={styles.brand}>
        <span className={styles.brandIconBox}>
          <Image
            src="/assets/favicon.png"
            alt="Agent Bora mark"
            width={34}
            height={34}
            unoptimized
            priority
            className={styles.brandIcon}
            style={{ borderRadius: 10 }}
          />
        </span>
        <span>
          Agent <span className={styles.brandB}>B</span>ora
        </span>
      </div>
      <nav className={styles.flowTopNav}>
        {navItems.map((item) => (
          <Link key={item} href="/" className={styles.flowTopLink}>
            {item}
          </Link>
        ))}
      </nav>
    </header>
  );
}
