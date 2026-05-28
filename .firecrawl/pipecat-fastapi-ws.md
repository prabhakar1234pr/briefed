[Skip to main content](https://docs.pipecat.ai/api-reference/server/services/transport/fastapi-websocket#content-area)

[Pipecat home page![light logo](https://mintcdn.com/daily/r4jEtY4thtHXjZ16/logo/light.svg?fit=max&auto=format&n=r4jEtY4thtHXjZ16&q=85&s=46cda5b2f0afabd5f0298c64082c4125)![dark logo](https://mintcdn.com/daily/r4jEtY4thtHXjZ16/logo/dark.svg?fit=max&auto=format&n=r4jEtY4thtHXjZ16&q=85&s=f018b960ba26051755803a128139431b)](https://docs.pipecat.ai/)

Search...

Ctrl K

Search...

Navigation

Transport

FastAPIWebsocketTransport

[Overview](https://docs.pipecat.ai/overview/introduction) [Pipecat](https://docs.pipecat.ai/pipecat/get-started/introduction) [Pipecat Subagents](https://docs.pipecat.ai/subagents/introduction) [Pipecat Clients](https://docs.pipecat.ai/client/introduction) [Pipecat Flows](https://docs.pipecat.ai/pipecat-flows/introduction) [Pipecat Cloud](https://docs.pipecat.ai/pipecat-cloud/introduction) [API Reference](https://docs.pipecat.ai/api-reference/server/introduction)

On this page

- [Overview](https://docs.pipecat.ai/api-reference/server/services/transport/fastapi-websocket#overview)
- [Installation](https://docs.pipecat.ai/api-reference/server/services/transport/fastapi-websocket#installation)
- [Prerequisites](https://docs.pipecat.ai/api-reference/server/services/transport/fastapi-websocket#prerequisites)
- [FastAPI Application Setup](https://docs.pipecat.ai/api-reference/server/services/transport/fastapi-websocket#fastapi-application-setup)
- [Configuration Options](https://docs.pipecat.ai/api-reference/server/services/transport/fastapi-websocket#configuration-options)
- [Key Features](https://docs.pipecat.ai/api-reference/server/services/transport/fastapi-websocket#key-features)
- [Configuration](https://docs.pipecat.ai/api-reference/server/services/transport/fastapi-websocket#configuration)
- [FastAPIWebsocketTransport](https://docs.pipecat.ai/api-reference/server/services/transport/fastapi-websocket#fastapiwebsockettransport)
- [FastAPIWebsocketParams](https://docs.pipecat.ai/api-reference/server/services/transport/fastapi-websocket#fastapiwebsocketparams)
- [Usage](https://docs.pipecat.ai/api-reference/server/services/transport/fastapi-websocket#usage)
- [Event Handlers](https://docs.pipecat.ai/api-reference/server/services/transport/fastapi-websocket#event-handlers)
- [Events Summary](https://docs.pipecat.ai/api-reference/server/services/transport/fastapi-websocket#events-summary)
- [Connection Lifecycle](https://docs.pipecat.ai/api-reference/server/services/transport/fastapi-websocket#connection-lifecycle)
- [on\_client\_connected](https://docs.pipecat.ai/api-reference/server/services/transport/fastapi-websocket#on_client_connected)
- [on\_client\_disconnected](https://docs.pipecat.ai/api-reference/server/services/transport/fastapi-websocket#on_client_disconnected)
- [on\_session\_timeout](https://docs.pipecat.ai/api-reference/server/services/transport/fastapi-websocket#on_session_timeout)
- [Additional Resources](https://docs.pipecat.ai/api-reference/server/services/transport/fastapi-websocket#additional-resources)

> ## Documentation Index
>
> Fetch the complete documentation index at: [https://docs.pipecat.ai/llms.txt](https://docs.pipecat.ai/llms.txt)
>
> Use this file to discover all available pages before exploring further.

## [​](https://docs.pipecat.ai/api-reference/server/services/transport/fastapi-websocket\#overview)  Overview

`FastAPIWebsocketTransport` provides WebSocket support for FastAPI web applications, enabling real-time audio communication over WebSocket connections. It’s primarily designed for telephony integrations with providers like Twilio, Telnyx, and Plivo, supporting bidirectional audio streams with configurable serializers and voice activity detection.

FastAPIWebsocketTransport is best suited for telephony applications and server-side WebSocket integrations.For general client/server applications, we recommend using WebRTC-based transports for more robust network and media handling.

[**FastAPI WebSocket API Reference** \\
\\
Pipecat’s API methods for FastAPI WebSocket integration](https://reference-server.pipecat.ai/en/latest/api/pipecat.transports.websocket.fastapi.html)

[**Example Implementation** \\
\\
Complete Twilio telephony integration example](https://github.com/pipecat-ai/pipecat-examples/tree/main/twilio-chatbot)

[**FastAPI Documentation** \\
\\
Official FastAPI WebSocket documentation](https://fastapi.tiangolo.com/advanced/websockets/)

[**Telephony Serializers** \\
\\
Learn about supported FrameSerializers for telephony providers](https://docs.pipecat.ai/api-reference/server/services/serializers/introduction)

## [​](https://docs.pipecat.ai/api-reference/server/services/transport/fastapi-websocket\#installation)  Installation

To use FastAPIWebsocketTransport, install the required dependencies:

```
uv add "pipecat-ai[websocket]"
```

## [​](https://docs.pipecat.ai/api-reference/server/services/transport/fastapi-websocket\#prerequisites)  Prerequisites

### [​](https://docs.pipecat.ai/api-reference/server/services/transport/fastapi-websocket\#fastapi-application-setup)  FastAPI Application Setup

Before using FastAPIWebsocketTransport, you need:

1. **FastAPI Application**: Set up a FastAPI web application
2. **WebSocket Endpoint**: Configure WebSocket routes for real-time communication
3. **Telephony Provider**: Set up integration with Twilio, Telnyx, or Plivo
4. **Frame Serializers**: Configure appropriate serializers for your telephony provider

### [​](https://docs.pipecat.ai/api-reference/server/services/transport/fastapi-websocket\#configuration-options)  Configuration Options

- **Serializer Selection**: Choose frame serializer based on telephony provider
- **Audio Parameters**: Configure sample rates and audio formats
- **VAD Integration**: Set up voice activity detection for optimal performance
- **Connection Management**: Handle WebSocket lifecycle and reconnections

### [​](https://docs.pipecat.ai/api-reference/server/services/transport/fastapi-websocket\#key-features)  Key Features

- **Telephony Integration**: Optimized for Twilio, Telnyx, and Plivo WebSocket streams
- **Frame Serialization**: Built-in support for telephony provider audio formats
- **FastAPI Integration**: Seamless WebSocket handling within FastAPI applications
- **Bidirectional Audio**: Real-time audio streaming in both directions

## [​](https://docs.pipecat.ai/api-reference/server/services/transport/fastapi-websocket\#configuration)  Configuration

### [​](https://docs.pipecat.ai/api-reference/server/services/transport/fastapi-websocket\#fastapiwebsockettransport)  FastAPIWebsocketTransport

[​](https://docs.pipecat.ai/api-reference/server/services/transport/fastapi-websocket#param-websocket)

websocket

WebSocket

required

The FastAPI WebSocket connection instance.

[​](https://docs.pipecat.ai/api-reference/server/services/transport/fastapi-websocket#param-params)

params

FastAPIWebsocketParams

required

Transport configuration parameters.

[​](https://docs.pipecat.ai/api-reference/server/services/transport/fastapi-websocket#param-input-name)

input\_name

str

default:"None"

Optional name for the input transport processor.

[​](https://docs.pipecat.ai/api-reference/server/services/transport/fastapi-websocket#param-output-name)

output\_name

str

default:"None"

Optional name for the output transport processor.

### [​](https://docs.pipecat.ai/api-reference/server/services/transport/fastapi-websocket\#fastapiwebsocketparams)  FastAPIWebsocketParams

Inherits from `TransportParams` with additional WebSocket-specific parameters.

[​](https://docs.pipecat.ai/api-reference/server/services/transport/fastapi-websocket#param-add-wav-header)

add\_wav\_header

bool

default:"False"

Whether to add WAV headers to outgoing audio frames.

[​](https://docs.pipecat.ai/api-reference/server/services/transport/fastapi-websocket#param-serializer)

serializer

FrameSerializer

default:"None"

Frame serializer for encoding/decoding WebSocket messages. Use a telephony
serializer (e.g., `TwilioFrameSerializer`, `TelnyxFrameSerializer`) for
provider-specific audio formats.

[​](https://docs.pipecat.ai/api-reference/server/services/transport/fastapi-websocket#param-session-timeout)

session\_timeout

int

default:"None"

Session timeout in seconds. When set, triggers `on_session_timeout` if the
session exceeds this duration. `None` disables the timeout.

[​](https://docs.pipecat.ai/api-reference/server/services/transport/fastapi-websocket#param-fixed-audio-packet-size)

fixed\_audio\_packet\_size

int

default:"None"

Optional fixed-size packetization for raw PCM audio payloads. Useful when the
remote WebSocket media endpoint requires strict audio framing (e.g., 640 bytes
for 20ms at 16kHz PCM16 mono).

## [​](https://docs.pipecat.ai/api-reference/server/services/transport/fastapi-websocket\#usage)  Usage

FastAPIWebsocketTransport integrates with your FastAPI application to handle telephony WebSocket connections. It works with telephony frame serializers to process audio streams from phone calls.See the [complete example](https://github.com/pipecat-ai/pipecat-examples/tree/main/twilio-chatbot) for a full implementation including:

- FastAPI WebSocket endpoint configuration
- Telephony provider integration setup
- Frame serializer configuration
- Audio processing pipeline integration

## [​](https://docs.pipecat.ai/api-reference/server/services/transport/fastapi-websocket\#event-handlers)  Event Handlers

FastAPIWebsocketTransport provides event handlers for client connection lifecycle and session management. Register handlers using the `@event_handler` decorator on the transport instance.

### [​](https://docs.pipecat.ai/api-reference/server/services/transport/fastapi-websocket\#events-summary)  Events Summary

| Event | Description |
| --- | --- |
| `on_client_connected` | Client WebSocket connected |
| `on_client_disconnected` | Client WebSocket disconnected |
| `on_session_timeout` | Session timed out |

### [​](https://docs.pipecat.ai/api-reference/server/services/transport/fastapi-websocket\#connection-lifecycle)  Connection Lifecycle

#### [​](https://docs.pipecat.ai/api-reference/server/services/transport/fastapi-websocket\#on_client_connected)  on\_client\_connected

Fired when a client successfully connects to the WebSocket.

```
@transport.event_handler("on_client_connected")
async def on_client_connected(transport, websocket):
    print("Client connected")
```

**Parameters:**

| Parameter | Type | Description |
| --- | --- | --- |
| `transport` | `FastAPIWebsocketTransport` | The transport instance |
| `websocket` | `WebSocket` | The FastAPI WebSocket connection object |

#### [​](https://docs.pipecat.ai/api-reference/server/services/transport/fastapi-websocket\#on_client_disconnected)  on\_client\_disconnected

Fired when a client disconnects from the WebSocket.

```
@transport.event_handler("on_client_disconnected")
async def on_client_disconnected(transport, websocket):
    print("Client disconnected")
```

**Parameters:**

| Parameter | Type | Description |
| --- | --- | --- |
| `transport` | `FastAPIWebsocketTransport` | The transport instance |
| `websocket` | `WebSocket` | The FastAPI WebSocket connection object |

#### [​](https://docs.pipecat.ai/api-reference/server/services/transport/fastapi-websocket\#on_session_timeout)  on\_session\_timeout

Fired when a session exceeds the configured `session_timeout` duration. Only fires if `session_timeout` is set in the params.

```
@transport.event_handler("on_session_timeout")
async def on_session_timeout(transport, websocket):
    print("Session timed out")
```

**Parameters:**

| Parameter | Type | Description |
| --- | --- | --- |
| `transport` | `FastAPIWebsocketTransport` | The transport instance |
| `websocket` | `WebSocket` | The FastAPI WebSocket connection object |

## [​](https://docs.pipecat.ai/api-reference/server/services/transport/fastapi-websocket\#additional-resources)  Additional Resources

- [Events Overview](https://docs.pipecat.ai/api-reference/server/events/overview) \- Overview of all events in Pipecat
- [Serializers](https://docs.pipecat.ai/api-reference/server/services/serializers/introduction) \- Frame serializers for telephony providers

[DailyTransport](https://docs.pipecat.ai/api-reference/server/services/transport/daily) [HeyGenTransport](https://docs.pipecat.ai/api-reference/server/services/transport/heygen)

Ctrl+I

![Project Logo](data:image/svg+xml,%3Csvg%20width%3D%2224%22%20height%3D%2224%22%20viewBox%3D%220%200%2024%2024%22%20fill%3D%22none%22%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%3E%3Cpath%20d%3D%22M3.3088%205.05615C3.64682%204.92779%204.02833%205.02411%204.26653%205.29797L7.36884%208.86461H16.6312L19.7335%205.29797C19.9717%205.02411%2020.3532%204.92779%2020.6912%205.05615C21.0292%205.18452%2021.253%205.51072%2021.253%205.87504V13.75H24V15.5H19.5181V8.19909L17.6762%2010.3167C17.5115%2010.506%2017.2738%2010.6146%2017.0241%2010.6146H6.9759C6.72616%2010.6146%206.48854%2010.506%206.32383%2010.3167L4.48193%208.19909V15.5H0V13.75H2.74699V5.87504C2.74699%205.51072%202.97078%205.18452%203.3088%205.05615Z%22%20fill%3D%22black%22%2F%3E%3Cpath%20d%3D%22M19.5181%2017.25H24V19H19.5181V17.25Z%22%20fill%3D%22black%22%2F%3E%3Cpath%20d%3D%22M0%2017.25H4.48193V19H0V17.25Z%22%20fill%3D%22black%22%2F%3E%3Cpath%20d%3D%22M9.25301%2014.3333C9.25301%2014.9777%208.73517%2015.5%208.09639%2015.5C7.4576%2015.5%206.93976%2014.9777%206.93976%2014.3333C6.93976%2013.689%207.4576%2013.1667%208.09639%2013.1667C8.73517%2013.1667%209.25301%2013.689%209.25301%2014.3333Z%22%20fill%3D%22black%22%2F%3E%3Cpath%20d%3D%22M17.0602%2014.3333C17.0602%2014.9777%2016.5424%2015.5%2015.9036%2015.5C15.2648%2015.5%2014.747%2014.9777%2014.747%2014.3333C14.747%2013.689%2015.2648%2013.1667%2015.9036%2013.1667C16.5424%2013.1667%2017.0602%2013.689%2017.0602%2014.3333Z%22%20fill%3D%22black%22%2F%3E%3C%2Fsvg%3E)

Ask AI

reCAPTCHA

Recaptcha requires verification.

protected by **reCAPTCHA**