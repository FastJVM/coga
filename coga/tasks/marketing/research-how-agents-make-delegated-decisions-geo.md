---
title: Research how agents make delegated decisions (GEO)
status: in_progress
owner: zach
workflow:
  name: human/run
  steps:
  - name: execute
    skills: []
    assignee: owner
step: 1 (execute)
agent: claude
---

## Description

Nico asked Zach (Nov 13) to spend 1–2 hours researching how agents make decisions that people delegate to them, which Nico called "search engine optimization for agents" and is usually called GEO (generative engine optimization). Then Zach reports back to Nico: "here's where you're right, here's where you're wrong, and here's what you forgot." This is Zach's research and Zach's conclusion. An agent supports it only as a sounding board in assist sessions (`coga launch <slug> --agent claude`): it answers Zach's questions, finds and checks sources, and pushes back on reasoning. It doesn't write the verdict or close the ticket.

Done when Zach has sent Nico a write-up that takes each of the six claims below and says right, wrong or more complicated, with sources; lists what the thesis leaves out; and says what it means for coga (README and docs written for agents, coga as the first test run).

### Nico's thesis (six claims to check)

1. Agents reason about documents, while search engines rank by consensus ("the loudest voice"). So one document with provable facts can beat the majority view.
2. People hand agents the decisions they don't care about (e.g. an engineer choosing a transactional email provider), and the agent does think those decisions through.
3. This only holds for decisions people don't care about. For ones they're invested in (savings, groceries, stock picking), people check the advice, and ordinary marketing still works.
4. Winning takes provable, trustworthy evidence: reproducible, objective benchmarks "endorsed by the right people." Marketing moves from being marketing-driven to benchmark-driven, a new channel.
5. Provable facts published online "bubble up all the way to the agent" through pre-training and post-training.
6. Only some markets are affected. Finding those markets is the point, and the reason for the focus on benchmarks.

### Main example: email delivery

Nico and Zach found that a small self-hosted mail server delivers out of the box everywhere except Outlook. Their view is that deliverability depends on the authentication and DNS setup more than on IP reputation, so small transactional senders don't need Resend (about $20/month; Nico estimates Resend's revenue from these customers at $20–50M). The industry says self-hosting isn't an option. A reproducible benchmark that agents can read could change what they recommend.

### Questions Zach raised to test

- Models are trained on the same internet. Don't they follow the majority view rather than a single well-evidenced source?
- Don't agents also have a big say in decisions people do care about?
- Keep live retrieval (the agent searching and reading now) separate from training (facts absorbed by the model). Claims 1 and 5 depend on different ones.

### Sources

- Summary doc, "Nico's thesis: agents as an evidence-driven marketing channel": https://docs.google.com/document/d/1KfB3Khf8x_osy2J2vJZOIpKi7tKrCqqxJ7x6qteNB9o/edit
- Pocket recording "Email Delivery and Agent Decision-Making," Nov 13 2026, 9:57 AM.
- Starting point: "GEO: Generative Engine Optimization" (Aggarwal et al., 2023, arXiv:2311.09735). Cited from memory, so verify it.

## Context

<!-- Ticket guide — keep this comment when filling in or updating the ticket.
It documents field shapes; these are examples, not values to copy into every
ticket. Omit optional fields and sections until needed. Editing rules come
from the base prompt; body regions from coga/tickets; blackboard conventions
(superseded designs, draft cleanup, oversized notes) from coga/blackboard.
Write requirements under ### subheadings of Description or Context; any other
level-two heading above the fence does not reach the launch prompt.

FRONTMATTER
The real values are in this ticket's YAML header. Required ordinary-ticket
keys are title, status, owner, and workflow. A minimal draft has workflow: null.

    title: Fix retry diagnostics           # What the work is called; identity comes from the file path.
    status: draft                          # CLI state: draft, active, in_progress, paused, blocked, done, canceled.
    owner: human-name                      # Accountable human; receives notifications and owner gates.
    agent: codex                           # Optional configured main agent; activation supplies the default if absent.
    contexts:                              # Optional facts to include in every launch; attach only what is needed.
      - service/retries
    skills:                                # Optional ticket-wide procedures, in addition to workflow step skills.
      - infra/testing-conventions
    workflow: code/with-review             # Draft reference or null; live tickets have the frozen mapping below.
    secrets:                               # Optional environment names mapped to references, never credentials.
      - API_TOKEN: env:LOCAL_API_TOKEN
      - SERVICE_KEY: op://automation-vault/service/api-key

