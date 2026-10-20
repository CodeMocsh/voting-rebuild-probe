# Architecture

## Context

| System | Perimeter | Role | Technology |
|---|---|---|---|
| Voting app | internal | Takes each voter's choice and shows the live tally, on a managed container platform | Managed Kubernetes |
| Voter | actor | Casts or changes a vote on the ballot page | not set |
| Results watcher | actor | Watches the live percentages on the results page | not set |
| Owning team | actor | Builds and runs the estate in working hours and answers its alerts | not set |
| Provider secret store | external | Holds the Postgres and Redis credentials the cluster injects into pods | Provider secret store |
| Provider logging and metrics | external | Keeps container logs, platform metrics and queue lengths, and raises the two alerts | Provider managed logging and metrics |
| DNS | external | Resolves the vote and result names; repointed once at cutover | not set |
| Today's voting app | external | The estate being moved; frozen, drained and copied at cutover, kept untouched as the rollback until the reconcile passes | Docker Compose, PostgreSQL 15, Redis |

### Outcome

The voting app runs on a managed Kubernetes cluster with managed PostgreSQL 15 and managed Redis, and no vote a voter was shown as taken is lost on the way. vote, worker and result keep their code and images; only the worker's queue handoff, TLS, the environment-driven connection settings and the ballot's https script URLs change. The move is known to have happened when both DNS names resolve to the new load balancer, the per-choice reconcile between old and new databases shows zero difference, and the 'votes' and 'processing' lists drain to zero in steady running.

### Constraints

Integrity is the stake and availability is not: the design carries durability of accepted votes (worker handoff, Redis persistence, Postgres point-in-time restore) and no standby, second zone, second region, second environment or out-of-hours response. The results page is not redesigned; its markup and stylesheet in dockersamples-example-voting-app/result/views/ ship as they are. No code change rides with the move beyond what the charter goal and the managed services force.

## Approach

### Replatform onto managed Kubernetes

vote, worker and result keep their languages, runtimes and looks and run on managed Kubernetes from manifests derived from k8s-specifications/ without the db and redis files. Only the worker's queue handoff, TLS and environment-driven connection settings change with the move; everything else waits.

Because The charter's goal is a managed container platform with no vote lost, and nothing else forces change.

### Managed data tier

The Postgres and Redis containers are replaced by managed PostgreSQL 15 and managed Redis with persistence, on private addresses with TLS and provider keys. The seed job is retired.

Because The provider operating the stores is what lets the building team run the estate in working hours.

### Reliable queue handoff

The worker moves each vote to a 'processing' list, removes it only after the Postgres write commits, and requeues on failure and at start, with one replica. Lengths of both lists are watched and alert when votes stop draining.

Because Integrity is the stake: an accepted vote must never be lost between queue and store.

### One wave, freeze and switch

Everything moves in one cutover: freeze intake, drain Redis to zero, dump and restore Postgres, reconcile counts per choice, then repoint both DNS names at once. Before the first vote the new estate accepts, rollback is repointing DNS to the untouched old estate.

Because Availability is not the stake, so a short freeze buys a copy whose counts can be proven equal.

### One region, one zone, no standby

The cluster and both stores run in one region nearest the voters, with no standby. Recovery is the provider replacing the instance and point-in-time restore of Postgres, rehearsed once before cutover.

Because Integrity, not availability, is what the estate is held to.

## Platform

### Regions and residency

One region, the one nearest the voters, holds the cluster, managed Postgres and managed Redis together, because the worker polls Redis every 100 ms (dockersamples-example-voting-app/worker/Program.cs:32) and result queries Postgres every second (result/server.js:52). The stores sit in one zone; the cluster's node pool runs in the same region. No data leaves that region except the final dump of the old database kept in storage in the same region.

| Setting | Value | Applies to |
|---|---|---|
| Region | not set | every environment |
| Regions in use | 1 | every environment |
| Zones for managed Postgres and Redis | 1 | db, queue |

### Resource hierarchy

