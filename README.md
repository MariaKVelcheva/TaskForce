# Task: Force!

A task manager for people who find it hard to keep every part of their life in one place.

Most to-do apps assume you already know how to organise. Task: Force! is built for the opposite case — the shopping you forgot, the workout you meant to do, the flat that needs cleaning, the errand you promised someone else. It keeps all of it in one system, and it offers two ways to look at that system: a plain, text-based mode for getting things done, and a game-like mode for when a list is not enough motivation.

Everything is framed as a military operation. Tasks are **missions**, groups are **units**, messages are **comms**, and your work earns your avatar **intel points**.

> **Status: v1 complete — v2 in progress.** Both modes are built and tested. v2 reshapes the app around shared household lists; see [What's next: v2](#whats-next-v2). The v1 code is preserved under the `v1.0` tag.

![Deploy mode: the base map, with the operative standing at the most urgent location](docs/deploy-map.png)

## Two modes

**Debrief** — the classic view. A dashboard with your open missions, overdue and due-soon panels, your units and your recent comms; a filterable, paginated mission log; quick-add from the home page.

**Deploy** — the visual view. Your missions are laid out on a tile map of a military base, in the style of classic strategy-game adventure maps. Each building is a place where a kind of work happens: the supply depot for groceries, the training ground for workouts, the barracks for chores, the rec room for lists, and HQ for everything unsorted. Deploy is a second rendering of the same data, not a separate app — the same missions appear in both modes, and you choose the mode when you enter.

The map is designed to answer one question without reading anything: **where should I go, and how urgently?**

- Buildings with nothing to do fade into fog.
- A building with something due later today glows amber; one with something overdue pulses rust; a critical mission raises a pennant. Counts sit on each building as badges.
- Hovering or focusing a building previews its three most urgent missions.
- Your operative stands at the location with the most urgent mission, with a marching route from HQ, and the same objective is written out in text under the map.

Inside a building, missions are pinned to a noticeboard grouped by urgency — overdue, today, next 48 hours, later, no date — with item progress, a one-click accomplish button, and a quick-add form that already knows the mission type from the place you are standing in.

## Domain vocabulary

| Term | Meaning |
| --- | --- |
| **Mission** | A single task. Has a name, an owner, points, a priority, and optionally a type, a unit, a due date and an assignee. |
| **Unit** | A group of users. Membership is via a UUID invite code or link, with roles of commander or operative. Each unit has exactly one commander. |
| **Comms** | Messaging. Visibility comes entirely from unit membership — there are no direct messages. |
| **Avatar** | A user's game profile, holding their intel points and time zone. Linked one-to-one to the Django user. |
| **Intel points** | In v1, awarded to whoever completes a mission. |
| **Location** | A place on the Deploy map. Defined in code, not in the database. |

In v1, mission completion is **global, not per-user**: when anyone in a unit completes a shared mission, it is complete for everyone, and the points go to the person who did it.

## Mission types

A mission can have a type, or none at all. Untyped missions ("buy tomatoes on the way home") are first-class — quick-add creates them, and the fastest path from opening the page to recording a task stays one field and one button.

Typed missions — groceries, workout, chores, list — contain items: a shopping list, a workout with exercises, a set of chores, a checklist. The type decides what a mission's contents look like and where it appears in Deploy. Chores recur: each chore has a frequency, a completion log, and becomes due again on its own.

## Stack

- **Django** with **PostgreSQL**
- **Vanilla JavaScript** — no frontend framework, by choice
- **SVG** for the Deploy map
- Deployed on **Render**
- Fonts: Barlow Condensed and Share Tech Mono; an olive and khaki palette driven by CSS variables

## Apps

| App | Responsibility |
| --- | --- |
| `accounts` | Users, avatars, profiles, per-user time zone middleware |
| `common` | Mode chooser, Debrief dashboard, Deploy map and location pages, shared templates, context processors |
| `tasks` | Missions and their items: models, views, forms, filtering, locations, urgency rules |
| `units` | Units, memberships, command transfer |
| `comms` | Conversations, messages, read state |

## Design notes

A few decisions that are easy to miss from the code alone.

### Data and permissions

**Permission lives in the queryset.** Every view resolves its objects through `Task.objects.visible_to(user)` or an equivalent filter, rather than trusting the page that linked there. A mission is visible if you own it or belong to its unit.

**Completion is a database operation, not a Python one.** `Task.complete()` claims the mission with a conditional `UPDATE ... WHERE is_done = false` and awards points with an `F()` expression inside a transaction. Two people clicking at the same moment cannot both be awarded, and concurrent point awards cannot clobber each other.

**Read state is a pointer, not a row per message.** `ConversationRead` stores one `last_read_at` per user per conversation; unread status is computed by comparing message timestamps against that pointer.

**Contents are related models, not subclasses.** A shopping list is a mission with grocery items attached, not a different kind of mission. This keeps one `Task` table, so cross-type queries, pagination and per-mission comms all keep working as new types are added.

**"Today" belongs to the user.** Each avatar stores a time zone, activated per request by middleware. Due dates, "due today" and overdue checks are all computed in the user's own zone, with tests pinned to the awkward hour just after midnight.

### Deploy

**Locations are code, not data.** Each location is a label, the mission type created there, and a filter function that returns a `Q` object. No migrations are needed to add or rename one, and a coverage test guarantees that every open mission appears in exactly one location — it reads the model's type choices, so adding a new mission type without a location fails the test.

**One query for the whole map.** Counts and urgency states for all five locations come from a single query using conditional aggregation (`Count(..., filter=...)`). Hover previews are a second query that labels each mission with its location using `CASE WHEN`. The page's query count is pinned by a test.

**One definition of urgent.** Overdue, due today, due soon and "duties waiting" are defined once and shared by the map, the noticeboard, the operative's objective and the Debrief dashboard, so the modes cannot disagree.

**SVG, not canvas.** Every building is a real link: the map works without JavaScript, is keyboard-navigable, and is readable by screen readers. Hover previews use CSS `:has()` rather than JavaScript, and animations respect `prefers-reduced-motion`.

**The map is a text file, and the tests check it.** The base is a grid of characters (`=` road, `T` forest, `H` HQ…). Tests verify that every row has the same width, every location has exactly one building, and every building can be reached from HQ along the roads. The operative's route uses breadth-first search — on a small, unweighted grid it finds the shortest path with less code than A*.

**Navigation remembers where you came from.** Links into shared pages carry a `next` parameter, validated against open redirects, so "back" returns you to the location or filtered log you came from.

## Running it locally

```powershell
git clone https://github.com/<your-username>/TaskForce.git
cd TaskForce

python -m venv .venv
.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

Create a PostgreSQL database and set the environment variables your `settings.py` expects, then:

```powershell
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Tests:

```powershell
python manage.py test
```

## What's next: v2

Using v1 made one thing clear: households don't keep five grocery lists. They keep **one** — the list on the fridge — and one chore rota. v2 reshapes the app around how shared homes, offices and groups actually work.

**Planned changes:**

- **Lone wolf by default.** Every user gets a personal unit for their own missions, and can join as many shared units as they like — one profile, many groups. Deploy shows one unit's base at a time; Debrief stays the overview across all of them.
- **One shared grocery list per unit**, refilled automatically in two ways: items that recur every few days, and a pantry that adds an item to the list when its stock runs low.
- **One shared chore rota per unit**, with chores placed by room — shown in Deploy as a floor plan inside the barracks.
- **Points per item, not per mission.** Shared lists never finish, so missions stop being "accomplished". Instead, whoever checks an item earns its points, and unchecking returns them from the person who earned them.
- **A budget per unit**, with prices on grocery items and spending recorded as a ledger.

Simple missions, lists and workouts keep working as they do now. A workout calendar is on the longer-term list.

---

Built by Kiara as a portfolio project.
