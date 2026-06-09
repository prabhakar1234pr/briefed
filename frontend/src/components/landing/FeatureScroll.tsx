"use client";

import Image from "next/image";
import { motion } from "motion/react";
import styles from "@/app/page.module.css";
import { upcomingMeetings, platformLogos, flowActionList, EASE } from "./data";

const panelHeader = {
  hidden: { opacity: 0, y: 30 },
  show: { opacity: 1, y: 0, transition: { duration: 0.6, ease: EASE } },
};

const panelCard = {
  hidden: { opacity: 0, y: 60, scale: 0.96 },
  show: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { duration: 0.7, ease: EASE, delay: 0.1 },
  },
};

function PanelHead({
  index,
  icon,
  iconAlt,
  title,
  desc,
}: {
  index: string;
  icon: string;
  iconAlt: string;
  title: string;
  desc: string;
}) {
  return (
    <motion.div variants={panelHeader} style={{ display: "contents" }}>
      <span className={styles.featureStepRow}>
        <span className={styles.featureStepBadge}>
          <Image src={icon} alt={iconAlt} width={22} height={22} />
        </span>
        <span className={styles.featureStepIndex}>STEP {index}</span>
      </span>
      <h3 className={styles.featureTitle}>{title}</h3>
      <p className={styles.featureDesc}>{desc}</p>
    </motion.div>
  );
}

