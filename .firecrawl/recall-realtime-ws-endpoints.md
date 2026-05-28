For AI agents: visit https://docs.recall.ai/llms.txt for an index of all pages formatted in Markdown and endpoints in OpenAPI.

In addition to [Webhooks](https://docs.recall.ai/docs/real-time-webhook-endpoints), Recall.ai supports receiving data in real-time via a websocket connection.

You can register a websocket real-time endpoint during data source creation (for instance, when [Creating a Bot](https://docs.recall.ai/reference/bot_create), specifying the specific events you want to receive.

> 📘
>
> Real-time websocket endpoints are for receiving in-call events and data in realtime, such as audio buffers, transcripts, and participant events.
>
> For lifecycle status events, see:
>
> - [Recording Webhooks](https://docs.recall.ai/docs/recording-webhooks)
> - [Bot Webhooks](https://docs.recall.ai/docs/bot-status-change-events)

# Event Types   [Skip link to Event Types](https://docs.recall.ai/docs/real-time-websocket-endpoints\#event-types)

Real-time websocket endpoints can subscribe to all of the following events:

| Event | Description | Payload |
| --- | --- | --- |
| `participant_events.join` | A participant joined. | [Schema](https://docs.recall.ai/docs/real-time-event-payloads#participant_events) |
| `participant_events.leave` | A participant left. | [Schema](https://docs.recall.ai/docs/real-time-event-payloads#participant_events) |
| `participant_events.update` | A participant updated their details. | [Schema](https://docs.recall.ai/docs/real-time-event-payloads#participant_events) |
| `participant_events.speech_on` | A participant started speaking. | [Schema](https://docs.recall.ai/docs/real-time-event-payloads#participant_events) |
| `participant_events.speech_off` | A participant stopped speaking. | [Schema](https://docs.recall.ai/docs/real-time-event-payloads#participant_events) |
| `participant_events.webcam_on` | A participant turned on their webcam. | [Schema](https://docs.recall.ai/docs/real-time-event-payloads#participant_events) |
| `participant_events.webcam_off` | A participant turned off their webcam. | [Schema](https://docs.recall.ai/docs/real-time-event-payloads#participant_events) |
| `participant_events.screenshare_on` | A participant started screen sharing. | [Schema](https://docs.recall.ai/docs/real-time-event-payloads#participant_events) |
| `participant_events.screenshare_off` | A participant stopped screen sharing. | [Schema](https://docs.recall.ai/docs/real-time-event-payloads#participant_events) |
| `participant_events.chat_message` | A participant sent a chat message. | [Schema](https://docs.recall.ai/docs/real-time-event-payloads#participant_events) |
| `transcript.data` | A transcript utterance was generated (see [Real-time Transcription](https://docs.recall.ai/docs/real-time-transcription) | [Schema](https://docs.recall.ai/docs/real-time-event-payloads#transcriptdata) |
| `transcript.partial_data` | A partial transcript utterance was generated (see [Real-time Transcription](doc:bot-real-time-transcription#/partial-results) | [Schema](doc:real-time-event-payloads#/transcriptpartial_data) |
| `transcript.provider_data` | A transcript utterance produced directly by the underlying transcription provider was generated (see [AI transcription](https://docs.recall.ai/docs/ai-transcription#how-to-get-custom-fields-from-your-transcription-provider)) |  |
| `audio_mixed_raw.data` | A mixed audio buffer was generated from the call. | [Schema](https://docs.recall.ai/docs/real-time-event-payloads#audio_mixed_rawdata) |
| `audio_separate_raw.data` | A separate audio buffer was generated from the call. | [Schema](https://docs.recall.ai/docs/real-time-event-payloads#audio_separate_rawdata) |
| `video_separate_png.data` | A separate video buffer was generated from the call. | [Schema](https://docs.recall.ai/docs/real-time-event-payloads#video_separate_pngdata) |
| `video_separate_h264.data` | A separate h264 video buffer was generated from the call. | [Schema](https://docs.recall.ai/docs/real-time-event-payloads#video_separate_h264data) |

# Setup & Configuration   [Skip link to Setup & Configuration](https://docs.recall.ai/docs/real-time-websocket-endpoints\#setup--configuration)

* * *

## Bots   [Skip link to Bots](https://docs.recall.ai/docs/real-time-websocket-endpoints\#bots)

To configure a real-time websocket endpoint for a bot, add a real time endpoint to your [Create Bot](https://docs.recall.ai/reference/bot_create) request with the `type` set to `websocket`:

cURL

```curl
curl --request POST \
     --url https://us-east-1.recall.ai/api/v1/bot/ \
     --header "Authorization: $RECALLAI_API_KEY" \
     --header "accept: application/json" \
     --header "content-type: application/json" \
     --data '
{
  "meeting_url": "https://meet.google.com/sde-zixx-iry",
  "recording_config": {
	  "realtime_endpoints": [\
      {\
        "type": "websocket",\
        "url": "wss://my-app.com/api/ws/audio",\
        "events": ["audio_mixed_raw.data"]\
      }\
    ]
  }
}
'
```

The above request creates a bot and registers a real-time websocket endpoint to receive `audio_mixed_raw.data` events at the following URL: `wss://my-app.com/api/ws/audio`

> 📘
>
> The `config.url` must be either a `ws` or `wss` endpoint.

> ❗️
>
> ### Limited support for verification on the Desktop SDK   [Skip link to Limited support for verification on the Desktop SDK](https://docs.recall.ai/docs/real-time-websocket-endpoints\#limited-support-for-verification-on-the-desktop-sdk)
>
> Verification is not currently supported on real-time webhook/websockets from the Desktop SDK. Async webhooks for the Desktop SDK are fully supported.

# Verification   [Skip link to Verification](https://docs.recall.ai/docs/real-time-websocket-endpoints\#verification)

Since your websocket receiver must be accessible at a publicly exposed endpoint, you should add a verification mechanism to ensure you only process requests coming from Recall.

There are two ways to verify the webhook:

1. Add a [secret to your workspace](https://docs.recall.ai/docs/verify-events#/) to receive headers with a cryptographic signature on every request
2. Add a token as a query parameter in the endpoint's URL, such as `?token=some-random-token`. When we make the request to your endpoint, we will use the **exact** url, including any query parameters. You will then be able to verify the query parameter in your server's webhook handler, and reject any requests that do not contain your secret/token value. Note that when constructing this URL, you must include a trailing `/` before adding any query parameters. If you do not, your request will fail with HTTP 400.

Whenever possible, we recommend the first approach as this offers industry-standard levels of security, and allows you to update the authentication without downtime.

# Retry Policy   [Skip link to Retry Policy](https://docs.recall.ai/docs/real-time-websocket-endpoints\#retry-policy)

Recall attemps to maintain a persistent WebSocket connection and will retry automatically upon connection failure using the following policy:

**Retry condition**: A retry is triggered when the WebSocket connection fails due to:

- Network interruptions
- Server-side disconnects
- Failed connection handshake

**Retry limit**: A maximum of 30 retry attempts are made per connection failure incident.

**Backoff strategy**: Each retry is delayed by a fixed **3-second interval**.

**Dropping behavior**: If all **30 attempts fail**, the realtime endpoint is marked as `failed` and no further messages are delivered

There's no way to manually retry real-time websocket endpoint events via dashboard or API outside of this automatic retry policy.

# FAQ   [Skip link to FAQ](https://docs.recall.ai/docs/real-time-websocket-endpoints\#faq)

## Why does the WebSocket connection close unexpectedly?   [Skip link to Why does the WebSocket connection close unexpectedly?](https://docs.recall.ai/docs/real-time-websocket-endpoints\#why-does-the-websocket-connection-close-unexpectedly)

This will appear in the dashboard logs as Connection closed by peer and typically means your application closed the WebSocket connection. If unexpected, the likely cause is that a load balancer or reverse proxy has an idle timeout and closes the connection after that period.

To fix this, increase the WebSocket timeout or send a ping to the server every 30 seconds to keep the connection alive.

Updated14 days ago

* * *

Did this page help you?

Yes

No

Copy Page

Sign in to Recall for advanced AI debugging

Use Ask AI for public Recall docs. Sign in later if you need workspace debugging.

Anonymous (docs only) (anonymous)US East 1 (us-east-1)US West 2 (us-west-2)EU Central 1 (eu-central-1)AP Northeast 1 (ap-northeast-1)Continue with docs-only Ask AI

Ask AI![](https://files.readme.io/2f4ba7b-small-favicon.png)