import Image from "next/image";
import Link from "next/link";
import { redirect } from "next/navigation";
import { getServerUser } from "@/lib/auth";
import LandingHeader from "@/components/LandingHeader";
import styles from "./page.module.css";

const upcomingMeetings = [
  {
    title: "Product Strategy Call",
    time: "10:30 AM - 11:30 AM",
    platform: "meet",
    attendees: "+3",
    avatars: [
      "/assets/headshot-1.jpg",
      "/assets/headshot-2.jpg",
      "/assets/headshot-3.webp",
    ],
  },
  {
    title: "Marketing Sync",
    time: "1:00 PM - 2:00 PM",
    platform: "zoom",
    attendees: "+2",
    avatars: [
      "/assets/headshot-4.jpg",
      "/assets/headshot-5.jpg",
      "/assets/headshot-6.jpg",
    ],
  },
  {
    title: "Engineering Review",
    time: "4:00 PM - 5:00 PM",
    platform: "teams",
    attendees: "+5",
    avatars: [
      "/assets/headshot-7.jpg",
      "/assets/headshot-8.jpg",
      "/assets/headshot-9.jpg",
    ],
  },
];

const memoryItems = [
  { text: "Discussed Q3 roadmap", age: "2h ago" },
  { text: "Budget approved", age: "Yesterday" },
  { text: "Launch date finalized", age: "2 days ago" },
];

const actionItems = [
  "Review proposal deck",
  "Send follow-up email",
  "Update product roadmap",
];

const docLogos = [
  { src: "/assets/notion-logo.png", alt: "Notion logo" },
  { src: "/assets/gmail-logo.png", alt: "Gmail logo" },
  { src: "/assets/pdf-logo.png", alt: "PDF logo" },
];

const platformLogos: Record<string, { src: string; alt: string }> = {
  meet: { src: "/assets/google-meet-logo.png", alt: "Google Meet logo" },
  zoom: { src: "/assets/zoom-logo.png", alt: "Zoom logo" },
  teams: { src: "/assets/teams-logo.png", alt: "Microsoft Teams logo" },
};

const flowActionList = [
  {
    title: "Create task in Asana",
    subtitle: "Review pricing deck",
    status: "Done",
    icon: "/assets/asana-logo-v2.png",
    iconAlt: "Asana logo",
  },
  {
    title: "Send follow-up email",
    subtitle: "To: stakeholders",
    status: "Done",
    icon: "/assets/gmail-logo.png",
    iconAlt: "Email logo",
    isWide: true,
  },
  {
    title: "Update roadmap in Linear",
    subtitle: "Enterprise SSO priority",
    status: "Done",
    icon: "/assets/linear-logo.png",
    iconAlt: "Linear logo",
  },
  {
    title: "Share notes in #product",
    subtitle: "Sent to Slack",
    status: "Done",
    icon: "/assets/slack-logo.png",
    iconAlt: "Slack logo",
  },
];

const flowFooterItems = [
  {
    icon: "✶",
    title: "Active participant",
    subtitle: "Engages when it matters",
  },
  {
    iconSrc: "/assets/document-icon.png",
    iconAlt: "Document icon",
    title: "Your context",
    subtitle: "Grounded in your data",
  },
  {
    iconSrc: "/assets/enterprise-ready-icon.png",
    iconAlt: "Enterprise ready icon",
    title: "Enterprise ready",
    subtitle: "Secure & private",
  },
  {
    iconSrc: "/assets/always-improving-icon.png",
    iconAlt: "Always improving icon",
    title: "Always improving",
    subtitle: "Gets smarter over time",
  },
];