One production environment holds everything the estate runs in the cloud: the managed Kubernetes cluster, the managed Postgres instance, the managed Redis instance, the secret store entries, the private network and the storage bucket holding the final old-database dump. Development and pre-merge tests stay on Docker Compose (dockersamples-example-voting-app/docker-compose.yml and result/docker-compose.test.yml) and take no cloud resources.

| Setting | Value | Applies to |
|---|---|---|
| Cloud environments | 1 (production) | every environment |
| Development and pre-merge environment | Docker Compose (docker-compose.yml, result/docker-compose.test.yml) | development |

- **production** (project): every cloud resource of the voting app
  - **voting cluster** (managed Kubernetes cluster): vote, worker and result Deployments
  - **votes database** (managed PostgreSQL instance): the votes table
  - **votes queue** (managed Redis instance): the 'votes' and 'processing' lists
  - **store credentials** (secret store): Postgres and Redis credentials
  - **old database dump** (storage bucket): the final dump of the old votes database

### Identity and access

Only the deploy job, run from the main branch, holds credentials that change production; people hold read access to the cluster and the provider console, and open sessions into the private network for database queries. Pods carry no provider credentials beyond what the secret sync injects. Postgres and Redis credentials are issued by the managed services and are not the 'postgres:postgres' pair written in worker/Program.cs:19 and result/server.js:21.

| Setting | Value | Applies to |
|---|---|---|
| Identity allowed to change production | deploy job on the main branch only | production |
| Operator path to the databases | session into the private network | db, queue |

### Network topology

One private network holds the cluster nodes and private endpoints for managed Postgres and managed Redis; neither store has a public endpoint. One public load balancer is the only public address and routes the vote name to vote and the result name to result, including result's socket.io WebSocket. There is no standing link to the old estate: the dump is taken on the old host and restored through an operator session into the private network. This mirrors docker-compose.yml, where redis, db and worker sit on back-tier only.

| Setting | Value | Applies to |
|---|---|---|
| Public endpoint on managed Postgres and Redis | off | db, queue |
| Public entry points | 1 load balancer serving the vote and result names | load-balancer |
| Private network address range | not set | production |
| Standing link to the old estate | none | production |

- **voting private network** (VPC): cluster nodes and the stores' private endpoints
  - **cluster subnet** (subnet): cluster nodes and pods
  - **Postgres private endpoint** (private endpoint): the only address of managed Postgres
  - **Redis private endpoint** (private endpoint): the only address of managed Redis
  - **public load balancer** (load balancer): the one public path in, for the vote and result names
  - **operator session** (bastion session): operator path into the private network for queries and the cutover restore

- **Rule.** Managed Postgres and managed Redis must never have a public endpoint. Enforced by public endpoint set off in infra/. Holds for Managed PostgreSQL, Managed Redis.
- **Rule.** The public load balancer must be the only public address in the estate. Nothing enforces it. Holds for Public load balancer.

### Encryption and secrets

Both stores encrypt at rest with provider-managed keys and accept only TLS connections. The provider secret store holds the Postgres and Redis credentials written by infra/; a secret sync exposes them to vote, worker and result as environment variables. Rotation is a manual operator step followed by a rollout restart of the consuming Deployments.

| Setting | Value | Applies to |
|---|---|---|
| Encryption at rest key | provider-managed | db, queue |
| TLS to the stores | required | db, queue |
| Credential store | provider secret store, synced into pods as environment variables | vote, worker, result |
| Credential rotation | manual, followed by a rollout restart | db, queue |

- **Rule.** Every connection to Postgres or Redis must use TLS. Enforced by TLS-only setting on both managed stores in infra/. Holds for Managed PostgreSQL, Managed Redis.
- **Rule.** Store credentials must never be written into source, manifests or images. Nothing enforces it. Holds for vote, worker, result.

### Policy and guardrails

Three controls refuse outright: the deploy job rejects a manifest naming an image by tag rather than digest; infra/ sets public endpoints off on managed Postgres and Redis; and managed Postgres has deletion protection on. Everything else is reported by the provider's default security findings. No admission controller runs in the cluster, so a hand-applied manifest is not stopped.

