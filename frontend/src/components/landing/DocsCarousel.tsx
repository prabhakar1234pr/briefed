"use client";

import { useRef } from "react";
import Link from "next/link";
import { motion } from "motion/react";
import styles from "@/app/page.module.css";
import { articles } from "@/app/docs/articles";
import { EASE } from "./data";

export default function DocsCarousel() {
  const viewportRef = useRef<HTMLDivElement>(null);

  const scrollBy = (dir: number) => {
    viewportRef.current?.scrollBy({ left: dir * 340, behavior: "smooth" });
  };

  return (
    <section className={styles.docs} id="docs">
      <motion.div
        initial={{ opacity: 0, y: 24 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, amount: 0.3 }}
        transition={{ duration: 0.6, ease: EASE }}
      >
        <span className={styles.sectionEyebrow}>Docs &amp; guides</span>
        <h2 className={styles.sectionHeading}>
          Learn how to get the <span>most out of Bora</span>
        </h2>
        <p className={styles.sectionSub}>
          Guides, deep dives, and tips to help your team run better meetings with
          your AI teammate.
        </p>
      </motion.div>

      <div
        className={styles.docsViewport}
        ref={viewportRef}
        style={{ overflowX: "auto" }}
      >
        <div className={styles.docsTrack}>
          {articles.map((article, idx) => (
            <motion.div
              key={article.slug}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.2 }}
              transition={{ duration: 0.5, delay: (idx % 3) * 0.08, ease: EASE }}
            >
              <Link href={`/docs/${article.slug}`} className={styles.docCard}>
                <div
                  className={styles.docCardCover}
                  style={{ background: article.gradient }}
                >
                  <span>{article.emoji}</span>
                </div>
                <div className={styles.docCardBody}>
                  <span className={styles.docCardTag}>{article.tag}</span>
                  <p className={styles.docCardTitle}>{article.title}</p>
                  <p className={styles.docCardExcerpt}>{article.excerpt}</p>
                  <div className={styles.docCardMeta}>
                    <span>{article.readTime}</span>
                    <span className={styles.docCardArrow}>Read →</span>
                  </div>
                </div>
              </Link>
            </motion.div>
          ))}
        </div>
      </div>

      <div className={styles.docsControls}>
        <button
          type="button"
          className={styles.docsArrowBtn}
          onClick={() => scrollBy(-1)}
          aria-label="Previous"
        >
          ←
        </button>
        <button
          type="button"
          className={styles.docsArrowBtn}
          onClick={() => scrollBy(1)}
          aria-label="Next"
        >
          →
        </button>
      </div>
    </section>
  );
}
