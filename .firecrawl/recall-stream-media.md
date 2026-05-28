For AI agents: visit https://docs.recall.ai/llms.txt for an index of all pages formatted in Markdown and endpoints in OpenAPI.

Output Media lets your app control what the bot outputs into a live meeting, for both audio and video. It’s the main API for building bots that “speak” and “show” content in the call.

With Output Media, the bot can play audio responses and update its video output with MP4s or GIFs, both with low latency in real-time. You can use it for interactive agents that react/respond in real time, or for simpler use cases like playing a specific audio clip or video at the moment you choose. The bot will output the content via the bot's camera feed or the bot's screenshare.

Some popular use cases for output media is to power AI sales agents, coaches, recruiters, interviewers, screenshare slides/videos, and more.

For example implementations and use cases, see our demo repos:

- [AI Voice Agent Demo](https://github.com/recallai/voice-agent-demo)
- [Real-time Translator Demo](https://github.com/recallai/real-time-translator-demo)
- [HeyGen Live Avatar Demo](https://github.com/recallai/sample-apps/tree/main/bot_output_media_heygen_avatar)

Recall.ai Output Media API: send AI agents to your meetings - YouTube

Tap to unmute

[Recall.ai Output Media API: send AI agents to your meetings](https://www.youtube.com/watch?v=YzzzqPpL47o) [RecallAI](https://www.youtube.com/channel/UCQXsakK2EQOF4qrTsEbyZHg)

RecallAI296 subscribers

[Watch on](https://www.youtube.com/watch?v=YzzzqPpL47o)

## Platform Support   [Skip link to Platform Support](https://docs.recall.ai/docs/stream-media\#platform-support)

| Platform | Bot Configuration ( `output_media` ) |
| --- | --- |
| Zoom | ✅ |
| Google Meet | ✅ |
| Microsoft Teams | ✅ |
| Cisco Webex | ✅ |
| Slack Huddles | ❌ |

## Quickstart   [Skip link to Quickstart](https://docs.recall.ai/docs/stream-media\#quickstart)

### How output media works   [Skip link to How output media works](https://docs.recall.ai/docs/stream-media\#how-output-media-works)

Output Media works by having the bot run a webpage you control and then stream that page’s audio and video into the meeting. The bot can present the webpage either as a screenshare or as its camera video, so whatever your page renders is what participants see and hear.

> 📘
>
> ### Why Use a Webpage?   [Skip link to Why Use a Webpage?](https://docs.recall.ai/docs/stream-media\#why-use-a-webpage)
>
> A webpage gives developers an easy and familiar interface to create real-time audio and visual responses: you can update charts, render an avatar, or play synthesized speech, all using standard HTML/CSS/JavaScript.

The bot will send your webpage the following data in real-time:

- A stream of audio data from the meeting
- The transcripts for the audio data (if configured)

Which you can then pass to third party speech-to-speech models or other LLMs to process/analyze. Then you can play audio/video on the webpage and the bot will stream it back into the meeting.

### Starting Output Media automatically when bot joins via the Create Bot API   [Skip link to Starting Output Media automatically when bot joins via the Create Bot API](https://docs.recall.ai/docs/stream-media\#starting-output-media-automatically-when-bot-joins-via-the-create-bot-api)

You can use the `output_media` configuration in the [Create Bot](https://docs.recall.ai/reference/bot_create) endpoint to stream the audio and video contents of a webpage to your meeting. The bot can display the webpage either as a screen-share, or directly through its own camera.

`output_media` takes the following parameters:

- `kind`: The type of media to stream (currently only `webpage` is supported)
- `config`: The webpage configuration (currently only supports `url`)

Let's look at an example call to the [Create Bot](https://docs.recall.ai/reference/bot_create) endpoint:

JSON

```json
// POST /api/v1/bot/
{
  "meeting_url": "https://us02web.zoom.us/j/1234567890",
  "bot_name": "Recall.ai Notetaker",
  "output_media": {
    "camera": {
      "kind": "webpage",
      "config": {
        "url": "https://www.recall.ai"
      }
    }
  }
}
```

The example above tells Recall to create a bot that will continuously stream the contents of the Recall.ai homepage to the provided meeting URL.

### Starting Output Media manually via the Start Output Media API   [Skip link to Starting Output Media manually via the Start Output Media API](https://docs.recall.ai/docs/stream-media\#starting-output-media-manually-via-the-start-output-media-api)

You can also choose to start streaming a webpage by calling the [Output Media](https://docs.recall.ai/reference/bot_output_media_create) endpoint at any time while the bot is in a call.

The parameters for the request are the same as the `output_media` configuration.

cURL

```curl
curl --request POST \
     --url https://us-west-2.recall.ai/api/v1/bot/{bot_id}/output_media/ \
     --header 'Authorization: ${RECALL_API_KEY}' \
     --header 'accept: application/json' \
     --header 'content-type: application/json' \
     --data-raw '
{
    "camera": {
      "kind": "webpage",
      "config": {
        "url": "https://recall.ai"
      }
    }
}
'
```

### Stopping Output Media via the API   [Skip link to Stopping Output Media via the API](https://docs.recall.ai/docs/stream-media\#stopping-output-media-via-the-api)

You can stop the bot's media output at any point while the bot is streaming media by calling the [Stop Output Media](https://docs.recall.ai/reference/bot_output_video_destroy) endpoint.

cURL

```curl
curl --request DELETE \
     --url https://us-west-2.recall.ai/api/v1/bot/{bot_id}/output_media/ \
     --header 'Authorization: ${RECALL_API_KEY}' \
     --header 'accept: application/json' \
     --header 'content-type: application/json'
     --data-raw '{ "camera": true }'
```

The above will make the bot stop screensharing or outputting video from camera, essentially stopping `output_media`.

## Making the bot interactive   [Skip link to Making the bot interactive](https://docs.recall.ai/docs/stream-media\#making-the-bot-interactive)

So far you've seen how to stream any webpage to a meeting. But to build a real AI agent, you need a webpage that can listen to the information coming from meeting and respond dynamically. This means creating a webpage that can receive live meeting data and update in real time.

### Setting up your development environment   [Skip link to Setting up your development environment](https://docs.recall.ai/docs/stream-media\#setting-up-your-development-environment)

For development, you'll want to be able to iterate quickly on your webpage and see changes reflected immediately in the bot. The easiest way to do this is:

1. Run a local development server with your webpage. You can either create your own or clone one of our sample repos ( [Real-Time Translator](https://github.com/recallai/real-time-translator-demo), [Voice Agent](https://github.com/recallai/voice-agent-demo))
2. Expose it publicly using a [tunneling service like Ngrok](https://docs.recall.ai/reference/local-webhook-development#ngrok-setup)
3. Point your bot to the public tunnel URL

This lets you edit your code locally and instantly see the results in your meeting bot. Once everything is configured, here's what your [Create Bot](https://docs.recall.ai/reference/bot_create) request should look like:

JSON

```json
// POST /api/v1/bot/
{
  "meeting_url": "https://us02web.zoom.us/j/1234567890",
  "bot_name": "Recall.ai Notetaker",
  "output_media": {
    "camera": {
      "kind": "webpage",
      "config": {
        // traffic to this URL will be forwarded to your localhost
        "url": "https://my-static-domain.ngrok-free.app"
      }
    }
  }
}
```

### Listening to meeting audio from the webpage   [Skip link to Listening to meeting audio from the webpage](https://docs.recall.ai/docs/stream-media\#listening-to-meeting-audio-from-the-webpage)

When your bot starts streaming your webpage, the webpage automatically gets access to the live audio from the meeting.

> 📘
>
> ### No User Interaction Required   [Skip link to No User Interaction Required](https://docs.recall.ai/docs/stream-media\#no-user-interaction-required)
>
> Normally, accessing microphone audio requires user permission and interaction (like a button click). However, the bot automatically grants microphone permissions, so your webpage will be able to access audio immediately without user prompts or click events.

You can access a [`MediaStream`](https://developer.mozilla.org/en-US/docs/Web/API/MediaStream) object and its audio track from the webpage running inside the bot. The following example shows how to get samples of the meeting audio in [`AudioData`](https://developer.mozilla.org/en-US/docs/Web/API/AudioData) objects:

javascript

```javascript

const mediaStream =   await navigator.mediaDevices.getUserMedia({ audio: true });
const meetingAudioTrack = mediaStream.getAudioTracks()[0];

const trackProcessor = new MediaStreamTrackProcessor({ track: meetingAudioTrack });
const trackReader = trackProcessor.readable.getReader();

while (true) {
  const { value, done } = await trackReader.read();
  const audioData = value;
  ... // Do something with the audio data
}
```

From here, you can process the audio however you need. For example, pipe it to [OpenAI's Realtime API](https://platform.openai.com/docs/guides/realtime) for speech-to-speech processing, then output the AI's audio response back to the meeting participants through your webpage's audio elements. This creates a fully interactive voice agent that can have natural conversations with meeting attendees.

### Accessing real-time meeting data from the webpage   [Skip link to Accessing real-time meeting data from the webpage](https://docs.recall.ai/docs/stream-media\#accessing-real-time-meeting-data-from-the-webpage)

The bot exposes a websocket endpoint to retrieve real-time meeting data while the webpage is streaming audio and video to the call. Right now, only real-time transcripts are supported. You can connect to the real-time API from your webpage with the following example:

JavaScript

```javascript

const ws = new WebSocket('wss://meeting-data.bot.recall.ai/api/v1/transcript');

ws.onmessage = (event) => {
  const message = JSON.parse(event.data).transcript?.words?.map(l => l.text)?.join(' ');

  // .. your logic to handle realtime transcripts
};

ws.onopen = () => {
  console.log('Connected to WebSocket server');
};

ws.onclose = () => {
  console.log('Disconnected from WebSocket server');
};
```

The websocket messages coming from the `/api/v1/transcript` endpoint have the same shape as the `data` object in [Real-time transcription](https://docs.recall.ai/docs/real-time-transcription#events) .

## Including Bot in Recording Media   [Skip link to Including Bot in Recording Media](https://docs.recall.ai/docs/stream-media\#including-bot-in-recording-media)

### Including Bot Audio in Recording   [Skip link to Including Bot Audio in Recording](https://docs.recall.ai/docs/stream-media\#including-bot-audio-in-recording)

You can include the bot's audio in the recording by adding the following to your [Create Bot](https://docs.recall.ai/reference/bot_create) config:

```undefined
{
  "recording_config": {
    "include_bot_in_recording": {
      "audio": true
    }
  }
}
```

### Including Bot Video in Recording   [Skip link to Including Bot Video in Recording](https://docs.recall.ai/docs/stream-media\#including-bot-video-in-recording)

It is not possible to include the bot's video in the recording at this time.

### Including Bot Audio in Transcript   [Skip link to Including Bot Audio in Transcript](https://docs.recall.ai/docs/stream-media\#including-bot-audio-in-transcript)

You can include the bot's audio in the transcript by:

- Including the bot's audio in the recording
- Enabling [Perfect Diarization](https://docs.recall.ai/docs/perfect-diarization)

#### Including Bot Audio in Transcript Using Real-Time Transcription   [Skip link to Including Bot Audio in Transcript Using Real-Time Transcription](https://docs.recall.ai/docs/stream-media\#including-bot-audio-in-transcript-using-real-time-transcription)

Include the following in your [Create Bot](https://docs.recall.ai/reference/bot_create) config:

```undefined
{
  "recording_config": {
    "transcript": {
      "diarization": {
        "use_separate_streams_when_available": true
      },
      "provider": { ... }
    },
    "include_bot_in_recording": {
      "audio": true
    }
  }
}
```

#### Including Bot Audio in Transcript Using Async Transcription   [Skip link to Including Bot Audio in Transcript Using Async Transcription](https://docs.recall.ai/docs/stream-media\#including-bot-audio-in-transcript-using-async-transcription)

Include the following in your [Create Bot](https://docs.recall.ai/reference/bot_create) config:

```undefined
{
  "recording_config": {
    "include_bot_in_recording": {
      "audio": true
    }
  }
}
```

Add the following to your [Create Async Transcript](https://docs.recall.ai/reference/recording_create_transcript_create) config:

```undefined
{
  "diarization": {
    "use_separate_streams_when_available": true
  }
}
```

## Debugging Your Webpage   [Skip link to Debugging Your Webpage](https://docs.recall.ai/docs/stream-media\#debugging-your-webpage)

> ❗️
>
> **Local development**
>
> When running your webpage locally, you will need to expose it through a public URL using a tunneling tool such as [ngrok](https://ngrok.com/).
>
> If your webpage is making API requests to another local server, you will also need to ensure that these are routed through a publicly exposed endpoint as well (using ngrok or similar). If you don't do this, your webpage may not function as expected since API calls to localhost endpoints are blocked within the bot's Output Media process.

### Accessing Chrome Devtools   [Skip link to Accessing Chrome Devtools](https://docs.recall.ai/docs/stream-media\#accessing-chrome-devtools)

During the development process, you will need to debug issues with your Output Media bot's webpage. Recall provides an easy way to connect to the webpage's [Chrome Devtools](https://developer.chrome.com/docs/devtools) while the bot is running. Check the video demo below and read the following instructions to learn how to access your bot's Devtools.

Debugging Live Output Media Bots with Recall.ai 🤖

Copy link

[Open video in Loom](https://www.loom.com/share/88268f164d164e809faba0befcb3b5c4)

0

1.2×

1 min 35 sec⚡️1 min 59 sec1 min 35 sec1 min 19 sec1 min 3 sec56 sec47 sec38 sec

![](https://cdn.loom.com/sessions/thumbnails/88268f164d164e809faba0befcb3b5c4-943b6d35ef9f25c0.jpg)

Copy link

[Open video in Loom](https://www.loom.com/share/88268f164d164e809faba0befcb3b5c4)

0

1.2×

1 min 35 sec⚡️1 min 59 sec1 min 35 sec1 min 19 sec1 min 3 sec56 sec47 sec38 sec

- - ❤️








      heart

      1

  - 👍








    yes

    2

  - 🔥








    fire

    3

  - 👏








    clap

    4

  - 🙌








    yay

    5

  - 👀








    eyes

    6


More reactions

7

✋

## Frequently Used

  - 💯

  - 🎉

  - ✅

  - ❌

  - 👀

  - ✨

  - 🚀

  - ➕

  - 🙏

  - 🔥

  - 😆

  - 🤔

  - 😱

  - 👋

  - 🌈

  - ❤️

  - 👏

  - 🐞


## Smileys & Emotion

## People & Body

## Animals & Nature

## Food & Drink

## Activities

## Travel & Places

## Objects

## Symbols

## Flags

Make frequently used emojis my default

Comment

Comment

C

1. Send an output media bot to your meeting, and wait for its output media stream
2. [Log in](https://www.recall.ai/login) to your Recall.ai dashboard
3. Select Bot Explorer in the sidebar
4. In the Bot Explorer app, search for your bot by ID
5. Open the "Debug Data" tab for your bot. Then under CPU Metrics, click the "Open Remote Devtools" button. A devtools inspector connected to your live bot will open in a new tab.

![](https://files.readme.io/12013f339d96e728aa6177faed2ab9d9d789f2012cdf43ee384d9904ccd562e3-CleanShot_2025-04-11_at_13.23.082x.png)

This opens a full Chrome inspector connected to your bot's browser. You can inspect elements, check console logs, monitor network requests, and debug just like you would locally.

> 📘
>
> ### Bot must be alive   [Skip link to Bot must be alive](https://docs.recall.ai/docs/stream-media\#bot-must-be-alive)
>
> Since Output Media Devtools are exposed by the bot itself and CPU metrics are in real-time, they are only available when the bot is actively in a call.

### Profiling CPU usage   [Skip link to Profiling CPU usage](https://docs.recall.ai/docs/stream-media\#profiling-cpu-usage)

You can also view the CPU usage for an individual bot in the "Bot Details" section. You can use this graph to uncover any performance bottlenecks with your webpage which might be causing the webpage to lag or perform poorly.

![](https://files.readme.io/2003b2475688e3109aeb12172426f2a153f5d276931e3bd0528209714f796c6a-CleanShot_2024-12-09_at_11.36.22.png)

### Addressing audio and video issues: bot variants   [Skip link to Addressing audio and video issues: bot variants](https://docs.recall.ai/docs/stream-media\#addressing-audio-and-video-issues-bot-variants)

While we expose CPU metrics to help you identify and address any performance issues on your end, sometimes this is out of your control and you just need more CPU power or hardware acceleration. Below is a breakdown of the compute resources available to the instance running your webpage:

| Variant | CPU | Memory | WebGL | Camera/Screenshare Resolution | Camera/Screenshare Framerate |
| --- | --- | --- | --- | --- | --- |
| `web` (default) | 250 millicores | 750MB | ❌ Unsupported | 1280x720 px | 15 fps |
| `web_4_core` | 2250 millicores | 5250MB | ❌ Unsupported | 1280x720 px | 15 fps |
| `web_gpu` | 6000 millicores | 13250MB | ✅ Supported | 1280x720 px | 15 fps |

To use these configurations, you can specify the `variant` in your [Create Bot](https://docs.recall.ai/reference/bot_create) request. For example, this is how you can specify that your bot should use the 4 core bot variety on all platforms:

JSON

```json
{
  ...
  "variant": {
    "zoom": "web_4_core",
    "google_meet": "web_4_core",
    "microsoft_teams": "web_4_core"
  }
}
```

These bots run on larger machines, which can help address any CPU bottlenecks hindering the audio & video quality of your Output Media feature.

> 📘
>
> ### Limitations on video quality   [Skip link to Limitations on video quality](https://docs.recall.ai/docs/stream-media\#limitations-on-video-quality)
>
> Upgrading to a larger bot variant (e.g., `web_4_core` or `web_gpu`) can help if your bot is dropping frames or struggling to keep up with real-time processing (i.e. the bot is resource-constrained).
>
> However, it won't improve the source video quality: resolution, compression artifacts, and "fuzziness" are determined by the meeting platform itself and can't be changed by the bot. If your video looks pixelated on `web_4_core`, it's likely the meeting platform is sending a lower-quality stream.

> ❗️
>
> ### Important   [Skip link to Important](https://docs.recall.ai/docs/stream-media\#important)
>
> Due to the inherent cost of running larger machines, the prices for some variants are higher:
>
> | Variant | Pay-as-you-go plan | Monthly plans |
> | --- | --- | --- |
> | `web_4_core` | $0.60/hour | standard bot usage rate + $0.10/hour |
> | `web_gpu` | $1.50/hour | standard bot usage rate + $1.00/hour |

## Securing your webpage   [Skip link to Securing your webpage](https://docs.recall.ai/docs/stream-media\#securing-your-webpage)

You will likely not want your webpage accessible to any individual that opens the page. The standard approach to securing an Output Media webpage is embed a short-lived/pre-authenticated session token within the Output Media URL that your backend can use to authenticate and subsequently redirect.

## FAQ   [Skip link to FAQ](https://docs.recall.ai/docs/stream-media\#faq)

### Why is the bot's audio / video output choppy? How can I improve streaming quality?   [Skip link to Why is the bot's audio / video output choppy? How can I improve streaming quality?](https://docs.recall.ai/docs/stream-media\#why-is-the-bots-audio--video-output-choppy-how-can-i-improve-streaming-quality)

If the audio or video output from your bot is choppy, it's likely that your bot's instance doesn't have enough CPU power to handle your use case. You can test this by upgrading the bot to a larger, more powerful instance. Typically the `web_4_core` instance is sufficient for most Output Media use cases. To switch to 4 core bots, include this in your [Create Bot](https://docs.recall.ai/reference/bot_create) request:

JSON

```json
{
  ...
  "variant": {
    "zoom": "web_4_core",
    "google_meet": "web_4_core",
    "microsoft_teams": "web_4_core"
  }
}
```

### What are the browser dimensions of the webpage?   [Skip link to What are the browser dimensions of the webpage?](https://docs.recall.ai/docs/stream-media\#what-are-the-browser-dimensions-of-the-webpage)

1280x720px

### Why doesn't the bot's video/screenshare show in the recording?   [Skip link to Why doesn't the bot's video/screenshare show in the recording?](https://docs.recall.ai/docs/stream-media\#why-doesnt-the-bots-videoscreenshare-show-in-the-recording)

It currently isn't possible to include the recording of the bot in the final recording. That said, you can still include the bot's audio by setting the `recording_config.include_bot_in_recording.audio = true`

### Can I use the Automatic Audio Output or Automatic Video Output parameters while using Output Media?   [Skip link to Can I use the Automatic Audio Output or Automatic Video Output parameters while using Output Media?](https://docs.recall.ai/docs/stream-media\#can-i-use-the-automatic-audio-output-or-automatic-video-output-parameters-while-using-output-media)

No. The Output Media cannot be used with [`automatic_video_output`](https://docs.recall.ai/docs/output-video-in-meetings) or [`automatic_audio_output`](https://docs.recall.ai/docs/output-audio-in-meetings) parameters. These features are mutually exclusive.

Similarly, the [Output Video](https://docs.recall.ai/reference/bot_output_video_create) and [Output Audio](https://docs.recall.ai/reference/bot_output_audio_create) endpoints can **not** be used if your bot is actively using the Output Media feature.

### Can I make the bot only output audio for an audio-only agent?   [Skip link to Can I make the bot only output audio for an audio-only agent?](https://docs.recall.ai/docs/stream-media\#can-i-make-the-bot-only-output-audio-for-an-audio-only-agent)

No, it is not possible to output only audio into the meeting. The output media feature will always include the webpage as the bot's video. It is also not possible to turn off the camera while output media is on.

As a workaround, developers will use a placeholder image (e.g. your company logo/brand) or show a black screen instead.

Updatedabout 1 month ago

* * *

Did this page help you?

Yes

No

Copy Page

Sign in to Recall for advanced AI debugging

Use Ask AI for public Recall docs. Sign in later if you need workspace debugging.

Anonymous (docs only) (anonymous)US East 1 (us-east-1)US West 2 (us-west-2)EU Central 1 (eu-central-1)AP Northeast 1 (ap-northeast-1)Continue with docs-only Ask AI

Ask AI![](https://files.readme.io/2f4ba7b-small-favicon.png)