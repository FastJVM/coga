---
title: Put into words why I would keep using Coga
status: in_progress
owner: zach
workflow:
  name: draft-for-human
  steps:
  - name: agent-produces
    skills: []
    assignee: agent
  - name: human-owns-and-finishes
    skills: []
    assignee: owner
  - name: report-to-coga
    skills: []
    assignee: agent
step: 1 (agent-produces)
agent: claude
launch_generation: pending:d12e45de-3781-463d-9b86-f8f37618b4c2
---

## Description

Put into words why I would keep using Coga to organize my work even outside the company, grounded in four real projects (passwords, patents, trademarks, accounting). Raw notes and first drafts below.

Goal: a half-page (or a few alternatives) that names the core product benefits
in a way that rings true to how the product actually stands, not just to the
conversations with my boss. Raw notes are kept verbatim below; first drafts and
the distilled benefit list are on the blackboard.

### Raw notes: four projects where Coga's substrate helped

1. **The password project.** Individual ticket creation here was extremely
   important for this project. There were a lot of places that I needed to stop
   for someone else to do their work. I think without Coga, I would have been
   less able to "save my place" on a project that spanned over a month. When I
   came across a block, either in my own work or waiting for someone else, I was
   able to create a ticket in that moment with a description of what was needed
   before moving on to the next step.

2. **The patents project.** I knew nothing about patents before starting work on
   this project. I remember when first starting on managing the patent
   inventory, I was very overwhelmed. I look at myself now and it was like I got
   comfortable and knowledgeable about the process without realizing it was
   happening (through working with Coga). Using a ticket to go back and forth
   with the AI to create an overall definition of how I thought the repo should
   work. I think Coga has a way of beckoning you to either a. finish tickets or
   b. remove them from the coga status board. The coga status board calls to be
   cleared more so (for me) than Linear ever did. I think it was this reason why
   we were able to discover (and use) the Patent Center API for our recurring
   work. It was a leftover piece of work from Nico's time in the repo that, when
   I started exploring it, we found (along with Nico) was a better way to manage
   all of the patent deadlines.

3. **The trademark project.** The TM project was an extension of the patent
   work. The granularity offered by the Coga ticket process offered different
   benefits: (1) I knew from my work with the patents that they should be
   tracked individually. (2) I was able to re-use my learning from working with
   the patents to structure the tracking of the TMs as well. (3) Since a
   previous Coga ticket/subdirectory surfaced an API that made tracking patents
   easier, that same method of exploration was applied to the TMs as well. I
   found the TSDR API, which tracks upcoming office actions and status changes
   on our open TMs. I think Coga tickets offer a necessary bridge between the
   human and the AI. You're able to focus your work on a direct task and use
   conversations with the AI to learn as you go and "save your spot" to use as a
   jumping-off point for the next unit of learning.

4. **The accounting project.** No accounting knowledge at all when I started
   this project. I believe Coga stands as the bridge between exploration and
   automation. Reconciling Xero charges: I needed to both use conversations
   with the AI to learn what was needed here AND apply that learning to a
   recurring automation so that it becomes a standard monthly task. I needed to
   go through adding missing memos and seeing charges that were without their
   receipts to finally turn those into a monthly recurring task. The early
   stages of these recurring tasks were rife with the unknown. Working through
   tickets/tasks allowed me to deconstruct what presented as a very
   big/overwhelming project into small, manageable pieces. "Saving my spot"
   allowed me both a pause to commit learnings to the repo and a jumping-off
   point to start the next task.

Meta-observation: creating this ticket to save and work from these ideas is
itself an instance of the benefit being described.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Production notes

### 2026-10-13: distilled benefits (first pass)

