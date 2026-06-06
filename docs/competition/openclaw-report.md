<!-- Exported from the Google Doc "OpenClaw Report" (Relay Competition Tests), 2026-06-06.
     Source: https://docs.google.com/document/d/1p3Ip1V7DP4rUa9uvXeV8etoRZKu5Zz45UlWq-Z8zZCA -->

# **OpenClaw Report**

This report reflects on my experience building the deliverability project with OpenClaw. It covers three questions: how long the project took, where the service was genuinely strong, and where it fell short. The short version is that OpenClaw keeps everything in one place — tools run directly in the conversation, and its agent-to-human handoff flow is the most natural part of the service — but when things went wrong it refused exactly that handoff, looping through wrong answers more than thirty times, and after two hours the project still wasn't finished.

## **1\. How long did the project take?**

The project took two hours of work with OpenClaw, and I still was unable to finish it. The time went in two phases: steady progress while the conversation-driven flow was working, and then a long stretch lost to the dns-checker loop described below, which ultimately stopped the project from completing.

## **2\. Strengths of the service**

OpenClaw's strengths cluster around keeping the entire loop inside the conversation: tools, retries, and human handoffs all happen in one window. The standout strengths:

* **Tools run directly in the conversation.** OpenClaw can run tools right in the chat, which meant I rarely had to leave its UI — no opening terminals to run commands.  
* **Smart auto-retries.** It runs auto-retries better than most other services: when it knew it hadn't found the correct selector yet, it kept trying on its own rather than stopping to report a failure.  
* **A natural agent-to-human-to-agent flow.** The service moves smoothly from automated agent work, to a handoff where the human runs a command directly in the running chat, and then back to the agent again. It's a genuinely good rhythm for collaborative work.

## **3\. Weaknesses of the service**

The weaknesses share a single root: OpenClaw insists on staying automated past the point where a human should be pulled in. The main failures:

* **Intimidating, unexplanatory setup.** The setup is intimidating and not very explanatory — I had to consult Claude about which options to choose during setup.  
* **Broken completion notifications.** It told me repeatedly that it would be notified when a task finished, but it wasn't. I had to keep prompting it to check whether, say, the Gmail login had been saved.  
* **The dns-checker loop.** After the state reset, the service completely failed to complete the dns-checker project. It got stuck in a continuous loop of selecting the wrong emails — a Google security email repeatedly, PlayStation invoices repeatedly — and I had to interfere to stop it after more than 30 cycles. Each time, it told me, authoritatively, that it had the answer to fix the incorrect selection, then started another never-ending loop of the same wrong selections.  
* **No human-in-the-loop instinct when it mattered.** OpenClaw tried to stay automated on a task that should have involved the human long before. The one moment its signature handoff flow was needed most, it never reached for it.

## **Closing thought**

OpenClaw's best idea is also its sharpest indictment. The agent-to-human-to-agent flow is the most natural handoff I've used — run a command in the chat, hand control back, keep moving — and yet when the dns-checker loop went wrong, the service never used it, grinding through thirty-plus wrong selections while insisting it had the fix. A service this good at handing control to a human should know when to do it.
