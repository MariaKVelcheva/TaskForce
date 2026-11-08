# Task: Force!

A task manager for people who find it hard to keep every part of their life in one place.

Most to-do apps assume you already know how to organise. Task: Force! is built for the opposite case — the shopping you forgot, the workout you meant to do, the flat that needs cleaning, the errand you promised someone else. It keeps all of it in one system, and it offers two ways to look at that system: a plain, text-based mode for getting things done, and a game-like mode for when a list is not enough motivation.

Everything is framed as a military operation. Tasks are **missions**, groups are **units**, messages are **comms**, and your work earns your avatar **intel points**.

> **Status: v2 core and Supply complete.** The app runs on shared household lists: a personal base for every user, one grocery list, pantry and chore rota per unit, points earned per checked item, and a pantry that refills the shopping list by itself. The barracks floor plan, a workout calendar and a unit budget are next — see [What's next](#whats-next). The v1 code is preserved under the `v1.0` tag.

![Deploy mode: the base map, with the operative standing at the most urgent location](docs/deploy-map.png)

## Two modes

**Debrief** — the overview. A dashboard across every unit you belong to: what needs action now, what is due soon, your active missions, and a status line for each of your bases ("6 to buy · 2 duties pending · 1 low"), each part linking straight to that list. Quick add creates a standing order in one field; the full briefing form is one link away. A filterable, paginated mission log, and a **shopping run** page that gathers everything still to buy across all your bases on one screen.

**Deploy** — the visual view. One base at a time: your personal base, or the base of a unit you belong to, switched from the nav. Its missions are laid out on a tile map of a military base, in the style of classic strategy-game adventure maps. Each building is a place where a kind of work happens: the supply depot for groceries and the pantry, the training ground for workouts, the barracks for chores, the rec room for lists, and HQ for standing orders. Deploy is a second rendering of the same data, not a separate app — the same missions appear in both modes.

The map is designed to answer one question without reading anything: **where should I go, and how urgently?**

- The whole base fits on screen, without scrolling.
- Buildings with nothing to do fade into fog.
- A building with something due later today glows amber; one that needs action pulses rust — an overdue standing order, a chore that is due again, a pantry product running low. A critical mission raises a pennant. Counts sit on each building as badges.
- Hovering or focusing a building previews its three most urgent missions.
- Your operative stands at the location with the most urgent mission, with a marching route from HQ, and the same objective is written out in text under the map.
- Training is personal: on a unit's base it is off limits, and says so.

Buildings open what they hold. HQ and the rec room show a noticeboard of missions grouped by urgency — action required, today, next 48 hours, later, no deadline — with a quick-add form. The barracks and the training ground hold a single list each, so they open it directly. The supply depot opens onto two panels side by side: the **shelves** and the **shopping list**.

## Domain vocabulary

| Term | Meaning |
| --- | --- |
| **Mission** | A single task, belonging to one unit. Has a name, a type, a priority, and optionally a due date and an assignee. Missions are active or inactive. |
| **Standing order** | A one-off mission with no items ("buy Mom a present"). The only kind of mission that is *accomplished*: doing so earns one point and retires it from the board. |
| **Unit** | A group of users, joined by a UUID invite code or link, with exactly one commander. Every user also has a **personal unit** — their lone-wolf base — which no one else can join. |
| **Comms** | Messaging inside group units. Visibility comes entirely from unit membership — there are no direct messages, and personal bases have no comms. |
| **Avatar** | A user's game profile: intel points, time zone, and the unit whose base Deploy is showing. |
| **Intel points** | One point per checked item or accomplished standing order, earned by whoever did it. Unchecking returns the point from the person who earned it, not from whoever unchecks. |
| **Location** | A place on the Deploy map. Defined in code, not in the database. |

## Missions and items

Every unit is created with its shared lists already in place: **one grocery list, one pantry and one chore rota**, plus a **workout** on personal bases. Nobody has to create them, and they cannot be deleted or deactivated — if a household doesn't use the pantry, it simply stays empty.

On top of those, anyone can create **standing orders** and **lists** (a watchlist, a packing list) as often as they like, and assign them to someone in the unit.

Items are where the work happens:

- **Checkable items** — groceries, chores, exercises, list entries — are ticked off by whoever does them, and each tick is one point. Bought groceries stay visible until someone clears them.
- **Recurring items** — groceries and chores can repeat every N days. A recurring item disappears when it is done and comes back on its own when it is due again; "Need it now" brings it back early (more milk because guests are coming).
- **Pantry products** are counted, not checked, with −/+ buttons. A product that runs out — or drops to an optional "low at" level, for things you want to buy before they are gone — **adds itself to the shopping list**, with the amount needed to restock. Buying it puts that amount back on the shelf.

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
| `common` | Mode chooser, Debrief dashboard, Deploy map, location pages and interiors, shared templates, context processors |
| `tasks` | Missions and their items: models, views, forms, filtering, locations, urgency rules, the shopping run |
| `units` | Units, memberships, command transfer, the active-unit switcher, unit creation |
| `comms` | Conversations, messages, read state |

## Design notes

A few decisions that are easy to miss from the code alone.

### Data and permissions

**Permission lives in the queryset.** Every view resolves its objects through `Task.objects.visible_to(user)` or an equivalent filter, rather than trusting the page that linked there. Since every mission belongs to a unit, visibility is a single rule — "missions of units I am a member of" — written as an `Exists` subquery rather than a join, so missions are never duplicated and no query needs `DISTINCT`.

**The database enforces the rules that matter.** One grocery list, pantry, chore rota and workout per unit is a conditional unique constraint. Shared lists can never be deactivated, due dates only exist on standing orders and lists, only standing orders can be accomplished, and a grocery item linked to the pantry cannot also be recurring — all check constraints. The views hide the buttons; the database is the guarantee.

**Points are claimed, not computed.** Checking an item is a conditional `UPDATE ... WHERE is_checked = false` plus an `F()` increment on the checker's points, inside one transaction. Unchecking locks the row with `select_for_update()` to read who earned the point before taking it back. Two people tapping the same item at once cannot both be paid, and a mis-tap can be undone without punishing the wrong person.

**Item behaviour is composed, not repeated.** Abstract `CheckableItem` and `RecurringItem` models carry the checking and recurrence logic; each item type is just the combination it needs (a grocery item is both, a list entry is only checkable, a pantry product is neither). A shopping list is still a mission with items attached, not a different kind of mission, so one `Task` table keeps cross-type queries, pagination and per-mission comms working.

**The pantry reacts to a change, not to a state.** A product goes on the shopping list when its stock *crosses* into low, not whenever it *is* low — so deleting it from the list sticks until the stock goes back up and drops again. Stock changes lock the row, so two people tapping − at once trigger the crossing exactly once. When a product runs low again, its old list line is put back rather than duplicated, and whoever bought it last time keeps their point.

**Creating a unit is one function.** `create_unit()` makes the unit, its commander and its shared lists in a single transaction, and every entry point — sign-up, the unit form, tests — goes through it. A unit can never exist without its grocery list.

**Read state is a pointer, not a row per message.** `ConversationRead` stores one `last_read_at` per user per conversation; unread status is computed by comparing message timestamps against that pointer.

**"Today" belongs to the user.** Each avatar stores a time zone, activated per request by middleware. "Due today" and overdue checks are computed in the user's own zone, with tests pinned to the awkward hour just after midnight.

### Deploy

**Urgency comes from items.** A chore rota is urgent because a chore is due, a pantry because a product is low; a standing order because of its due date. Priority sorts within each level, and a critical mission is actionable even without a deadline. All of it is defined once and shared by the map, the noticeboard, the operative's objective and the Debrief dashboard, so the modes cannot disagree.

**Locations are code, not data.** Each location is a label, the mission types it holds, the type it creates (if any), and optionally an interior template. No migrations are needed to add or rename one, and a coverage test guarantees that every active mission appears in exactly one location — it reads the model's type choices, so adding a new mission type without a location fails the test.

**Two queries for the whole map.** Counts and urgency states for every location come from a single query using conditional aggregation (`Count(..., filter=...)`). Hover previews are a second query that labels each mission with its location using `CASE WHEN`. The page's total query count is pinned by a test.

**SVG, not canvas.** Every building is a real link: the map works without JavaScript, is keyboard-navigable, and is readable by screen readers. Hover previews use CSS `:has()` rather than JavaScript, and animations respect `prefers-reduced-motion`.

**The map is a text file, and the tests check it.** The base is a grid of characters (`=` road, `T` forest, `H` HQ…). Tests verify that every row has the same width, every location has exactly one building, and every building can be reached from HQ along the roads. The operative's route uses breadth-first search — on a small, unweighted grid it finds the shortest path with less code than A*.

**Lists update in place, and still work without JavaScript.** Every list action is a plain form that works on its own; a small script intercepts them with one delegated listener and swaps in the updated list. Pages showing several lists at once — the supply depot, the shopping run — refresh all of them after each action, since buying milk changes both the shelves and the list.

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

Users created with `createsuperuser` skip sign-up, so they don't get a personal base automatically. Create one from the shell:

```powershell
python manage.py shell -c "from django.contrib.auth import get_user_model; from taskForce.units.services import create_personal_unit; create_personal_unit(get_user_model().objects.get(username='admin'))"
```

Tests:

```powershell
python manage.py test
```

## What's next

- **A barracks floor plan.** Chores placed room by room on a plan of the house, built on the same engine and tests as the base map; rooms glow when something is due, and opening one shows its chores.
- **A workout calendar**, attaching training sessions to days of the week.
- **A budget per unit**, with optional limits per category (groceries first), prices on grocery items, spending recorded as a ledger, and a unit settings page around it.
- **A guided tour** for first-time visitors, as a short sequence of slides.
- **Original artwork** for the map, replacing the placeholder sprites.

---

Built by Kiara as a portfolio project.
