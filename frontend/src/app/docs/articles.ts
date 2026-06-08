export type ArticleBlock =
  | { type: "p"; text: string }
  | { type: "h2"; text: string }
  | { type: "ul"; items: string[] };

export type Article = {
  slug: string;
  tag: string;
  title: string;
  excerpt: string;
  emoji: string;
  gradient: string;
  readTime: string;
  date: string;
  body: ArticleBlock[];
};

export const articles: Article[] = [
  {
    slug: "getting-started",
    tag: "Guide",
    title: "Getting started with Agent Bora",
    excerpt:
      "Create your first AI teammate in under five minutes and connect it to your calendar.",
    emoji: "🚀",
    gradient: "linear-gradient(135deg, rgba(45,212,191,0.22), rgba(37,99,235,0.22))",
    readTime: "4 min read",
    date: "May 2026",
    body: [
      {
        type: "p",
        text: "Agent Bora is your team's AI teammate for meetings. It joins calls, follows the conversation, remembers what matters, and turns decisions into action. This guide walks you through setting up your first agent.",
      },
      { type: "h2", text: "1. Create your agent" },
      {
        type: "p",
        text: "From the dashboard, click Create your agent. Give it a name, choose a voice, and pick the meetings it should attend automatically. You can create as many agents as your plan allows.",
      },
      { type: "h2", text: "2. Connect your calendar" },
      {
        type: "p",
        text: "Bora reads your calendar to know when to show up. Connect Google Calendar or Outlook and Bora will quietly join Google Meet, Zoom, or Microsoft Teams calls on time.",
      },
      { type: "h2", text: "3. Add context" },
      {
        type: "ul",
        items: [
          "Upload docs, notes, and past meeting summaries",
          "Connect Notion, Gmail, and PDFs as live sources",
          "Tell Bora when it should speak versus stay silent",
        ],
      },
      {
        type: "p",
        text: "That's it. The next time a meeting starts, Bora will be there, grounded in your context and ready to help.",
      },
    ],
  },
  {
    slug: "how-bora-joins-meetings",
    tag: "Product",
    title: "How Bora joins your meetings",
    excerpt:
      "A look at how Bora connects to Meet, Zoom, and Teams without disrupting your flow.",
    emoji: "🎥",
    gradient: "linear-gradient(135deg, rgba(34,211,238,0.22), rgba(45,212,191,0.22))",
    readTime: "3 min read",
    date: "May 2026",
    body: [
      {
        type: "p",
        text: "One of the most common questions we get is simple: how does Bora actually get into the call? The short answer is that it behaves like a well-prepared participant.",
      },
      { type: "h2", text: "Always on time" },
      {
        type: "p",
        text: "Bora watches your calendar and joins a moment before the meeting begins. It appears as a clearly labeled participant so everyone knows an AI teammate is present.",
      },
      { type: "h2", text: "Works across platforms" },
      {
        type: "ul",
        items: [
          "Google Meet",
          "Zoom",
          "Microsoft Teams",
        ],
      },
      {
        type: "p",
        text: "No matter which platform your team uses, the experience is the same: Bora listens, follows along, and only steps in when it can add value.",
      },
    ],
  },
  {
    slug: "memory-and-context",
    tag: "Deep dive",
    title: "Memory and context, explained",
    excerpt:
      "How Bora turns every meeting and document into searchable, trustworthy memory.",
    emoji: "🧠",
    gradient: "linear-gradient(135deg, rgba(37,99,235,0.22), rgba(34,211,238,0.22))",
    readTime: "6 min read",
    date: "April 2026",
    body: [
      {
        type: "p",
        text: "Most meeting tools forget everything the moment the call ends. Bora is different — it builds a living memory of your team's decisions, context, and follow-ups.",
      },
      { type: "h2", text: "What goes into memory" },
      {
        type: "ul",
        items: [
          "Transcripts and summaries from every meeting",
          "Documents and notes you connect",
          "Decisions, owners, and due dates",
        ],
      },
      { type: "h2", text: "Ask anything" },
      {
        type: "p",
        text: "Instead of scrolling through notes, just ask. \"What did we decide about pricing last month?\" Bora returns the decision, who approved it, and the meeting it came from.",
      },
      {
        type: "p",
        text: "Every answer is grounded in your real history, so you can trust it — and click through to the source whenever you want.",
      },
    ],
  },
  {
    slug: "automations-and-integrations",
    tag: "Integrations",
    title: "Automations and integrations",
    excerpt:
      "Connect Asana, Linear, Slack, and email so outcomes happen automatically.",
    emoji: "⚡",
    gradient: "linear-gradient(135deg, rgba(45,212,191,0.22), rgba(34,211,238,0.22))",
    readTime: "5 min read",
    date: "April 2026",
    body: [
      {
        type: "p",
        text: "A great summary is only useful if it leads to action. Bora closes the loop by turning conversations into real tasks in the tools your team already uses.",
      },
      { type: "h2", text: "Out-of-the-box integrations" },
      {
        type: "ul",
        items: [
          "Create tasks in Asana and Linear",
          "Send follow-up emails via Gmail",
          "Share notes to Slack channels",
        ],
      },
      { type: "h2", text: "How it works" },
      {
        type: "p",
        text: "When Bora detects an action item — a commitment, a deadline, a next step — it drafts the task and routes it to the right tool. You stay in control and can review everything before it ships.",
      },
    ],
  },
  {
    slug: "security-and-privacy",
    tag: "Security",
    title: "Security and privacy at Bora",
    excerpt:
      "How we keep your meetings, memory, and integrations private and secure.",
    emoji: "🔒",
    gradient: "linear-gradient(135deg, rgba(37,99,235,0.22), rgba(45,212,191,0.22))",
    readTime: "4 min read",
    date: "March 2026",
    body: [
      {
        type: "p",
        text: "Your meetings contain some of your team's most sensitive information. We treat that responsibility seriously.",
      },
      { type: "h2", text: "Built for trust" },
      {
        type: "ul",
        items: [
          "Encryption in transit and at rest",
          "Granular roles and permissions",
          "Enterprise SSO on Premium plans",
          "You control what Bora can access",
        ],
      },
      {
        type: "p",
        text: "Bora only sees the context you give it, and you can revoke access or delete memory at any time. Privacy isn't an add-on — it's the foundation.",
      },
    ],
  },
  {
    slug: "best-practices-meeting-notes",
    tag: "Tips",
    title: "Best practices for AI meeting notes",
    excerpt:
      "Small habits that make Bora's summaries and actions dramatically better.",
    emoji: "✨",
    gradient: "linear-gradient(135deg, rgba(34,211,238,0.22), rgba(37,99,235,0.22))",
    readTime: "5 min read",
    date: "March 2026",
    body: [
      {
        type: "p",
        text: "Bora is smart out of the box, but a few simple habits help it produce summaries and actions your whole team will love.",
      },
      { type: "h2", text: "Give it context early" },
      {
        type: "p",
        text: "Connect the docs and notes relevant to a project before the meeting. The more grounded Bora is, the sharper its answers.",
      },
      { type: "h2", text: "Be explicit about decisions" },
      {
        type: "ul",
        items: [
          "State decisions clearly: \"We're going with option B.\"",
          "Name owners: \"Sarah will handle the rollout.\"",
          "Set timelines: \"By end of next week.\"",
        ],
      },
      {
        type: "p",
        text: "These cues help Bora capture clean action items and assign them to the right people automatically.",
      },
    ],
  },
];

export function getArticle(slug: string) {
  return articles.find((article) => article.slug === slug);
}
