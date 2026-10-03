# 0003. Send through Resend's free plan

- **Status:** Accepted
- **Date:** 2026-10-03

## Context

The Friday job needs a mailbox that can send one message a week. Using the personal mailbox password means handing a login to GitHub Actions. [Resend](https://resend.com/pricing) has a free plan of 3,000 emails a month and 100 a day, with no overage charge. A send-only API key cannot read the inbox.

The schedule is unchanged from [ADR 0002](0002-friday-email-via-github-actions.md).

## Decision

Send with Resend's SMTP relay (`smtp.resend.com`, user `resend`, password is the API key). The program accepts `RESEND_API_KEY` and fills those SMTP settings itself. No extra Python package.

Until a domain is verified, the from-address is `onboarding@resend.dev`. Resend delivers that test sender only to the email address on the Resend account, so the account is Alan@alanstirling.com.

A verified domain can replace the from-address later by setting `SMTP_FROM`.

## Consequences

- One secret, `RESEND_API_KEY`, instead of a mailbox password.
- The account and the API key are created by the owner in the Resend dashboard. They are not created from this repository.
- The free test sender will not deliver to any address other than the Resend signup address.
- If the monthly or daily free quota is hit, Resend stops sending until the quota resets. This volume is about four messages a month.

## References

- [planner/mailer.py](../../planner/mailer.py)
- [docs/ops/friday-email.md](../ops/friday-email.md)
- [Resend pricing](https://resend.com/pricing)
- [Resend test-domain limit](https://resend.com/docs/knowledge-base/403-error-resend-dev-domain)
