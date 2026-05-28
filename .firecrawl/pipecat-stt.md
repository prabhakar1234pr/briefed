[Skip to main content](https://docs.pipecat.ai/pipecat/learn/speech-to-text#content-area)

[Pipecat home page![light logo](https://mintcdn.com/daily/r4jEtY4thtHXjZ16/logo/light.svg?fit=max&auto=format&n=r4jEtY4thtHXjZ16&q=85&s=46cda5b2f0afabd5f0298c64082c4125)![dark logo](https://mintcdn.com/daily/r4jEtY4thtHXjZ16/logo/dark.svg?fit=max&auto=format&n=r4jEtY4thtHXjZ16&q=85&s=f018b960ba26051755803a128139431b)](https://docs.pipecat.ai/)

Search...

Ctrl K

Search...

Navigation

Learning Pipecat

Speech to Text

[Overview](https://docs.pipecat.ai/overview/introduction) [Pipecat](https://docs.pipecat.ai/pipecat/get-started/introduction) [Pipecat Subagents](https://docs.pipecat.ai/subagents/introduction) [Pipecat Clients](https://docs.pipecat.ai/client/introduction) [Pipecat Flows](https://docs.pipecat.ai/pipecat-flows/introduction) [Pipecat Cloud](https://docs.pipecat.ai/pipecat-cloud/introduction) [API Reference](https://docs.pipecat.ai/api-reference/server/introduction)

> ## Documentation Index
>
> Fetch the complete documentation index at: [https://docs.pipecat.ai/llms.txt](https://docs.pipecat.ai/llms.txt)
>
> Use this file to discover all available pages before exploring further.

**Speech to Text (STT)** services are responsible for converting user audio into text transcriptions. They receive audio input from users and provide real-time transcriptions that your bot can process and respond to.

## [​](https://docs.pipecat.ai/pipecat/learn/speech-to-text\#pipeline-placement)  Pipeline Placement

STT processors must be positioned correctly in your pipeline to receive and process audio frames:

```
pipeline = Pipeline([\
    transport.input(),             # Creates InputAudioRawFrames\
    stt,                           # Processes audio → creates TranscriptionFrames\
    context_aggregator.user(),     # Uses transcriptions for context\
    llm,\
    tts,\
    transport.output(),\
])
```

**Placement requirements:**

- **After `transport.input()`**: STT needs `InputAudioRawFrame`s from the transport
- **Before context processing**: Transcriptions must be available for context aggregation
- **Before LLM processing**: Text must be ready for language model input

## [​](https://docs.pipecat.ai/pipecat/learn/speech-to-text\#stt-service-types)  STT Service Types

Pipecat provides two types of STT services based on how they process audio:

### [​](https://docs.pipecat.ai/pipecat/learn/speech-to-text\#1-sttservice-streaming)  1\. STTService (Streaming)

**How it works:**

- Establishes a WebSocket connection to the STT provider
- Continuously streams audio for real-time transcription
- Lower latency due to persistent connection

### [​](https://docs.pipecat.ai/pipecat/learn/speech-to-text\#2-segmentedsttservice-http-based)  2\. SegmentedSTTService (HTTP-based)

**How it works:**

- Uses local VAD (Voice Activity Detection) to chunk speech
- Sends audio segments to STT service as wav files
- Higher latency due to segmentation and HTTP POST requests

STT services are modular and can be swapped out with no additional overhead.
You can easily switch between streaming and segmented services based on your
needs.

## [​](https://docs.pipecat.ai/pipecat/learn/speech-to-text\#supported-stt-services)  Supported STT Services

Pipecat supports a wide range of STT providers to fit different needs and budgets:

[**Supported STT Services** \\
\\
View the complete list of supported speech-to-text providers](https://docs.pipecat.ai/api-reference/server/services/supported-services#speech-to-text)

Popular options include:

[**Deepgram** \\
\\
Fast, accurate streaming STT with excellent real-time performance](https://docs.pipecat.ai/api-reference/server/services/stt/deepgram)

[**Speechmatics** \\
\\
Advanced speech recognition with strong accent and dialect handling](https://docs.pipecat.ai/api-reference/server/services/stt/speechmatics)

[**AssemblyAI** \\
\\
AI-powered transcription with speaker diarization and sentiment analysis](https://docs.pipecat.ai/api-reference/server/services/stt/assemblyai)

[**Gladia** \\
\\
High-performance STT with multilingual support and custom models](https://docs.pipecat.ai/api-reference/server/services/stt/gladia)

[**Azure Speech** \\
\\
Microsoft’s enterprise-grade STT service with extensive language support](https://docs.pipecat.ai/api-reference/server/services/stt/azure)

[**Google Speech-to-Text** \\
\\
Reliable transcription with strong language model integration](https://docs.pipecat.ai/api-reference/server/services/stt/google)

## [​](https://docs.pipecat.ai/pipecat/learn/speech-to-text\#stt-configuration)  STT Configuration

### [​](https://docs.pipecat.ai/pipecat/learn/speech-to-text\#service-specific-configuration)  Service-Specific Configuration

Each STT service has its own customization options. Refer to specific service documentation for details:

[**Individual STT Services** \\
\\
Explore configuration options for each supported STT provider](https://docs.pipecat.ai/api-reference/server/services/supported-services#speech-to-text)

For example, let’s look at configuring the **DeepgramSTTService** using the `LiveOptions` class:

```
from deepgram import LiveOptions
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.transcriptions.language import Language

# Configure using LiveOptions for full control
live_options = LiveOptions(
    model="nova-2",
    language=Language.EN_US,
    interim_results=True,        # Enable interim transcripts
    punctuate=True,              # Add punctuation
    profanity_filter=True,       # Filter profanity
    vad_events=False,            # Use pipeline VAD instead
)

stt = DeepgramSTTService(
    api_key=os.getenv("DEEPGRAM_API_KEY"),
    live_options=live_options,
)
```

### [​](https://docs.pipecat.ai/pipecat/learn/speech-to-text\#sttservice-base-class-configuration)  STTService Base Class Configuration

All STT services inherit from the STTService base class. The base class has base configuration options which are set with smart defaults:

```
stt = YourSTTService(
    # Service-specific options...
    audio_passthrough=True,      # Pass audio frames downstream (recommended)
    sample_rate=16000,           # Audio sample rate (better set in PipelineParams)
)
```

**Key options:**

- **`audio_passthrough=True`**: Allows audio frames to continue downstream to other processors (like audio recording)
- **`sample_rate`**: Audio sampling rate - best practice is to **set the `audio_in_sample_rate` in `PipelineParams` for consistency**

Setting `audio_passthrough=False` will stop audio frames from being passed
downstream, which may break audio recording or other audio-dependent
processors.

### [​](https://docs.pipecat.ai/pipecat/learn/speech-to-text\#pipeline-level-audio-configuration)  Pipeline-Level Audio Configuration

Instead of setting sample rates on individual services, configure them pipeline-wide:

```
task = PipelineTask(
    pipeline,
    params=PipelineParams(
        audio_in_sample_rate=16000,   # All input processors use this rate
        audio_out_sample_rate=24000,  # All output processors use this rate
    ),
)
```

This ensures all audio processors use consistent sample rates without manual configuration.

Always set audio sample rates in `PipelineParams` to avoid mismatches between
different audio processors. This simplifies configuration and ensures
consistent audio quality across your pipeline.

## [​](https://docs.pipecat.ai/pipecat/learn/speech-to-text\#multilingual-transcription)  Multilingual Transcription

Many STT services in Pipecat default to `Language.EN` (English). If you need to transcribe speech in other languages or let the model auto-detect the spoken language, you can enable multilingual support. However, providers implement this differently:**`language=None`** — Whisper-based services (Groq, OpenAI, local Whisper) and ElevenLabs support automatic language detection when no language is specified:

```
from pipecat.services.groq.stt import GroqSTTService

stt = GroqSTTService(
    api_key=os.getenv("GROQ_API_KEY"),
    settings=GroqSTTService.Settings(
        language=None,  # Auto-detect language
    ),
)
```

**`language="multi"`** — Deepgram uses a special `"multi"` language code to enable multilingual transcription:

```
from pipecat.services.deepgram.stt import DeepgramSTTService

stt = DeepgramSTTService(
    api_key=os.getenv("DEEPGRAM_API_KEY"),
    settings=DeepgramSTTService.Settings(
        language="multi",  # Enable multilingual mode
    ),
)
```

**Language array** — Google Cloud STT accepts a list of languages for multi-language recognition. See the [Google STT docs](https://docs.pipecat.ai/api-reference/server/services/stt/google) for details.

Some services have additional multilingual features. For example, Soniox
supports language hints, AssemblyAI offers a dedicated multilingual model, and
Speechmatics supports bilingual transcription. See individual service docs for
details.

## [​](https://docs.pipecat.ai/pipecat/learn/speech-to-text\#best-practices)  Best Practices

### [​](https://docs.pipecat.ai/pipecat/learn/speech-to-text\#enable-interim-results)  Enable Interim Results

When available, enable interim transcripts for better user experience:

```
stt = DeepgramSTTService(
    api_key=os.getenv("DEEPGRAM_API_KEY"),
    live_options=LiveOptions(
      interim_results=True,
    )
)
```

**Benefits:**

- Notifies context aggregation that more text is coming
- Prevents premature LLM completions
- Enables interruption detection
- Improves conversation flow

### [​](https://docs.pipecat.ai/pipecat/learn/speech-to-text\#enable-punctuation-and-formatting)  Enable Punctuation and Formatting

Use punctuation when available for better LLM comprehension:

```
stt = DeepgramSTTService(
    api_key=os.getenv("DEEPGRAM_API_KEY"),
    live_options=LiveOptions(
        punctuate=True,        # Adds punctuation
        profanity_filter=True, # Optional content filtering
    )
)
```

**Benefits:**

- Professional-looking transcripts
- Better LLM comprehension
- Eliminates post-processing needs
- Improved context understanding

### [​](https://docs.pipecat.ai/pipecat/learn/speech-to-text\#use-local-vad)  Use Local VAD

While many STT services provide Voice Activity Detection, use Pipecat’s local Silero VAD for better performance:

```
from pipecat.audio.vad.silero import SileroVADAnalyzer

# Configure in context aggregator
user_aggregator, assistant_aggregator = LLMContextAggregatorPair(
    context,
    user_params=LLMUserAggregatorParams(
        vad_analyzer=SileroVADAnalyzer(),
    ),
)
```

**Advantages:**

- **150-200ms faster** speech detection (no network round trip)
- More responsive conversation flow
- Better interruption handling
- Reduced latency overall

### [​](https://docs.pipecat.ai/pipecat/learn/speech-to-text\#tune-stt-latency)  Tune STT Latency

Each STT service has a measured P99 latency for delivering final transcripts after the user stops speaking. This value is used by turn stop strategies to decide how long to wait before ending the user’s turn. If you notice the bot responding too early (cutting off the user) or too late (long pauses), tuning this value can help.

[**STT Latency Tuning** \\
\\
Learn about TTFS latency, see default values for every STT service, and how to\\
measure and override for your deployment](https://docs.pipecat.ai/pipecat/fundamentals/stt-latency-tuning)

## [​](https://docs.pipecat.ai/pipecat/learn/speech-to-text\#key-takeaways)  Key Takeaways

- **Pipeline placement matters** \- STT must come after transport input, before context processing
- **Service types differ** \- streaming services have lower latency than segmented
- **Services are modular** \- easily swap providers without code changes
- **Best practices improve performance** \- use interim results, formatting, and local VAD
- **Configuration affects quality** \- proper setup significantly impacts transcription accuracy

## [​](https://docs.pipecat.ai/pipecat/learn/speech-to-text\#what%E2%80%99s-next)  What’s Next

Now that you understand speech recognition, let’s explore how to manage conversation context and memory in your voice AI bot.

[**Context Management** \\
\\
Learn how to handle conversation history and context in your pipeline](https://docs.pipecat.ai/pipecat/learn/context-management)

[Speech Input & Turn Detection](https://docs.pipecat.ai/pipecat/learn/speech-input) [Context Management](https://docs.pipecat.ai/pipecat/learn/context-management)

Ctrl+I

![Project Logo](data:image/svg+xml,%3Csvg%20width%3D%2224%22%20height%3D%2224%22%20viewBox%3D%220%200%2024%2024%22%20fill%3D%22none%22%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%3E%3Cpath%20d%3D%22M3.3088%205.05615C3.64682%204.92779%204.02833%205.02411%204.26653%205.29797L7.36884%208.86461H16.6312L19.7335%205.29797C19.9717%205.02411%2020.3532%204.92779%2020.6912%205.05615C21.0292%205.18452%2021.253%205.51072%2021.253%205.87504V13.75H24V15.5H19.5181V8.19909L17.6762%2010.3167C17.5115%2010.506%2017.2738%2010.6146%2017.0241%2010.6146H6.9759C6.72616%2010.6146%206.48854%2010.506%206.32383%2010.3167L4.48193%208.19909V15.5H0V13.75H2.74699V5.87504C2.74699%205.51072%202.97078%205.18452%203.3088%205.05615Z%22%20fill%3D%22black%22%2F%3E%3Cpath%20d%3D%22M19.5181%2017.25H24V19H19.5181V17.25Z%22%20fill%3D%22black%22%2F%3E%3Cpath%20d%3D%22M0%2017.25H4.48193V19H0V17.25Z%22%20fill%3D%22black%22%2F%3E%3Cpath%20d%3D%22M9.25301%2014.3333C9.25301%2014.9777%208.73517%2015.5%208.09639%2015.5C7.4576%2015.5%206.93976%2014.9777%206.93976%2014.3333C6.93976%2013.689%207.4576%2013.1667%208.09639%2013.1667C8.73517%2013.1667%209.25301%2013.689%209.25301%2014.3333Z%22%20fill%3D%22black%22%2F%3E%3Cpath%20d%3D%22M17.0602%2014.3333C17.0602%2014.9777%2016.5424%2015.5%2015.9036%2015.5C15.2648%2015.5%2014.747%2014.9777%2014.747%2014.3333C14.747%2013.689%2015.2648%2013.1667%2015.9036%2013.1667C16.5424%2013.1667%2017.0602%2013.689%2017.0602%2014.3333Z%22%20fill%3D%22black%22%2F%3E%3C%2Fsvg%3E)

Ask AI

reCAPTCHA

Recaptcha requires verification.

protected by **reCAPTCHA**