The agent choice is not the current operator or the ticket interviewer.
Omit empty contexts, skills, and secrets lists. Each secrets entry has exactly
one unique name (no COGA_ prefix); env: reads the operator's environment and
op:// reads a 1Password item at launch, exposing the value under the left-hand
name. An unavailable reference prevents launch. Never put a literal secret here.

A workflow must be selected before activation. Creation with --workflow, or
activation of a draft reference, freezes its steps. CLI transitions manage step;
do not rewrite a live snapshot or advance it by editing YAML. Frozen example:

    workflow:
      name: code/with-review                # Selected workflow name.
      steps:
        - name: implement                  # Ordered step name.
          skills:                          # Optional procedures for this step; plural, never skill.
            - code/implement
          assignee: agent                  # Role: owner, agent, or other-agent (the configured peer).
          requires: branch                 # Optional completion gate: branch or pr.
    step: 1 (implement)                    # One-based position plus name; CLI removes this on completion.

An omitted step assignee inherits the previous role; the first defaults to
owner. The current step determines who holds the ticket. There is no top-level
assignment field. Removed keys slug, human, assignee, and watchers are invalid.
There is no execution-mode field: a sibling ticket.py supplies a script phase.

Repo extensions are string fields declared under [ticket.fields.<name>] in
coga.toml: description explains the field, values restricts its choices,
default seeds it, and required prevents activation while it is empty. Actual
values live below the extensions marker comment in the YAML header. Preserve
them; do not invent extension fields or change their definitions in config.

Machine-owned fields: delegate freezes a recurring parent's bootstrap/<name>
target; period_generation identifies its materialized run. Both belong only on
period tasks directly under tasks/recurring/. launch_generation is megalaunch's
session claim. Preserve these fields; do not add or clear them yourself.

BLACKBOARD (BELOW THE FENCE)
Keep current decisions and their reasons, verification, next actions, and
blockers here. Update current values in place instead of appending stale copies.

Optional ## Dev: branch: <name> when created; pr: <full /pull/ URL> when opened;
worktree: <path> only for a sandbox clone. One field per line, notes on separate
lines, omit unknown values. For multiple owned branches, the first branch is
the workflow branch.

Optional ## PR: one fenced YAML mapping of PR-preparation receipts (title,
author, head/base OIDs, review depth, files, review, checks). Record only actual
implementation and evidence, never placeholders; coga/pr-publication/
preparation owns the fields and the publishing workflow the review rules.

Optional ## Blockers and ## Blocker reminders are CLI-maintained. Preserve
blocker IDs, timestamps, actor names, resolved answers, and reminder fingerprints
with last_reminded timestamps; use lifecycle commands to block or resolve them.

Recurring parents (coga/recurring/<name>/ticket.md) take schedule and related
template settings owned by coga/recurring/templates; do not add them to an
ordinary ticket.
-->

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

**Sources Reviewed:** 

1. Optimizing Visibility in Generative Engines: A Critical Survey of Generative Engine Optimization 

  *GE's move through steps. How it sounds like this process differs from SEO is that SEO simply ranks a list of links based on traffic or revenue generation. GEO retrieves documents (I think docs that explain what they searched), uses those documents to create contexts, and then from those documents, makes a decision on how the information should be presented to users? -- **I'm having trouble reconciling between the fact that traffic is an output, yet that the GE doesn't distinguish between maliciousness and truthfulness. Maybe I'm looking at the wrong information** 

  **The author says that traffic is an output, not an input** -- But according to the paper, when your info is cited it implies neither credibility nor support. Maliciousness and truthfulness is found to be an aspect that the GE's can't identify themselves. The paper states that this boundary is more a problem of humans creating the right boundaries and not something the AI, as it stands, is capable of separating. 

  **There's a discovery bottleneck according to this source** -- This study found that GEO works AFTER a document is already retrieved. If your document lacks traditional web discovery, regardless of its "correctness", the chances of an agent citing it is still a problem. 

