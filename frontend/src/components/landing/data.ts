// Shared cubic-bezier easing for landing animations.
// Typed as a 4-tuple so Framer Motion's `Easing` type accepts it
// (a plain array literal widens to number[], which is rejected).
export const EASE: [number, number, number, number] = [0.22, 1, 0.36, 1];

export const upcomingMeetings = [
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

export const memoryItems = [
  { text: "Discussed Q3 roadmap", age: "2h ago" },
  { text: "Budget approved", age: "Yesterday" },
  { text: "Launch date finalized", age: "2 days ago" },
];

export const actionItems = [
  "Review proposal deck",
  "Send follow-up email",
  "Update product roadmap",
];

export const docLogos = [
  { src: "/assets/notion-logo.png", alt: "Notion logo" },
  { src: "/assets/gmail-logo.png", alt: "Gmail logo" },
  { src: "/assets/pdf-logo.png", alt: "PDF logo" },
];

export const platformLogos: Record<string, { src: string; alt: string }> = {
  meet: { src: "/assets/google-meet-logo.png", alt: "Google Meet logo" },
  zoom: { src: "/assets/zoom-logo.png", alt: "Zoom logo" },
  teams: { src: "/assets/teams-logo.png", alt: "Microsoft Teams logo" },
};

export const flowActionList = [
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
