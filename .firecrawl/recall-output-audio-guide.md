For AI agents: visit https://docs.recall.ai/llms.txt for an index of all pages formatted in Markdown and endpoints in OpenAPI.

Recall bots can speak back into the meeting in two different ways, depending on your use case:

- **Agent / back-and-forth conversations (longer audio):** use **[Output Media](https://docs.recall.ai/reference/bot_output_media_create)** to send longer audio responses into the meeting (commonly used for voice agents).
- **Short, predefined audio clips (e.g., a greeting or disclaimer):**
  - **Automatic audio output** (configure the bot to play audio when recording starts, and optionally replay when participants join), or
  - **Call the [Output Audio](https://docs.recall.ai/reference/bot_output_audio_create) endpoint** (trigger a short clip on-demand via API).

## Dynamic Speech and Conversations: Output Media   [Skip link to Dynamic Speech and Conversations: Output Media](https://docs.recall.ai/docs/output-audio-in-meetings\#dynamic-speech-and-conversations-output-media)

> 📘
>
> This is recommended for use cases with agents

Use **[Output Media](https://docs.recall.ai/reference/bot_output_media_create)** when you need the bot to **speak back into the meeting as part of an ongoing interaction**, such as:

- Back-and-forth conversational flows via voice-agents
- Scenarios where you want to send/receive longer audio clips over time (e.g. playing an audio clip)

## Short, Predefined Audio Clips   [Skip link to Short, Predefined Audio Clips](https://docs.recall.ai/docs/output-audio-in-meetings\#short-predefined-audio-clips)

Short clips are best for things like:

- A greeting / introduction
- A compliance message (e.g., “This meeting is being recorded”)
- A short announcement

You can deliver short clips either automatically (configuration) or manually (API call).

### Platform Support   [Skip link to Platform Support](https://docs.recall.ai/docs/output-audio-in-meetings\#platform-support)

| Platform | Available |
| --- | --- |
| Zoom | ✅ |
| Google Meet | ✅ |
| Microsoft Teams | ✅ |
| Cisco Webex | ✅ |
| Slack Huddles | ❌ |

### Audio Format   [Skip link to Audio Format](https://docs.recall.ai/docs/output-audio-in-meetings\#audio-format)

Audio should be provided as an **mp3 encoded as a base 64 string**.

MP3 files can easily be converted to a b64 string using CLI tools such as [ffmpeg](https://ffmpeg.org/) or an online tool such as [b64Guru](https://base64.guru/converter/encode/audio/mp3).

### Option 1: `automatic_audio_output` (play on recording start, optionally replay when participants join)   [Skip link to Option 1: ,[object Object], (play on recording start, optionally replay when participants join)](https://docs.recall.ai/docs/output-audio-in-meetings\#option-1-automatic_audio_output-play-on-recording-start-optionally-replay-when-participants-join)

[Create Bot](https://docs.recall.ai/reference/bot_create) accepts an `automatic_audio_output` configuration for automatically outputting audio when the bot starts recording, with the option to repeat the audio when participants join.

`data` allows you to specify the mp3 the bot should play:

- `kind` \- The type of data encoded in the b64 string (Currently only `mp3` is supported)
- `b64_data` \- Data encoded in Base64 format, using the standard alphabet (as specified [here](https://datatracker.ietf.org/doc/html/rfc4648#section-4))

`replay_on_participant_join` can be optionally used to repeat the audio whenever someone joins:

- `debounce_mode`: Debounce mode ("trailing" or "leading")

  - `leading`: The debounce timer will start counting down when the first participant joins.
  - `trailing`: The debounce timer will start counting down when the last participant joins.
- `debounce_interval`: The amount of time to wait for additional participants to join before replaying the audio.
- `disable_after`: The number of seconds after which the audio will no longer replay when new participants join. This parameter is useful to prevent the bot from interrupting a meeting, if a late participant joins.

**`automatic_audio_output` example**

JSON

```json
// POST https://us-east-1.recall.ai/api/v1/bot/
{
  "automatic_audio_output": {
    "in_call_recording": {
      "data": {
        "kind": "mp3",
        "b64_data": "..."
      },
      "replay_on_participant_join": {
        "debounce_mode": "trailing",
        "debounce_interval": 10,
        "disable_after": 60
      }
    }
  },
  ...
}
```

Using the above configuration as an example, let's say we have the following scenario:

- Participant 1 is there a bit early and joins right before the bot starts recording.
- 5 seconds after recording starts, Participant 2 joins.
- 5 seconds later, Participant 3 joins.
- Participant 4 is running late, and joins the call three minutes after recording starts.

In this scenario, Participants 1 and 4's experiences are fairly straightforward:

- Participant 1 hears the audio played when the bot starts recording.
- Participant 4 never hears the audio played since they joined 180 seconds after the bot started recording, which is greater than the `disable_after` value of 60.

Participants 2 and 3 will experience something slightly different based on the `debounce_mode`:

- In `trailing` mode, the audio would play 10 seconds after Participant 3 joins (15 seconds after Participant 2 joins).
- If we set the `debounce_mode` to `leading`, however, the audio will play 10 seconds after Participant 2 joins (5 seconds after Participant 3 joins).

### Option 2: Output Audio endpoint (trigger on-demand via API)   [Skip link to Option 2: Output Audio endpoint (trigger on-demand via API)](https://docs.recall.ai/docs/output-audio-in-meetings\#option-2-output-audio-endpoint-trigger-on-demand-via-api)

If your use case requires more manual control over outputting the audio clip, you can use the [Output Audio](https://docs.recall.ai/reference/bot_output_audio_create) endpoint.

This endpoint takes the same parameters as the configuration objects above:

JSON

```json
// POST https://us-west-2.recall.ai/api/v1/bot/{id}/output_audio/
{
  "kind": "mp3",
  "b64_data": "..." // b64 encoded string
}
```

> 📘
>
> To use the [Output Audio](https://docs.recall.ai/reference/bot_output_audio_create) endpoint, currently bots must be configured with an `automatic_audio_output` in the [Create Bot](https://docs.recall.ai/reference/bot_create) request.
>
> If you do not wish to leverage any automatic audio output, and just want to use the endpoint, we recommend adding a short silent mp3 file as the `b64_data` in this configuration.

Updated4 months ago

* * *

Did this page help you?

Yes

No

Copy Page

Sign in to Recall for advanced AI debugging

Use Ask AI for public Recall docs. Sign in later if you need workspace debugging.

Anonymous (docs only) (anonymous)US East 1 (us-east-1)US West 2 (us-west-2)EU Central 1 (eu-central-1)AP Northeast 1 (ap-northeast-1)Continue with docs-only Ask AI

Ask AI![](https://files.readme.io/2f4ba7b-small-favicon.png)