/**
 * Cartesia Sonic TTS voices for the Output Media copilot.
 * Voice IDs from https://cartesia.ai/voices — curated for meeting copilot use.
 *
 * Model: sonic-2 | Language: en (hardcoded)
 */

export type CartesiaVoice = {
  id: string;
  label: string;
  gender: "male" | "female";
  description: string;
  category: "recommended" | "professional" | "conversational" | "authoritative" | "expressive";
};

export const CARTESIA_VOICES: CartesiaVoice[] = [
  // ─── Recommended — best for voice agents ──────────────────────────────
  {
    id: "f786b574-daa5-4673-aa0c-cbe3e8534c02",
    label: "Katie — Friendly Fixer",
    gender: "female",
    category: "recommended",
    description: "Clear, enunciating young adult female — great default for meeting copilots",
  },
  {
    id: "47c38ca4-5f35-497b-b1a3-415245fb35e1",
    label: "Daniel — Modern Assistant",
    gender: "male",
    category: "recommended",
    description: "Clear, crisp male voice for digital assistants and system interactions",
  },
  {
    id: "2a17e905-8f14-4db7-9b9d-9223a8e3f278",
    label: "Jane — Digital Guide",
    gender: "female",
    category: "recommended",
    description: "Crisp, modern voice with a friendly, intelligent tone",
  },
  {
    id: "96c64eb5-a945-448f-9710-980abe7a514c",
    label: "Carson — Friendly Support",
    gender: "male",
    category: "recommended",
    description: "Friendly young adult male for customer support conversations",
  },
  {
    id: "55deba52-bc73-4481-ab69-9c8831c8a7c3",
    label: "Camille — Friendly Expert",
    gender: "female",
    category: "recommended",
    description: "Calm, neutral female for customer support and instructional videos",
  },
  // ─── Professional — confident, clear delivery ─────────────────────────
  {
    id: "228fca29-3a0a-435c-8728-5cb483251068",
    label: "Kiefer — Assured Tone",
    gender: "male",
    category: "professional",
    description: "Confident voice with strong clarity, ideal for presentations",
  },
  {
    id: "8a1b8af0-c4f6-423f-a268-5507fd4aefdf",
    label: "Denise — Professional Woman",
    gender: "female",
    category: "professional",
    description: "Professional female with confident clarity and polished tone",
  },
  {
    id: "c0f43c66-9f21-4034-b485-8f1d3340d759",
    label: "Clarkson — Executive Tone",
    gender: "male",
    category: "professional",
    description: "Businesslike voice with confident tone and professional delivery",
  },
  {
    id: "2948c301-9211-4112-8f36-4c3fc836ef12",
    label: "Bryce — Clear Explainer",
    gender: "male",
    category: "professional",
    description: "Confident voice with clear enunciation, ideal for professional use",
  },
  {
    id: "f24ae0b7-a3d2-4dd1-89df-959bdc4ab179",
    label: "Ross — Reliable Partner",
    gender: "male",
    category: "professional",
    description: "Steady voice with balanced tone and clear delivery",
  },
  {
    id: "489b647b-5662-408f-8c95-82e26ef8d29e",
    label: "Kate — Practical Voice",
    gender: "female",
    category: "professional",
    description: "Direct, no-nonsense female voice for instructions and explanations",
  },
  {
    id: "c78dd7ae-6692-4c44-a2a2-834e365afe60",
    label: "Clark — Trustworthy Expert",
    gender: "male",
    category: "professional",
    description: "Approachable male with confident, knowledgeable tone",
  },
  {
    id: "996a8b96-4804-46f0-8e05-3fd4ef1a87cd",
    label: "Darla — Resolution Agent",
    gender: "female",
    category: "professional",
    description: "Firm and confident female with calm, supportive tone",
  },
  // ─── Authoritative — deep, commanding ─────────────────────────────────
  {
    id: "42b39f37-515f-4eee-8546-73e841679c1d",
    label: "James — Navigator",
    gender: "male",
    category: "authoritative",
    description: "Very deep, authoritative male for guidance and instruction",
  },
  {
    id: "f0377496-2708-4cc9-b2f8-1b7fdb5e1a2a",
    label: "Elaine — Confident Guide",
    gender: "female",
    category: "authoritative",
    description: "Assured voice with calm confidence and clear tone",
  },
  {
    id: "b9cf5ec3-eaa4-46a5-a5b2-b0d0f22395a2",
    label: "Caleb — Seasoned Pro",
    gender: "male",
    category: "authoritative",
    description: "Confident male with authoritative clarity for expert insights",
  },
  {
    id: "9a0894a9-28f0-436e-9a1d-e92bccbce4dd",
    label: "Albert — Firm Guide",
    gender: "male",
    category: "authoritative",
    description: "Firm and authoritative tone for providing clear guidance",
  },
  {
    id: "c8f7835e-28a3-4f0c-80d7-c1302ac62aae",
    label: "Alistair — Composed Consultant",
    gender: "male",
    category: "authoritative",
    description: "Sophisticated, steady British male for client interactions",
  },
  // ─── Conversational — warm, natural ───────────────────────────────────
  {
    id: "ea7c252f-6cb1-45f5-8be9-b4f6ac282242",
    label: "Logan — Approachable Friend",
    gender: "male",
    category: "conversational",
    description: "Casual voice with an easy, conversational tone",
  },
  {
    id: "f6ce3444-478b-4ce4-982e-bcb72dffe7aa",
    label: "Emily — Easygoing Pal",
    gender: "female",
    category: "conversational",
    description: "Cheerful voice with warm and welcoming tone",
  },
  {
    id: "df872fcd-da17-4b01-a49f-a80d7aaee95e",
    label: "Cameron — Chill Companion",
    gender: "male",
    category: "conversational",
    description: "Laidback voice with a natural, conversational tone",
  },
  {
    id: "f4a3a8e4-694c-4c45-9ca0-27caf97901b5",
    label: "Gavin — Friendly Vibe",
    gender: "male",
    category: "conversational",
    description: "Casual male voice with a relaxed, conversational tone",
  },
  {
    id: "87041166-c212-4838-9028-05d7437df750",
    label: "Aubrey — Easygoing Pal",
    gender: "female",
    category: "conversational",
    description: "Warm voice with a relaxed, natural tone that feels effortless",
  },
  {
    id: "3d808d23-cb09-4c39-8afd-528e209cba4f",
    label: "Brent — Steady Conversationalist",
    gender: "male",
    category: "conversational",
    description: "Calm, steady, and composed delivery",
  },
  {
    id: "2747b6cf-fa34-460c-97db-267566918881",
    label: "Allie — Natural Conversationalist",
    gender: "female",
    category: "conversational",
    description: "Confident, approachable young adult woman for natural conversation",
  },
  // ─── Expressive — emotive, dynamic ────────────────────────────────────
  {
    id: "6ccbfb76-1fc6-48f7-b71d-91ac6298247b",
    label: "Tessa — Kind Companion",
    gender: "female",
    category: "expressive",
    description: "Friendly female with warm, conversational tone that builds trust",
  },
  {
    id: "c961b81c-a935-4c17-bfb3-ba2239de8c2f",
    label: "Kyle — Approachable Friend",
    gender: "male",
    category: "expressive",
    description: "Friendly male with warm, conversational tone",
  },
  {
    id: "a167e0f3-df7e-4d52-a9c3-f949145efdab",
    label: "Blake — Helpful Agent",
    gender: "male",
    category: "expressive",
    description: "Energetic adult male for engaging customer support",
  },
  {
    id: "ec1e269e-9ca0-402f-8a18-58e0e022355a",
    label: "Ariana — Kind Friend",
    gender: "female",
    category: "expressive",
    description: "Friendly and approachable with a warm, welcoming tone",
  },
];

export const DEFAULT_CARTESIA_VOICE_ID = "f786b574-daa5-4673-aa0c-cbe3e8534c02"; // Katie

export const VOICE_CATEGORIES = [
  { key: "recommended", label: "Recommended" },
  { key: "professional", label: "Professional" },
  { key: "authoritative", label: "Authoritative" },
  { key: "conversational", label: "Conversational" },
  { key: "expressive", label: "Expressive" },
] as const;
