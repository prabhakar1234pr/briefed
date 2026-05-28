"""
v2 voice pipeline package.

Components:
  - memory:      Supermemory client (unified doc + meeting + code memory)
  - context:     in-meeting turn buffer + cross-meeting recall composition
  - turn_taking: hybrid trigger (name regex OR addressed-to-bot classifier)
  - runner:      per-meeting Pipecat pipeline lifecycle
  - bot_bridge:  FastAPI WebSocket route the bot-page connects to
"""
