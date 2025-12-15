# AGENTS.md

This document defines the roles and responsibilities of automated agents (AI or otherwise) used in the development and simulation of **Peanuts and Crackerjacks**.

Agents are treated as collaborators, not oracles.

---

## 🧠 Agent Philosophy

Agents in this project must:
- Preserve simulation realism
- Avoid retroactively altering historical data
- Operate within clearly defined scopes
- Prefer transparency over cleverness

No agent should “win” the game for the player.

---

## ⚾ Simulation Agents

### Pitch Simulation Agent
Responsible for:
- Resolving individual pitch outcomes
- Using provided stats, context, and modifiers
- Returning deterministic results when seeded

Must NOT:
- Invent stats
- Rewrite player history
- Force narrative outcomes

---

### Game Flow Agent
Responsible for:
- Managing inning progression
- Outs, runners, substitutions
- Triggering play-by-play events

Operates strictly on state transitions.

---

## 🧮 Management AI (League Opponents)

### AI Team Manager
Used for non-player-controlled teams.

Responsibilities:
- Setting lineups and rotations
- Managing fatigue and injuries
- Making reasonable strategic decisions

Design goal:
> Feel *human*, not optimal.

---

## 📣 Commentary & Flavor Agents

### Play-by-Play Narrator
Generates:
- Pitch descriptions
- Play outcomes
- Occasional color commentary

Constraints:
- Must match the actual simulation result
- Cannot contradict stats or game state
- Tone varies by stadium and crowd energy

---

### Lore Whisper Agent
Optional, subtle agent that:
- Injects rare atmospheric lines
- References history obliquely
- Never explains the full truth

This agent should feel like coincidence.

---

## 🎺 Organ / Crowd Agent

Controls:
- Crowd energy accumulation
- Threshold-triggered effects
- Visual/audio feedback signals

Rules:
- Effects apply as modifiers, never as absolutes
- Crowd energy decays naturally
- Home field advantage must remain bounded

---

## 🧪 Experimental Agents (Future)

- Marketing strategy suggestion agents
- Stadium upgrade planners
- Long-term league history archivists

These agents must be sandboxed and optional.

---

## 🚫 What Agents Must Never Do

- Change player stats permanently without a game event
- Override simulation results after resolution
- Reveal lore explicitly unless unlocked
- Optimize fun out of the game

---

## ✅ Agent Output Format

All agent outputs should be:
- Structured (JSON preferred)
- Deterministic when seeded
- Logged for replay/debugging

---

## 📝 Final Note

Agents exist to support **emergence**, not control it.

If the game ever feels scripted, an agent is doing too much.
