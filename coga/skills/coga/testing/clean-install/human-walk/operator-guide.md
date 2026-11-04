# Testing the coga install: a guide for the tester

<!-- Plain-language guide for the human in an attended install walk. The
helper record and fix loop are in SKILL.md beside this file; VM setup is
owned by coga/testing/fresh-vm. Keep this file free of names and dates. -->

## What this is and why

We want to know what it feels like to install coga for the very first time.
You play the new user. Install it on a clean computer, following only the
public instructions, and write down everything you notice:

- **Does it work?** Did each step do what it said it would?
- **Lag.** Anything that takes a while, especially with nothing on screen to
  say it's working. A long wait with no feedback is exactly what we're after.
- **Weird stuff.** Confusing messages, words you don't know, popups or
  security warnings you didn't expect, steps where you had to guess, things
  that look broken or unprofessional even if they work.

There are no wrong answers. If something confused you, it will confuse other
people too, and that's a finding. You aren't being tested; the installer is.

Your ticket says which computer (Mac, Windows, or both), which install to
test, and how far to go. Follow its order if it specifies one.

If you test with both a VM and a new user account, do the VM walk first and
do it cold. Whichever walk you do first is the only one that captures your
genuine first reaction. After that you know the answers, and the confusion we
are looking for is gone.

## What you need

- The Mac or Windows PC your ticket names.
- About 2–3 hours per computer the first time (most of it is downloads).
- Your normal account with the helper agent open in the coga folder. This is your
  helper: when you're stuck, or want to report something, tell it there.
  Keep this separate from the clean computer.
- A notes file or a sheet of paper.

## Part 1: Prepare the test computer

Follow the [shared fresh-VM guide](../../fresh-vm/SKILL.md) with your helper.
It has the Mac and Windows setup steps, the commands that record the starting
state, and the procedure for returning a used VM to a clean starting point.
It also explains when a new user account is suitable for a repeat check.
Finish that preparation before beginning the install walk below.

## Part 2: Install coga like a new user

On the clean computer, open a web browser and go to
**https://github.com/FastJVM/coga**. From here on, **only follow what the
page tells you.** Don't use what you already know about coga. If the page
doesn't say how to do something, that's a finding: write it down, then ask
your helper.

Follow the README and the user guides it links, using the install source
and stopping point your ticket names. A release check may require you to
finish a real first task and inspect its result; creating a ticket alone
does not meet that requirement. Record any help you needed to reach the next
step, including a hint from your helper.

If your helper told you a step is already known to fail on your computer,
write down everything up to that point, paste the error to your helper, and
stop there.

### For every step, write down

```
Step:        (number and what you were doing)
Command:     (what you typed or clicked)
Waiting:     (anything slow, especially with nothing on screen saying it's working)
What I saw:  (copy the message, or take a screenshot)
What I expected:
Weird / confusing / slow?:
Did I need help?: (yes/no; what you asked)
```

Screenshots are great: Cmd+Shift+4 on Mac, Win+Shift+S on Windows.

## Part 3: When something goes wrong

1. Don't try to fix it yourself with tricks you know. A real new user
   wouldn't know them either.
2. Copy the full error text (or screenshot it) and paste it to your helper
   (on your normal account) with one line about what you were doing.
3. The helper records it as a finding and either tells you how to get past
   it or fixes coga. If it fixes coga, you may be asked to redo that step on
   a fresh copy (the clone on Mac, the snapshot on Windows).

## Part 4: When you're done

Tell your helper "Mac walk done" (or Windows) and give it your notes. Then
answer three quick questions:

1. What was the single most annoying moment?
2. Was there a point where you'd have given up if this weren't your job?
3. Roughly how long did it feel, start to finish?

Then follow the shared guide's [teardown](../../fresh-vm/SKILL.md#teardown)
with your helper.
