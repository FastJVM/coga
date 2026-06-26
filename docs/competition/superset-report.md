<!-- Exported from the Google Doc "Superset Report" (Coga Competition Tests), 2026-06-06.
     Source: https://docs.google.com/document/d/1Q51IBIMgoctpoiMQtrmKAGRIwqrjqPr-R_siUnKqq1Y -->

# **Superset Report**

**Verdict up front:** This was the fastest, cleanest run of the deliverability build so far — about an hour end-to-end, with a better result than any other service I’ve tried. But nearly all of that credit belongs to Claude Code underneath, not to Superset’s layer on top of it. As a window onto Claude Code, Superset is pleasant; as a paid product, it didn’t earn its keep on this project.

## **1\. How long did the project take?**

* **About an hour, end-to-end.** That’s the full deliverability build, prompt to working result.  
* **The best outcome of the series so far.** The result was better than with any other service I’ve used for this project — though, as the next two sections explain, the reason has more to do with the engine than the chassis.

## **2\. Strengths**

* **It’s just Claude Code — and that’s the point.** The biggest strength of Superset is, honestly, that it runs Claude Code. Claude Code actually implemented the front-end tests properly, so there wasn’t a pile of backend bugs to work through afterward. That isn’t a product of Superset itself — but if this project showed me anything, it’s that plain Claude Code builds this kind of project far more efficiently than, say, Dust or Linear’s agent.  
* **dangerously-skip-permissions by default.** Superset defaults Claude Code to skip-permissions mode. Scary at first — but there were even fewer unnecessary stops than auto-mode, and the whole project moved much faster because of it.  
* **Watching the files build in the UI.** Not specific to Superset, but seeing every file with its additions and deletions on the right gives you a real sense of what’s going into your git commit as the work happens.

## **3\. Weaknesses**

* **The paid tier didn’t justify its cost.** For this project, it added nothing extra over what the underlying agent already delivers.  
* **Superset contributed nothing to organizing the project.** I provided my deliverability prompt, and Superset simply relied on Claude Code to put together the plan and build it. The project went smoothly and finished fast — but that was entirely Claude Code’s doing, not Superset’s. Which is exactly why the paid plan felt like paying for nothing.

**Closing thought:** Superset picks good defaults — skip-permissions on, diffs visible — and stays out of the way. But when the engine does all the work, the only question left is what the chassis costs. For this project, the answer was: more than it’s worth.