| Setting | Value | Applies to |
|---|---|---|
| Image reference in deployed manifests | digest only | vote, worker, result |
| Deletion protection on managed Postgres | on | db |
| Cluster admission controller | none | production |

- **Rule.** A deployed manifest must name every image by digest. Enforced by deploy job rejects a manifest with a tag reference. Holds for vote, worker, result.
- **Rule.** The managed Postgres instance must never be deleted. Enforced by deletion protection on in infra/. Holds for Managed PostgreSQL.

### Observability

The provider's managed logging keeps container stdout from vote, worker and result, and its metrics keep platform metrics for the cluster and both stores plus the lengths of the 'votes' and 'processing' Redis lists. Two alerts go to the owning team in working hours: queued votes not draining, and the worker crash-looping or a managed store unavailable. Retention is the provider default; there is no tracing and no self-hosted monitoring.

| Setting | Value | Applies to |
|---|---|---|
| Log destination | provider managed logging, from container stdout | vote, worker, result |
| Log retention | provider default | production |
| Application metrics | length of 'votes' and length of 'processing' | queue |
| Minutes a non-empty, non-shrinking list waits before alerting | not set | queue |
| Alert response hours | working hours, no out-of-hours paging | production |

- **Reliability.** The worker stops recording votes while the 'votes' or 'processing' list stays non-empty and is not shrinking; the queue-not-draining alert reaches the owning team. Measured as minutes from the list stopping draining to the alert being raised No target set. Holds for Managed Redis, Provider logging and metrics.

### Platform automation

The existing GitHub Actions workflows (dockersamples-example-voting-app/.github/workflows/call-docker-build-*.yaml) keep building images on pull requests and pushing on main. One added deploy job, run only from main, applies codemocsh-voting-rebuild-probe/infra/ and then k8s/ with every image named by digest. There is one deploy target: production.

| Setting | Value | Applies to |
|---|---|---|
| Image build | existing GitHub Actions workflows: build on pull request, push on main | vote, worker, result |
| Deploy job inputs and order | infra/ then k8s/ | production |
| Deploy trigger | merge to main | production |

- **Rule.** Production must change only through the deploy job on the main branch. Nothing enforces it. Holds for the whole platform.

## Workload

### Parts

#### Public load balancer

The one public entry to the vote and result web apps

- Shape: gateway
- Technology: Cloud load balancer

Does:

- Terminates public traffic for the vote and result names
- Routes ballot traffic to vote and results traffic to result, including the socket.io connection
- Is the only public address; every other part sits on private addresses

Calls:

- vote: forwards ballot requests (sync · HTTP), carrying ballot page and submitted choice
- result: forwards results requests (sync · HTTP, WebSocket), carrying results page and score updates

#### vote `codemocsh-voting-rebuild-probe/vote/`

Web app serving the ballot and accepting each voter's choice onto the queue

- Shape: app
- Technology: Python Flask on Kubernetes

Does:

- Serves the ballot page with the two option labels, in its current look
- Sets the voter cookie that identifies a voter
- Pushes each submitted vote (voter id and choice) onto the Redis 'votes' list
- Reads the Redis endpoint, port, credentials and TLS setting from environment variables

Owns:

- Voter cookie

Calls:

- Managed Redis: pushes the vote onto 'votes' (async · Redis over TLS), carrying voter id and choice
- Provider secret store: receives Redis credentials as environment variables (sync · Kubernetes secret injection), carrying Redis credentials

Replaces:

- vote

#### worker `codemocsh-voting-rebuild-probe/worker/`

Single consumer that moves each accepted vote from the queue into the votes table without losing it

- Shape: job
- Technology: .NET worker on Kubernetes

Does:

- Moves each pending vote from 'votes' to the 'processing' list with LMOVE
- Inserts or updates the voter's one row in the votes table, then removes the vote from 'processing'
- Requeues a vote whose write failed, and requeues everything left in 'processing' at start
- Runs as exactly one replica
- Connects to Redis and Postgres over TLS from environment-variable settings

