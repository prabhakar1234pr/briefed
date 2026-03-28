import Link from "next/link";

export default function HomePage() {
  return (
    <div style={{ maxWidth: 1100, margin: "0 auto", padding: "0 24px" }}>
      {/* Hero — single intro (avoid duplicating a separate “landing” blurb above) */}
      <section
        style={{
          padding: "88px 0 72px",
          textAlign: "center",
        }}
        className="anim-0"
      >
        {/* Eyebrow */}
        <div
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 8,
            background: "rgba(59,130,246,0.1)",
            border: "1px solid rgba(59,130,246,0.2)",
            borderRadius: 100,
            padding: "5px 14px",
            marginBottom: 28,
          }}
        >
          <span
            style={{
              width: 6,
              height: 6,
              borderRadius: "50%",
              background: "var(--accent)",
              boxShadow: "0 0 8px rgba(59,130,246,0.6)",
              display: "inline-block",
            }}
          />
          <span
            style={{ fontSize: 12, color: "#93c5fd", fontWeight: 500, letterSpacing: "0.04em" }}
          >
            AI Meeting Intelligence
          </span>
        </div>

        {/* Headline */}
        <h1
          style={{
            fontFamily: "var(--font-display)",
            fontSize: "clamp(42px, 6vw, 68px)",
            fontWeight: 400,
            lineHeight: 1.1,
            letterSpacing: "-0.02em",
            color: "var(--text-primary)",
            marginBottom: 20,
            maxWidth: 760,
            margin: "0 auto 20px",
          }}
        >
          Your meeting has{" "}
          <span
            style={{
              fontStyle: "italic",
              background: "linear-gradient(135deg, #60a5fa 0%, #2dd4bf 100%)",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
            }}
          >
            a brain now
          </span>
        </h1>

        <p
          style={{
            fontSize: 17,
            color: "var(--text-secondary)",
            maxWidth: 560,
            margin: "0 auto 40px",
            lineHeight: 1.65,
            fontWeight: 300,
          }}
        >
          Unlike passive note-takers, Briefed is built for{" "}
          <strong style={{ color: "var(--text-secondary)", fontWeight: 500 }}>
            live participation
          </strong>
          — it joins your calls, listens in real time, and delivers transcripts,
          recordings, and briefs when the meeting ends.
        </p>

        {/* CTA row */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: 12,
            flexWrap: "wrap",
          }}
        >
          <Link href="/auth" className="btn-primary" style={{ fontSize: 15, padding: "12px 28px" }}>
            Get started
          </Link>
          <Link href="/meeting" className="btn-secondary" style={{ fontSize: 15, padding: "12px 28px" }}>
            Start a meeting
          </Link>
          <Link href="/agents/new" className="btn-secondary" style={{ fontSize: 15, padding: "12px 28px" }}>
            Design an agent
          </Link>
        </div>
      </section>

      {/* How it works — PRD user flow */}
      <section
        style={{
          padding: "56px 0 72px",
          borderTop: "1px solid var(--border-subtle)",
        }}
        className="anim-2"
      >
        <p
          style={{
            fontSize: 11,
            fontWeight: 600,
            letterSpacing: "0.12em",
            textTransform: "uppercase",
            color: "var(--text-tertiary)",
            textAlign: "center",
            marginBottom: 12,
          }}
        >
          How it works
        </p>
        <h2
          style={{
            fontFamily: "var(--font-display)",
            fontSize: "clamp(26px, 4vw, 36px)",
            fontWeight: 400,
            textAlign: "center",
            color: "var(--text-primary)",
            marginBottom: 40,
            letterSpacing: "-0.02em",
          }}
        >
          From agent to brief in three steps
        </h2>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
            gap: 20,
          }}
        >
          {[
            {
              step: "01",
              title: "Design your agent",
              body: "Name, persona, and mode — Copilot for live Q&A and context, or Proctor for interview integrity signals.",
            },
            {
              step: "02",
              title: "Briefed joins the call",
              body: "Our Recall.ai bot enters Zoom or Google Meet, streams real-time transcript, and captures recording artifacts.",
            },
            {
              step: "03",
              title: "Get the brief",
              body: "Full transcript, video, audio, and summaries land in your dashboard when processing completes.",
            },
          ].map((s) => (
            <div
              key={s.step}
              className="card"
              style={{ padding: 24, position: "relative" }}
            >
              <span
                style={{
                  fontFamily: "var(--font-display)",
                  fontSize: 36,
                  color: "rgba(59,130,246,0.2)",
                  position: "absolute",
                  top: 16,
                  right: 20,
                  lineHeight: 1,
                }}
              >
                {s.step}
              </span>
              <h3
                style={{
                  fontSize: 15,
                  fontWeight: 600,
                  color: "var(--text-primary)",
                  marginBottom: 10,
                }}
              >
                {s.title}
              </h3>
              <p style={{ fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.65 }}>
                {s.body}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* Feature cards */}
      <section
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
          gap: 16,
          paddingBottom: 80,
        }}
      >
        {[
          {
            icon: "◎",
            color: "#60a5fa",
            glow: "rgba(59,130,246,0.08)",
            title: "Copilot Mode",
            desc: "Pre-load GitHub repos, docs, and context. The agent answers questions live in your call using its knowledge base.",
            tag: "Voice + Memory",
            tagClass: "tag-blue",
            delay: "anim-1",
            href: "/agents/new",
          },
          {
            icon: "◈",
            color: "#5eead4",
            glow: "rgba(45,212,191,0.08)",
            title: "Proctor Mode",
            desc: "Silent AI observer for interviews. Detects suspicious eye movement, scripted speech, and potential earpiece use.",
            tag: "Vision + Audio",
            tagClass: "tag-teal",
            delay: "anim-2",
            href: "/agents/new",
          },
          {
            icon: "◉",
            color: "#fcd34d",
            glow: "rgba(245,158,11,0.08)",
            title: "Post-Meeting Brief",
            desc: "Summary, action items, key decisions, and a searchable transcript — ready 30 seconds after the call ends.",
            tag: "AI Summary",
            tagClass: "tag-amber",
            delay: "anim-3",
            href: "/meetings",
          },
        ].map((f) => (
          <Link
            key={f.title}
            href={f.href}
            className={`card card-hover ${f.delay}`}
            style={{
              padding: 28,
              textDecoration: "none",
              display: "block",
              position: "relative",
              overflow: "hidden",
            }}
          >
            {/* Glow bg */}
            <div
              style={{
                position: "absolute",
                top: -40,
                right: -40,
                width: 180,
                height: 180,
                borderRadius: "50%",
                background: `radial-gradient(circle, ${f.glow} 0%, transparent 70%)`,
                pointerEvents: "none",
              }}
            />
            <div
              style={{
                fontSize: 22,
                color: f.color,
                marginBottom: 16,
                display: "block",
              }}
            >
              {f.icon}
            </div>
            <h3
              style={{
                fontSize: 16,
                fontWeight: 500,
                color: "var(--text-primary)",
                marginBottom: 8,
                letterSpacing: "-0.01em",
              }}
            >
              {f.title}
            </h3>
            <p
              style={{
                fontSize: 13,
                color: "var(--text-secondary)",
                lineHeight: 1.65,
                marginBottom: 20,
              }}
            >
              {f.desc}
            </p>
            <span className={`tag ${f.tagClass}`}>{f.tag}</span>
          </Link>
        ))}
      </section>

      {/* Footer */}
      <footer
        style={{
          borderTop: "1px solid var(--border-subtle)",
          padding: "40px 0 56px",
          textAlign: "center",
        }}
        className="anim-4"
      >
        <div
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 10,
            marginBottom: 12,
          }}
        >
          <div
            style={{
              width: 24,
              height: 24,
              borderRadius: 7,
              background: "linear-gradient(135deg, #3b82f6 0%, #2dd4bf 100%)",
            }}
          />
          <span style={{ fontWeight: 500, color: "var(--text-primary)" }}>Briefed</span>
        </div>
        <p style={{ fontSize: 12, color: "var(--text-tertiary)", maxWidth: 480, margin: "0 auto", lineHeight: 1.6 }}>
          Multimodal meeting intelligence — Copilot and Proctor modes, powered by Recall.ai
          and your stack on Supabase &amp; GCP.
        </p>
      </footer>
    </div>
  );
}
