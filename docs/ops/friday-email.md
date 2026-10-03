# Friday email

The digest is sent by GitHub Actions, not by a server in this project. See [ADR 0002](../adr/0002-friday-email-via-github-actions.md) and [how the list is chosen](../features/weekend-planner.md).

## Schedule

| Clock | What runs |
| --- | --- |
| Friday 09:00 UTC | Workflow starts. Sends only during British Summer Time, when London is at 10:00. |
| Friday 10:00 UTC | Workflow starts. Sends only during Greenwich Mean Time, when London is at 10:00. |

The other run exits without sending. You can also run the workflow by hand from the Actions tab; that sends immediately.

Recipient: `Alan@alanstirling.com`.

## Resend account

This has to be done in a browser, signed in as you. The repository cannot create the account.

1. Open [resend.com/signup](https://resend.com/signup) and sign up with **Alan@alanstirling.com**.
2. Open the confirmation message Resend sends and confirm the account.
3. Open [API Keys](https://resend.com/api-keys) and create a key with permission to send.
4. Copy the key. Resend shows it once. Do not paste it into chat.

The free test sender (`onboarding@resend.dev`) delivers only to that signup address. To send from an `@alanstirling.com` address later, add the domain at [resend.com/domains](https://resend.com/domains) and set `SMTP_FROM`. That step is not required for the Friday list.

## Secret

In the GitHub repository: Settings → Secrets and variables → Actions → New repository secret.

| Name | Value |
| --- | --- |
| `RESEND_API_KEY` | The key from the Resend dashboard |

The job turns that key into Resend's SMTP login. No mailbox password is used.

## Local send

```bash
cp .env.example .env
# put the key in RESEND_API_KEY
python3 -m planner --send
```

`.env` is gitignored. Create it on your own computer, not in chat.

## If a Friday mail does not arrive

1. Actions → Friday weekend digest → the Friday run. A green run that says "Not sending" is the extra UTC slot and is expected.
2. A failed run with "Cannot send yet" means a secret is missing or mistyped.
3. A failed run with "Email failed" means Resend rejected the key, or the message was sent to an address other than the Resend signup address while still using `onboarding@resend.dev`.
4. If the mail arrived but the weekend events are missing, What's On Edinburgh's page layout has probably changed. Standing places still send. The parser is in `planner/events.py`.
