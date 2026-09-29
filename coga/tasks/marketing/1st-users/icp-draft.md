# ICP draft (owner-supplied, 2026-09-29, verbatim — unaudited)

The best target is probably not “developers who use agents.” It is more specific:

**Small technical teams that already use coding agents heavily, where coordination and accumulated knowledge are becoming more expensive than writing the code itself.**

The strongest fit looks like this:

- **2–8 person technical teams** that are Git/CLI native and use Claude Code, Codex, or similar tools every day.
- **Startups or labs building something genuinely new**, where a lot of the work involves judgment, evolving conventions, and learning what works.
- **Teams doing repetitive but not fully automatable engineering work**: releases, migrations, triage, maintenance, PR cleanup, operational checks, recurring investigations.
- **Teams using multiple agents or models on the same codebase**, where project-owned knowledge is more useful than memory tied to one agent.
- **Teams where a founder or tech lead holds a lot of important context in their head**, and repeatedly has to explain the same things to agents or teammates.

The mindset matters almost as much as team size. The ideal Coga user naturally thinks:

> “We just learned something. How do we make sure we never have to explain it again?”

rather than:

> “I just want the agent to finish this task right now.”

Strong signs of fit are complaints like:

- “Claude keeps making the same mistake.”
- “I keep having to re-explain how our system works.”
- “Our AGENTS.md is getting huge.”
- “We have lots of rules and skills, but they are becoming messy.”
- “We use several agents, but there is no reliable shared memory.”

I would **not** target first:

- occasional agent users;
- teams whose work is mostly one-off;
- people who do not want Git/text-file workflows;
- large enterprises that immediately need RBAC, dashboards, permissions, and compliance infrastructure;
- teams mainly looking for a dynamic swarm/runtime rather than a human+agent work system.

If I had to pick one beachhead:

**2–5 engineers building a technically novel product, already spending several hours a day with coding agents, and repeatedly reviewing and correcting agent work.**

That is where Coga’s value becomes concrete: **each correction can become a permanent improvement to the way future work gets done, instead of disappearing into a chat.**
