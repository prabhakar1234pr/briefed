"""
Vertex AI Gemini + Google Cloud TTS client.

Key decisions:
- Two models enabled on project 'meetstreamiq':
    * gemini-2.5-flash — live Q&A (low latency, fast first token)
    * gemini-2.5-pro   — post-meeting intelligence (higher quality)
- NO token limits on answers: the agent speaks as much as the question needs.
- Two SDK paths:
    * google.genai (newer) — used for STREAMING Q&A with thinking_budget=128.
    * vertexai (older) — used for blocking calls (post-meeting intelligence).
- 429 retries with exponential backoff on all blocking calls.
"""
from __future__ import annotations

import asyncio
import json
import random
import time
from collections.abc import AsyncIterator
from typing import Any

from app.logger import get_logger, log_timing

log = get_logger(__name__)


def _model() -> str:
    """Live Q&A model. Defaults to gemini-2.5-flash for low latency."""
    try:
        from app.config import get_settings
        return get_settings().get("live_qa_model") or "gemini-2.5-flash"
    except Exception:
        return "gemini-2.5-flash"


def _flush_sentence(buf: str) -> tuple[str, str]:
    """
    Extract one complete sentence from the buffer.
    Returns (sentence, remainder). Empty sentence means not ready yet.
    Handles: '. ', '! ', '? ', '.\n'
    """
    import re
    m = re.search(r'([^.!?]*[.!?])[\s\n]', buf)
    if m:
        return buf[: m.end(1)].strip(), buf[m.end():].strip()
    return "", buf


# ─── Blocking Gemini call (post-meeting, fact-check) ─────────────────────────

async def generate_text(
    prompt: str,
    system: str | None = None,
    max_tokens: int = 16384,
    model_override: str | None = None,
    temperature: float = 0.3,
) -> str:
    """
    Blocking Gemini call in a thread. Retries on 429 with exponential backoff.
    max_tokens defaults to 16384 — no artificial cap on answer length.
    """
    from app.config import get_settings
    import vertexai
    from vertexai.generative_models import GenerativeModel, GenerationConfig
    from google.api_core.exceptions import ResourceExhausted

    s = get_settings()
    project = s["gcp_project"]
    location = s["gcp_location"] or "us-central1"
    model_id = model_override or str(s.get("vertex_gemini_model") or "gemini-2.5-pro")
    if not project:
        raise RuntimeError("GCP_PROJECT not set")

    log.debug("generate_text", model=model_id, max_tokens=max_tokens,
              prompt_chars=len(prompt))

    def _run() -> str:
        vertexai.init(project=project, location=location)
        model = GenerativeModel(
            model_id,
            system_instruction=system or "You are a precise AI meeting analyst. Follow all instructions exactly. Return only what is asked for.",
        )
        resp = model.generate_content(
            prompt,
            generation_config=GenerationConfig(
                max_output_tokens=max_tokens, temperature=temperature
            ),
        )
        return resp.text

    last_exc: Exception | None = None
    for attempt, wait in enumerate([0, 5, 15, 45]):
        if wait:
            log.warning("generate_text_429_retry", attempt=attempt,
                        wait_s=wait, model=model_id)
            await asyncio.sleep(wait)
        try:
            t0 = time.perf_counter()
            result = await asyncio.to_thread(_run)
            elapsed = int((time.perf_counter() - t0) * 1000)
            log.info("generate_text_done", model=model_id,
                     elapsed_ms=elapsed, chars=len(result))
            return result
        except ResourceExhausted as e:
            last_exc = e
            if attempt >= 3:
                raise
        except Exception:
            raise
    raise last_exc  # type: ignore


# ─── Streaming live Q&A ───────────────────────────────────────────────────────

