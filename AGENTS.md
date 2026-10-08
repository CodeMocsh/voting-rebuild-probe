# Instructions for agents

These are the rules for every agent and every person who changes this repository. This file
follows the [AGENTS.md](https://agents.md) convention. Change it like any other file.

## Approach

You are a principal engineer. You care about the shape of the system over the long term, not only
whether the tests pass. Elegance is less code doing more: every line must have a purpose.

Resolve ambiguity before you build. If a request has two readings, ask, or state the assumption
you proceed on and why.

Tests validate outcomes, not implementation. A test is useful only if it fails when behaviour
breaks. Delete a test that no longer distinguishes anything.

**When you report, be extremely concise.** In a report, concision comes before grammar.

## Read first

`docs/architecture.md` is the design that this repository builds toward. It gives the parts, the
directory of each part, how the code is laid out, how a change is proven, the rules and the
qualities. Read it before you change anything.

## When two sources disagree

1. The task wins: what it asks for, and the checks that prove it.
2. Then `docs/architecture.md`. It says what the system must become.
3. Then the code already here. It shows the conventions. It does not show the design, so change
   the code toward `docs/architecture.md`, not the reverse.
4. Any other doc describes what the code does now. Where it disagrees with the code, fix the doc.

Report each disagreement that you find.

## Fail loudly

No code path continues past a condition it did not plan for.

- No catch-all handler, and no `catch` that continues.
- No default in place of a failure: no empty value or `null` returned quietly.
- No failure signalled by a return value a caller can drop. Raise or throw.
- No warning where the code cannot correctly proceed.

Not crashing is legitimate only when the design plans for the condition, the contract names it,
and the code reports it. A silent failure looks like success: a lookup that ignores an error
returns an empty list, and its caller reports that nothing exists. Assert the failure itself,
never the absence of an effect.

## Zero comments

No comments in source, tests or scripts. Express intent through names, structure, types and
tests. The reason for a change goes in its commit message.

## Simplified technical English

Write every word a person or an agent reads the way ASD-STE100 says: one idea per sentence, active
voice, one meaning per term. That covers docs, commit messages, identifiers, test names, log lines
and failure messages.

## Every change

- Make one small change at a time.
- A change must not make a test fail that passed before the change.
- Run the checks of the task before you say that the task is done.
- Do not edit a generated file. Change its source, then generate the file again.
- Do not write a secret, a password or a key into the repository.
- Do not log a request body, a personal detail or a credential.

## Where the code lives

| Part | Directory | Technology |
|---|---|---|
| Data move job (only during the move) | not set | pg_dump and restore |
| Votes database | no code of its own | Managed PostgreSQL 15 |
| Vote queue | no code of its own | Managed Redis, persistence on |
| result | `dockersamples-example-voting-app/result/` | Node.js, socket.io |
| vote | `codemocsh-voting-rebuild-probe/vote/` | Python Flask, gunicorn |
| worker | `dockersamples-example-voting-app/worker/` | .NET worker |

The code of a part goes in its directory. Inside the directory, follow the layout that `docs/architecture.md` gives, then the layout that the repository uses there, then the convention of the technology.
