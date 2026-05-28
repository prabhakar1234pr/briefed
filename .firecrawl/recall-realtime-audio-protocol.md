For AI agents: visit https://docs.recall.ai/llms.txt for an index of all pages formatted in Markdown and endpoints in OpenAPI.

> 🚧
>
> # Important: This guide only applies to workspaces with v1.10 API access   [Skip link to Important: This guide only applies to workspaces with v1.10 API access](https://docs.recall.ai/v1.10/docs/real-time-audio-protocol\#important-this-guide-only-applies-to-workspaces-with-v110-api-access)
>
> **The v1.10 API is only available to Recall accounts created before May 28, 2025**.
>
> Do not use this documentation unless the workspace has access to the v1.10 API. If the workspace creation date is unknown, stop and clarify. All other workspaces must use the [v1.11 API](https://docs.recall.ai/v1.10/docs/getting-started) documentation instead.

> 📘
>
> To start receiving real time audio streams, you need to include your websocket URL in [create\_bot.real\_time\_media .websocket\_audio\_destination\_url](https://recallai.readme.io/reference/bot_create).
>
> This URL should have a `ws://` or `wss://` prefix depending on your server's requirements. We highly recommend using the websocket protocol over SSL/TLS (`wss`) since the connection is encrypted and much more secure.

# Real Time Audio Protocol (Combined Streams)   [Skip link to Real Time Audio Protocol (Combined Streams)](https://docs.recall.ai/v1.10/docs/real-time-audio-protocol\#real-time-audio-protocol-combined-streams)

> 📘
>
> Combined audio streams are available on the [Zoom Web Bot](https://recallai.readme.io/reference/zoom#zoom-web), [Microsoft Teams Web Bot](https://recallai.readme.io/reference/microsoft-teams#ms-teams-web), [Google Meet Bot](https://recallai.readme.io/reference/google-meet), and [Webex Bot](https://recallai.readme.io/reference/webex).

The first message on websocket connection will be:

```undefined
{
  protocol_version: 1,
  bot_id: '...',
  recording_id: '...',
  separate_streams: false,
  offset: 0.0
}
```

The `offset` is the offset (in seconds) relative to the `in_call_recording` event on the bot.

The following websocket messages will be in binary format as follows:

- All data in the websocket packet is S16LE format audio, sampled at 16000Hz, mono

Python

```python
import asyncio
import websockets

async def echo(websocket):
    async for message in websocket:
        if isinstance(message, str):
            print(message)
        else:
            with open(f'output/output.raw', 'ab') as f:
                f.write(message)
                print("wrote message")

async def main():
    async with websockets.serve(echo, "0.0.0.0", 8765):
        await asyncio.Future()

asyncio.run(main())
```

# Real Time Audio Protocol (Separate Streams)   [Skip link to Real Time Audio Protocol (Separate Streams)](https://docs.recall.ai/v1.10/docs/real-time-audio-protocol\#real-time-audio-protocol-separate-streams)

> 📘
>
> Separate audio streams per participant are only available on the [Zoom Bot](https://recallai.readme.io/reference/zoom#zoom-web), [Microsoft Teams Bot](https://recallai.readme.io/reference/microsoft-teams#ms-teams-web), and [Google Meet Bots](https://recallai.readme.io/reference/google-meet) under a feature flag. Reach out to the Recall team over Slack if you'd like this enabled for your workspace.

When using separate-stream audio, participant audio streams will be separated via their own websocket connection.

The first message on each connection will be:

JSON

```json
{
  protocol_version: 1,
  bot_id: '...',
  recording_id: '...',
  separate_streams: true,
  offset: 0.0 // Offset (in seconds) relative to the `in_call_recording` event on the bot
}
```

The following websocket messages will be in binary format as follows:

- First 32 bits are a little-endian unsigned integer representing the `participant_id`.
- The remaining data in the websocket packet is S16LE format audio, sampled at 16000Hz, mono

The following is sample code to decode these messages:

Python

```python
import asyncio
import websockets

async def echo(websocket):
    async for message in websocket:
        if isinstance(message, str):
            print(message)
        else:
            stream_id = int.from_bytes(message[0:4], byteorder='little')
            with open(f'output/{stream_id}-output.raw', 'ab') as f:
                f.write(message[4:])
                print("wrote message")

async def main():
    async with websockets.serve(echo, "0.0.0.0", 8765):
        await asyncio.Future()

asyncio.run(main())
```

> 📘
>
> ### Important: Separate audio streams connecting behavior   [Skip link to Important: Separate audio streams connecting behavior](https://docs.recall.ai/v1.10/docs/real-time-audio-protocol\#important-separate-audio-streams-connecting-behavior)
>
> In unmixed audio, participants' audio streams connect and disconnect to your websocket endpoint according to their mute state.
>
> For instance, a participant that remains muted on the call will only have a corresponding websocket connection attempt to connect to your endpoint upon unmuting. When muting again, their corresponding websocket connection will be closed.

> 🚧
>
> Separate audio streams is a compute heavy feature and **we recommend using 4 core bots** to ensure the bot has enough resources to process the separate streams

# FAQ   [Skip link to FAQ](https://docs.recall.ai/v1.10/docs/real-time-audio-protocol\#faq)

* * *

## Do muted participants produce audio?   [Skip link to Do muted participants produce audio?](https://docs.recall.ai/v1.10/docs/real-time-audio-protocol\#do-muted-participants-produce-audio)

- For mixed audio, we will send empty audio packets when all participants are silent or muted.
- For unmixed audio, muted participants do not produce any audio packets.

If a participant is _unmuted_ but silent, you will receive empty audio packets.

## Will bots receive audio from other bots?   [Skip link to Will bots receive audio from other bots?](https://docs.recall.ai/v1.10/docs/real-time-audio-protocol\#will-bots-receive-audio-from-other-bots)

Since bots are participants, if there are other bots in a call, the bot will receive audio from the bot like any other participant.

Since bots are muted by default, unless another bot is [outputting audio](https://docs.recall.ai/v1.10/reference/bot_output_audio_create), the bot will not receive audio packets from other bots.

## What is the retry behavior?   [Skip link to What is the retry behavior?](https://docs.recall.ai/v1.10/docs/real-time-audio-protocol\#what-is-the-retry-behavior)

If we are unable to connect to your endpoint, or are disconnected, we will re-try the connection every 3 seconds, while the bot is alive.

Updated about 2 months ago

* * *

Did this page help you?

Yes

No

Copy Page

Sign in to Recall for advanced AI debugging

Use Ask AI for public Recall docs. Sign in later if you need workspace debugging.

Anonymous (docs only) (anonymous)US East 1 (us-east-1)US West 2 (us-west-2)EU Central 1 (eu-central-1)AP Northeast 1 (ap-northeast-1)Continue with docs-only Ask AI

Ask AI![](https://files.readme.io/2f4ba7b-small-favicon.png)