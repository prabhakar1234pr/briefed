export type AgentMode = "copilot" | "proctor";

export type Agent = {
  id: string;
  user_id: string;
  name: string;
  description: string | null;
  mode: AgentMode;
  persona_prompt: string | null;
  voice_id: string | null;
  bot_image_url: string | null;
  proactive_fact_check: boolean;
  screenshot_on_request: boolean;
  send_post_meeting_email: boolean;
  created_at: string;
  updated_at: string;
};

export type MeetingStatus =
  | "scheduled"
  | "joining"
  | "in_meeting"
  | "processing"
  | "completed"
  | "failed";

export type Meeting = {
  id: string;
  user_id: string;
  agent_id: string;
  meeting_link: string;
  bot_id: string | null;
  status: MeetingStatus;
  transcript_text: string | null;
  audio_url: string | null;
  video_url: string | null;
  created_at: string;
  updated_at: string;
};
