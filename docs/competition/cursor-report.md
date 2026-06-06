<!-- Exported from the Google Doc "Cursor Report" (Relay Competition Tests), 2026-06-06.
     Source: https://docs.google.com/document/d/1BHT1URqFrCjbFXBtsi3XQl-zCTsexrTNIqqcOrR2dOI -->

# **Cursor Report**

This report reflects on my experience building a project with Cursor. It covers three questions: how long the project took, where the service was genuinely strong, and where it fell short. The short version is that Cursor’s GitHub integration and task planning were the best parts of the experience, but the confusing built-in terminal and the lack of an upfront workflow pushed testing to the very end of the project — and after 2.5 hours the project was left unfinished, with the email never sent.

## **1\. How long did the project take?**

The project took 2.5 hours, and it still didn’t finish. The live run of actually sending the email turned into more rounds of testing to find the send button, and that’s where the project was left — unfinished, with the email never sent. For comparison, Conductor completed the same project in two hours.

## **2\. Strengths of the service**

Cursor’s strengths cluster around GitHub integration and planning — it keeps you oriented in the repo and breaks the work down before it starts. The standout strengths:

* **Direct GitHub connection.** Cursor connects straight to GitHub and gives easy visibility into which branch you’re on.  
* **The agent drop-down.** You can select from a drop-down of agents, with frontier models all available on the pro plan.  
* **Task list generation.** Describe the project and Cursor builds out the task list for you.  
* **Automatic branch management.** It auto-creates and switches branches as it moves through the tasks, separating commits into reasonable blocks.  
* **Default model selection.** You can set a default model that carries out the work across all projects.  
* **Clickable work boxes.** The agent conversation creates clickable boxes that let you click into the work it did — I could see that Playwright got downloaded, and which version.

## **3\. Weaknesses of the service**

The weaknesses share a single root: it was never clear where work could actually run, and no workflow kept testing from piling up at the end. The main friction points:

* **The built-in terminal was confusing.** I didn’t know what I could run there and what I couldn’t. In Conductor I could run tests directly in the built-in terminal, but Cursor wouldn’t let me run the auth login to save my Gmail login — I had to run it in my computer’s terminal.  
* **Backend testing hit the same wall.** Running the backend tests needed to fix the Playwright selectors had the same problem.  
* **No workflow up front.** The lack of an upfront workflow pushes fixing the selectors to the moment you think you’re ready to test the project — exactly when you expect to be done.  
* **“Done” wasn’t done.** The project was said to be done, but the live run of actually sending the email required more rounds of testing just to find the send button. That’s where the 2.5 hours ran out — the email never sent.

## **Closing thought**

Cursor gets the front of the project right: GitHub connection, task planning, and branch management are the strongest of any service so far, and watching the work through clickable boxes builds real trust. But the same gap that keeps appearing across these services — no robust workflow pulling testing forward — cost the most here: the project ended unfinished at 2.5 hours, where Conductor finished in two. Pairing Cursor’s GitHub ergonomics with a workflow that surfaces selector testing early would have changed the outcome.