2. GEO: Generative Engine Optimization

  **Black Box** It's still not well understood how GE's pick links to cite. There's no clear way for website owners to measure how their content is displayed. 

  **Clear Gains were Achieved** The authors, by applying GEO strategies, achieved a 40% increase in source citation? The tactics that worked best were adding citations, quotes from relevant sources, and statistics. These were the strategies used to lock the 40% gain in visibility. This point clearly relates to the finding from the first paper that **traffic is an output, not an input**

  **Visibility Gains were not Equally Distributed** It depended heavily on the domain where the strategies were applied. It sounds like some topics resulted in no or little gain from the strategies. Certain domains experienced gains from the same strategies that didn't work for others. 

  **Information on the Types of Domains where Strategies Worked** The author found that the edits achieved the best gains when the strategies suited the specific query need. This means that adding citations helped most for factual or statement style questions. While adding statistics were most helpful for Law and Government and **opinion** related questions. When **arguments** are coupled with data-driven support, it's thought to lead to better visibility. **The results support choosing edits that best fit the query**

  The paper gives evidence that content changes can influence what surfaces in generated answers, but does not support the main claim in our paper that objective, reproducible, evidence alters an agent's decision on what it recommends among competing products. 


3. What Evidence Do Language Models Find Convincing?

  **Agent decisions based on relevance** The paper found that models generally rank the information's relevance to the question above whether the information is found credible or not. 

  **Adding references had a neutral or negative effect** 


4. Adaptive Chameleon or Stubborn Sloth: REVEALING THE BEHAVIOR OF LARGE LANGUAGE MODELS IN KNOWLEDGE CONFLICTS

  **LLM's can accept convincing external evidence even that goes against their training** -- The authors provided the agents with coherent "counter-memories" against an answer that the agent already had supporting evidence for. They found that when these "counter memories" were the only example provided, agents were receptive to the new knowledge, even when it went against their "parametric memory". 

  **A breakdown of the findings** The authors first elicited a model’s answer and explanation in a separate, closed-book step, treating that as evidence of its “parametric memory.” They filtered examples so the explanation supported the answer and the model gave the same answer when shown that explanation later. Then, in the single-source test, they presented a coherent passage supporting a different answer as the only external evidence and asked the model to answer. Models were generally receptive and often chose the counter-answer, despite their internally stored answer pointing the other way.

  **A good point here** The work here separates being cited from actually shaping the answer. Being cited isn't the same as influencing the answer.


5. Generative Engine Optimization: How to Dominate AI Search 

  **Low Domain Overlap with Google** This proves that Generative engines build substantially different search results from Google.

  **What Won in AI Search** Earned results heavily outperformed Brand results. The paper distinguishes sources by who publishes them. If we were to produce a reproducible benchmark that was published in an engineering or software journal, the paper's findings are that this source would win out in agent decisions over things published on a brand page. 


-- Restarting, or rather digesting the research in a different way from here on. Specifically using our document to test claims against the prevailing research. -- 

