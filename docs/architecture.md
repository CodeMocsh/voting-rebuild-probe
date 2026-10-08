# Architecture

## Context

| System | Perimeter | Role | Technology |
|---|---|---|---|
| Voting app | internal | Vote intake, vote queue, vote recording and live results on a managed container platform | Managed Kubernetes |
| Results watcher | actor | Watches the live tally | not set |
| Voter | actor | Casts a vote | not set |
| Old estate | external | Current voting app, kept untouched as rollback until decommission | Docker Compose |
| Platform secret store | external | Holds database credentials injected into pods | not set |

### Outcome

vote, worker and result run on managed Kubernetes with managed Postgres 15 and managed Redis, with no redesign of the app and no accepted vote lost across the move.

### Constraints

Vote integrity is the stake; availability is not, so short outages are tolerated and no standby or second environment is built. The results page is not redesigned.

## Approach

### Freeze, copy, switch DNS

A short write freeze drains Redis, copies the database and reconciles counts, then DNS flips once. Before the first vote on the new estate, rollback is repointing DNS to the untouched old estate.

Because No accepted vote may be lost across the move.

### Reliable queue handoff

The worker moves each vote to a processing list, deletes it after the database commit and requeues on failure, with Redis persistence on.

Because Vote integrity is the stake: a lost accepted vote is not tolerable.

### Replatform onto managed Kubernetes

vote, worker and result keep their code and run on managed Kubernetes reusing k8s-specifications with the db and redis Deployments removed. Postgres 15 and Redis become managed services.

Because The goal is to run on a managed container platform without redesigning the app.

### Keep the three services as they are

No new domain split: the existing vote, worker and result boundaries stay, results page unchanged, and code layout stays with infra/ added.

Because The plan replatforms and the results page is out of scope.

## Platform

### Regions and residency

One region, chosen nearest the voters, holds the cluster, Postgres and Redis. No second region.

| Setting | Value | Applies to |
|---|---|---|
| Region | not set | every environment |

### Encryption and secrets

The managed database sets its password; the platform secret store holds the credentials and injects them into pods as environment variables. Today worker/Program.cs hardcodes Username=postgres;Password=postgres, which is removed.

| Setting | Value | Applies to |
|---|---|---|
| Credential delivery | Platform secret store, injected as environment variables | worker, result |

- **Rule.** Database credentials must never appear in source or images. Nothing enforces it. Holds for worker, result.

### Platform automation

The existing GitHub Actions image builds (.github/workflows/call-docker-build-*.yaml) stay. A deploy job applies manifests by immutable image digest, and infrastructure as code defines the managed services in infra/.

| Setting | Value | Applies to |
|---|---|---|
| Image reference | Immutable image digest | every environment |

- **Rule.** The deploy job must apply manifests only by immutable image digest. Enforced by Deploy job in GitHub Actions. Holds for the whole platform.

## Workload

### Parts

#### Votes database

Durable store of votes

- Shape: store
- Technology: Managed PostgreSQL 15

Does:

- Hold one vote per voter
- Provide automated backups and point-in-time restore

Owns:

- votes table

Keeps:

- Vote
- Option

Replaces:

- db

#### Vote queue

Pending votes list

- Shape: queue
- Technology: Managed Redis, persistence on

Does:

- Hold the votes list and processing list with persistence on

Owns:

- pending votes list
- processing list

Replaces:

- redis

#### result `dockersamples-example-voting-app/result/`

Shows live tally

- Shape: app
- Technology: Node.js, socket.io

Does:

- Poll vote counts from Postgres and push scores to browsers, results page unchanged

Calls:

- Votes database: Read counts (batch · PostgreSQL), carrying Vote counts by choice

Replaces:

- result

#### vote `codemocsh-voting-rebuild-probe/vote/`

Serves the ballot and queues each submitted vote

- Shape: app
- Technology: Python Flask, gunicorn

Does:

- Serve the voting page with the current look
- Push each vote (voter id, choice) onto the Redis votes list and acknowledge only after the push

Calls:

- Vote queue: Push vote (async · Redis over TLS), carrying Voter id and choice

Replaces:

- vote

#### worker `dockersamples-example-voting-app/worker/`