export default async function LandingPage() {
  const user = await getServerUser();
  if (user) {
    redirect("/home");
  }

  return (
    <div className={styles.page}>
      <LandingHeader />

      <section className={`${styles.hero} anim-1`}>
        <div className={styles.left}>
          <p className={styles.badge}>Meeting intelligence for teams</p>
          <h1 className={styles.title}>
            <span className={styles.titleLinePrimary}>Your AI teammate</span>
            <span className={styles.timelineLine}>
              <span className={styles.beforeWord}>before</span>,{" "}
              <span className={styles.duringWord}>during</span>, and{" "}
              <span className={styles.afterWord}>after</span>
            </span>
            <span className={styles.titleLineFinal}>every meeting.</span>
          </h1>
          <p className={styles.subtitle}>
            Agent Bora helps your team run better meetings by combining your
            context, speaking live when needed, and delivering clear follow-up
            summaries.
          </p>
          <div className={styles.actions}>
            <Link href="/auth?mode=signup" className={styles.buttonPrimary}>
              Create your agent
            </Link>
            <Link
              href="/auth?mode=signin"
              className={`${styles.buttonSecondary} ${styles.signinMain}`}
            >
              Login
            </Link>
          </div>
          <div className={styles.points}>
            <div className={styles.point}>
              <span className={styles.pointDot} />
              <p>Joins meetings</p>
            </div>
            <div className={styles.point}>
              <span className={styles.pointDot} />
              <p>Remembers everything</p>
            </div>
            <div className={styles.point}>
              <span className={styles.pointDot} />
              <p>Takes action</p>
            </div>
          </div>
        </div>

        <div className={styles.workspace}>
          <div className={styles.workspaceHeader}>
            <p>Live Bora workspace</p>
            <span>In call</span>
          </div>

          <div className={styles.workspaceGrid}>
            <div className={styles.mainColumn}>
              <div className={styles.statusGrid}>
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
                    {[10, 14, 22, 16, 11, 18, 26, 19, 13, 10, 15].map(
                      (height, idx) => (
                        <span
                          key={`${height}-${idx}`}
                          className={styles.waveBar}
                          style={{ height, animationDelay: `${idx * 0.1}s` }}
                        />
                      )
                    )}
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
                      <span />
                    </div>
                    <p>76%</p>
                  </div>
                </div>
              </div>

              <div className={styles.upcoming}>
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
              </div>
            </div>

            <div className={styles.sideColumn}>
              <div className={styles.sideCard}>
                <p className={styles.sideTitle}>Agent status</p>
                <span className={styles.sideText}>
                  Agent Bora is ready to join meetings
                </span>
                <div className={styles.online}>
                  <span />
                  <p>Active</p>
                </div>
              </div>

              <div className={styles.sideCard}>
                <p className={styles.sideTitle}>Recent memory</p>
                <div className={styles.list}>
                  {memoryItems.map((item) => (
                    <div key={item.text} className={styles.listItem}>
                      <p>{item.text}</p>
                      <span>{item.age}</span>
                    </div>
                  ))}
                </div>
                <button type="button" className={styles.linkButton}>
                  View all memory
                </button>
              </div>

              <div className={styles.sideCard}>
                <p className={styles.sideTitle}>Generated actions</p>
                <div className={styles.list}>
                  {actionItems.map((item) => (
                    <div key={item} className={styles.actionItem}>
                      <span />
                      <p>{item}</p>
                    </div>
                  ))}
                </div>
                <button type="button" className={styles.linkButton}>
                  View all actions
                </button>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className={`${styles.flowSection} anim-2`}>
        <div className={styles.flowHeroCopy}>
          <h2>
            From <span>meeting</span> to meaningful <span>outcomes.</span>
          </h2>
          <p>
            AgentBora is more than a notetaker - it is an AI teammate that joins,
            speaks, remembers, and acts.
          </p>
        </div>

        <div className={styles.flowColumns}>
          <article className={styles.flowColumn}>
            <div className={styles.flowStepTrack}>
              <span className={`${styles.flowStepBadge} ${styles.flowStepBadgeVideo}`}>
                <Image
                  src="/assets/google-meet-logo.png"
                  alt="Meeting logo"
                  width={16}
                  height={16}
                  className={styles.flowStepBadgeImage}
                />
              </span>
              <span className={styles.flowStepIndex}>01</span>
              <span className={styles.flowStepLine} />
              <span className={styles.flowStepArrow}>→</span>
            </div>
            <h3>Joins Meetings</h3>
            <p>
              AgentBora automatically joins your meetings on Google Meet, Zoom, or
              Microsoft Teams.
            </p>
            <div className={styles.flowCard}>
              <p className={styles.flowCardTitle}>Upcoming Meetings</p>
              {upcomingMeetings.map((meeting) => (
                <div key={`flow-${meeting.title}`} className={styles.flowMeetingRow}>
                  <div className={styles.flowMeetingLeft}>
                    <span className={styles.flowMeetingPlatform}>
                      <Image
                        src={platformLogos[meeting.platform].src}
                        alt={platformLogos[meeting.platform].alt}
                        width={14}
                        height={14}
                      />
                    </span>
                    <div>
                      <p>{meeting.title}</p>
                      <span>{meeting.time}</span>
                    </div>
                  </div>
                  <div className={styles.flowMeetingFaces}>
                    {meeting.avatars.slice(0, 3).map((src, idx) => (
                      <Image
                        key={`flow-face-${meeting.title}-${src}`}
                        src={src}
                        alt={`Meeting attendee ${idx + 1}`}
                        width={18}
                        height={18}
                        className={styles.flowFace}
                      />
                    ))}
                    <span className={styles.flowMeetingCount}>{meeting.attendees}</span>
                  </div>
                </div>
              ))}
            </div>
            <div className={styles.flowMiniCard}>
              <div className={styles.flowMiniText}>
                <p>AgentBora is joining...</p>
                <span>Product Strategy Call</span>
              </div>
              <span className={styles.flowMiniStatusWave} aria-hidden="true" />
            </div>
          </article>

          <article className={styles.flowColumn}>
            <div className={styles.flowStepTrack}>
              <span className={`${styles.flowStepBadge} ${styles.flowStepBadgeChat}`}>
                <Image
                  src="/assets/voice-icon.png"
                  alt="Voice logo"
                  width={16}
                  height={16}
                  className={styles.flowStepBadgeImage}
                />
              </span>
              <span className={styles.flowStepIndex}>02</span>
              <span className={styles.flowStepLine} />
              <span className={styles.flowStepArrow}>→</span>
            </div>
            <h3>Speaks When Needed</h3>
            <p>
              AgentBora speaks up in the meeting when it can help answer questions,
              provide updates, or bring clarity.
            </p>
            <div className={styles.flowCard}>
              <div className={styles.flowCardTitleRow}>
                <p className={styles.flowCardTitle}>AgentBora is speaking...</p>
                <div className={styles.flowSpeakGlyph}>
                  {Array.from({ length: 6 }).map((_, i) => (
                    <span key={`speak-glyph-${i}`} style={{ animationDelay: `${i * 0.05}s` }} />
                  ))}
                </div>
              </div>
              <div className={styles.flowSpeechBody}>
                Based on the roadmap discussion last week, the team agreed to
                prioritize enterprise SSO before mobile improvements.
              </div>
              <div className={styles.flowVoiceRow}>
                <div className={styles.flowVoiceGroup}>
                  {["/assets/headshot-1.jpg", "/assets/headshot-2.jpg"].map((src, idx) => (
                    <Image
                      key={`voice-left-${src}`}
                      src={src}
                      alt={`Left participant ${idx + 1}`}
                      width={24}
                      height={24}
                      className={styles.flowVoiceFace}
                    />
                  ))}
                </div>
                <Image
                  src="/assets/favicon.png"
                  alt="Bora avatar"
                  width={36}
                  height={36}
                  unoptimized
                  className={styles.flowVoiceBora}
                />
                <div className={styles.flowVoiceGroup}>
                  {["/assets/headshot-4.jpg", "/assets/headshot-5.jpg"].map((src, idx) => (
                    <Image
                      key={`voice-right-${src}`}
                      src={src}
                      alt={`Right participant ${idx + 1}`}
                      width={24}
                      height={24}
                      className={styles.flowVoiceFace}
                    />
                  ))}
                </div>
              </div>
              <div className={styles.flowMiniWave}>
                {Array.from({ length: 18 }).map((_, i) => (
                  <span key={`mini-wave-${i}`} style={{ animationDelay: `${i * 0.06}s` }} />
                ))}
              </div>
            </div>
            <div className={styles.flowMiniCard}>
              <span className={`${styles.flowMiniIcon} ${styles.flowMiniIconPurple}`}>
                <Image
                  src="/assets/voice-icon.png"
                  alt="Voice icon"
                  width={11}
                  height={11}
                />
              </span>
              <div className={styles.flowMiniText}>
                <p>Added clarity to the discussion</p>
                <span>Helped the team move forward</span>
              </div>
            </div>
          </article>

          <article className={styles.flowColumn}>
            <div className={styles.flowStepTrack}>
              <span className={`${styles.flowStepBadge} ${styles.flowStepBadgeMemory}`}>
                <Image
                  src="/assets/document-icon.png"
                  alt="Memory logo"
                  width={16}
                  height={16}
                  className={styles.flowStepBadgeImage}
                />
              </span>
              <span className={styles.flowStepIndex}>03</span>
              <span className={styles.flowStepLine} />
              <span className={styles.flowStepArrow}>→</span>
            </div>
            <h3>Remembers Everything</h3>
            <p>
              AgentBora remembers all meetings and context you provide.
            </p>
            <div className={styles.flowCard}>
              <p className={styles.flowCardTitle}>Ask anything from your memory</p>
              <div className={styles.flowSearchBox}>What did we decide about pricing last month?</div>
              <div className={styles.flowMemorySnippet}>
                <p>From Product Review</p>
                <span>
                  We decided to move to tiered pricing with a new enterprise plan.
                  Approved by Sarah.
                </span>
              </div>
              <button type="button" className={styles.flowLinkButton}>
                View full memory
              </button>
            </div>
            <div className={styles.flowMiniCard}>
              <span className={`${styles.flowMiniIcon} ${styles.flowMiniIconBlue}`}>🧠</span>
              <div className={styles.flowMiniText}>
                <p>Memory updated</p>
                <span>Linked to 24 related conversations</span>
              </div>
            </div>
          </article>

          <article className={styles.flowColumn}>
            <div className={`${styles.flowStepTrack} ${styles.flowStepTrackLast}`}>
              <span className={`${styles.flowStepBadge} ${styles.flowStepBadgeAction}`}>
                <Image
                  src="/assets/asana-logo-v2.png"
                  alt="Action logo"
                  width={16}
                  height={16}
                  className={styles.flowStepBadgeImage}
                />
              </span>
              <span className={styles.flowStepIndex}>04</span>
            </div>
            <h3>Takes Action</h3>
            <p>
              AgentBora turns conversations into outcomes by creating tasks,
              updating tools, and following through.
            </p>
            <div className={styles.flowCard}>
              <p className={styles.flowCardTitle}>Actions generated</p>
              <div className={styles.flowActionList}>
                {flowActionList.map((item) => (
                  <div key={item.title} className={styles.flowActionRow}>
                    <div className={styles.flowActionLeft}>
                      <span className={styles.flowActionLogoBox}>
                        <Image
                          src={item.icon}
                          alt={item.iconAlt}
                          width={14}
                          height={14}
                          className={`${styles.flowActionLogo} ${
                            item.isWide ? styles.flowActionLogoWide : ""
                          }`}
                        />
                      </span>
                      <div className={styles.flowActionText}>
                        <p>{item.title}</p>
                        <span>{item.subtitle}</span>
                      </div>
                    </div>
                    <strong>{item.status}</strong>
                  </div>
                ))}
              </div>
              <button type="button" className={styles.flowLinkButton}>
                View all actions
              </button>
            </div>
            <div className={styles.flowMiniCard}>
              <span className={`${styles.flowMiniIcon} ${styles.flowMiniIconOrange}`}>✓</span>
              <div className={styles.flowMiniText}>
                <p>Actions completed</p>
                <span>Work in motion</span>
              </div>
            </div>
          </article>
        </div>

        <div className={styles.flowFooter}>
          <div className={styles.flowFooterLeadWrap}>
            <div className={styles.flowFooterOrb}>
              <span>✦</span>
            </div>
            <div className={styles.flowFooterLead}>
              <p>Not just present. Productive.</p>
              <span>
                AgentBora is an active participant that helps your team make better
                decisions and move work forward.
              </span>
            </div>
          </div>
          <div className={styles.flowFooterTags}>
            {flowFooterItems.map((item) => (
              <div key={item.title} className={styles.flowFooterTag}>
                <span className={styles.flowFooterTagIcon}>
                  {item.iconSrc ? (
                    <Image
                      src={item.iconSrc}
                      alt={item.iconAlt ?? item.title}
                      width={18}
                      height={18}
                      className={styles.flowFooterTagIconImage}
                    />
                  ) : (
                    item.icon
                  )}
                </span>
                <div className={styles.flowFooterTagText}>
                  <p>{item.title}</p>
                  <span>{item.subtitle}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
