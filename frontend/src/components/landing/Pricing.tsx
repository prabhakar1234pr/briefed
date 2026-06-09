"use client";

import { useState } from "react";
import Link from "next/link";
import { motion } from "motion/react";
import styles from "@/app/page.module.css";
import { EASE } from "./data";

type Tier = {
  name: string;
  monthly: number;
  annual: number;
  note: string;
  cta: string;
  featured?: boolean;
  features: string[];
};

const tiers: Tier[] = [
  {
    name: "Basic",
    monthly: 0,
    annual: 0,
    note: "Free forever",
    cta: "Get started",
    features: [
      "1 AI agent",
      "Up to 5 meetings / month",
      "Live transcription",
      "Basic meeting summaries",
      "7-day memory history",
    ],
  },
  {
    name: "Pro",
    monthly: 20,
    annual: 16,
    note: "For growing teams",
    cta: "Start Pro",
    featured: true,
    features: [
      "Unlimited agents",
      "Unlimited meetings",
      "Speaks live in meetings",
      "Full searchable memory",
      "Actions & integrations (Asana, Linear, Slack)",
      "Priority support",
    ],
  },
  {
    name: "Premium",
    monthly: 40,
    annual: 35,
    note: "For scaling orgs",
    cta: "Start Premium",
    features: [
      "Everything in Pro",
      "Advanced automations",
      "Custom agent personas",
      "Enterprise SSO & roles",
      "Unlimited memory retention",
      "Dedicated success manager",
    ],
  },
];

export default function Pricing() {
  const [annual, setAnnual] = useState(true);

  return (
    <section className={styles.pricing} id="pricing">
      <motion.div
        initial={{ opacity: 0, y: 24 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, amount: 0.3 }}
        transition={{ duration: 0.6, ease: EASE }}
      >
        <span className={styles.sectionEyebrow}>Pricing</span>
        <h2 className={styles.sectionHeading}>
          Simple plans that <span>scale with you</span>
        </h2>
        <p className={styles.sectionSub}>
          Start free. Upgrade when your team is ready for live participation,
          memory, and automations.
        </p>
      </motion.div>

      <div className={styles.pricingToggleWrap}>
        <div className={styles.pricingToggle}>
          <button
            type="button"
            className={`${styles.toggleBtn} ${!annual ? styles.toggleBtnActive : ""}`}
            onClick={() => setAnnual(false)}
          >
            Monthly
          </button>
          <button
            type="button"
            className={`${styles.toggleBtn} ${annual ? styles.toggleBtnActive : ""}`}
            onClick={() => setAnnual(true)}
          >
            Annual
            <span className={styles.toggleSave}>Save 20%</span>
          </button>
        </div>
      </div>

      <div className={styles.pricingGrid}>
        {tiers.map((tier, idx) => {
          const price = annual ? tier.annual : tier.monthly;
          return (
            <motion.div
              key={tier.name}
              className={`${styles.priceCard} ${tier.featured ? styles.priceCardFeatured : ""}`}
              initial={{ opacity: 0, y: 40 }}
              whileInView={{ opacity: 1, y: tier.featured ? -8 : 0 }}
              viewport={{ once: true, amount: 0.2 }}
              transition={{ duration: 0.55, delay: idx * 0.1, ease: EASE }}
            >
              {tier.featured && <span className={styles.priceTag}>Most popular</span>}
              <p className={styles.priceName}>{tier.name}</p>
              <div className={styles.priceAmountRow}>
                <span className={styles.priceAmount}>${price}</span>
                <span className={styles.pricePer}>{price === 0 ? "" : "/ month"}</span>
              </div>
              <p className={styles.priceNote}>
                {price === 0
                  ? tier.note
                  : annual
                  ? `Billed annually ($${tier.annual * 12}/yr) · ${tier.note}`
                  : `Billed monthly · ${tier.note}`}
              </p>
              <Link
                href="/auth?mode=signup"
                className={`${tier.featured ? styles.buttonPrimary : styles.buttonSecondary} ${styles.priceCta}`}
              >
                {tier.cta}
              </Link>
              <div className={styles.priceFeatures}>
                {tier.features.map((feature) => (
                  <div key={feature} className={styles.priceFeature}>
                    <span className={styles.priceCheck}>✓</span>
                    {feature}
                  </div>
                ))}
              </div>
            </motion.div>
          );
        })}
      </div>
    </section>
  );
}