Owns:

- votes table schema

Calls:

- Managed Redis: moves votes to 'processing', removes after commit, requeues on failure (async · Redis over TLS), carrying pending votes
- Managed PostgreSQL: inserts or updates one vote per voter (sync · PostgreSQL over TLS), carrying voter id and choice
- Provider secret store: receives Redis and Postgres credentials as environment variables (sync · Kubernetes secret injection), carrying Redis and Postgres credentials
- Provider logging and metrics: ships logs (async · Container stdout), carrying worker log lines

Replaces:

- worker

#### result `codemocsh-voting-rebuild-probe/result/`

Web app showing the live percentages for each option

- Shape: app
- Technology: Node.js on Kubernetes

Does:

- Reads vote counts grouped by choice from Postgres every second
- Pushes the scores to watching browsers over socket.io, in its current look
- Reads the Postgres endpoint, credentials and TLS setting from environment variables

Calls:

- Managed PostgreSQL: reads counts by choice every second (sync · PostgreSQL over TLS), carrying vote counts per choice
- Provider secret store: receives Postgres credentials as environment variables (sync · Kubernetes secret injection), carrying Postgres credentials

Replaces:

- result

#### Managed Redis

Holds accepted votes until the worker has recorded them

- Shape: queue
- Technology: Managed Redis, persistence on

Does:

- Holds the 'votes' list of pending votes and the 'processing' list of votes in flight
- Persists both lists so a restart keeps queued votes
- Accepts TLS connections on a private address only, encrypted at rest with provider keys

Owns:

- 'votes' pending list
- 'processing' in-flight list

Calls:

- Provider logging and metrics: reports list lengths and health (async · Provider metrics), carrying 'votes' and 'processing' lengths

Replaces:

- redis

#### Managed PostgreSQL

The record of every voter's current vote

- Shape: store
- Technology: Managed PostgreSQL 15

Does:

- Holds the votes table, one row per voter
- Takes automated backups with point-in-time restore
- Accepts TLS connections on a private address only, encrypted at rest with provider keys

Owns:

- votes table rows

Keeps:

- Vote

Calls:

- Provider logging and metrics: reports health (async · Provider metrics), carrying database platform metrics

Replaces:

- db

### Switched off

- seed

### What callers reach today

#### db

Replaced by Managed PostgreSQL.

| Address | Form | Protocol |
|---|---|---|
| `healthchecks/postgres.sh` | command |  |

#### redis

Replaced by Managed Redis.

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
| Voter | Public load balancer | votes in a browser | sync · HTTPS | ballot page and submitted choice |
| Results watcher | Public load balancer | watches results in a browser | sync · HTTPS, WebSocket | live percentages |
| Voter | DNS | resolves the vote and result names | sync · DNS | load balancer address |
| Provider logging and metrics | Owning team | alerts the owning team | async · Provider alerting | queue-not-draining and part-down alerts |

### Runtime

#### A vote reaches the live tally

1. Voter → Public load balancer: Open ballot page and submit choice
2. Public load balancer → vote: Serve ballot, accept voter's choice
3. vote → Managed Redis: Push accepted vote onto queue
4. worker → Managed Redis: Take next accepted vote
5. worker → Managed PostgreSQL: Record voter's current vote
6. Results watcher → Public load balancer: Open results page
7. Public load balancer → result: Route to results web app
8. result → Managed PostgreSQL: Read counts per option for percentages

### Migration strategy

vote and result replatform unchanged except the ballot's https script and icon URLs; worker replatforms with the queue-handoff fix and the stop-dropping-on-disconnect fix; db and redis are replaced by managed Postgres 15 and managed Redis; seed is retired. All three services read endpoints, credentials and TLS from environment variables. Runtime upgrades, the results 'Giving up' path and the voter-identifier truncation wait until after the move.

| Setting | Value | Applies to |
|---|---|---|
| vote and result disposition | replatform unchanged | vote, result |
| worker disposition | replatform with queue-handoff fix | worker |
| db, redis, seed disposition | db and redis replaced by managed services; seed retired | db, queue |

