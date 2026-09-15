# Task: Force!

A task manager for people who find it hard to keep every part of their life in one place.

Most to-do apps assume you already know how to organise. Task: Force! is built for the opposite case — the shopping you forgot, the workout you meant to do, the flat that needs cleaning, the errand you promised someone else. It keeps all of it in one system, and it offers two ways to look at that system: a plain, text-based mode for getting things done, and a game-like mode for when a list is not enough motivation.

Everything is framed as a military operation. Tasks are **missions**, groups are **units**, messages are **comms**, and finishing a mission earns your avatar **intel points**.

## Two modes

**Debrief** — the classic view. A dashboard with your open missions, your units and your recent comms; a searchable, filterable mission log; quick-add from the home page. This is the mode that is built.

**Deploy** — planned. A visual, game-like interface where your avatar moves around a base and each location shows the missions relevant to that moment: the supply depot for groceries, the training ground for workouts, HQ for everything unsorted. Deploy is a second rendering of the same data, not a separate app — the same missions appear in both modes.

## Domain vocabulary

| Term | Meaning |
| --- | --- |
| **Mission** | A single task. Has a name, an owner, points, and optionally a type, a unit, a due date and an assignee. |
| **Unit** | A group of users. Membership is via a UUID invite code or link, with roles of commander or operative. |
| **Comms** | Messaging. Visibility comes entirely from unit membership — there are no direct messages. |
| **Avatar** | A user's game profile, holding their intel points. Linked one-to-one to the Django user. |
| **Intel points** | Awarded to whoever completes a mission. |

Mission completion is **global, not per-user**: when anyone in a unit completes a shared mission, it is complete for everyone, and the points go to the person who did it. This is deliberate — a unit mission is one job, not the same job repeated per member.

## Mission types

A mission can have a type, or none at all. Untyped missions ("buy tomatoes on the way home") are first-class — quick-add creates them, and the app is designed so that the fastest possible path from opening the page to recording a task stays one field and one button.

Typed missions — groceries, workout, chores, list — are for tasks that contain things: a shopping list with items, a workout with sets, a cleaning session with steps. The type decides what a mission's contents look like and where it appears in Deploy.

## Stack

- **Django** with **PostgreSQL**
- **Vanilla JavaScript** — no frontend framework, by choice
- Deployed on **Render**
- Fonts: Barlow Condensed and Share Tech Mono; an olive and khaki palette driven by CSS variables

## Apps

| App | Responsibility |
| --- | --- |
| `accounts` | Users, avatars, profiles |
| `common` | Home dashboard, shared templates, context processors |
| `tasks` | Missions: models, views, forms, filtering |
| `units` | Units and memberships |
| `comms` | Conversations, messages, read state |

## Design notes

A few decisions that are easy to miss from the code alone:

**Permission lives in the queryset.** Every view resolves its objects through `Task.objects.visible_to(user)` or an equivalent filter, rather than trusting the page that linked there. A mission is visible if you own it or belong to its unit.

**Completion is a database operation, not a Python one.** `Task.complete()` claims the mission with a conditional `UPDATE ... WHERE is_done = false` and awards points with an `F()` expression inside a transaction. Two people clicking at the same moment cannot both be awarded, and concurrent point awards cannot clobber each other.

**Read state is a pointer, not a row per message.** `ConversationRead` stores one `last_read_at` per user per conversation; unread status is computed by comparing message timestamps against that pointer.

**Contents are related models, not subclasses.** A shopping list is a mission with grocery items attached, not a different kind of mission. This keeps one `Task` table, so cross-type queries, pagination and per-mission comms all keep working as new types are added.

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

## Status

Debrief mode is functional: missions, units, comms, filtering, pagination, and the points economy. Mission contents (grocery items, workout sets, chore steps) are in progress. Deploy mode, unit member management, and recurring missions are planned.

---

Built by Kiara as a portfolio project.