1. When agents make delegated decisions

  Open web search wins rely on query relevance and "Earned" distinction. 

  **"In-context"** generation can result in coherent technical evidence winning the agent recommendation. When an LLM is provided with coherent counter-evidence to its trained beliefs, it's very receptive to changing its mind. (I need to understand in-context generation though). 

  **Structuring for Justification** Agent functions as a decision-making partner where decision support dominates. (I don't know what this means). 

  **Upstream Retrieval Bottleneck** Optimizing body content often detracted from the chances that new or unconventional information was retrieved in the first place. 

  Agents show extreme confirmation bias in multi-source contexts. If the agent is choosing between incumbent information (SendGrid, Resend) and the conflicting perspective of lesser-known information. Regardless of its credibility, agents tend to fall back to their overall training knowledge. 

  Models judge convincingness based on the relevance to the query rather than credibility or empirical rigor. If an incumbent document matches the user's prompt tokens more closely, it is far more likely to show the result with more relevance to the query. 

2. Influencing human decisions based on shifted mental models 

    Studies have found that nearly half of cited sentences in commercial generative engines fail to support the text they accompany. An agent may cite a technical benchmark to support a general point, yet still recommend the market leader in its summary sentence.

    Observed increases in referral traffic from AI engines were not based on content-level changes but rather on general platform growth. 

3. Market variance and vulnerability to evidence-driven disruption 

  The GEO survey and empirical audits show that market structure dictates agent behavior. Certain markets are highly impacted by evidence where others aren't. For example, developer tools and infrastructure: Include objective, measurable metrics. While consumer lifestyle was more impacted by brand entrenchment. Subjective, taste-driven criteria. 

  The GEO paper found that factual and legal queries responded better to citations, while opinion-driven queries responded better to statistics and benchmarks. It's like if you can find the right class of supportive evidence to fit the other side of the puzzle, then agents will award you with higher visibility. 

  For evidence to win, the market must be one with users who naturally prompt the agent with hard functional constraints. This allows quantitative, established figures to award more visibility in domains where requirements can be specified mathematically. You won't see the same visibility gains for subjective statements of "this product has a better ergonomic design."

  In fragmented technical markets where there is no single monolithic authority, agents must research **the long tail** providing an opening for new technical benchmarks to surface. (Consumer electronics is dominated by TechRadar and RTINGS, making these markets more difficult for uncoventional data to gain visibility). 

4. Is a repeatable marketing advantage realistic? 

  In regards to publishing a technical benchmark on your own domain and expecting agents to organically discover it and switch their defaults, the current literature says no. The research shows that agents heavily penalize vendor owned blogs. If you're able to have your technical benchmark covered by an independent third-party, however, the research says this can be repeatable. "AI search engines allocate 70%–95% of their citations to independent third-party outlets."

  Agents are more likely to give visibility to "lots of facts in a little space, with no sales talk around it." For example, specs on a phone's box: "battery 20 hours, weight 180 g, price $499". An agent that's trying to answer a question can lift one exact fact out of a table more reliably than it can dig the same fact out of paragraphs of marketing copy. 

  Charts showing explicit trade-offs: Option B: Cheapest? No. Fastest? Yes. Easiest to set up? No. Option A: Cheapest? Yes. Fastest? No. Easiest to set up? Yes. Agents can quickly answer questions posed by the user's prompt. A table helps if it answers what the agent was asked, not just because it's a table. This supports that edits achieved the best gains when the strategies suited the specific query need. **The real hurdle, in my opinion, in gaining visibility, is almost being able to guess how a user in a specific market will prompt the agent?**

  In-context: describes a situation: the model is given information right now, inside the conversation, and answers from that information rather than only from what it memorized in training. "In context" means "in front of it at the moment."

**Important Point** GEO is a pipeline (discovery->retrieval->citation->traffic) 

"In Chameleon Table 6, with one source supporting what ChatGPT already believed against two contradicting it, ChatGPT sided with the contradicting sources about 70% of the time. With equal numbers, the prior belief won. So "the majority view wins" partly means count the sources, and that actually helps your third-party argument (below)."

**Agent session notes (Nov 15–16)**

Findings doc: [GEO research: findings and view](https://docs.google.com/document/d/1mhyblHAhw4GSKY5dn6jAJmedTL5AbPrtfBzxiRx77Po/edit)

Corrections:
- Relevance (Wan et al.) = text that directly answers the question in its own words. On-topic text that doesn't answer it doesn't help. Win rate = which of two in-context docs the model sides with, so it measures being chosen, not discovery.
- Assertiveness ("most reliable", "actively maintained") helped only for picking between tools (Faghih). In Wan, rewriting for confidence was neutral to negative. Don't group it with relevance.
- References and data underneath didn't move models in either study. Evidence isn't shown to be what wins.
- Nico's doc never says how evidence reaches the agent (search, training, codebase), and says evidence gets "a new route," not that it wins.

Coding-agent sources (summaries only, check before citing numbers):
- Twist et al. 2025, https://arxiv.org/abs/2503.17181: coding models default to established libraries (NumPy unnecessarily in up to 48% of cases). Incumbent bias from training.
- CodeUpdateArena + ReCode, https://arxiv.org/abs/2506.20495: models ignore updated API docs even when they're in the prompt.
- Faghih et al. 2025, https://arxiv.org/abs/2505.18135: description-only edits shift tool choice up to ~10x between identical tools.
- Allouah et al. 2025, https://arxiv.org/abs/2508.02630: shopping agents. Query-matched description tweaks won market share.

Discovery (survey): no technique proven to improve it. SAGEO: body-only rewrites cut retrieval about 9%. 53% of AI Overview–cited domains weren't in Google's organic top 10.

Coga discoverability test (Nov 15): two Claude searches, one using near-README wording, never surfaced Coga. Repo is public and on PyPI (0.4.1) but has no GitHub topics and no outside mentions. Both sessions had Coga memory, so rerun clean.
