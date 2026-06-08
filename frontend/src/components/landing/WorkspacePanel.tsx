"use client";

import Image from "next/image";
import { motion } from "motion/react";
import styles from "@/app/page.module.css";
import {
  upcomingMeetings,
  memoryItems,
  actionItems,
  docLogos,
  platformLogos,
} from "./data";

const waveHeights = [10, 14, 22, 16, 11, 18, 26, 19, 13, 10, 15];

const reveal = {
  hidden: { opacity: 0, y: 40 },
  show: { opacity: 1, y: 0, transition: { duration: 0.6, ease: [0.22, 1, 0.36, 1] } },
};

const stagger = {
  hidden: {},
  show: { transition: { staggerChildren: 0.08 } },
};

const card = {
  hidden: { opacity: 0, y: 24, scale: 0.98 },
  show: { opacity: 1, y: 0, scale: 1, transition: { duration: 0.5, ease: [0.22, 1, 0.36, 1] } },
};

export default function WorkspacePanel() {
  return (
    <section className={styles.workspaceSection} id="workspace">
      <motion.div
        initial="hidden"
        whileInView="show"
        viewport={{ once: true, amount: 0.2 }}
        variants={reveal}
      >
        <span className={styles.sectionEyebrow}>Live workspace</span>
        <h2 className={styles.sectionHeading}>
          Watch Bora <span>work in real time</span>
        </h2>
        <p className={styles.sectionSub}>
          Context, voice, and summaries come together in one calm, always-on
          surface while your meeting happens.
        </p>
      </motion.div>

      <motion.div
        className={styles.workspace}
        initial="hidden"
        whileInView="show"
        viewport={{ once: true, amount: 0.15 }}
        variants={stagger}
        whileHover={{ y: -4 }}
        transition={{ type: "spring", stiffness: 200, damping: 24 }}
      >
        <div className={styles.workspaceHeader}>
          <p>Live Bora workspace</p>
          <span>
            <span className={styles.liveDot} /> In call
          </span>
        </div>

        <div className={styles.workspaceGrid}>
          <div className={styles.mainColumn}>
            <motion.div className={styles.statusGrid} variants={card}>
              <div className={styles.statusRow}>
                <div className={styles.statusLeft}>
                  <span className={`${styles.statusIcon} ${styles.statusIconContext}`}>
                    <Image
                      src="/assets/document-icon.png"
                      alt="Document icon"
                      width={16}
                      height={16}
                      className={styles.statusIconImage}
                    />
                  </span>
                  <div>
                    <p>Context loaded</p>
                    <span>6 docs + 2 meeting notes</span>
                  </div>
                </div>
                <div className={styles.docIcons}>
                  {docLogos.map((logo) => (
                    <Image
                      key={logo.alt}
                      src={logo.src}
                      alt={logo.alt}
                      width={18}
                      height={18}
                      className={styles.docIconImage}
                    />
                  ))}
                  <p>+3</p>
                </div>
              </div>

              <div className={styles.statusRow}>
                <div className={styles.statusLeft}>
                  <span className={`${styles.statusIcon} ${styles.statusIconVoice}`}>
                    <Image
                      src="/assets/voice-icon.png"
                      alt="Voice icon"
                      width={16}
                      height={16}
                      className={styles.statusIconImage}
                    />
                  </span>
                  <div>
                    <p>Voice ready</p>
                    <span>Realtime response on</span>
                  </div>
                </div>
                <div className={styles.waveform}>
                  {waveHeights.map((height, idx) => (
                    <span
                      key={`${height}-${idx}`}
                      className={styles.waveBar}
                      style={{ height, animationDelay: `${idx * 0.1}s` }}
                    />
                  ))}
                </div>
              </div>

              <div className={styles.statusRow}>
                <div className={styles.statusLeft}>
                  <span className={`${styles.statusIcon} ${styles.statusIconSummary}`}>
                    <Image
                      src="/assets/pencil-icon.png"
                      alt="Pencil icon"
                      width={16}
                      height={16}
                      className={styles.statusIconImage}
                    />
                  </span>
                  <div>
                    <p>Summary drafting</p>
                    <span>Actions captured instantly</span>
                  </div>
                </div>
                <div className={styles.progress}>
                  <div className={styles.progressBar}>
                    <motion.span
                      initial={{ width: 0 }}
                      whileInView={{ width: "76%" }}
                      viewport={{ once: true }}
                      transition={{ duration: 1, delay: 0.3, ease: "easeOut" }}
                    />
                  </div>
                  <p>76%</p>
                </div>
              </div>
            </motion.div>

            <motion.div className={styles.upcoming} variants={card}>
              <div className={styles.upcomingHead}>
                <p>Upcoming meetings</p>
                <span>View calendar</span>
              </div>

              {upcomingMeetings.map((meeting) => (
                <div key={meeting.title} className={styles.meetingRow}>
                  <div className={styles.meetingLeft}>
                    <span
                      className={`${styles.platform} ${
                        meeting.platform === "meet"
                          ? styles.platformMeet
                          : meeting.platform === "zoom"
                          ? styles.platformZoom
                          : styles.platformTeams
                      }`}
                    >
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
                  <div className={styles.meetingRight}>
                    <div className={styles.avatars}>
                      {meeting.avatars.map((src, idx) => (
                        <Image
                          key={`${meeting.title}-${src}`}
                          src={src}
                          alt={`${meeting.title} attendee ${idx + 1}`}
                          width={22}
                          height={22}
                          className={`${styles.avatarImage} ${
                            idx === 0 ? styles.avatarFirst : ""
                          }`}
                        />
                      ))}
                      <p>{meeting.attendees}</p>
                    </div>
                    <button type="button">Join</button>
                  </div>
                </div>
              ))}
            </motion.div>
          </div>

          <div className={styles.sideColumn}>
            <motion.div className={styles.sideCard} variants={card}>
              <p className={styles.sideTitle}>Agent status</p>
              <span className={styles.sideText}>
                Agent Bora is ready to join meetings
              </span>
              <div className={styles.online}>
                <span />
                <p>Active</p>
              </div>
            </motion.div>

            <motion.div className={styles.sideCard} variants={card}>
              <p className={styles.sideTitle}>Recent memory</p>
              <div className={styles.list}>
                {memoryItems.map((memory) => (
                  <div key={memory.text} className={styles.listItem}>
                    <p>{memory.text}</p>
                    <span>{memory.age}</span>
                  </div>
                ))}
              </div>
              <button type="button" className={styles.linkButton}>
                View all memory
              </button>
            </motion.div>

            <motion.div className={styles.sideCard} variants={card}>
              <p className={styles.sideTitle}>Generated actions</p>
              <div className={styles.list}>
                {actionItems.map((action) => (
                  <div key={action} className={styles.actionItem}>
                    <span />
                    <p>{action}</p>
                  </div>
                ))}
              </div>
              <button type="button" className={styles.linkButton}>
                View all actions
              </button>
            </motion.div>
          </div>
        </div>
      </motion.div>
    </section>
  );
}
