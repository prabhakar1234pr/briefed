/**
 * Google Cloud TTS Neural2 & Studio voices for the meeting copilot.
 * These are high-quality voices that output clean MP3 natively.
 *
 * Voice IDs match Google Cloud TTS voice names (e.g. "en-US-Neural2-J").
 * Language: English only.
 */

export type TTSVoice = {
  id: string;
  label: string;
  gender: "male" | "female";
  description: string;
  category: "recommended" | "neural2" | "studio" | "wavenet";
};

export const TTS_VOICES: TTSVoice[] = [
  // ─── Recommended ────────────────────────────────────────────────────
  {
    id: "en-US-Neural2-J",
    label: "James",
    gender: "male",
    category: "recommended",
    description: "Clear, confident male — great all-around default",
  },
  {
    id: "en-US-Neural2-F",
    label: "Fiona",
    gender: "female",
    category: "recommended",
    description: "Warm, professional female with clear enunciation",
  },
  {
    id: "en-US-Neural2-D",
    label: "David",
    gender: "male",
    category: "recommended",
    description: "Natural, friendly male voice for conversations",
  },
  {
    id: "en-US-Neural2-C",
    label: "Claire",
    gender: "female",
    category: "recommended",
    description: "Bright, articulate female with modern tone",
  },

  // ─── Neural2 — high quality, low latency ────────────────────────────
  {
    id: "en-US-Neural2-A",
    label: "Alex",
    gender: "male",
    category: "neural2",
    description: "Deep, composed male for professional settings",
  },
  {
    id: "en-US-Neural2-E",
    label: "Emma",
    gender: "female",
    category: "neural2",
    description: "Calm, clear female voice with steady delivery",
  },
  {
    id: "en-US-Neural2-G",
    label: "Grace",
    gender: "female",
    category: "neural2",
    description: "Warm female with a natural, approachable tone",
  },
  {
    id: "en-US-Neural2-H",
    label: "Henry",
    gender: "male",
    category: "neural2",
    description: "Balanced male voice with confident delivery",
  },
  {
    id: "en-US-Neural2-I",
    label: "Iris",
    gender: "female",
    category: "neural2",
    description: "Professional female with polished clarity",
  },

  // ─── Studio — highest quality, slightly more latency ────────────────
  {
    id: "en-US-Studio-O",
    label: "Oliver",
    gender: "male",
    category: "studio",
    description: "Premium studio male — richest tone quality",
  },
  {
    id: "en-US-Studio-Q",
    label: "Quinn",
    gender: "female",
    category: "studio",
    description: "Premium studio female — natural and expressive",
  },

  // ─── WaveNet — natural-sounding alternatives ────────────────────────
  {
    id: "en-US-Wavenet-D",
    label: "Derek",
    gender: "male",
    category: "wavenet",
    description: "Smooth male voice with natural inflection",
  },
  {
    id: "en-US-Wavenet-F",
    label: "Felicity",
    gender: "female",
    category: "wavenet",
    description: "Clear female voice with conversational warmth",
  },
  {
    id: "en-US-Wavenet-J",
    label: "Jack",
    gender: "male",
    category: "wavenet",
    description: "Friendly male with relaxed, natural delivery",
  },
  {
    id: "en-US-Wavenet-H",
    label: "Hannah",
    gender: "female",
    category: "wavenet",
    description: "Approachable female with warm tone",
  },

  // ─── British English ────────────────────────────────────────────────
  {
    id: "en-GB-Neural2-B",
    label: "Benedict",
    gender: "male",
    category: "neural2",
    description: "British male — composed and articulate",
  },
  {
    id: "en-GB-Neural2-A",
    label: "Amelia",
    gender: "female",
    category: "neural2",
    description: "British female — clear and professional",
  },
];

export const DEFAULT_VOICE_ID = "en-US-Neural2-J";

export const VOICE_CATEGORIES = [
  { key: "recommended", label: "★ Recommended" },
  { key: "neural2", label: "Neural2 — Fast & Clear" },
  { key: "studio", label: "Studio — Premium Quality" },
  { key: "wavenet", label: "WaveNet — Natural" },
] as const;
