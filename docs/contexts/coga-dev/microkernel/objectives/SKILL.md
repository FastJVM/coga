---
name: coga-dev/microkernel/objectives
description: The goals of Coga's ticket-centred microkernel — editable behavior, a small generic command surface, and a simpler program contributors can understand.
---

# Microkernel objectives

Owner clarification, 2026-11-12. Coga should be organized around a small
kernel that executes tickets. Tickets carry scripts or agent prompts, together
with the workflows and skills they use. Put as much behavior as possible in
that common model so users can reshape Coga and more contributors can read it.

This topic owns the architectural objectives. The
[microkernel boundary](../SKILL.md) owns the current placement rules and
contracts; the [microkernel group](../../../../../coga/tasks/v1/microkernel/README.md)
tracks the proposed work and its review. The objectives guide that review;
they do not choose the final command inventory or migration order.

## Hackable and accessible

A user, directly or with an agent, should be able to find the files that own
a shipped behavior, obtain an editable copy in their repository, and change
the behavior there. Surrounding execution machinery should keep working when
the user changes the procedure, workflow, or instructions.

One command should make the effective source and the path to customization
discoverable. Follow the whole path from the command or alias to its ticket,
workflow, skills, and implementation as needed. The user should be able to
tell which file Coga actually uses and where their change belongs.

Wheel distribution is part of this objective. A definition available only
inside an installation directory that the user cannot conveniently edit is
insufficient. Customization needs a usable route to repo-owned files without
editing the installed package. For a script that imports its implementation
from the wheel, that route must reach the implementation itself: copying the
import wrapper alone does not expose the behavior. Make the effect of a local
customization on future package updates understandable.

The desired freedom covers shipped procedures broadly. Existing placement
inside the package is not a reason to exclude a behavior from review.

## As much behavior as possible in tickets

Tickets are the common home for behavior. Deterministic work belongs in
scripts; agent work belongs in prompts and the instructions they compose.
Workflows express how that work proceeds. Keep the procedure and its
implementation close enough that someone reading the ticket can follow it.

The kernel supplies the generic machinery necessary to execute and manage
those tickets. Keep its command surface small. Aliases expose familiar names
and extensions by directing them to tickets, so adding or changing a procedure
usually means changing repository files.

Evaluate existing commands, registered recipes, and special cases against
that target. Retaining something in core needs a concrete reason tied to the
shared execution machinery or an invariant it must preserve. Its current
registration is an inventory fact, not the architectural objective. The
design review decides the retained primitives and their interfaces.

Moving deterministic behavior into a ticket keeps it deterministic. The ticket
model must carry the existing completion and failure guarantees while making
the behavior accessible to its user.

## A simpler program people can read

Aim for a structure a contributor can explain and follow: a few generic
mechanisms, tickets that own their behavior, and a short path from a command
to the code or prompt that implements it. Elegance means fewer concepts and
special cases to understand, with clear responsibilities.

Reduce duplicated mechanics, redundant wrappers, obsolete paths, and
command-specific branches as the architecture changes. Reuse shared primitives
when there are real callers to simplify. A new abstraction earns its place by
replacing existing complexity.

Count the whole system: kernel, edge modules, and ticket or skill scripts.
Moving code into another directory can improve ownership, but does not by
itself reduce the amount or complexity of code maintained. There is no
arbitrary line-count quota; preserve useful behavior, deterministic execution,
visible failures, and meaningful verification.

## First acceptance case

Starting from a fresh installed repo, a user should be able to discover and
customize peer review to use a single agent without maintainer help. They
should find the relevant workflow and instructions, obtain editable local
files, and run their customized procedure with the expected checkout behavior.
Hidden package rules must not invalidate that customization merely because
the user changed the workflow or its instructions.

This case comes from a contributor getting lost while changing peer review.
It exercises discoverability, editable distribution, and the separation
between a procedure and the machinery that executes it.

## Evaluating a proposed change

Each design names the objectives it advances, the behavior the user will be
able to change, and the concrete simplifications it proposes. Work that
advances none of these objectives waits.

For implementation, report before/after evidence at named revisions: production
code across core, edge, and ticket or skill scripts in scope, and the
entrypoints, dependency paths, or duplicate implementations removed. State
the counting method; report tests, documentation, and packaged copies
separately. Distinguish relocation from deletion or deduplication.

A justified extraction can be size-neutral if it makes the ownership or
dependency boundary clearer. Record that gain and assign any deferred
simplification to a named follow-up. Classification work supplies the proposed
boundary and baseline for its implementation rather than claiming a reduction
that has not happened.
