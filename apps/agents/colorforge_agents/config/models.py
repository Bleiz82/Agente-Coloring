"""Centralized Claude model registry for ColorForge agents.

This module is the single source of truth for which Claude model
each agent uses. Changing a model here propagates to all callers.

Cost reference (per 1M tokens, May 2026):
- claude-sonnet-4-6:           $3 input / $15 output
- claude-haiku-4-5-20251001:   $1 input / $5  output  (~70% cheaper)
- claude-opus-4-7:             $15 input / $75 output (premium tier)
"""
from __future__ import annotations

# Strategic tasks requiring deep reasoning / creativity
SONNET = "claude-sonnet-4-6"

# High-volume repetitive tasks (critique, validation, structured output)
HAIKU = "claude-haiku-4-5-20251001"

# Premium tasks (reserved for future use)
OPUS = "claude-opus-4-7"

# Per-agent assignments — change here to update all callers
CRITIC_MODEL = HAIKU
VISION_CHECKER_MODEL = HAIKU
LISTING_AGENT_MODEL = HAIKU
POLICY_PROPOSER_MODEL = HAIKU
NICHE_ANALYZER_MODEL = SONNET  # keep Sonnet for strategic niche research
