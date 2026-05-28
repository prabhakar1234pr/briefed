[Skip to main content](https://docs.pipecat.ai/pipecat/learn/transports#content-area)

[Pipecat home page![light logo](https://mintcdn.com/daily/r4jEtY4thtHXjZ16/logo/light.svg?fit=max&auto=format&n=r4jEtY4thtHXjZ16&q=85&s=46cda5b2f0afabd5f0298c64082c4125)![dark logo](https://mintcdn.com/daily/r4jEtY4thtHXjZ16/logo/dark.svg?fit=max&auto=format&n=r4jEtY4thtHXjZ16&q=85&s=f018b960ba26051755803a128139431b)](https://docs.pipecat.ai/)

Search...

Ctrl K

Search...

Navigation

Learning Pipecat

Transports

[Overview](https://docs.pipecat.ai/overview/introduction) [Pipecat](https://docs.pipecat.ai/pipecat/get-started/introduction) [Pipecat Subagents](https://docs.pipecat.ai/subagents/introduction) [Pipecat Clients](https://docs.pipecat.ai/client/introduction) [Pipecat Flows](https://docs.pipecat.ai/pipecat-flows/introduction) [Pipecat Cloud](https://docs.pipecat.ai/pipecat-cloud/introduction) [API Reference](https://docs.pipecat.ai/api-reference/server/introduction)

> ## Documentation Index
>
> Fetch the complete documentation index at: [https://docs.pipecat.ai/llms.txt](https://docs.pipecat.ai/llms.txt)
>
> Use this file to discover all available pages before exploring further.

**Transports** are the communication layer between users and your Pipecat bot. They handle receiving and sending audio, video, and data, serving as the media interface that enables real-time interaction.

## [​](https://docs.pipecat.ai/pipecat/learn/transports\#available-transport-types)  Available Transport Types

Pipecat supports multiple transport types to fit different use cases and deployment scenarios:

[**DailyTransport** \\
\\
WebRTC-based transport using Daily’s infrastructure for video calls and\\
conferencing](https://docs.pipecat.ai/api-reference/server/services/transport/daily)

[**FastAPIWebsocketTransport** \\
\\
WebSocket transport for telephony providers and custom WebSocket connections](https://docs.pipecat.ai/api-reference/server/services/transport/fastapi-websocket)

[**HeyGenTransport** \\
\\
Specialized transport for HeyGen LiveAvatar video generation and streaming](https://docs.pipecat.ai/api-reference/server/services/transport/heygen)

[**LiveKitTransport** \\
\\
WebRTC transport using LiveKit’s real-time communication platform](https://docs.pipecat.ai/api-reference/server/services/transport/livekit)

[**SmallWebRTCTransport** \\
\\
Direct peer-to-peer WebRTC connections without cloud infrastructure](https://docs.pipecat.ai/api-reference/server/services/transport/small-webrtc)

[**TavusTransport** \\
\\
Specialized transport for Tavus video generation and streaming](https://docs.pipecat.ai/api-reference/server/services/transport/tavus)

[**WebsocketTransport** \\
\\
General-purpose WebSocket transport for custom implementations](https://docs.pipecat.ai/api-reference/server/services/transport/websocket-server)

## [​](https://docs.pipecat.ai/pipecat/learn/transports\#pipeline-integration)  Pipeline Integration

Transports provide two key components for your pipeline: `input()` and `output()` methods. These methods define how the transport interacts with the pipeline:

### [​](https://docs.pipecat.ai/pipecat/learn/transports\#transport-input-and-output)  Transport Input and Output

```
pipeline = Pipeline([\
    transport.input(),              # Receives user audio/video\
    stt,\
    context_aggregator.user(),\
    llm,\
    tts,\
    transport.output(),             # Sends bot audio/video\
    context_aggregator.assistant(), # Processes after output\
])
```

**Key points about transport placement:**

- **`transport.input()`** typically goes first in the pipeline to receive user input
- **`transport.output()`** doesn’t always go last - you may want processors after it
- **Post-output processing**enables synchronized actions like:

  - Recording with word-level accuracy
  - Displaying subtitles synchronized to audio
  - Capturing context information precisely timed to output

## [​](https://docs.pipecat.ai/pipecat/learn/transports\#transport-modularity)  Transport Modularity

Transports are modular components in your Pipeline, allowing you to flexibly change how users connect to your bot depending on the context. This modularity enables you to:

- **Switch environments easily**: Use P2P WebRTC for development, Daily for production
- **Support multiple connection types**: Same bot logic works across different transports
- **Optimize for use case**: Choose the best transport for your specific requirements

## [​](https://docs.pipecat.ai/pipecat/learn/transports\#transport-configuration)  Transport Configuration

All transports are configured using `TransportParams`, which provides common settings across transport types:

```
from pipecat.transports.base_transport import TransportParams

params = TransportParams(
    # Audio settings
    audio_in_enabled=True,
    audio_out_enabled=True,

    # Video settings
    video_in_enabled=False,
    video_out_enabled=False,

    # Video stream configuration
    video_out_width=1024,
    video_out_height=576,
    video_out_bitrate=800000,
    video_out_framerate=30,
)
```

Each transport may have its own specialized parameters class that extends
TransportParams with transport-specific options. Check the individual
transport documentation for details.

For advanced turn detection (like Smart Turn), configure [User Turn\\
Strategies](https://docs.pipecat.ai/api-reference/server/utilities/turn-management/user-turn-strategies) on the
context aggregator instead of using the transport’s turn\_analyzer parameter.

[**TransportParams Reference** \\
\\
Complete reference for all transport configuration options](https://reference-server.pipecat.ai/en/latest/api/pipecat.transports.base_transport.html#pipecat.transports.base_transport.TransportParams)

## [​](https://docs.pipecat.ai/pipecat/learn/transports\#telephony-integration)  Telephony Integration

Telephony services (phone calls) use WebSocket connections with specialized serialization:

### [​](https://docs.pipecat.ai/pipecat/learn/transports\#supported-telephony-providers)  Supported Telephony Providers

[**Twilio** \\
\\
Media Streams over WebSocket with TwilioFrameSerializer](https://docs.pipecat.ai/api-reference/server/services/serializers/twilio)

[**Telnyx** \\
\\
Real-time media streaming with TelnyxFrameSerializer](https://docs.pipecat.ai/api-reference/server/services/serializers/telnyx)

[**Plivo** \\
\\
Voice streaming API with PlivoFrameSerializer](https://docs.pipecat.ai/api-reference/server/services/serializers/plivo)

[**Exotel** \\
\\
Voice streaming integration with ExotelFrameSerializer](https://docs.pipecat.ai/api-reference/server/services/serializers/exotel)

### [​](https://docs.pipecat.ai/pipecat/learn/transports\#telephony-transport-setup)  Telephony Transport Setup

Telephony requires a `FrameSerializer` to handle provider-specific message formats:

```
# Create provider-specific serializer
serializer = TwilioFrameSerializer(
    stream_sid=stream_sid,
    call_sid=call_sid,
    account_sid=os.getenv("TWILIO_ACCOUNT_SID", ""),
    auth_token=os.getenv("TWILIO_AUTH_TOKEN", ""),
)

# Configure transport with serializer
transport = FastAPIWebsocketTransport(
    websocket=websocket_client,
    params=FastAPIWebsocketParams(
        audio_in_enabled=True,
        audio_out_enabled=True,
        add_wav_header=False,
        serializer=serializer,  # Provider-specific serialization
    ),
)
```

The development runner automatically detects and configures the appropriate
serializer when using `parse_telephony_websocket()`.

## [​](https://docs.pipecat.ai/pipecat/learn/transports\#conditional-transport-selection)  Conditional Transport Selection

The development runner provides a pattern for conditionally selecting transports based on the environment:

```
async def bot(runner_args: RunnerArguments):
    """Main bot entry point compatible with Pipecat Cloud."""

    transport = None

    if isinstance(runner_args, DailyRunnerArguments):
        from pipecat.transports.daily.transport import DailyParams, DailyTransport

        transport = DailyTransport(
            runner_args.room_url,
            runner_args.token,
            "Pipecat Bot",
            params=DailyParams(
                audio_in_enabled=True,
                audio_out_enabled=True,
            ),
        )

    elif isinstance(runner_args, SmallWebRTCRunnerArguments):
        from pipecat.transports.base_transport import TransportParams
        from pipecat.transports.network.small_webrtc import SmallWebRTCTransport

        transport = SmallWebRTCTransport(
            params=TransportParams(
                audio_in_enabled=True,
                audio_out_enabled=True,
            ),
            webrtc_connection=runner_args.webrtc_connection,
        )
    else:
        logger.error(f"Unsupported runner arguments type: {type(runner_args)}")
        return

    if transport is None:
        logger.error("Failed to create transport")
        return

    await run_bot(transport)
```

This pattern allows you to run the same bot code across different environments with different connection types.

## [​](https://docs.pipecat.ai/pipecat/learn/transports\#webrtc-vs-websocket-considerations)  WebRTC vs WebSocket Considerations

Understanding when to use each connection type is crucial for building effective voice AI applications:

### [​](https://docs.pipecat.ai/pipecat/learn/transports\#webrtc-recommended-for-client-applications)  WebRTC (Recommended for Client Applications)

**Best for:** Browser apps, mobile apps, real-time conversations**Advantages:**

- **Low latency**: Optimized for real-time media with minimal delay
- **Built-in resilience**: Handles packet loss and network variations
- **Advanced audio processing**: Echo cancellation, noise reduction, automatic gain control
- **Quality monitoring**: Detailed performance and media quality statistics
- **Automatic timestamping**: Simplifies interruption and playout logic
- **Robust reconnection**: Built-in connection management

**Use WebRTC when:**

- Building client-facing applications (web, mobile)
- Conversational latency is critical
- Users are on potentially unreliable networks
- You need built-in audio processing features

### [​](https://docs.pipecat.ai/pipecat/learn/transports\#websocket-good-for-server-to-server)  WebSocket (Good for Server-to-Server)

**Best for:** Telephony integration, server-to-server communication, prototyping**Limitations for real-time media:**

- **TCP-based**: Subject to head-of-line blocking
- **Network sensitivity**: Less resilient to packet loss and jitter
- **Manual implementation**: Requires custom logic for reconnection, timestamping
- **Limited observability**: Harder to monitor connection quality

**Use WebSocket when:**

- Integrating with telephony providers (Twilio, Telnyx, etc.)
- Building server-to-server connections
- Prototyping or latency isn’t critical
- Working within existing WebSocket infrastructure

## [​](https://docs.pipecat.ai/pipecat/learn/transports\#key-takeaways)  Key Takeaways

- **Transports are modular** \- swap them without changing bot logic
- **Choose based on use case** \- WebRTC for clients, WebSocket for telephony
- **Configuration is standardized** \- TransportParams work across transport types
- **Pipeline placement matters** \- consider what processing happens after output
- **Development runner helps** \- provides patterns for multi-transport bots

## [​](https://docs.pipecat.ai/pipecat/learn/transports\#what%E2%80%99s-next)  What’s Next

Now that you understand how transports connect users to your bot, let’s explore how to configure speech recognition to convert user audio into text.

[**Speech Input & Turn Detection** \\
\\
Learn how to configure speech recognition in your voice AI pipeline](https://docs.pipecat.ai/pipecat/learn/speech-input)

[Pipeline & Frame Processing](https://docs.pipecat.ai/pipecat/learn/pipeline) [Speech Input & Turn Detection](https://docs.pipecat.ai/pipecat/learn/speech-input)

Ctrl+I

![Project Logo](data:image/svg+xml,%3Csvg%20width%3D%2224%22%20height%3D%2224%22%20viewBox%3D%220%200%2024%2024%22%20fill%3D%22none%22%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%3E%3Cpath%20d%3D%22M3.3088%205.05615C3.64682%204.92779%204.02833%205.02411%204.26653%205.29797L7.36884%208.86461H16.6312L19.7335%205.29797C19.9717%205.02411%2020.3532%204.92779%2020.6912%205.05615C21.0292%205.18452%2021.253%205.51072%2021.253%205.87504V13.75H24V15.5H19.5181V8.19909L17.6762%2010.3167C17.5115%2010.506%2017.2738%2010.6146%2017.0241%2010.6146H6.9759C6.72616%2010.6146%206.48854%2010.506%206.32383%2010.3167L4.48193%208.19909V15.5H0V13.75H2.74699V5.87504C2.74699%205.51072%202.97078%205.18452%203.3088%205.05615Z%22%20fill%3D%22black%22%2F%3E%3Cpath%20d%3D%22M19.5181%2017.25H24V19H19.5181V17.25Z%22%20fill%3D%22black%22%2F%3E%3Cpath%20d%3D%22M0%2017.25H4.48193V19H0V17.25Z%22%20fill%3D%22black%22%2F%3E%3Cpath%20d%3D%22M9.25301%2014.3333C9.25301%2014.9777%208.73517%2015.5%208.09639%2015.5C7.4576%2015.5%206.93976%2014.9777%206.93976%2014.3333C6.93976%2013.689%207.4576%2013.1667%208.09639%2013.1667C8.73517%2013.1667%209.25301%2013.689%209.25301%2014.3333Z%22%20fill%3D%22black%22%2F%3E%3Cpath%20d%3D%22M17.0602%2014.3333C17.0602%2014.9777%2016.5424%2015.5%2015.9036%2015.5C15.2648%2015.5%2014.747%2014.9777%2014.747%2014.3333C14.747%2013.689%2015.2648%2013.1667%2015.9036%2013.1667C16.5424%2013.1667%2017.0602%2013.689%2017.0602%2014.3333Z%22%20fill%3D%22black%22%2F%3E%3C%2Fsvg%3E)

Ask AI

reCAPTCHA

Recaptcha requires verification.

protected by **reCAPTCHA**