### Tech stack

vote stays on Python 3.11 with Flask, redis-py and gunicorn; worker on .NET 7 with StackExchange.Redis 2.2.4, Npgsql 4.1.9 and Newtonsoft.Json; result on Node 18 with express, pg and socket.io (worker/Worker.csproj, result/Dockerfile, vote/Dockerfile). The worker issues LMOVE through its client's command API where the pinned client has no typed method; worker and result enable TLS on their store connections.

| Setting | Value | Applies to |
|---|---|---|
| vote runtime | Python 3.11 (python:3.11-slim), Flask, redis-py, gunicorn | vote |
| worker runtime | .NET 7, StackExchange.Redis 2.2.4, Npgsql 4.1.9 | worker |
| result runtime | Node 18 (node:18-slim), express, pg, socket.io | result |

### Code organization

vote lives at codemocsh-voting-rebuild-probe/vote/ with tests in vote/tests/; worker and result stay in dockersamples-example-voting-app/worker/ and result/. Platform definitions go in codemocsh-voting-rebuild-probe/infra/, Kubernetes manifests derived from k8s-specifications/ without the db and redis files in codemocsh-voting-rebuild-probe/k8s/, and vote-loss and cutover checks in codemocsh-voting-rebuild-probe/tests/. No generated code is committed.

| Setting | Value | Applies to |
|---|---|---|
| vote directory | codemocsh-voting-rebuild-probe/vote/ | vote |
| worker and result directories | dockersamples-example-voting-app/worker/ and result/ | worker, result |
| Platform, manifests and cutover checks | codemocsh-voting-rebuild-probe/infra/, k8s/, tests/ | every environment |

### Test strategy

Every pull request runs fast unit tests for the changed service (worker handoff order, worker retry on DB error, refusal to start without endpoint variables) and the compose end-to-end check in result/docker-compose.test.yml moved to postgres:15. Before the wave lands, on production before DNS moves: the vote-loss test that kills the worker pod and restarts Redis mid-load, one case per changed sentence from records/cases.jsonl, the restore rehearsal and the per-choice reconcile. A flaky test is a defect fixed at its cause.

| Setting | Value | Applies to |
|---|---|---|
| Every pull request | unit tests of the changed service plus result/docker-compose.test.yml end-to-end on postgres:15 | vote, worker, result |
| Before the wave lands | vote-loss test, records/cases.jsonl cases, restore rehearsal, per-choice reconcile | production |
| Test retries | none; a flaky test is a defect | every environment |

### Compute and runtime

vote, result and worker run as Deployments on a managed Kubernetes cluster from manifests in codemocsh-voting-rebuild-probe/k8s/, derived from dockersamples-example-voting-app/k8s-specifications/ with db- and redis-deployment.yaml and their Services removed. vote and result Services change from NodePort (31000, 31001) to back ends of the one public load balancer. worker runs exactly one replica.

| Setting | Value | Applies to |
|---|---|---|
| worker replicas | 1 | worker |
| Node size and node pool count | not set | production |
| vote and result Service exposure | behind the public load balancer (replaces NodePort 31000 and 31001) | vote, result |

### Data and storage

Managed PostgreSQL 15, single instance, holds the votes table (one row per voter, two VARCHAR(255) columns as created in worker/Program.cs:96-99) with automated backups and point-in-time restore. Managed Redis with persistence on holds the 'votes' and 'processing' lists. Existing votes cross by a short write freeze: drain the old Redis list to zero, pg_dump and restore the votes table, reconcile counts per choice.

| Setting | Value | Applies to |
|---|---|---|
| Postgres engine and topology | managed PostgreSQL 15, single instance, no standby | db |
| Redis persistence | on | queue |
| Postgres backups | automated, point-in-time restore on | db |
| Redis backups | none | queue |
| Postgres backup retention | not set | db |

### Integration and state

