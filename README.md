# Livingston weekend planner

A Friday morning email of things to do with an 11-year-old, a 13-year-old, and both parents, starting from Livingston, Scotland.

Each email has **6 free** and **6 paid** ideas, all within 20 miles as the crow flies. Every idea is tagged **Whole family** or **Kids**. The list mixes what is on that weekend with places you can go any weekend. If the forecast is wet, it leans indoor.

It is email only. There is no website.

## Run it locally

Python 3.11 or newer. No packages to install.

```bash
python3 -m planner
```

That prints the digest for the coming Saturday and Sunday. It does not send email.

## Friday email

The mail goes to **Alan@alanstirling.com** on Friday morning, from **10:00 Europe/London** onward, including when the job starts late.

GitHub Actions runs the job once each Friday (`.github/workflows/friday-digest.yml`), at 10:00 UTC. That is 10:00 in London in winter and 11:00 in summer, so it sends on a Friday morning in both seasons. If the job starts later the same day, it still sends. A second Friday cron is not used, because both slots would send once the window stays open past 10:00.

Mail goes out through [Resend](https://resend.com/pricing)'s free plan (3,000 emails a month, no charge). The only secret is a send-only API key. Nothing sends until that key is set. Do not put the key in chat or in a file that gets committed.

| Secret | What it is |
| --- | --- |
| `RESEND_API_KEY` | Sending key from the Resend dashboard |

Sign up with **Alan@alanstirling.com**. Until a domain is verified, Resend only delivers the test sender to that signup address. Full steps are in [docs/ops/friday-email.md](docs/ops/friday-email.md).

To send a copy from your own machine, copy `.env.example` to `.env`, paste the key there, and run:

```bash
python3 -m planner --send
```

## How a list is chosen

See [docs/features/weekend-planner.md](docs/features/weekend-planner.md).

- Home is The Centre, Almondvale, Livingston.
- Standing places live in `planner/catalogue.py`.
- Weekend events are read from What's On Edinburgh's family-and-kids pages for that Saturday and Sunday. Toddler sessions, 18+ nights, and anything outside 20 miles are dropped.
- Weather is the Open-Meteo forecast for Livingston. No API key.

## Tests

```bash
python3 -m unittest discover -s tests -v
```
