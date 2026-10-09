# 0002. Friday email via GitHub Actions and SMTP

- **Status:** Accepted
- **Date:** 2026-10-03

The mail relay is Resend's free plan. See [ADR 0003](0003-resend-free-plan.md).

## Context

The weekend list has to arrive by email at 10:00 Europe/London on Friday. There is no website. The job has to keep running after this session ends, and it needs a mailbox password that must not live in the repository.

A hosted web app was the other way to run a schedule. It was not asked for, and it would mean a server that stays up all week for one email.

## Decision

A Python program in this repo builds the digest. GitHub Actions runs it on Friday. Mail is sent with the standard library over SMTP. The host, username, password, and from-address are GitHub Actions secrets (or a local `.env` that is not committed).

Weather comes from Open-Meteo. Weekend events come from the public What's On Edinburgh listings. Neither needs an API key. Standing places are a curated list in `planner/catalogue.py`.

The workflow runs once, at 09:00 UTC on Friday. The program sends when Europe/London is Friday and the hour is 10 or later. GitHub Actions often starts after the scheduled minute, and the window stays open so a late start still sends. A second UTC cron is not used: with the window open for the rest of Friday, both the summer and winter slots would send.

## Consequences

- The email keeps going as long as GitHub Actions and the SMTP account work.
- Nothing sends until the secrets are added. A missing password fails the job instead of silently skipping.
- The event parser depends on What's On Edinburgh's HTML. If that markup changes, the weekend half of the list falls back to standing places and the email says so.
- Open-Meteo being down has the same shape: the email still goes out, without a weather lean.
- There is no page to browse during the week.

## References

- [planner/main.py](../../planner/main.py)
- [.github/workflows/friday-digest.yml](../../.github/workflows/friday-digest.yml)
- [docs/features/weekend-planner.md](../features/weekend-planner.md)
- [docs/ops/friday-email.md](../ops/friday-email.md)
