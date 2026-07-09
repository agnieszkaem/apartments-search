# Apartment Monitor Plan

## Goal

Build a simple apartment monitor that checks a few websites every 10 minutes, finds new listings marked as immediately available, and sends one email with all new matches. The first version should stay simple, cost €0, and be easy to extend with another website later.

## What this project should do

- Run on a schedule without your computer being on.
- Check a small set of apartment websites.
- Keep only listings that match your filters.
- Send one batched email per run.
- Never report the same listing twice.
- Make each new website an isolated adapter, not a rewrite.

## What we will not try to do in v1

- No visual dashboard.
- No database server.
- No browser automation unless a site really requires it.
- No overengineering around ranking, ML, or maps.

## Chosen setup

- Scheduler: GitHub Actions cron.
- Mail: Gmail SMTP.
- Runtime: Python.
- Persistence: one small state file in the repo for already-seen listings.
- Site support model: one adapter per website.

## Core architecture

The app should follow one pipeline for every source:

1. Fetch the page or API response.
2. Parse listings from that source.
3. Normalize them into one shared apartment shape.
4. Apply filters in Python.
5. Remove duplicates using a stable listing key.
6. Send one email with all new matches.

## Shared apartment shape

Every scraper should return the same minimal object:

```python
Apartment(
    source="GESIBA",
    listing_id="123456",
    title="2 Zimmer",
    location="1100 Wien",
    price=742,
    size_sqm=61,
    rooms=2,
    url="https://...",
    available_immediately=True,
)
```

Only the scraper should know the site-specific details. Everything after that should work with the same shape.

## Stable duplicate rule

Use this order:

1. Website listing ID if the site provides one.
2. Otherwise a normalized URL.
3. Otherwise a fallback fingerprint from title, location, price, and size.

That keeps the dedupe logic simple and lets us add sites without changing the rest of the app.

## Configuration

Put all user choices in one config file so filters can change without code edits:

```yaml
filters:
  max_price: 900
  min_size_sqm: 45
  min_rooms: 2
  location_contains: Wien
  immediate_only: true

sources:
  - gesiba
  - sozialbau
  - wohnen
```

## Minimal repository structure

```text
src/
  main.py
  config.py
  models.py
  filters.py
  dedupe.py
  mailer.py
  state.py
  scrapers/
    gesiba.py
    sozialbau.py
    wohnen.py
tests/
config.yml
state.json
```

## Step by step implementation plan

### Step 1: Define the data model

Create the shared apartment model and the config format first. This gives every later piece one contract to follow.

Done when:

- The apartment fields are defined.
- The config file has the first filter options.
- There is one place that standardizes scraped data.

### Step 2: Build the runner

Create one entry point that loads config, calls all enabled scrapers, filters results, deduplicates them, and prepares an email.

Done when:

- One command runs the whole pipeline locally.
- It prints new matches or says there are none.

### Step 3: Add persistence for seen listings

Store the seen keys in a small repo file so the next scheduled run can skip old listings.

Done when:

- A listing seen in one run is skipped in the next run.
- The state format is human-readable and easy to inspect.

### Step 4: Add email sending

Send one email per run with all new listings, grouped by source.

Done when:

- The email contains title, price, location, and link.
- Multiple new listings are bundled into a single message.

### Step 5: Implement the first scraper

Start with one site only, preferably the easiest one to fetch and parse.

Done when:

- The scraper returns normalized apartments.
- It works on recorded sample HTML or API responses.

### Step 6: Add GitHub Actions scheduling

Set up the 10-minute cron and wire the run so it executes automatically.

Done when:

- The workflow runs on schedule.
- The workflow can send an email and update state.

### Step 7: Add more sites one by one

For each new website, only implement the adapter and tests. Do not change the pipeline unless a site truly requires it.

Done when:

- A new site can be added without touching filtering, dedupe, or mail logic.

## Practical rule for new websites

Before adding a site, check these in order:

1. Is there a simple HTML page or JSON endpoint?
2. Does the site expose a stable listing ID?
3. Can the listing data be parsed without a browser?
4. Only if not, use browser automation as a last resort.

## First implementation target

Start with one site only so the framework stays small and testable. After that, each additional site should be a repeatable adapter task instead of a new design problem.

## Success criteria for v1

- One scheduled run works end to end.
- New listings are emailed once.
- Existing listings are ignored.
- Adding a site means adding one scraper module and one test set.
- The code stays simple enough to maintain without a lot of infrastructure.