Moves queued votes into Postgres reliably

- Shape: job
- Technology: .NET worker

Does:

- LMOVE each vote to a processing list
- Delete it from the processing list only after the database commit
- Requeue on failure

Calls:

- Votes database: Upsert vote (sync · PostgreSQL), carrying One vote per voter
- Vote queue: Move and acknowledge votes (async · Redis over TLS), carrying Pending votes

Replaces:

- worker

### Switched off

- seed

### What callers reach today

#### db

Replaced by Votes database.

| Address | Form | Protocol |
|---|---|---|
| `healthchecks/postgres.sh` | command |  |

#### redis

Replaced by Vote queue.

| Address | Form | Protocol |
|---|---|---|
| `/healthchecks/redis.sh` | command |  |

#### result

Replaced by result.

| Address | Form | Protocol |
|---|---|---|
| `GET /` | route | http |
| `socket.io:scores` | event | socket.io |

#### seed

Switched off: nothing replaces it.

| Address | Form | Protocol |
|---|---|---|
| `compose:seed` | command | docker compose |

#### vote

Replaced by vote.

| Address | Form | Protocol |
|---|---|---|
| `/` | route | http |

### What reaches the estate

| From | To | Call | How | Carries |
|---|---|---|---|---|
| Platform secret store | worker | Inject credentials as env vars | sync · Platform injection | Database credentials |
| Voter | vote | Open ballot and cast vote | sync · HTTPS | Vote choice |
| Results watcher | result | Watch live tally | sync · HTTPS | Vote percentages |

### Runtime

#### A vote reaches the live tally

1. Voter → vote: Open vote page, ballot served
2. Voter → vote: Submit choice
3. vote → Vote queue: Queue the vote
4. worker → Vote queue: Take queued vote
5. worker → Votes database: Record vote durably
6. result → Votes database: Read vote counts
7. Results watcher → result: View live percentages

### Code organization

The vote, worker, result and k8s-specifications layout is kept. Platform definitions go in a new top-level infra/ directory.

### Compute and runtime

vote, worker and result run as Deployments on managed Kubernetes, reusing k8s-specifications/ with db-deployment, db-service, redis-deployment and redis-service removed.

### Data and storage

Votes live in a single-instance managed Postgres 15 with automated backups and point-in-time restore. The queue lives in managed Redis with persistence on. Old votes move by a short write freeze: intake stops, the old worker drains Redis to zero, pg_dump and restore run, and counts are reconciled before the switch.

| Setting | Value | Applies to |
|---|---|---|
| Postgres engine and topology | Managed PostgreSQL 15, single instance | production |
| Redis persistence | On | redis |

### Integration and state

Services read the redis and db endpoints from environment variables; today vote/app.py uses host "redis" and worker/Program.cs uses "redis" and "db" literally. The worker moves each vote with LMOVE from votes to a processing list, deletes it after the database commit, and requeues on failure; today it uses ListLeftPopAsync, which loses a vote if the worker dies after the pop.

| Setting | Value | Applies to |
|---|---|---|
| Endpoint configuration | Redis and database endpoints read from environment variables | vote, worker, result |
| Queue lists | votes (pending), processing (in flight) | redis |

- **Reliability.** When the worker is killed between taking a vote and committing it, the vote is requeued and recorded after restart. Measured as Accepted votes missing from the votes table after a vote-loss test Target: 0. Holds for worker, Vote queue.
- **Rule.** The worker must delete a vote from the processing list only after the database commit. Enforced by Vote-loss test run before each wave lands. Holds for worker.
- **Rule.** Services must read the redis and database endpoints from environment variables, never from literal hostnames. Nothing enforces it. Holds for vote, worker, result.
- **Rule.** The vote service must acknowledge a vote only after it is pushed to Redis. Nothing enforces it. Holds for vote.

### User experience

The vote page and the results page keep their current look.

## Transition

### The switch