vote keeps RPUSH to 'votes' and answers only after the push returns. worker LMOVEs each vote from the head of 'votes' to 'processing', upserts it keyed on voter id, then removes it from 'processing'; on a DB error it retries the same vote, and at start it moves everything left in 'processing' back to the head of 'votes'. Every service reads endpoint, port, credentials and TLS setting from environment variables with no default, and fails at start if one is missing.

| Setting | Value | Applies to |
|---|---|---|
| Connection settings source | environment variables for endpoint, port, credentials, TLS; no defaults | vote, worker, result |
| Redis list names | 'votes' (pending), 'processing' (in flight) | queue |
| worker handoff order | LMOVE votes→processing, upsert by voter id, LREM from processing; requeue processing at start | worker |

- **Reliability.** While a known number of votes is posted, the worker pod is killed between LMOVE and commit and Redis is restarted; the worker requeues 'processing' at start and every vote is recorded. Measured as votes accepted minus rows recorded in the votes table Target: 0. Holds for worker, Managed Redis, Managed PostgreSQL.
- **Rule.** The worker must remove a vote from 'processing' only after its Postgres write commits. Nothing enforces it. Holds for worker.
- **Rule.** The worker must run exactly one replica. Enforced by replicas: 1 in the worker Deployment in k8s/. Holds for worker.
- **Rule.** A service must refuse to start when any store connection variable is missing. Nothing enforces it. Holds for vote, worker, result.

### User experience

The look of both screens comes from the code that draws them today: the ballot from vote/templates/index.html and vote/static/stylesheets/style.css, shown by vote to voters; the results page from result/views/index.html, app.js and stylesheets/style.css, shown by result to results watchers. No shared design system and no component library; no WCAG level is claimed by the move. The only edit is serving the ballot's jQuery and icon URLs over https so the confirmation tick still renders under TLS.

| Setting | Value | Applies to |
|---|---|---|
| Design source | current templates and stylesheets of each screen; no shared design system | vote, result |
| Component library | none | vote, result |
| Themes | the one current look of each screen | vote, result |
| Browsers and devices | not set | vote, result |
| Locales | not set | vote, result |
| Ballot script and icon URLs | https | vote |

- **Interaction capability.** Each screen is audited by an automated accessibility checker after the move; no WCAG 2.2 level is claimed, so the audit records the level met against today's. Measured as automated WCAG 2.2 audit failures per screen, compared with the same screen before the move No target set. Holds for vote, result.
- **Rule.** Every screen must take its colours, type and spacing from its own current stylesheet, the design source this move keeps. Nothing enforces it. Holds for vote, result.

## Transition

### The switch

1. Lower the TTL on the vote and result DNS names and wait at least one old TTL On DNS.
2. Stop intake on the old estate so its ballot accepts no new vote On Today's voting app.
3. Let the old worker drain the old 'votes' list and confirm its length is 0 On Cutover data move and reconcile, Today's voting app.
4. Dump the old votes table on the old host and keep the dump in the storage bucket On Cutover data move and reconcile, Today's voting app, old database dump.
5. Restore the dump into managed Postgres through the operator session On Cutover data move and reconcile, Managed PostgreSQL, operator session.
6. Reconcile counts per choice between old and new databases; stop on any difference On Cutover data move and reconcile, Managed PostgreSQL, Today's voting app.
7. Smoke-test the ballot and results pages on the new load balancer without casting a vote On Public load balancer, vote, result.
8. Repoint both DNS names to the new load balancer at once On DNS, Public load balancer.
9. Let the new estate accept its first vote On vote, Managed Redis, worker, Managed PostgreSQL. Past this step the move cannot be reversed.
10. After the post-cutover reconcile passes and the first automated backup exists, stop the old estate and remove the data-move job and its credentials On Today's voting app, Cutover data move and reconcile.

### Putting it back

1. Repoint both DNS names back to the old estate On DNS, Today's voting app.
2. Reopen intake on the old estate On Today's voting app.
3. Empty the votes table in managed Postgres and both Redis lists for the next attempt On Managed PostgreSQL, Managed Redis.

