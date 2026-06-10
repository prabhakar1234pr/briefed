"""Focused test for the TurnGate SPEAKING-deadlock fix (no meeting/keys needed).

Reproduces the prod bug: the gate sits upstream of the LLM, so it never sees
LLMFullResponseEndFrame and used to stick in SPEAKING after the first answer →
every later non-name utterance was silently dropped → the bot went mute.

Verifies:
  1. notify_response_complete() (the signal the native injector now sends) takes
     the gate back to IDLE so a SECOND, non name-addressed question is answered.
  2. The watchdog forces IDLE even if that signal is never sent.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipecat.frames.frames import TranscriptionFrame
from pipecat.processors.frame_processor import FrameDirection

from app.pipeline.turn_gate import TurnGate


class FakeContext:
    def __init__(self):
        self.turns = []

    async def append_turn(self, who, text):
        self.turns.append((who, text))

    async def recent_turns_text(self, n=8):
        return [f"{w}: {t}" for w, t in self.turns[-n:]]

    async def gather_for_qa(self, text, top_k=5):
        return {"knowledge": [], "prior_meetings": []}


class FakeSession:
    def __init__(self):
        self.meeting_id = "test-meeting"
        self.controls = []
        self.turn_gate = None

    def push_control(self, msg):
        self.controls.append(msg)


def make_gate(monkeypatch_classify=None):
    sess = FakeSession()
    ctx = FakeContext()
    gate = TurnGate(session=sess, context=ctx, agent_name="Bora")
    # The gate isn't inside a running pipeline, so its FrameProcessor task
    # manager isn't wired. Route create_task to the live loop directly, and
    # capture frames it pushes downstream instead of forwarding them.
    gate.create_task = lambda coro, *a, **k: asyncio.create_task(coro)
    pushed = []

    async def _capture_push(frame, direction=FrameDirection.DOWNSTREAM):
        pushed.append((frame, direction))

    gate.push_frame = _capture_push
    gate._pushed = pushed
    return gate, sess, ctx


def tf(text):
    return TranscriptionFrame(text=text, user_id="speaker", timestamp="")


def released_questions(gate):
    """Questions the gate forwarded to the LLM (TranscriptionFrames pushed down)."""
    return [f.text for f, d in gate._pushed if isinstance(f, TranscriptionFrame)]


async def test_deadlock_reset():
    """Answer a name-addressed Q, signal completion, then a NON-name question
    must still be answered (the bug dropped it)."""
    import app.pipeline.turn_gate as tg

    # Force the addressed-classifier to say "addressed" so the 2nd (no-name)
    # question is a clean test of the gate state, not the classifier.
    async def fake_classify(agent_name, utterance, recent_turns):
        return True, 0.99
    orig = tg.classify_addressed
    tg.classify_addressed = fake_classify
    try:
        gate, sess, _ = make_gate()

        # 1) Direct name-addressed question → answered, gate enters SPEAKING.
        await gate._on_final_transcript(tf("Bora, what's the deadline?"))
        assert gate._state == TurnGate.SPEAKING, f"expected SPEAKING, got {gate._state}"
        assert "what's the deadline" in " ".join(released_questions(gate)).lower()

        # 2) Reply finishes → the native injector signals completion.
        gate.notify_response_complete()
        await asyncio.sleep(0.05)  # let the scheduled _finish_speaking run
        assert gate._state == TurnGate.IDLE, f"gate stuck in {gate._state} after reply!"

        # 3) A NON name-addressed question — the one the bug silently dropped.
        before = len(released_questions(gate))
        await gate._on_final_transcript(tf("How many users do we have?"))
        await asyncio.sleep(0.05)  # _maybe_answer_question runs as a task
        after = len(released_questions(gate))
        assert after == before + 1, "2nd (no-name) question was NOT answered — still deadlocked!"
        print("PASS test_deadlock_reset: 2nd non-name question answered after reply completed")
    finally:
        tg.classify_addressed = orig


async def test_watchdog_backstop():
    """Even with NO completion signal, the watchdog must force IDLE."""
    gate, sess, _ = make_gate()
    gate._speaking_max_secs = 0.2  # shrink for the test
    gate._enter_speaking()
    assert gate._state == TurnGate.SPEAKING
    await asyncio.sleep(0.4)  # > watchdog timeout, no notify sent
    assert gate._state == TurnGate.IDLE, f"watchdog failed to reset; gate in {gate._state}"
    print("PASS test_watchdog_backstop: watchdog reset SPEAKING -> IDLE with no signal")


async def main():
    await test_deadlock_reset()
    await test_watchdog_backstop()
    print("\nALL TESTS PASSED")


if __name__ == "__main__":
    asyncio.run(main())
