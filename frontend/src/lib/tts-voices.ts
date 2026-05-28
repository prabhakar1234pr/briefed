/**
 * ElevenLabs voices for the v2 live voice pipeline.
 *
 * IDs are ElevenLabs pre-made voice IDs (no clone or library import needed).
 * They work with the `eleven_flash_v2_5` streaming model out of the box and
 * are passed to `ElevenLabsTTSService` in backend-fastapi/app/pipeline/runner.py.
 *
 * Browse the full library at https://elevenlabs.io/app/voice-library — paste
 * any voice's ID below to add more options.
 */

export type TTSVoice = {
  id: string;
  label: string;
  gender: "male" | "female";
  description: string;
  category: "recommended" | "professional" | "casual" | "british";
};

export const TTS_VOICES: TTSVoice[] = [
  // ─── Recommended ────────────────────────────────────────────────────
  {
    id: "21m00Tcm4TlvDq8ikWAM",
    label: "Rachel",
    gender: "female",
    category: "recommended",
    description: "Calm, articulate American female — the all-purpose default",
  },
  {
    id: "ErXwobaYiN019PkySvjV",
    label: "Antoni",
    gender: "male",
    category: "recommended",
    description: "Well-rounded American male, natural narration tone",
  },
  {
    id: "EXAVITQu4vr4xnSDxMaL",
    label: "Sarah",
    gender: "female",
    category: "recommended",
    description: "Soft, news-anchor American female with crisp delivery",
  },
  {
    id: "TX3LPaxmHKxFdv7VOQHJ",
    label: "Liam",
    gender: "male",
    category: "recommended",
    description: "Articulate American male, confident professional vibe",
  },

  // ─── Professional ───────────────────────────────────────────────────
  {
    id: "CwhRBWXzGAHq8TQ4Fs17",
    label: "Roger",
    gender: "male",
    category: "professional",
    description: "Confident American male, news/conference tone",
  },
  {
    id: "9BWtsMINqrJLrRacOk9x",
    label: "Aria",
    gender: "female",
    category: "professional",
    description: "Expressive American female, social-media polished",
  },
  {
    id: "nPczCjzI2devNBz1zQrb",
    label: "Brian",
    gender: "male",
    category: "professional",
    description: "Deep American male, narration-grade authority",
  },
  {
    id: "cgSgspJ2msm6clMCkdW9",
    label: "Jessica",
    gender: "female",
    category: "professional",
    description: "Young expressive American female, conversational",
  },

  // ─── Casual ─────────────────────────────────────────────────────────
  {
    id: "bIHbv24MWmeRgasZH58o",
    label: "Will",
    gender: "male",
    category: "casual",
    description: "Friendly American male, approachable everyday voice",
  },
  {
    id: "iP95p4xoKVk53GoZ742B",
    label: "Chris",
    gender: "male",
    category: "casual",
    description: "Casual American male — relaxed, conversational",
  },
  {
    id: "FGY2WhTYpPnrIDTdsKH5",
    label: "Laura",
    gender: "female",
    category: "casual",
    description: "Upbeat American female, podcast-style energy",
  },

  // ─── British English ────────────────────────────────────────────────
  {
    id: "JBFqnCBsd6RMkjVDRZzb",
    label: "George",
    gender: "male",
    category: "british",
    description: "Warm British male, mature narration tone",
  },
  {
    id: "Xb7hH8MSUJpSbSDYk0k2",
    label: "Alice",
    gender: "female",
    category: "british",
    description: "Confident British female, broadcaster polish",
  },
  {
    id: "onwK4e9ZLuTAKqWW03F9",
    label: "Daniel",
    gender: "male",
    category: "british",
    description: "Authoritative British male, presenter delivery",
  },
  {
    id: "pFZP5JQG7iQjIQuC4Bku",
    label: "Lily",
    gender: "female",
    category: "british",
    description: "Warm British female, friendly clarity",
  },
];

// Default = Rachel — the same value as ELEVENLABS_DEFAULT_VOICE in the backend
export const DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM";

export const VOICE_CATEGORIES = [
  { key: "recommended", label: "★ Recommended" },
  { key: "professional", label: "Professional — Newsroom Polish" },
  { key: "casual", label: "Casual — Friendly & Conversational" },
  { key: "british", label: "British English" },
] as const;
