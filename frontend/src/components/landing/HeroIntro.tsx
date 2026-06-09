"use client";

import Link from "next/link";
import { motion } from "motion/react";
import styles from "@/app/page.module.css";
import { EASE } from "./data";

const container = {
  hidden: {},
  show: {
    transition: { staggerChildren: 0.09, delayChildren: 0.05 },
  },
};

const item = {
  hidden: { opacity: 0, y: 18 },
  show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: EASE } },
};

const points = ["Joins meetings", "Remembers everything", "Takes action"];

export default function HeroIntro() {
  return (
    <motion.section
      className={styles.hero}
      variants={container}
      initial="hidden"
      animate="show"
    >
      <motion.p className={styles.badge} variants={item}>
        Meeting intelligence for teams
      </motion.p>

      <motion.h1 className={styles.title} variants={item}>
        <span className={styles.titleLinePrimary}>Your AI teammate</span>
        <span className={styles.timelineLine}>
          <span className={styles.beforeWord}>before</span>,{" "}
          <span className={styles.duringWord}>during</span>, and{" "}
          <span className={styles.afterWord}>after</span>
        </span>
        <span className={styles.titleLineFinal}>every meeting.</span>
      </motion.h1>

      <motion.p className={styles.subtitle} variants={item}>
        Agent Bora helps your team run better meetings by combining your context,
        speaking live when needed, and delivering clear follow-up summaries.
      </motion.p>

      <motion.div className={styles.actions} variants={item}>
        <Link href="/auth?mode=signup" className={styles.buttonPrimary}>
          Create your agent
        </Link>
      </motion.div>

      <motion.div className={styles.points} variants={item}>
        {points.map((point) => (
          <div key={point} className={styles.point}>
            <span className={styles.pointDot} />
            <p>{point}</p>
          </div>
        ))}
      </motion.div>
    </motion.section>
  );
}
