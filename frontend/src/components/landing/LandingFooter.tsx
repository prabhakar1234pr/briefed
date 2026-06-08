import Image from "next/image";
import Link from "next/link";
import styles from "@/app/page.module.css";
import { articles } from "@/app/docs/articles";

const productLinks = [
  { label: "Features", href: "/#features" },
  { label: "Live workspace", href: "/#workspace" },
  { label: "Pricing", href: "/#pricing" },
  { label: "Create your agent", href: "/auth?mode=signup" },
];

const companyLinks = [
  { label: "About", href: "/#features" },
  { label: "Careers", href: "/#features" },
  { label: "Contact", href: "/#features" },
  { label: "Login", href: "/auth?mode=signin" },
];

const legalLinks = [
  { label: "Privacy", href: "/docs/security-and-privacy" },
  { label: "Terms", href: "/docs/security-and-privacy" },
  { label: "Security", href: "/docs/security-and-privacy" },
];

const socials = [
  { label: "X", href: "https://x.com", glyph: "𝕏" },
  { label: "LinkedIn", href: "https://linkedin.com", glyph: "in" },
  { label: "GitHub", href: "https://github.com", glyph: "" },
];

export default function LandingFooter() {
  return (
    <footer className={styles.footer}>
      <div className={styles.footerTop}>
        <div className={styles.footerBrandCol}>
          <Link href="/" className={styles.brand} style={{ textDecoration: "none" }}>
            <span className={styles.brandIconBox}>
              <Image
                src="/assets/logo-b.png"
                alt="Agent Bora logo"
                width={40}
                height={40}
                unoptimized
                className={styles.brandIcon}
              />
            </span>
            <span>
              Agent <span className={styles.brandB}>Bora</span>
            </span>
          </Link>
          <p className={styles.footerTagline}>
            Your AI teammate before, during, and after every meeting. Bora joins,
            speaks, remembers, and turns conversations into action.
          </p>
          <div className={styles.footerSocials}>
            {socials.map((social) => (
              <a
                key={social.label}
                href={social.href}
                target="_blank"
                rel="noreferrer"
                className={styles.footerSocial}
                aria-label={social.label}
              >
                {social.glyph}
              </a>
            ))}
          </div>
        </div>

        <div className={styles.footerLinkGroups}>
          <div className={styles.footerCol}>
            <p className={styles.footerColTitle}>Product</p>
            {productLinks.map((link) => (
              <Link key={link.label} href={link.href} className={styles.footerLink}>
                {link.label}
              </Link>
            ))}
          </div>

          <div className={styles.footerCol}>
            <p className={styles.footerColTitle}>Resources</p>
            <Link href="/#docs" className={styles.footerLink}>
              Docs &amp; guides
            </Link>
            {articles.slice(0, 3).map((article) => (
              <Link
                key={article.slug}
                href={`/docs/${article.slug}`}
                className={styles.footerLink}
              >
                {article.title}
              </Link>
            ))}
          </div>

          <div className={styles.footerCol}>
            <p className={styles.footerColTitle}>Company</p>
            {companyLinks.map((link) => (
              <Link key={link.label} href={link.href} className={styles.footerLink}>
                {link.label}
              </Link>
            ))}
          </div>

          <div className={styles.footerCol}>
            <p className={styles.footerColTitle}>Legal</p>
            {legalLinks.map((link) => (
              <Link key={link.label} href={link.href} className={styles.footerLink}>
                {link.label}
              </Link>
            ))}
          </div>
        </div>
      </div>

      <div className={styles.footerBottom}>
        <p>© {new Date().getFullYear()} Agent Bora. All rights reserved.</p>
        <div className={styles.footerBottomLinks}>
          <Link href="/docs/security-and-privacy">Privacy</Link>
          <Link href="/docs/security-and-privacy">Terms</Link>
          <span className={styles.footerStatus}>
            <span className={styles.footerStatusDot} /> All systems operational
          </span>
        </div>
      </div>
    </footer>
  );
}
