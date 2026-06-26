<!-- Exported from the Google Doc "Conductor Report" (Coga Competition Tests), 2026-06-06.
     Source: https://docs.google.com/document/d/1cij60SgQAqeKxNt8QOFJ9R_sChlPS0OayMaOel7wZV4 -->

# **Conductor Report**

This report reflects on my experience building a project with Conductor. It covers three questions: how long the project took, where the service was genuinely strong, and where it fell short. The short version is that Conductor was fast — two hours end to end — and made the git side of the work nearly invisible, but the lack of robust workflows pushed too much of the testing to the back end of the project.

## **1\. How long did the project take?**

The project took two hours to complete, end to end. Notably, Conductor worked its way through the Playwright selector problems twice as fast as Dust did — the exact part of the work that turned into a trial-and-error grind on that service moved at double the pace here.

## **2\. Strengths of the service**

Conductor's strengths cluster around git ergonomics: branches, PRs, worktrees, and testing all live in one place, and the service keeps track of their state so I didn't have to. The standout strengths:

* **PR creation directly in the UI.** Amazing for someone who isn't very proficient with GitHub — opening a PR never required leaving the tool.  
* **Full access to Opus.** Conductor offered full accessibility to Opus, where Dust only offered Sonnet.  
* **Merge awareness.** It was very good at recognizing that something had been merged so it could create and move me to a new branch. At one point I wasn't sure whether a PR had been merged — whether I could start on a new task — and I was able to check right there in the UI. It recognized the state, let me merge, and moved me to a new branch and task.  
* **Automatic branches and worktrees.** Every new task auto-created a new branch and git worktree, which made keeping branches and PRs organized very easy.  
* **A built-in terminal.** Having a terminal directly in the UI made testing seamless. Conductor could give me something to run, the terminal auto-connected to the current branch, and I was able to quickly test from there.  
* **The UI:** The layout of the Conductor UI gave you everything you needed in a single window. Claude conversation to drive the coding and changes, built-in terminal to run tests when you needed, and then the gh additions/ deletions/ merge functions. This was the best UI in the sense that you never had to leave it. 

## **3\. Weaknesses of the service**

There aren't many complaints with this service, and the ones that exist share a single root: the absence of robust workflows. The main friction points:

* **The end state wasn't the real end state.** When the process was supposed to be fully live, further testing was still required — the project “finished” before it was actually done.  
* **Lack of robust workflows.** The missing workflows pushed a lot of the testing to the back end of the project — when it should have been ready to run live — and made the Playwright selector process tedious, as it has been on every service without workflow support.  
* **Less granular than Dust.** Conductor didn't break the work down as finely as Dust did, and I think that's a big part of why so much testing was pushed to the back end.

## **Closing thought**

Conductor nails the part of the work that Dust made painful: the mechanics of branches, worktrees, PRs, and testing are nearly invisible, and the project finished in two hours instead of Dust's three. The remaining gap is the same one that keeps appearing across these services — without robust, granular workflows, testing piles up at the end of the project instead of happening along the way. Pairing Conductor's git ergonomics with Dust-grade task granularity would close that gap.