async def answer_question_streaming(
    question: str,
    context_chunks: list[str],
    transcript: str | None,
    agent_name: str,
    persona: str | None,
    meeting_id: str = "",
) -> AsyncIterator[str]:
    """
    Stream Gemini answer sentence-by-sentence using google.genai SDK.

    Uses thinking_budget=128 (minimum allowed for gemini-2.5-pro) which cuts
    first-sentence latency from ~15s to ~3s by capping the thinking phase.

    - NO output token limit — the agent answers as fully as the question needs.
    - Each yielded string is one complete, speakable sentence.
    - Caller immediately converts each sentence to TTS MP3 and injects into call.
    """
    from app.config import get_settings
    s = get_settings()
    project = s["gcp_project"]
    location = s["gcp_location"] or "us-central1"
    if not project:
        raise RuntimeError("GCP_PROJECT not set")

    context_block = "\n\n---\n\n".join(context_chunks) if context_chunks else ""
    transcript_block = (transcript or "")[:16000]
    has_context = bool(context_chunks)
    has_transcript = bool(transcript_block.strip())

    # ── System instruction: base behavior + optional persona layered on top ──
    system = (
        f"You are {agent_name}, an AI copilot participating live in a corporate meeting. "
        "You are heard through the meeting's audio — your words are spoken aloud to everyone in the room via text-to-speech. "
        "The people in this meeting are discussing a project. You have access to the project's knowledge base.\n\n"

        "VOICE & TONE:\n"
        "- Speak like a sharp, confident colleague — not a chatbot.\n"
        "- Be direct. Lead with the answer, then explain if needed.\n"
        "- Use natural spoken language. No filler ('Sure!', 'Great question!', 'Absolutely!'). "
        "No hedging ('I think', 'It seems like', 'I believe'). No corporate fluff.\n"
        "- Vary sentence length. Mix short punchy statements with longer explanations.\n"
        "- Use contractions (it's, don't, we're) — you're speaking, not writing an essay.\n"
        "- You're in a professional meeting. Read the room from the transcript — match the formality level of the conversation.\n\n"

        "FORMAT RULES (critical — your output is read aloud by text-to-speech):\n"
        "- Plain sentences only. NO bullet points, numbered lists, markdown, headers, or special formatting.\n"
        "- NO parenthetical asides or bracketed text.\n"
        "- NEVER use special characters: no !, no *, no #, no @, no &, no (, no ), no [, no ], no {, no }.\n"
        "- Use periods and commas only for punctuation. Use question marks for questions.\n"
        "- Spell out abbreviations and acronyms on first use unless they've already been used in the meeting.\n"
        "- Numbers: say 'fifteen thousand' not '15,000'. Say 'twenty percent' not '20%'.\n"
        "- Symbols: say 'and' not '&'. Say 'at' not '@'. Say 'dollars' not '$'.\n"
        "- Don't say 'quote' or 'unquote' — just paraphrase naturally.\n"
        "- Write exactly how you want it spoken. The TTS engine reads every character literally.\n\n"

        "ACCURACY & GROUNDING:\n"
        "- Your primary source of truth is the KNOWLEDGE BASE provided below. This contains verified project documentation, specs, and context.\n"
        "- If the knowledge base answers the question, ground your response in it. Reference specific details: names, numbers, dates, milestones, section titles. "
        "Say things like 'According to the project spec...' or 'The roadmap shows...' or 'Based on the documentation...' — don't just vaguely summarize.\n"
        "- If the knowledge base does NOT cover the question, say so honestly: 'That's not covered in the project materials I have' — then offer what you do know, if relevant.\n"
        "- NEVER fabricate facts, statistics, dates, or names. If you're unsure, say so clearly.\n"
        "- Use the recent meeting transcript for conversational context — understand what's being discussed, who said what, and what was just asked. Don't repeat what someone just said.\n"
        "- If someone asks about something that was just discussed in the meeting, use both the transcript and the knowledge base to give the most helpful answer.\n\n"

        "RESPONSE LENGTH:\n"
        "- Match your response length to the question's complexity.\n"
        "- Simple factual question → one to three sentences.\n"
        "- Complex or open-ended question → a thorough spoken explanation, as long as it needs to be.\n"
        "- Don't pad short answers. Don't truncate long ones.\n"
        "- You're in a live meeting — everyone is waiting. Lead with the most important point first. "
        "If there's extensive detail, give the key answer then offer to elaborate rather than delivering everything unprompted.\n"
    )

    # Layer persona on top — it adds character/expertise, doesn't replace core behavior
    if persona:
        system += (
            "\nADDITIONAL PERSONA & EXPERTISE:\n"
            f"{persona}\n"
            "(Follow the persona above for your identity, expertise, and style — "
            "but always respect the format rules and accuracy guidelines above.)\n"
        )

    # ── User prompt: structured with clear sections ──
    prompt_parts = [f'QUESTION FROM THE MEETING:\n"{question}"']

    if has_context:
        prompt_parts.append(
            "KNOWLEDGE BASE (use this as your primary source — cite specific details from here):\n"
            f"{context_block}"
        )

    if has_transcript:
        prompt_parts.append(
            "RECENT MEETING TRANSCRIPT (use for conversational context — understand what's being discussed):\n"
            f"{transcript_block}"
        )

    prompt_parts.append(
        "Respond now. Speak directly to the room. "
        "Answer the question fully using the knowledge base where applicable."
    )

    prompt = "\n\n".join(prompt_parts)

    log.info("streaming_qa_start", meeting_id=meeting_id,
             agent=agent_name, model=_model(),
             context_chunks=len(context_chunks),
             question_chars=len(question))

    queue: asyncio.Queue[str | None] = asyncio.Queue()
    loop = asyncio.get_running_loop()
    t_start = time.perf_counter()
    sentence_count = [0]
    first_sentence_ms = [0]

    def _stream_worker() -> None:
        """
        Uses google.genai SDK with thinking_budget=128 (minimum allowed).
        This cuts first-text-chunk latency from ~15s to ~3s vs uncontrolled thinking.
        Chunks with no .text (thinking-only) are skipped via AttributeError/None check.
        """
        try:
            from google import genai
            from google.genai.types import GenerateContentConfig, ThinkingConfig

            from app.config import get_settings
            s = get_settings()
            project = s["gcp_project"]
            location = s["gcp_location"] or "us-central1"

            # Use SA key file if set; otherwise fall back to ADC (Cloud Run uses ADC)
            import os as _os
            creds_file = s.get("google_application_credentials") or _os.getenv(
                "GOOGLE_APPLICATION_CREDENTIALS", ""
            )
            if creds_file and _os.path.exists(creds_file):
                import google.oauth2.service_account as _sa
                _creds = _sa.Credentials.from_service_account_file(
                    creds_file,
                    scopes=["https://www.googleapis.com/auth/cloud-platform"],
                )
                client = genai.Client(
                    vertexai=True, project=project, location=location,
                    credentials=_creds,
                )
            else:
                client = genai.Client(vertexai=True, project=project, location=location)

            chunk_count = 0
            text_chunks = 0
            for chunk in client.models.generate_content_stream(
                model=_model(),
                contents=prompt,
                config=GenerateContentConfig(
                    max_output_tokens=8192,
                    temperature=0.7,
                    thinking_config=ThinkingConfig(thinking_budget=128),
                    system_instruction=system,
                ),
            ):
                chunk_count += 1
                text = getattr(chunk, "text", None)
                if text:
                    text_chunks += 1
                    loop.call_soon_threadsafe(queue.put_nowait, text)
            log.debug("stream_worker_done",
                      meeting_id=meeting_id,
                      total_chunks=chunk_count,
                      text_chunks=text_chunks)
        except Exception as e:
            log.exception("stream_worker_error", meeting_id=meeting_id, error=str(e))
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, None)

    loop.run_in_executor(None, _stream_worker)

    buf = ""
    while True:
        chunk = await queue.get()
        if chunk is None:
            break
        buf += chunk
        while True:
            sentence, buf = _flush_sentence(buf)
            if not sentence:
                break
            sentence_count[0] += 1
            elapsed = int((time.perf_counter() - t_start) * 1000)
            if sentence_count[0] == 1:
                first_sentence_ms[0] = elapsed
                log.info("first_sentence_ready",
                         meeting_id=meeting_id,
                         elapsed_ms=elapsed,
                         sentence_preview=sentence[:60])
            else:
                log.debug("sentence_ready",
                          meeting_id=meeting_id,
                          n=sentence_count[0],
                          elapsed_ms=elapsed)
            yield sentence

    # Yield any trailing text (no terminal punctuation — common at end of responses)
    remainder = buf.strip()
    if remainder:
        sentence_count[0] += 1
        yield remainder

    total_ms = int((time.perf_counter() - t_start) * 1000)
    log.info("streaming_qa_complete",
             meeting_id=meeting_id,
             sentences=sentence_count[0],
             first_sentence_ms=first_sentence_ms[0],
             total_ms=total_ms)