1. **Save your place at the moment of interruption.** A block, whether yours or someone else's, becomes a ticket written right then, saying what's needed. Long, stop-start projects stay resumable. *(passwords, accounting)*
2. **Learning builds up in the repo instead of staying in your head or a chat.** Each ticket is a scoped conversation with the AI that ends with what was learned committed back. You get competent without noticing. *(patents, accounting)*
3. **A finite board you own asks to be cleared.** Every item is either finished or deliberately removed. Dealing with leftovers turns up hidden value. *(the Patent Center API in Nico's leftover work)*
4. **Structure transfers between projects.** The granularity and the habit of exploring that one project taught you become the template for the next. *(patents → trademarks → TSDR)*
5. **Exploration turns into automation in the same place.** The tickets that held the uncertain early learning become a recurring job. *(Xero reconciliation → monthly task)*
6. **A ticket is the right-sized unit for working with AI.** It's narrow enough to keep a conversation focused and lasting enough to pick back up.
7. **It's portable and it's mine.** Plain markdown in git, readable and local. This is the root of "I'd use it even if I left."

### Draft A: three things it changes (principle-led)

Coga gives my work a place to stand. Every unit of work is a ticket: a small markdown file describing what's needed, kept in a repo I control. That sounds modest, but it changes three things.

First, I can stop anywhere. The password project ran over a month and kept pausing on other people's work. Every time I hit a block, I wrote a ticket on the spot describing exactly what was needed, then moved to the next step. None of it depended on my memory.

Second, what I learn stays learned. I started the patent, trademark, and accounting work knowing nothing about any of them. Each ticket was a scoped conversation with the AI, and each one ended with what I'd worked out committed to the repo. The next ticket started from there. I became fluent without ever setting out to study.

Third, the board wants to be empty. `coga status` is a finite list that's mine, and every item gets either finished or deliberately removed. Clearing it is how I found the Patent Center API sitting in leftover work. That API now tracks our patent deadlines, and it was the model for tracking trademarks through TSDR.

That's why I'd keep using it anywhere. It breaks big, unfamiliar projects into small steps I can resume, and it keeps what I learn.

### Draft B: from not knowing to running on its own (arc-led)

Every project I've done in Coga has followed the same path: I start out not understanding it, I come to understand it, and then it runs on its own.

Accounting shows it most clearly. I had no accounting background when I took on reconciling Xero charges, and as one big project it was overwhelming. So I broke it into tickets: charges missing memos, charges missing receipts, what "reconciled" actually means for us. Each ticket was a conversation with the AI where I learned one piece, and each ended with that piece written into the repo. Once the pieces were understood, they became a recurring monthly task.

Patents and trademarks went the same way. Patents taught me that each filing deserves its own ticket and that exploring leftover work pays off; that's how we found the Patent Center API. When trademarks came along, I didn't start from zero. I reused the structure and the habit of exploring, and found TSDR.

Most tools only cover the last stage, tracking tasks once you already know what they are. Coga covers the whole path. And because everything is files in git, what I learn builds up instead of disappearing into chat history. That's what I'd take with me.

### Draft C: why I'd use it even if I left (personal)

If I left tomorrow, I'd still organize my work in Coga. That isn't loyalty. It's because of what the tool does for me.

It lets me put work down. Long projects stall on other people. In Coga, the moment I'm blocked I write a ticket saying what's needed and move on. When the block clears, my place is saved.

It makes me finish things. Linear let tickets pile up. The Coga status board feels like something I own and should clear: finish it or remove it. That pressure is why I opened up old leftover work in the patents repo and found the API that now handles our deadlines.

It turns conversations into knowledge. I'd never worked with patents, trademarks, or accounting. Each ticket was a focused back-and-forth with the AI, and the result went into the repo. I got competent without noticing, and each project made the next one easier.

It turns knowledge into routine. Once the Xero reconciliation was understood, it became a monthly recurring task in the same system where I'd learned it.

And it's plain markdown in git: mine, readable, and not dependent on any company to keep working.

### 2026-10-13: Draft D (picked C's style; exploration-first, facts only)

Owner feedback on C: keep the style and message, put more weight on the early
exploration step and on how exploration inside Coga produces lasting knowledge
that feeds other tasks, drop the rhetoric, and use only facts from the notes.

I would keep using Coga to organize my work even outside this company. Most of the reason is how it handles the early, exploratory stage of a project, when I don't yet understand the work.

I started the patent, trademark, and accounting projects with no background in any of them. Each time, I explored inside a ticket: a focused back-and-forth with the AI about one piece of the problem, ending with what I'd learned committed to the repo. For patents, the first ticket worked out how I thought the repo should work. Over time I got comfortable with the process without noticing it happening.

What I learned while exploring didn't stay inside the ticket it came from. While exploring leftover work from Nico's time in the patents repo, Nico and I found the Patent Center API. It was a better way to manage patent deadlines, and it now drives our recurring patent work. When the trademark project started, I already knew trademarks should be tracked individually, I reused the patent structure, and I explored the same way, which led me to the TSDR API for upcoming office actions and status changes. Accounting went the same way: working through Xero charges with missing memos and missing receipts became a monthly recurring task.

Two other things support this. When I hit a block, mine or someone else's, I can create a ticket right then describing what's needed and move on; that's how I kept my place on the month-long password project. And the status board pushes me to either finish tickets or remove them, more than Linear did, which is why the leftover patent work got explored at all.

Coga is plain markdown in git, so all of this stays readable and stays with me.

### 2026-10-13: Draft E (Draft D + small steps lead to lasting change)

Owner addition: Coga's structure resembles the most effective way to learn.
Trying to change too much at once doesn't last; consistent small steps toward
a goal are much more likely to produce lasting change, and Coga naturally
supports taking those small steps.

I would keep using Coga to organize my work even outside this company. Most of the reason is how it handles the early, exploratory stage of a project, when I don't yet understand the work.

I started the patent, trademark, and accounting projects with no background in any of them. Each time, I explored inside a ticket: a focused back-and-forth with the AI about one piece of the problem, ending with what I'd learned committed to the repo. For patents, the first ticket worked out how I thought the repo should work. Over time I got comfortable with the process without noticing it happening.

What I learned while exploring didn't stay inside the ticket it came from. While exploring leftover work from Nico's time in the patents repo, Nico and I found the Patent Center API. It was a better way to manage patent deadlines, and it now drives our recurring patent work. When the trademark project started, I already knew trademarks should be tracked individually, I reused the patent structure, and I explored the same way, which led me to the TSDR API for upcoming office actions and status changes. Accounting went the same way: working through Xero charges with missing memos and missing receipts became a monthly recurring task. Coga is the bridge between exploration and automation: work starts as first-time learning inside a ticket and ends as a recurring task.

I think this works because Coga's structure matches how learning tends to stick. Trying to change too much at once usually doesn't last. Taking small steps toward a goal, consistently, is much more likely to produce a change that lasts. Coga makes the small step the default: a ticket covers one piece of work, it ends with what I learned saved in the repo, and the next ticket starts from there. The accounting project felt overwhelming as a whole, but as a series of tickets it was manageable, and the result was a lasting monthly routine instead of a one-time cleanup. It's also why I picked up patents without noticing: there was no single big leap, just a series of small steps that added up.

Two other things support this. When I hit a block, mine or someone else's, I can create a ticket right then describing what's needed and move on; that's how I kept my place on the month-long password project. And the status board pushes me to either finish tickets or remove them, more than Linear did, which is why the leftover patent work got explored at all.

Coga is plain markdown in git, so all of this stays readable and stays with me.

### 2026-10-13: Final (owner's chosen text)

The owner finished from Draft E: they cut the patents-first-ticket line, the trademark "tracked individually" clause, the standalone accounting sentence, "instead of a one-time cleanup", and the closing markdown-in-git line, and moved the bridge sentence to the end of the small-steps paragraph.

What makes Coga Unique to me

I would keep using Coga to organize my work even outside this company. Most of the reason is how it handles the early, exploratory stage of a project, when I don't yet understand the work.

I started the patent, trademark, and accounting projects with no background in any of them. Each time, I explored inside a ticket: a focused back-and-forth with the AI about one piece of the problem, ending with what I'd learned committed to the repo. Over time I got comfortable with the process without noticing it happening.

What I learned while exploring didn't stay inside the ticket it came from. While exploring leftover work from Nico's time in the patents repo, Nico and I found the Patent Center API. It was a better way to manage patent deadlines, and it now drives our recurring patent work. When the trademark project started, I reused the patent structure, and I explored the same way, which led me to the TSDR API for upcoming office actions and status changes.

I think this works because Coga's structure matches how learning tends to stick. Trying to change too much at once usually doesn't last. Taking small steps toward a goal, consistently, is much more likely to produce a change that lasts. Coga makes the small step the default: a ticket covers one piece of work, it ends with what I learned saved in the repo, and the next ticket starts from there. The accounting project felt overwhelming as a whole, but as a series of tickets it was manageable, and the result was a lasting monthly routine. It's also why I picked up patents without noticing: there was no single big leap, just a series of small steps that added up. Coga is the bridge between exploration and automation: work starts as first-time learning inside a ticket and ends as a recurring task.

Two other things support this. When I hit a block, mine or someone else's, I can create a ticket right then describing what's needed and move on; that's how I kept my place on the month-long password project. And the status board pushes me to either finish tickets or remove them, more than Linear did, which is why the leftover patent work got explored at all.

### Open threads for the human step

- ~~Pick a spine~~: owner picked C's style; Final text recorded above; Drafts A to E are history.
- Check each claim against the product as it stands, for example whether the Xero task is a real `coga/recurring/` job and whether to name the `coga block` command for the password story.
- Drafts A to C added a detail that isn't in the notes ("what 'reconciled' actually means for us"); Draft D leaves it out.
- Decide whether naming Nico and Linear is right for the audience.
