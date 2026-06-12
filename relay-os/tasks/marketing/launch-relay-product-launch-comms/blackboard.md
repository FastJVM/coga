The blackboard is a notepad to be written to often as the human and agent works through a task.

## 2026-06-12 — Fork decided: B (Relay-as-category brand bet)

Zach picked Fork B. Tone: the Linear playbook — opinionated craft, a
name, evangelism — aimed at the narrow tribe, never mass appeal. The
spine stays ownership/independence ("own your machine, depend on
vendors less"); category is operations-as-code; lead with the legible
version of the thesis, not the reading list. Honest limits stay in the
copy — a brand bet that oversells dies on first contact.

## Launch plan — concrete actions

### Phase 0 — prerequisites (gate the public flip)

1. **Make the relay repo public.** Owner: Zach (GitHub settings; agent
   can pre-flight: scan history for secrets/PII, check relay.local.toml
   never committed). Also the prerequisite for the relay-discord rollout.
2. **README rewritten to launch tone.** Hero one-liner, the worldview in
   three paragraphs, quickstart, honest-limits section, Discord invite.
   Agent drafts, Zach reviews. This is the landing page for fork B until
   a real one exists — decide explicitly whether README-as-landing is
   enough for v1 (recommend: yes, ship a site later).
3. **Discord live.** Channels #general/#help/#contributing/#announcements,
   invite link in README. Owner: per `relay-discord` ticket (Nick).
4. **Killer demo recorded.** The 2-minute correction loop — catch the
   agent wrong → fix one context line → re-run → right behavior. This is
   the felt proof point fork B rests on. Ties to `add-killer-demo`
   ticket. Owner: Zach/Nick record, agent scripts the scenario.
5. **Timing decision.** Positioning context warns: auto-mode is
   temporarily disabled and the felt layer is gated behind maturity
   fixes (Slack drops, watchdog). Either (a) hold launch until those
   land, or (b) launch now with limits stated plainly. Needs Zach's
   call — recommend (b) only if the demo works without auto-mode.

### Phase 1 — launch assets (agent-draftable, Zach reviews each)

6. **Hero copy / launch narrative.** The one-liner + the worldview
   ("compile your company", classical-in-a-romantic-stampede). One
   canonical long-form post; everything else derives from it.
7. **Channel copy derived from the post:**
   - Show HN title + first comment
   - X/Twitter thread (concrete, no transformation buzzwords)
   - Discord #announcements inaugural post
   - Personal-network message — the "tell our users/friends" item from
     `relay-discord` (short, sendable by Zach/Nick directly)

### Phase 2 — sequencing (single day for the public beats)

8. Repo public → README + demo merged → Discord invite live →
   **soft circle first** (friends/users get the personal message, a few
   days of quiet feedback) → then Show HN + X thread same day →
   Discord announcement.

### Phase 3 — post-launch cadence

9. Monthly changelog in #announcements (candidate for relay-recurring,
   per the relay-discord ticket).
10. Respond loop: HN comments + Discord #help for the first week is a
    daily human task, not agent-delegable.

### What the agent intends to take next (in order)

- Draft the README rewrite (action 2) as a PR for review.
- Draft the canonical launch post (action 6) in this task dir for
  iteration before any channel copy.
- Script the correction-loop demo scenario (action 4 support).

### Open questions for Zach

- Timing call (action 5): wait for maturity fixes or launch with stated
  limits?
- Is README-as-landing acceptable for v1, or does fork B need a site
  before going loud?
- Who sends the personal-network message, and roughly how many people
  is the soft circle?