# ─── Non-streaming answer (/ask endpoint) ────────────────────────────────────

async def answer_question(
    question: str,
    context_chunks: list[str],
    transcript: str | None,
    agent_name: str,
    persona: str | None,
) -> str:
    """Non-streaming answer for the /ask endpoint (text response, not audio)."""
    context_block = "\n\n---\n\n".join(context_chunks) if context_chunks else ""
    transcript_block = (transcript or "")[:16000]
    has_context = bool(context_chunks)
    has_transcript = bool(transcript_block.strip())

    system = (
        f"You are {agent_name}, an AI meeting assistant. "
        "You answer questions using the knowledge base provided and the meeting transcript for context.\n\n"
        "RULES:\n"
        "- Ground your answers in the knowledge base. Use specific details from it.\n"
        "- If the knowledge base doesn't cover the question, say so clearly — don't make things up.\n"
        "- Be thorough but concise. No fluff, no filler.\n"
        "- Use the meeting transcript to understand conversational context.\n"
        "- Use clean prose. Markdown formatting is fine here (unlike audio responses).\n"
        "- Never fabricate facts, statistics, dates, or names.\n"
    )
    if persona:
        system += f"\nADDITIONAL PERSONA & EXPERTISE:\n{persona}\n"

    prompt_parts = [f'Question: "{question}"']
    if has_context:
        prompt_parts.append(f"KNOWLEDGE BASE:\n{context_block}")
    if has_transcript:
        prompt_parts.append(f"MEETING TRANSCRIPT:\n{transcript_block}")
    prompt_parts.append("Answer the question using the knowledge base. Be specific and accurate.")
    prompt = "\n\n".join(prompt_parts)

    return await generate_text(prompt, system=system, max_tokens=8192,
                               model_override=_model(), temperature=0.7)