### Transitional parts

#### Cutover data move and reconcile `codemocsh-voting-rebuild-probe/tests/`

Copies the frozen, drained votes from today's database into managed Postgres and proves the counts match

- Shape: job
- Technology: pg_dump and pg_restore

Does:

- Checks today's Redis 'votes' list is drained to zero after intake stops
- Dumps today's votes table and restores it into managed Postgres
- Reconciles the vote count for each choice between the old and new databases
- Keeps a final dump of the old database in storage

Owns:

- Reconcile report

Calls:

- Today's voting app: checks the drain and dumps today's votes (batch · PostgreSQL, Redis), carrying votes table dump and queue length
- Managed PostgreSQL: restores and reconciles the votes (batch · PostgreSQL over TLS), carrying votes table rows and counts per choice

### Cutover and rollback

Traffic moves by one DNS switch of both names at once, after the TTL has been lowered ahead, so there is never a moment when two estates take votes and split the tally. Data crosses under a write freeze: the old worker drains the old 'votes' list to zero, the votes table is dumped and restored, and counts per choice are reconciled; any difference stops the switch. The old estate's stores are only read, so until the new estate accepts its first vote rollback is repointing DNS back and reopening intake, and the old data is intact because nothing wrote to it. Go signals are the reconcile report at zero difference, the old queue length at zero, and smoke tests of both screens on the new estate; the data-move job is transitional, runs only through an operator session into the private network, and is removed with its credentials once the reconcile passes.

| Setting | Value | Applies to |
|---|---|---|
| DNS TTL during the move | not set | dns |
| Names switched | vote and result names, both at once | dns |
| Reconcile pass condition | zero difference in vote count per choice | data-move |
| Old 'votes' list length before dump | 0 | old-estate |

- **Functional suitability.** After the freeze, drain, dump and restore, the vote count for each choice is compared between the old and new databases before DNS moves. Measured as difference in vote count per choice Target: 0. Holds for Cutover data move and reconcile, Managed PostgreSQL.
- **Rule.** The old and new estates must never accept votes at the same time. Nothing enforces it. Holds for Today's voting app, vote.
- **Rule.** The data move must only read the old estate's Postgres and Redis. Nothing enforces it. Holds for Cutover data move and reconcile, Today's voting app.

## Operate

### Resilience and recovery

There is no standby: the stores run in one zone, the cluster's node pool replaces failed nodes, and an instance failure is an outage until the provider replaces it. Recorded votes are recovered by Postgres point-in-time restore, rehearsed once into a scratch instance before cutover and passed when counts per choice match. Redis is not backed up; its persistence covers a restart, and a lost Redis volume loses only votes not yet drained.

| Setting | Value | Applies to |
|---|---|---|
| Recovery point for recorded votes | not set | db |
| Recovery time | not set | production |
| Standby capacity | none | db, queue |
| Restore rehearsal | once before cutover, into a scratch instance; passes on equal counts per choice | db |

- **Reliability.** The managed Postgres instance is lost and recorded votes are restored to a point in time into a new instance. Measured as recorded votes missing after restore, and hours to restore No target set. Holds for Managed PostgreSQL.
- **Rule.** The stores must run as single instances with no standby. Enforced by single-instance topology in infra/. Holds for Managed PostgreSQL, Managed Redis.

### Operating model

The team that builds the app runs it in working hours, answers the two alerts, upgrades the cluster and runtimes and runs restores; the provider operates the control plane and both stores. The old estate is stopped once the post-cutover reconcile passes and the new database has its first automated backup, keeping a final dump of the old database in storage; the seed profile and the in-cluster db and redis manifests retire with it.

| Setting | Value | Applies to |
|---|---|---|
| Who runs the estate | the building team, working hours; provider runs control plane and stores | production |
| Old estate stops when | post-cutover reconcile passes and new database has its first automated backup | old-estate |
| Final dump of the old database | kept in storage | old-estate |

## What the charter sets

- Goal: Run the voting app on a managed container platform, losing no vote cast. (5 rows)
- Out of scope: Redesigning the results page. (6 rows)