export default function FeatureScroll() {
  return (
    <div className={styles.features} id="features">
      {/* 01 — Joins meetings */}
      <motion.section
        className={styles.featurePanel}
        initial="hidden"
        whileInView="show"
        viewport={{ once: true, amount: 0.4 }}
        variants={{ hidden: {}, show: { transition: { staggerChildren: 0.12 } } }}
      >
        <PanelHead
          index="01"
          icon="/assets/google-meet-logo.png"
          iconAlt="Meeting"
          title="Joins your meetings automatically"
          desc="AgentBora hops onto Google Meet, Zoom, or Microsoft Teams right on time — no link juggling, no reminders."
        />
        <motion.div className={styles.featureCard} variants={panelCard}>
          <p className={styles.featureCardTitle}>Upcoming meetings</p>
          {upcomingMeetings.map((meeting) => (
            <div key={meeting.title} className={styles.meetingRow}>
              <div className={styles.meetingLeft}>
                <span className={styles.platform}>
                  <Image
                    src={platformLogos[meeting.platform].src}
                    alt={platformLogos[meeting.platform].alt}
                    width={16}
                    height={16}
                    className={styles.platformLogo}
                  />
                </span>
                <div>
                  <p>{meeting.title}</p>
                  <span>{meeting.time}</span>
                </div>
              </div>
              <div className={styles.avatars}>
                {meeting.avatars.map((src, idx) => (
                  <Image
                    key={`${meeting.title}-${src}`}
                    src={src}
                    alt={`Attendee ${idx + 1}`}
                    width={22}
                    height={22}
                    className={`${styles.avatarImage} ${idx === 0 ? styles.avatarFirst : ""}`}
                  />
                ))}
                <p>{meeting.attendees}</p>
              </div>
            </div>
          ))}
        </motion.div>
      </motion.section>

      {/* 02 — Speaks when needed */}
      <motion.section
        className={styles.featurePanel}
        initial="hidden"
        whileInView="show"
        viewport={{ once: true, amount: 0.4 }}
        variants={{ hidden: {}, show: { transition: { staggerChildren: 0.12 } } }}
      >
        <PanelHead
          index="02"
          icon="/assets/voice-icon.png"
          iconAlt="Voice"
          title="Speaks up when it can help"
          desc="When a question comes up or context is missing, AgentBora answers out loud — grounded in your team's real history."
        />
        <motion.div className={styles.featureCard} variants={panelCard}>
          <div className={styles.featureCardTitleRow}>
            <p className={styles.featureCardTitle}>AgentBora is speaking...</p>
            <div className={styles.speakGlyph}>
              {Array.from({ length: 6 }).map((_, i) => (
                <span key={`speak-${i}`} style={{ animationDelay: `${i * 0.05}s` }} />
              ))}
            </div>
          </div>
          <div className={styles.speechBody}>
            Based on the roadmap discussion last week, the team agreed to prioritize
            enterprise SSO before mobile improvements.
          </div>
          <div className={styles.voiceRow}>
            <div className={styles.voiceGroup}>
              {["/assets/headshot-1.jpg", "/assets/headshot-2.jpg"].map((src) => (
                <Image
                  key={src}
                  src={src}
                  alt="Participant"
                  width={26}
                  height={26}
                  className={styles.voiceFace}
                />
              ))}
            </div>
            <Image
              src="/assets/logo-b.png"
              alt="Bora"
              width={40}
              height={40}
              unoptimized
              className={styles.voiceBora}
            />
            <div className={styles.voiceGroup}>
              {["/assets/headshot-4.jpg", "/assets/headshot-5.jpg"].map((src) => (
                <Image
                  key={src}
                  src={src}
                  alt="Participant"
                  width={26}
                  height={26}
                  className={styles.voiceFace}
                />
              ))}
            </div>
          </div>
          <div className={styles.miniWave}>
            {Array.from({ length: 18 }).map((_, i) => (
              <span key={`wave-${i}`} style={{ animationDelay: `${i * 0.06}s` }} />
            ))}
          </div>
        </motion.div>
      </motion.section>

      {/* 03 — Remembers everything */}
      <motion.section
        className={styles.featurePanel}
        initial="hidden"
        whileInView="show"
        viewport={{ once: true, amount: 0.4 }}
        variants={{ hidden: {}, show: { transition: { staggerChildren: 0.12 } } }}
      >
        <PanelHead
          index="03"
          icon="/assets/document-icon.png"
          iconAlt="Memory"
          title="Remembers everything for you"
          desc="Every meeting and document becomes searchable memory. Ask a question and get the decision, the owner, and the context."
        />
        <motion.div className={styles.featureCard} variants={panelCard}>
          <p className={styles.featureCardTitle}>Ask anything from your memory</p>
          <div className={styles.searchBox}>
            What did we decide about pricing last month?
          </div>
          <div className={styles.memorySnippet}>
            <p>From Product Review</p>
            <span>
              We decided to move to tiered pricing with a new enterprise plan.
              Approved by Sarah.
            </span>
          </div>
          <button type="button" className={styles.featureLinkButton}>
            View full memory
          </button>
        </motion.div>
      </motion.section>

      {/* 04 — Takes action */}
      <motion.section
        className={styles.featurePanel}
        initial="hidden"
        whileInView="show"
        viewport={{ once: true, amount: 0.4 }}
        variants={{ hidden: {}, show: { transition: { staggerChildren: 0.12 } } }}
      >
        <PanelHead
          index="04"
          icon="/assets/asana-logo-v2.png"
          iconAlt="Action"
          title="Turns talk into action"
          desc="AgentBora creates tasks, updates your tools, and follows through — so outcomes happen without anyone chasing them."
        />
        <motion.div className={styles.featureCard} variants={panelCard}>
          <p className={styles.featureCardTitle}>Actions generated</p>
          {flowActionList.map((action) => (
            <div key={action.title} className={styles.actionRow}>
              <div className={styles.actionRowLeft}>
                <span className={styles.actionLogoBox}>
                  <Image src={action.icon} alt={action.iconAlt} width={15} height={15} />
                </span>
                <div className={styles.actionRowText}>
                  <p>{action.title}</p>
                  <span>{action.subtitle}</span>
                </div>
              </div>
              <strong>{action.status}</strong>
            </div>
          ))}
          <button type="button" className={styles.featureLinkButton}>
            View all actions
          </button>
        </motion.div>
      </motion.section>
    </div>
  );
}