# ─── Post-meeting intelligence ────────────────────────────────────────────────

async def generate_meeting_intelligence(transcript: str, agent_name: str) -> dict[str, Any]:
    """Full summary + action items + key decisions. Unlimited output length."""
    log.info("generate_intelligence_start", transcript_chars=len(transcript))

    system = (
        "You are a senior meeting analyst. Your job is to extract precise, actionable intelligence "
        "from meeting transcripts. You produce structured JSON output only."
    )

    prompt = (
        f"Analyze this meeting transcript and extract structured intelligence.\n\n"
        f"TRANSCRIPT:\n{transcript[:60000]}\n\n"
        "Return ONLY valid JSON (no markdown fences, no commentary) with this exact schema:\n\n"
        "{\n"
        '  "summary": "...",\n'
        '  "action_items": ["...", ...],\n'
        '  "key_decisions": ["...", ...]\n'
        "}\n\n"
        "FIELD INSTRUCTIONS:\n\n"
        "summary:\n"
        "- Write a detailed executive summary (3-8 paragraphs depending on meeting length).\n"
        "- Start with the meeting's primary purpose and outcome.\n"
        "- Cover every major topic discussed, in the order they came up.\n"
        "- Name the participants and attribute key points to who said them.\n"
        "- End with the overall outcome: what was resolved, what remains open.\n"
        "- Write in past tense, third person. Professional tone.\n\n"
        "action_items:\n"
        '- Format each as: "Owner: Task description (deadline if mentioned)"\n'
        "- Include every commitment, to-do, follow-up, or next step mentioned by anyone.\n"
        "- If an owner isn't clear, write 'TBD' as the owner.\n"
        "- Be specific — 'John: Send updated pricing deck to Sarah by Friday' not 'Follow up on pricing'.\n\n"
        "key_decisions:\n"
        "- Include every decision that was agreed upon or finalized during the meeting.\n"
        "- Be specific about what was decided, not vague.\n"
        "- 'Approved Q3 budget of $2.1M for the marketing team' not 'Budget was discussed'.\n"
        "- If a decision was deferred, don't include it here — it's not a decision yet.\n"
    )

    raw = await generate_text(prompt, system=system, max_tokens=16384, temperature=0.2)
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1]) if len(lines) > 2 else text
    try:
        result = json.loads(text)
        log.info("generate_intelligence_done",
                 summary_chars=len(result.get("summary", "")),
                 action_items=len(result.get("action_items", [])),
                 key_decisions=len(result.get("key_decisions", [])))
        return result
    except Exception:
        log.warning("intelligence_json_parse_failed", raw_preview=text[:200])
        return {"summary": text[:2000], "action_items": [], "key_decisions": []}