## Decisions this design rests on

- What shape is the network, and how do the services reach the managed stores and the old estate during the move? (23 rows)
- How do the existing votes and any queued votes get to the new stores, and with what downtime? (16 rows)
- How is an accepted vote kept safe between the vote service, the queue and the worker? (14 rows)
- How do vote, worker and result find Redis and Postgres after the move? (11 rows)
- Where does the look of the ballot and results screens come from after the move, and which of them change? (11 rows)
- What is backed up, and when is a restore proven? (11 rows)
- Who holds the encryption keys for the votes database and queue? (11 rows)
- Which strategy does each of the six containers (vote, result, worker, redis, db, seed) take? (10 rows)
- Where do the database and Redis credentials live, and what rotates them? (10 rows)
- What is collected, where does it go, and how long is it kept? (10 rows)
- What alerts a person, and who answers? (10 rows)
- How does voter and watcher traffic move to the new estate? (10 rows)
- How is the code laid out after the move, and where do platform definitions, manifests and tests go? (9 rows)
- What builds and ships the images, the manifests and the platform definitions, and who may run it? (9 rows)
- Where is the point of no return, and how is the cutover reversed before it? (9 rows)
- How far does the estate fail over, and what does the standby cost? (9 rows)
- When does the old estate go off? (9 rows)
- What does the platform refuse outright, and what does it only report? (9 rows)
- Which stores hold the votes table and the pending-votes queue after the move? (8 rows)
- Which languages, runtimes and client libraries does each service run on after the move? (8 rows)
- Which managed container platform runs vote, worker and result? (7 rows)
- How is a change proven, and what proves no vote was lost before the cutover lands? (7 rows)
- What does the voting app carry, and what does an hour of it being unavailable cost? (5 rows)
- How many environments does the estate need, and who pays for them? (5 rows)
- Who runs the estate after the cutover? (5 rows)
- Which code changes ride with the move, and which wait until after it? (4 rows)
- Which region does the estate run in? (4 rows)
- What is the default strategy for the voting app, and what earns an exception? (3 rows)
- What moves together? (1 rows)

### Decided, and not an architecture decision

- What has to be ready before the one wave starts?

## Risks and open questions

### Regions and residency

- Region: no value set

### Network topology

- Private network address range: no value set
- The public load balancer must be the only public address in the estate.: nothing enforces it

### Encryption and secrets

- Store credentials must never be written into source, manifests or images.: nothing enforces it

### Observability

- Minutes a non-empty, non-shrinking list waits before alerting: no value set
- The worker stops recording votes while the 'votes' or 'processing' list stays non-empty and is not shrinking; the queue-not-draining alert reaches the owning team.: no target set

### Platform automation

- Production must change only through the deploy job on the main branch.: nothing enforces it

### Compute and runtime

- Node size and node pool count: no value set

### Data and storage

- Postgres backup retention: no value set

### Integration and state

- The worker must remove a vote from 'processing' only after its Postgres write commits.: nothing enforces it
- A service must refuse to start when any store connection variable is missing.: nothing enforces it

### User experience

- Browsers and devices: no value set
- Locales: no value set
- Each screen is audited by an automated accessibility checker after the move; no WCAG 2.2 level is claimed, so the audit records the level met against today's.: no target set
- Every screen must take its colours, type and spacing from its own current stylesheet, the design source this move keeps.: nothing enforces it

### Cutover and rollback

- DNS TTL during the move: no value set
- The old and new estates must never accept votes at the same time.: nothing enforces it
- The data move must only read the old estate's Postgres and Redis.: nothing enforces it

### Resilience and recovery

- Recovery point for recorded votes: no value set
- Recovery time: no value set
- The managed Postgres instance is lost and recorded votes are restored to a point in time into a new instance.: no target set

## Glossary

- **Option**: One of the two things voted between, shown on the ballot with a label (default Cats and Dogs).
- **Vote**: A voter's current choice between the two options; one per voter, a later choice replaces the earlier.
