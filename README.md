# Task: Force!

A task manager for people who find it hard to keep every part of their life in one place.

Most to-do apps assume you already know how to organise. Task: Force! is built for the opposite case — the shopping you forgot, the workout you meant to do, the flat that needs cleaning, the errand you promised someone else. It keeps all of it in one system, and it offers two ways to look at that system: a plain, text-based mode for getting things done, and a game-like mode for when a list is not enough motivation.

Everything is framed as a military operation. Tasks are **missions**, groups are **units**, messages are **comms**, money is **funds**, and your work earns your avatar **intel points**.

> **Status: v2 complete.** Shared household lists with a personal base for every user; a pantry that refills the shopping list by itself; a barracks floor plan for chores; a weekly training planner; unit settings with command hand-over and member management; and a monthly budget per unit and per mission. Next: a guided tour and calorie estimates for workouts — see [What's next](#whats-next). The v1 code is preserved under the `v1.0` tag.

![Deploy mode: the base map, with the operative standing at the most urgent location](docs/deploy-map.png)

## Two modes

**Debrief** — the overview. A dashboard across every unit you belong to: what needs action now, what is due soon, your active missions, and a status line for each of your bases ("6 to buy · 2 duties pending · 1 low"), each part linking straight to that list. Quick add creates a standing order in one field; the full briefing form is one link away. A filterable, paginated mission log, and a **shopping run** page that gathers everything still to buy across all your bases on one screen.

**Deploy** — the visual view. One base at a time: your personal base, or the base of a unit you belong to, switched from the nav. Its missions are laid out on a tile map of a military base, in the style of classic strategy-game adventure maps. Each building is a place where a kind of work happens: the supply depot for groceries and the pantry, the training ground for workouts, the barracks for chores, the rec room for lists, and HQ for standing orders. Deploy is a second rendering of the same data, not a separate app — the same missions appear in both modes.

The map is designed to answer one question without reading anything: **where should I go, and how urgently?**

- The whole base fits on screen, without scrolling.
- Buildings with nothing to do fade into fog.
- A building with something due later today glows amber; one that needs action pulses rust — an overdue standing order, a chore that is due again, a pantry product running low, a drill planned for today. A critical mission raises a pennant. Counts sit on each building as badges.
- Hovering or focusing a building previews its three most urgent missions.
- Your operative stands at the location with the most urgent mission, with a marching route from HQ, and the same objective is written out in text under the map, next to the unit's funds for the month.
- Training is personal: on a unit's base it is off limits, and says so.

Buildings open what they hold:

- **HQ** and the **rec room** show a noticeboard of missions grouped by urgency — action required, today, next 48 hours, later, no deadline — with a quick-add form.
- The **supply depot** opens onto two panels side by side: the **shelves** and the **shopping list**.
- The **barracks** opens onto a floor plan of the house. Each room shows how many chores are due; the operative walks from the door to the most urgent one, and choosing a room lists its chores.
- The **training ground** opens onto a Monday-to-Sunday planner: today highlighted, rest days marked, drills added to a day from an exercise library, and an "unplanned" tray for drills without a day.

Every list inside a building also shows its funds: what was spent this month, against what budget.

## Domain vocabulary

| Term | Meaning |
| --- | --- |
| **Mission** | A single task, belonging to one unit. Has a name, a type, a priority, and optionally a due date, an assignee and a monthly budget. Missions are active or inactive. |
| **Standing order** | A one-off mission with no items ("buy Mom a present"). The only kind of mission that is *accomplished*: doing so earns one point and retires it from the board. |
| **Unit** | A group of users, joined by an invite link, with exactly one **commander**; everyone else is an **operative**. Every user also has a **personal unit** — their lone-wolf base — which no one else can join. |
| **Comms** | Messaging inside group units. Visibility comes entirely from unit membership — there are no direct messages, and personal bases have no comms. |
| **Avatar** | A user's game profile: intel points, time zone, and the unit whose base Deploy is showing. |
| **Intel points** | One point per checked item or accomplished standing order, earned by whoever did it. Unchecking returns the point from the person who earned it, not from whoever unchecks. |
| **Funds** | A unit's or a mission's monthly budget, and what has been spent against it this month. |
| **Location** | A place on the Deploy map. Defined in code, not in the database. |

## Missions and items

Every unit is created with its shared lists already in place: **one grocery list, one pantry and one chore rota**, plus a **workout** on personal bases. Nobody has to create them, and they cannot be deleted or deactivated — if a household doesn't use the pantry, it simply stays empty.

On top of those, anyone can create **standing orders** and **lists** (a watchlist, a packing list) as often as they like, and assign them to someone in the unit.

Items are where the work happens:

- **Checkable items** — groceries, chores, drills, list entries — are ticked off by whoever does them, and each tick is one point. Bought groceries stay visible until someone clears them.
- **Recurring items** — groceries and chores can repeat every N days. A recurring item disappears when it is done and comes back on its own when it is due again; "Need it now" brings it back early (more milk because guests are coming).
- **Weekly items** — drills belong to a day of the week. A drill counts as done once it is ticked on or after its day; future days stay locked, and a late tick still counts.
- **Chores** belong to a room, which places them on the barracks floor plan.
- **Drills** come from an exercise library: twenty shared starter exercises, plus your own, created the first time you type a new name.
- **Pantry products** are counted, not checked, with −/+ buttons. A product that runs out — or drops to an optional "low at" level, for things you want to buy before they are gone — **adds itself to the shopping list**, with the amount needed to restock. Buying it puts that amount back on the shelf; "Low" puts it on the list straight away.

## Units

A unit's **settings page** is open to every member — read-only for operatives — and holds everything that changes the unit: its name, its invite link (copy or reset), its members, and the danger zone. Every destructive action asks first, in a dialog on the same page rather than a separate confirmation page.

- The commander can **hand over command** or **remove a member**. Removing someone can also reset the invite code, so old links stop working; it is ticked by default.
- Operatives can **leave**. The commander can't, until they hand over command; a commander alone in their unit dissolves it instead.
- **Deleting your account** is blocked while you command a unit with other members — the profile page lists those units and links to their settings. Units you command alone are dissolved with your account, and the confirmation dialog says which ones.

## Budget

Each unit can set a **monthly budget**, and each mission can have its own. Spending is logged in a line — an amount and a date — from the unit page, any mission page, or the buildings on the map, and the funds line updates itself:

> **Funds** · €1,000 of €12,000 expended · **€11,000 remaining**
> **Funds** · €13,500 of €12,000 expended · **€1,500 overrun** *(in red)*

A mission without a budget of its own shows the unit's funds, labelled as such, so the figure is never mistaken for that mission's spending. Spending on a mission always counts towards the unit's total. Anyone in the unit can set budgets and log spending; an entry can be deleted by whoever logged it, or by the commander.

## Stack

- **Django** with **PostgreSQL**
- **Vanilla JavaScript** — no frontend framework, by choice
- **SVG** for the maps
- Deployed on **Render**
- Fonts: Barlow Condensed and Share Tech Mono; an olive and khaki palette driven by CSS variables

## Apps

| App | Responsibility |
| --- | --- |
| `accounts` | Users, avatars, profiles, account deletion, per-user time zone middleware |
| `common` | Mode chooser, Debrief dashboard, Deploy map and the map engine, location pages and interiors, shared templates and dialogs, context processors |
| `tasks` | Missions and their items: models, views, forms, filtering, locations, urgency rules, the exercise library, the shopping run |
| `units` | Units, memberships and roles, unit settings, command hand-over, invites, the active-unit switcher, unit creation |
| `budget` | Spending, monthly budgets, funds calculations |
| `comms` | Conversations, messages, read state |

## Design notes

A few decisions that are easy to miss from the code alone.

### Data and permissions

**Permission lives in the queryset.** Every view resolves its objects through `Task.objects.visible_to(user)` or an equivalent filter, rather than trusting the page that linked there. Since every mission belongs to a unit, visibility is a single rule — "missions of units I am a member of" — written as an `Exists` subquery rather than a join, so missions are never duplicated and no query needs `DISTINCT`. Commander-only actions start from one `commanded_by(user)` query, which keeps the user and the role on the same membership row.

**The database enforces the rules that matter.** One grocery list, pantry, chore rota and workout per unit, and exactly one commander per unit, are conditional unique constraints. Shared lists can never be deactivated, due dates only exist on standing orders and lists, only standing orders can be accomplished, a grocery item linked to the pantry cannot also be recurring, and amounts and budgets must be positive — all check constraints. The views hide the buttons; the database is the guarantee.

**Points are claimed, not computed.** Checking an item is a conditional `UPDATE ... WHERE is_checked = false` plus an `F()` increment on the checker's points, inside one transaction. Unchecking locks the row with `select_for_update()` to read who earned the point before taking it back. Two people tapping the same item at once cannot both be paid, and a mis-tap can be undone without punishing the wrong person.

**Item behaviour is composed, not repeated.** Abstract `CheckableItem`, `RecurringItem` and `WeeklyItem` models carry the checking, recurrence and weekly logic; each item type is just the combination it needs (a grocery item is checkable and recurring, a drill is checkable and weekly, a pantry product is neither). A shopping list is still a mission with items attached, not a different kind of mission, so one `Task` table keeps cross-type queries, pagination and per-mission comms working.

**The pantry reacts to a change, not to a state.** A product goes on the shopping list when its stock *crosses* into low, not whenever it *is* low — so deleting it from the list sticks until the stock goes back up and drops again. Stock changes lock the row, so two people tapping − at once trigger the crossing exactly once. When a product runs low again, its old list line is put back rather than duplicated, and whoever bought it last time keeps their point.

**Creating a unit is one function.** `create_unit()` makes the unit, its commander and its shared lists in a single transaction, and every entry point — sign-up, the unit form, tests — goes through it. A unit can never exist without its grocery list.

**A unit can't lose its commander.** The commander can't leave or be removed, and can't delete their account while others depend on them; command has to be handed over first. Units they command alone are deleted in the same transaction as the account, so no unit is ever left with nobody in it.

**Read state is a pointer, not a row per message.** `ConversationRead` stores one `last_read_at` per user per conversation; unread status is computed by comparing message timestamps against that pointer.

**"Today" belongs to the user.** Each avatar stores a time zone, activated per request by middleware. "Due today", overdue checks, the training week and the date of a purchase are computed in the user's own zone, with tests pinned to the awkward hour just after midnight.

### Budget

**Spending is a ledger, not a total.** Each purchase is a row; "spent this month" is a sum. An editable total would need resetting every month, would lose a purchase whenever two people saved at once, and would drift away from the missions' own figures. With rows, the month resets by itself, simultaneous entries both count, a typo is fixed by deleting one line, and a mission's spending is automatically part of the unit's.

**Money is never a float.** Amounts and budgets are `DecimalField`s, and positive by constraint; an empty budget means "none set" rather than zero.

**Months are a date range.** A month's spending is `spent_on >= the 1st and < the 1st of next month`, not an `EXTRACT(MONTH ...)`, so the query can use the `(unit, spent_on)` index. The calculations live in one place — a small `Funds` value object built by service functions — and every page only displays the result.

**A deleted mission keeps its money.** Spending points to its mission with `SET_NULL` and to its unit directly, so deleting a mission never rewrites the month's totals.

### Deploy

**Urgency comes from items.** A chore rota is urgent because a chore is due, a pantry because a product is low, a workout because a drill is planned for today; a standing order because of its due date. Priority sorts within each level, and a critical mission is actionable even without a deadline. All of it is defined once and shared by the map, the noticeboard, the operative's objective and the Debrief dashboard, so the modes cannot disagree.

**Locations are code, not data.** Each location is a label, the mission types it holds, the type it creates (if any), and optionally an interior template. No migrations are needed to add or rename one, and a coverage test guarantees that every active mission appears in exactly one location — it reads the model's type choices, so adding a new mission type without a location fails the test.

**Few queries for the whole map.** Counts and urgency states for every location come from a single query using conditional aggregation (`Count(..., filter=...)`). Hover previews are a second query that labels each mission with its location using `CASE WHEN`. The page's total query count is pinned by a test.

**SVG, not canvas.** Every building is a real link: the map works without JavaScript, is keyboard-navigable, and is readable by screen readers. Hover previews use CSS `:has()` rather than JavaScript, and animations respect `prefers-reduced-motion`.

**The maps are text files, and the tests check them.** The base and the barracks floor plan are grids of characters (`=` road, `T` forest, `#` wall, `+` door…), shared by one small map engine. Tests verify that every row has the same width, every location or room has exactly one marker, and every one of them can be reached on foot. The operative's route uses breadth-first search — on a small, unweighted grid it finds the shortest path with less code than A*.

**Lists update in place, and still work without JavaScript.** Every list action is a plain form that works on its own; a small script intercepts them with one delegated listener and swaps in the updated parts of the page. Pages showing several lists at once — the supply depot, the shopping run — refresh all of them after each action, since buying milk changes both the shelves and the list.

**Confirmations are native dialogs.** Dangerous actions open an HTML `<dialog>` holding an ordinary POST form, through one shared partial and one delegated listener. Focus starts on Cancel, so pressing Enter by accident cancels; Escape and a click outside close it. The server still checks every permission — the dialog is a convenience, not a guard.

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

- **Receipts from the shopping run.** When a run is finished, one tap logs the receipt against the grocery list.
- **A guided tour** for first-time visitors, as a short sequence of slides.
- **Calorie estimates** for drills, from standard exercise intensity values and an optional body weight.
- **Budget extras:** splitting costs between members, and a month-by-month history.
- **More artwork** for the barracks furniture.