# ─── Fact-check ───────────────────────────────────────────────────────────────

async def fact_check(
    statement: str, context_chunks: list[str], agent_name: str
) -> dict[str, Any]:
    if not context_chunks:
        return {"contradicts": False, "correction": None}
    context_block = "\n\n---\n\n".join(context_chunks[:5])

    system = (
        f"You are {agent_name}, a fact-checking assistant in a live corporate meeting. "
        "The knowledge base contains verified project documentation. "
        "Your job is to catch factual errors and inaccuracies — statements that contradict "
        "or misrepresent information in the verified knowledge base. You speak corrections aloud to the room. "
        "Be helpful and diplomatic — you're correcting a colleague, not an opponent."
    )

    prompt = (
        "A participant in the meeting just said the following:\n\n"
        f'STATEMENT: "{statement}"\n\n'
        f"VERIFIED KNOWLEDGE BASE:\n{context_block[:8000]}\n\n"
        "TASK: Does this statement contain ANY factual inaccuracy when compared against the knowledge base?\n\n"
        "CHECK FOR:\n"
        "- Wrong numbers, dates, percentages, or statistics\n"
        "- Wrong names, titles, roles, or attributions\n"
        "- Incorrect technical facts or specifications\n"
        "- Misrepresented timelines, milestones, or deadlines\n"
        "- Confused or swapped details (e.g. saying X when the knowledge base says Y)\n"
        "- Claims about education, experience, or background that don't match the knowledge base\n\n"
        "RULES:\n"
        "- If the knowledge base has the correct info and the statement gets it wrong, flag it.\n"
        "- Do NOT flag opinions or predictions.\n"
        "- Do NOT flag topics not covered in the knowledge base at all.\n\n"
        "Return ONLY valid JSON (no markdown fences):\n"
        '{"contradicts": true/false, "correction": "spoken correction or null"}\n\n'
        "If contradicts is true, write the correction as a natural spoken sentence for the room. "
        "Be diplomatic: 'Actually, according to our records...' — keep it brief, one to two sentences."
    )

    raw = await generate_text(prompt, system=system, max_tokens=2048,
                              model_override=_model(), temperature=0.2)
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1])
    try:
        return json.loads(text)
    except Exception:
        return {"contradicts": False, "correction": None}


# ─── Embeddings ───────────────────────────────────────────────────────────────