1. Lower the DNS TTL on the voting name and wait for the old TTL to expire
2. Stop vote intake on the old estate to start the write freeze On Old estate.
3. Let the old worker drain the Redis votes list to zero On Old estate.
4. Dump the old database and restore it into managed Postgres On Data move job, Votes database.
5. Reconcile vote counts between old and new; stop if they differ On Data move job, Votes database.
6. Repoint the DNS name to the new vote and result services On vote, result.
7. Let the new estate accept its first vote; from here roll forward only On vote, Vote queue, worker. Past this step the move cannot be reversed.

### Putting it back

1. Repoint the DNS name back to the old estate On Old estate.
2. Reopen vote intake on the old estate, whose database and Redis were not changed On Old estate.
3. Empty the new database and redo the copy at the next attempt On Votes database.

### Transitional parts

#### Data move job

One-time copy of old votes

- Shape: job
- Technology: pg_dump and restore

Does:

- During the write freeze, dump the old database, restore into the new one and reconcile counts

Calls:

- Votes database: Restore votes (batch · PostgreSQL), carrying Vote rows
- Old estate: Dump old votes (batch · PostgreSQL), carrying Vote rows

### Cutover and rollback

Lower the DNS TTL, freeze writes, drain and copy, reconcile, then flip the DNS name once. Until the new estate accepts its first vote, the old estate is untouched and rollback is a DNS repoint. After that, only roll forward.

| Setting | Value | Applies to |
|---|---|---|
| DNS TTL before cutover | not set | voting DNS name |

- **Reliability.** When the cutover runs, the new database holds every vote the old one held. Measured as Difference in vote counts per choice between old and new after reconcile Target: 0. Holds for Data move job, Votes database.
- **Rule.** The old estate must stay untouched until the post-cutover reconciliation passes and a first backup of the new database exists. Nothing enforces it. Holds for Old estate.

## Operate

### Resilience and recovery

Postgres has automated backups and point-in-time restore, proven by one restore rehearsal into a scratch instance before cutover. Redis is not backed up; its persistence setting protects the queue across restarts.

| Setting | Value | Applies to |
|---|---|---|
| Postgres backups | Automated backups with point-in-time restore | postgres |

- **Reliability.** The restore rehearsal recovers the database into a scratch instance before cutover. Measured as Vote count in the restored instance against the source Target: Equal. Holds for Votes database.

### Operating model

The old estate is stopped once the post-cutover count reconciliation passes and a first backup of the new database exists. A final dump of the old database is kept in storage.

## What the charter sets

- Goal: Run the voting app on a managed container platform, losing no vote cast. (3 rows)
- Out of scope: Redesigning the results page. (4 rows)

## Decisions this design rests on

- How is an accepted vote kept safe between the vote service, Redis and the worker? (13 rows)
- How do existing votes get to the new database, and with what downtime? (12 rows)
- How do services find redis and db after the move? (9 rows)
- Where is the point of no return, and how is the move reversed before it? (7 rows)
- How does voter traffic move to the new estate? (7 rows)
- How is the code laid out after the move? (6 rows)
- Which managed container platform runs vote, worker and result? (6 rows)
- Which store holds the votes and the pending queue after the move? (5 rows)
- When does the old estate go off? (5 rows)
- What do the vote and results screens look like after the move? (5 rows)
- Where do the database credentials live? (5 rows)
- What is backed up, and how is a restore proven? (4 rows)
- What builds and ships the images and platform definitions? (3 rows)
- What is the default strategy for the voting app, and what earns an exception? (3 rows)
- What does the voting app carry, and what does an hour of it being unavailable cost? (3 rows)
- Which region does the estate run in? (2 rows)

## Risks and open questions

### Regions and residency

- Region: no value set

### Encryption and secrets

- Database credentials must never appear in source or images.: nothing enforces it

### Integration and state

- Services must read the redis and database endpoints from environment variables, never from literal hostnames.: nothing enforces it
- The vote service must acknowledge a vote only after it is pushed to Redis.: nothing enforces it

### Cutover and rollback

- DNS TTL before cutover: no value set
- The old estate must stay untouched until the post-cutover reconciliation passes and a first backup of the new database exists.: nothing enforces it

## Glossary

- **Option**: One of the two things voted between, shown on the ballot with a label (default Cats and Dogs).
- **Vote**: A voter's current choice between the two options; one per voter, a later choice replaces the earlier.
