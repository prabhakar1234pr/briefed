[Skip to main content](https://docs.pipecat.ai/api-reference/server/services/tts/elevenlabs#content-area)

[Pipecat home page![light logo](https://mintcdn.com/daily/r4jEtY4thtHXjZ16/logo/light.svg?fit=max&auto=format&n=r4jEtY4thtHXjZ16&q=85&s=46cda5b2f0afabd5f0298c64082c4125)![dark logo](https://mintcdn.com/daily/r4jEtY4thtHXjZ16/logo/dark.svg?fit=max&auto=format&n=r4jEtY4thtHXjZ16&q=85&s=f018b960ba26051755803a128139431b)](https://docs.pipecat.ai/)

Search...

Ctrl K

Search...

Navigation

Text-to-Speech

ElevenLabs

[Overview](https://docs.pipecat.ai/overview/introduction) [Pipecat](https://docs.pipecat.ai/pipecat/get-started/introduction) [Pipecat Subagents](https://docs.pipecat.ai/subagents/introduction) [Pipecat Clients](https://docs.pipecat.ai/client/introduction) [Pipecat Flows](https://docs.pipecat.ai/pipecat-flows/introduction) [Pipecat Cloud](https://docs.pipecat.ai/pipecat-cloud/introduction) [API Reference](https://docs.pipecat.ai/api-reference/server/introduction)

On this page

- [Overview](https://docs.pipecat.ai/api-reference/server/services/tts/elevenlabs#overview)
- [Installation](https://docs.pipecat.ai/api-reference/server/services/tts/elevenlabs#installation)
- [Prerequisites](https://docs.pipecat.ai/api-reference/server/services/tts/elevenlabs#prerequisites)
- [Configuration](https://docs.pipecat.ai/api-reference/server/services/tts/elevenlabs#configuration)
- [ElevenLabsTTSService](https://docs.pipecat.ai/api-reference/server/services/tts/elevenlabs#elevenlabsttsservice)
- [ElevenLabsHttpTTSService](https://docs.pipecat.ai/api-reference/server/services/tts/elevenlabs#elevenlabshttpttsservice)
- [Settings](https://docs.pipecat.ai/api-reference/server/services/tts/elevenlabs#settings)
- [Usage](https://docs.pipecat.ai/api-reference/server/services/tts/elevenlabs#usage)
- [Basic Setup](https://docs.pipecat.ai/api-reference/server/services/tts/elevenlabs#basic-setup)
- [With Voice Customization](https://docs.pipecat.ai/api-reference/server/services/tts/elevenlabs#with-voice-customization)
- [Updating Settings at Runtime](https://docs.pipecat.ai/api-reference/server/services/tts/elevenlabs#updating-settings-at-runtime)
- [HTTP Service](https://docs.pipecat.ai/api-reference/server/services/tts/elevenlabs#http-service)
- [Notes](https://docs.pipecat.ai/api-reference/server/services/tts/elevenlabs#notes)
- [Event Handlers](https://docs.pipecat.ai/api-reference/server/services/tts/elevenlabs#event-handlers)

> ## Documentation Index
>
> Fetch the complete documentation index at: [https://docs.pipecat.ai/llms.txt](https://docs.pipecat.ai/llms.txt)
>
> Use this file to discover all available pages before exploring further.

## [​](https://docs.pipecat.ai/api-reference/server/services/tts/elevenlabs\#overview)  Overview

ElevenLabs provides high-quality text-to-speech synthesis with two service implementations:

- **`ElevenLabsTTSService`** (WebSocket) — Real-time streaming with word-level timestamps, audio context management, and interruption handling. Recommended for interactive applications.
- **`ElevenLabsHttpTTSService`** (HTTP) — Simpler batch-style synthesis. Suitable for non-interactive use cases or when WebSocket connections are not possible.

[**ElevenLabs TTS API Reference** \\
\\
Complete API reference for all parameters and methods](https://reference-server.pipecat.ai/en/latest/api/pipecat.services.elevenlabs.tts.html)

[**Example Implementation** \\
\\
Complete example with WebSocket streaming](https://github.com/pipecat-ai/pipecat/blob/main/examples/voice/voice-elevenlabs.py)

[**ElevenLabs Documentation** \\
\\
Official ElevenLabs TTS API documentation](https://elevenlabs.io/docs/api-reference/text-to-speech/v-1-text-to-speech-voice-id-multi-stream-input)

[**Voice Library** \\
\\
Browse and clone voices from the community](https://elevenlabs.io/voice-library)

## [​](https://docs.pipecat.ai/api-reference/server/services/tts/elevenlabs\#installation)  Installation

```
uv add "pipecat-ai[elevenlabs]"
```

## [​](https://docs.pipecat.ai/api-reference/server/services/tts/elevenlabs\#prerequisites)  Prerequisites

1. **ElevenLabs Account**: Sign up at [ElevenLabs](https://elevenlabs.io/app/sign-up)
2. **API Key**: Generate an API key from your account dashboard
3. **Voice Selection**: Choose voice IDs from the [voice library](https://elevenlabs.io/voice-library)

Set the following environment variable:

```
export ELEVENLABS_API_KEY=your_api_key
```

## [​](https://docs.pipecat.ai/api-reference/server/services/tts/elevenlabs\#configuration)  Configuration

### [​](https://docs.pipecat.ai/api-reference/server/services/tts/elevenlabs\#elevenlabsttsservice)  ElevenLabsTTSService

[​](https://docs.pipecat.ai/api-reference/server/services/tts/elevenlabs#param-api-key)

api\_key

str

required

ElevenLabs API key.

[​](https://docs.pipecat.ai/api-reference/server/services/tts/elevenlabs#param-voice-id)

voice\_id

str

required

deprecated

Voice ID from the [voice library](https://elevenlabs.io/voice-library).
_Deprecated in v0.0.105. Use_
_`settings=ElevenLabsTTSService.Settings(voice=...)` instead._

[​](https://docs.pipecat.ai/api-reference/server/services/tts/elevenlabs#param-model)

model

str

default:"eleven\_turbo\_v2\_5"

deprecated

ElevenLabs model ID. Use a `multilingual` model variant (e.g.
`eleven_multilingual_v2`) if you need non-English language support.
_Deprecated in v0.0.105. Use_
_`settings=ElevenLabsTTSService.Settings(model=...)` instead._

[​](https://docs.pipecat.ai/api-reference/server/services/tts/elevenlabs#param-url)

url

str

default:"wss://api.elevenlabs.io"

WebSocket endpoint URL. Override for custom or proxied deployments.

[​](https://docs.pipecat.ai/api-reference/server/services/tts/elevenlabs#param-sample-rate)

sample\_rate

int

default:"None"

Output audio sample rate in Hz. When `None`, uses the pipeline’s configured
sample rate.

[​](https://docs.pipecat.ai/api-reference/server/services/tts/elevenlabs#param-auto-mode)

auto\_mode

bool

default:"None"

Whether to enable ElevenLabs’ auto mode, which reduces latency by disabling
server-side chunk scheduling and buffering. Recommended when sending complete
sentences or phrases. When `None` (default), auto mode is automatically
enabled for `SENTENCE` aggregation and disabled for `TOKEN` aggregation —
because token streaming relies on the server-side chunk scheduler to
accumulate enough text for natural-sounding synthesis.

[​](https://docs.pipecat.ai/api-reference/server/services/tts/elevenlabs#param-text-aggregation-mode)

text\_aggregation\_mode

TextAggregationMode

default:"TextAggregationMode.SENTENCE"

Controls how incoming text is aggregated before synthesis. `SENTENCE`
(default) buffers text until sentence boundaries, producing more natural
speech. `TOKEN` streams tokens directly for lower latency. Import from
`pipecat.services.tts_service`.

[​](https://docs.pipecat.ai/api-reference/server/services/tts/elevenlabs#param-aggregate-sentences)

aggregate\_sentences

bool

default:"None"

deprecated

_Deprecated in v0.0.104._ Use `text_aggregation_mode` instead.

[​](https://docs.pipecat.ai/api-reference/server/services/tts/elevenlabs#param-params)

params

InputParams

default:"None"

deprecated

_Deprecated in v0.0.105. Use `settings=ElevenLabsTTSService.Settings(...)`_
_instead._

[​](https://docs.pipecat.ai/api-reference/server/services/tts/elevenlabs#param-settings)

settings

ElevenLabsTTSService.Settings

default:"None"

Runtime-configurable settings. See [Settings](https://docs.pipecat.ai/api-reference/server/services/tts/elevenlabs#settings) below.

### [​](https://docs.pipecat.ai/api-reference/server/services/tts/elevenlabs\#elevenlabshttpttsservice)  ElevenLabsHttpTTSService

The HTTP service accepts the same parameters as the WebSocket service, with these differences:

[​](https://docs.pipecat.ai/api-reference/server/services/tts/elevenlabs#param-aiohttp-session)

aiohttp\_session

aiohttp.ClientSession

required

An aiohttp session for HTTP requests. You must create and manage this
yourself.

[​](https://docs.pipecat.ai/api-reference/server/services/tts/elevenlabs#param-base-url)

base\_url

str

default:"https://api.elevenlabs.io"

HTTP API base URL (instead of `url` for WebSocket).

[​](https://docs.pipecat.ai/api-reference/server/services/tts/elevenlabs#param-enable-logging)

enable\_logging

bool

default:"None"

Whether to enable ElevenLabs server-side logging. Set to `False` for zero
retention mode (enterprise only).

The HTTP service uses `ElevenLabsHttpTTSSettings` which also includes:

[​](https://docs.pipecat.ai/api-reference/server/services/tts/elevenlabs#param-optimize-streaming-latency)

optimize\_streaming\_latency

int

default:"None"

Latency optimization level (0–4). Higher values reduce latency at the cost of
quality.

### [​](https://docs.pipecat.ai/api-reference/server/services/tts/elevenlabs\#settings)  Settings

Runtime-configurable settings passed via the `settings` constructor argument using `ElevenLabsTTSService.Settings(...)`. These can be updated mid-conversation with `TTSUpdateSettingsFrame`. See [Service Settings](https://docs.pipecat.ai/pipecat/fundamentals/service-settings) for details.

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `model` | `str` | `None` | ElevenLabs model identifier. _(Inherited from base settings.)_ |
| `voice` | `str` | `None` | Voice identifier. _(Inherited from base settings.)_ |
| `language` | `Language | str` | `None` | Language code. Only effective with multilingual models. _(Inherited from base settings.)_ |
| `stability` | `float` | `NOT_GIVEN` | Voice consistency (0.0–1.0). Lower values are more expressive, higher values are more consistent. |
| `similarity_boost` | `float` | `NOT_GIVEN` | Voice clarity and similarity to the original (0.0–1.0). |
| `style` | `float` | `NOT_GIVEN` | Style exaggeration (0.0–1.0). Higher values amplify the voice’s style. |
| `use_speaker_boost` | `bool` | `NOT_GIVEN` | Enhance clarity and target speaker similarity. |
| `speed` | `float` | `NOT_GIVEN` | Speech rate. WebSocket: 0.7–1.2. HTTP: 0.25–4.0. |
| `apply_text_normalization` | `Literal` | `NOT_GIVEN` | Text normalization: `"auto"`, `"on"`, or `"off"`. |

`NOT_GIVEN` values use the ElevenLabs API defaults. See [ElevenLabs voice\\
settings](https://elevenlabs.io/docs/api-reference/text-to-speech/v-1-text-to-speech-voice-id-multi-stream-input)
for details on how these parameters interact.

## [​](https://docs.pipecat.ai/api-reference/server/services/tts/elevenlabs\#usage)  Usage

### [​](https://docs.pipecat.ai/api-reference/server/services/tts/elevenlabs\#basic-setup)  Basic Setup

```
from pipecat.services.elevenlabs import ElevenLabsTTSService

tts = ElevenLabsTTSService(
    api_key=os.getenv("ELEVENLABS_API_KEY"),
    settings=ElevenLabsTTSService.Settings(
        voice="21m00Tcm4TlvDq8ikWAM",  # Rachel
    ),
)
```

### [​](https://docs.pipecat.ai/api-reference/server/services/tts/elevenlabs\#with-voice-customization)  With Voice Customization

```
tts = ElevenLabsTTSService(
    api_key=os.getenv("ELEVENLABS_API_KEY"),
    settings=ElevenLabsTTSService.Settings(
        voice="21m00Tcm4TlvDq8ikWAM",
        model="eleven_multilingual_v2",
        language=Language.ES,
        stability=0.7,
        similarity_boost=0.8,
        speed=1.1,
    ),
)
```

### [​](https://docs.pipecat.ai/api-reference/server/services/tts/elevenlabs\#updating-settings-at-runtime)  Updating Settings at Runtime

Voice settings can be changed mid-conversation using `TTSUpdateSettingsFrame`:

```
from pipecat.frames.frames import TTSUpdateSettingsFrame
from pipecat.services.elevenlabs.tts import ElevenLabsTTSSettings

await task.queue_frame(
    TTSUpdateSettingsFrame(
        delta=ElevenLabsTTSSettings(
            stability=0.3,
            speed=1.1,
        )
    )
)
```

### [​](https://docs.pipecat.ai/api-reference/server/services/tts/elevenlabs\#http-service)  HTTP Service

```
import aiohttp
from pipecat.services.elevenlabs import ElevenLabsHttpTTSService

async with aiohttp.ClientSession() as session:
    tts = ElevenLabsHttpTTSService(
        api_key=os.getenv("ELEVENLABS_API_KEY"),
        settings=ElevenLabsHttpTTSService.Settings(
            voice="21m00Tcm4TlvDq8ikWAM",
        ),
        aiohttp_session=session,
    )
```

The `InputParams` / `params=` pattern is deprecated as of v0.0.105. Use
`Settings` / `settings=` instead. See the [Service Settings\\
guide](https://docs.pipecat.ai/pipecat/fundamentals/service-settings) for migration details.

## [​](https://docs.pipecat.ai/api-reference/server/services/tts/elevenlabs\#notes)  Notes

- **Multilingual models required for `language`**: Setting `language` with a non-multilingual model (e.g. `eleven_turbo_v2_5`) has no effect. Use `eleven_multilingual_v2` or similar.
- **WebSocket vs HTTP**: The WebSocket service supports word-level timestamps and interruption handling, making it significantly better for interactive conversations. The HTTP service is simpler but lacks these features.
- **Text aggregation**: Sentence aggregation is enabled by default (`text_aggregation_mode=TextAggregationMode.SENTENCE`). Buffering until sentence boundaries produces more natural speech. Set `text_aggregation_mode=TextAggregationMode.TOKEN` to stream tokens directly for lower latency. The `auto_mode` parameter is automatically configured based on the aggregation mode for optimal quality.
- **Word timestamp accuracy**: Word timestamps reflect the original input text by default, preserving non-Latin scripts in transcripts and LLM context. When pronunciation dictionaries are configured via `pronunciation_dictionary_locators`, the service switches to ElevenLabs’ normalized alignment to avoid duplicate words caused by dictionary substitutions. Text normalization (`apply_text_normalization`) does not affect which alignment field is used.

## [​](https://docs.pipecat.ai/api-reference/server/services/tts/elevenlabs\#event-handlers)  Event Handlers

ElevenLabs TTS supports the standard [service connection events](https://docs.pipecat.ai/api-reference/server/events/service-events):

| Event | Description |
| --- | --- |
| `on_connected` | Connected to ElevenLabs WebSocket |
| `on_disconnected` | Disconnected from ElevenLabs WebSocket |
| `on_connection_error` | WebSocket connection error occurred |

```
@tts.event_handler("on_connected")
async def on_connected(service):
    print("Connected to ElevenLabs")
```

[Deepgram](https://docs.pipecat.ai/api-reference/server/services/tts/deepgram) [Fish Audio](https://docs.pipecat.ai/api-reference/server/services/tts/fish)

Ctrl+I

![Project Logo](data:image/svg+xml,%3Csvg%20width%3D%2224%22%20height%3D%2224%22%20viewBox%3D%220%200%2024%2024%22%20fill%3D%22none%22%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%3E%3Cpath%20d%3D%22M3.3088%205.05615C3.64682%204.92779%204.02833%205.02411%204.26653%205.29797L7.36884%208.86461H16.6312L19.7335%205.29797C19.9717%205.02411%2020.3532%204.92779%2020.6912%205.05615C21.0292%205.18452%2021.253%205.51072%2021.253%205.87504V13.75H24V15.5H19.5181V8.19909L17.6762%2010.3167C17.5115%2010.506%2017.2738%2010.6146%2017.0241%2010.6146H6.9759C6.72616%2010.6146%206.48854%2010.506%206.32383%2010.3167L4.48193%208.19909V15.5H0V13.75H2.74699V5.87504C2.74699%205.51072%202.97078%205.18452%203.3088%205.05615Z%22%20fill%3D%22black%22%2F%3E%3Cpath%20d%3D%22M19.5181%2017.25H24V19H19.5181V17.25Z%22%20fill%3D%22black%22%2F%3E%3Cpath%20d%3D%22M0%2017.25H4.48193V19H0V17.25Z%22%20fill%3D%22black%22%2F%3E%3Cpath%20d%3D%22M9.25301%2014.3333C9.25301%2014.9777%208.73517%2015.5%208.09639%2015.5C7.4576%2015.5%206.93976%2014.9777%206.93976%2014.3333C6.93976%2013.689%207.4576%2013.1667%208.09639%2013.1667C8.73517%2013.1667%209.25301%2013.689%209.25301%2014.3333Z%22%20fill%3D%22black%22%2F%3E%3Cpath%20d%3D%22M17.0602%2014.3333C17.0602%2014.9777%2016.5424%2015.5%2015.9036%2015.5C15.2648%2015.5%2014.747%2014.9777%2014.747%2014.3333C14.747%2013.689%2015.2648%2013.1667%2015.9036%2013.1667C16.5424%2013.1667%2017.0602%2013.689%2017.0602%2014.3333Z%22%20fill%3D%22black%22%2F%3E%3C%2Fsvg%3E)

Ask AI

reCAPTCHA

Recaptcha requires verification.

protected by **reCAPTCHA**