async def embed_text(texts: list[str]) -> list[list[float]]:
    """Embed texts using Vertex AI text-embedding-004. Retries on 429 with backoff."""
    from app.config import get_settings
    import vertexai
    from vertexai.language_models import TextEmbeddingModel
    from google.api_core.exceptions import ResourceExhausted

    s = get_settings()
    project = s["gcp_project"]
    location = s["gcp_location"] or "us-central1"
    if not project:
        raise RuntimeError("GCP_PROJECT not set")

    log.debug("embed_text", count=len(texts))

    def _run() -> list[list[float]]:
        vertexai.init(project=project, location=location)
        model = TextEmbeddingModel.from_pretrained("text-embedding-004")
        results = model.get_embeddings(texts)
        return [r.values for r in results]

    last_exc: Exception | None = None
    for attempt, wait in enumerate([0, 3, 8, 20, 45]):
        if wait:
            log.warning("embed_text_429_retry", attempt=attempt,
                        wait_s=wait, count=len(texts))
            await asyncio.sleep(wait)
        try:
            t0 = time.perf_counter()
            result = await asyncio.to_thread(_run)
            log.debug("embed_text_done",
                      count=len(texts),
                      elapsed_ms=int((time.perf_counter() - t0) * 1000))
            return result
        except ResourceExhausted as e:
            last_exc = e
            if attempt >= 4:
                raise
        except Exception:
            raise
    raise last_exc  # type: ignore


# ─── Google Cloud TTS ─────────────────────────────────────────────────────────

# Persistent TTS client — avoids credential loading + gRPC channel setup per call
_tts_client: Any = None


def _get_tts_client() -> Any:
    global _tts_client
    if _tts_client is None:
        from google.cloud import texttospeech  # type: ignore
        _tts_client = texttospeech.TextToSpeechClient()
    return _tts_client


async def text_to_speech_mp3(
    text: str,
    voice_name: str = "en-US-Neural2-J",
    speaking_rate: float = 1.05,
) -> bytes:
    """Convert text to MP3 bytes using Google Cloud TTS Neural2.
    Uses a cached client to avoid re-init overhead on every call."""
    from google.cloud import texttospeech  # type: ignore

    # Sanitize text for TTS — strip chars that get read literally
    import re as _re
    clean = text
    clean = _re.sub(r'[*#@&\[\]{}()<>|\\~`^]', '', clean)  # remove special chars
    clean = clean.replace('!', '.').replace(';', ',')  # replace ! with period, ; with comma
    clean = _re.sub(r'\s+', ' ', clean).strip()  # collapse whitespace

    log.debug("tts_start", chars=len(clean), voice=voice_name)
    client = _get_tts_client()

    def _run() -> bytes:
        synthesis_input = texttospeech.SynthesisInput(text=clean[:4096])
        voice = texttospeech.VoiceSelectionParams(
            language_code="-".join(voice_name.split("-")[:2]),
            name=voice_name,
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=speaking_rate,
            pitch=0.0,
        )
        response = client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )
        return response.audio_content

    t0 = time.perf_counter()
    result = await asyncio.to_thread(_run)
    log.debug("tts_done",
              chars=len(text),
              voice=voice_name,
              bytes=len(result),
              elapsed_ms=int((time.perf_counter() - t0) * 1000))
    return result


# ─── Instant acknowledgement ──────────────────────────────────────────────────

_ACK_PHRASES = [
    "On it.", "Sure.", "Let me check.", "One moment.", "Got it.",
    "Good question, let me answer that.", "Sure, here's what I know.",
]

# Cache: voice_name → { phrase: mp3_bytes }
_ack_cache: dict[str, dict[str, bytes]] = {}


async def thinking_acknowledgement(voice_name: str) -> bytes:
    """
    Short phrase injected instantly when a trigger fires, before Gemini responds.
    Cached per voice — subsequent calls return pre-synthesized audio (~0ms).
    """
    phrase = random.choice(_ACK_PHRASES)
    log.debug("ack_phrase", phrase=phrase)

    voice_cache = _ack_cache.get(voice_name, {})
    if phrase in voice_cache:
        log.debug("ack_cache_hit", phrase=phrase, voice=voice_name)
        return voice_cache[phrase]

    mp3 = await text_to_speech_mp3(phrase, voice_name, speaking_rate=1.1)
    _ack_cache.setdefault(voice_name, {})[phrase] = mp3
    return mp3
