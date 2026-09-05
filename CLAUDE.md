# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Working with the user

Mostafa is learning Django and Tailwind. When setting things up, explain rather than do: give **one step at a time**, wait for confirmation, and explain *why* each piece exists before moving on. Only make edits directly when asked to. Verify each step's result before giving the next one.

## Layout gotcha

The project root is nested one level down:

```
Documents\calen\            <- session cwd; contains nothing but the folder below
└── calen\                  <- ** project root: manage.py, package.json, static\, templates\ **
    ├── calen\              <- settings package (settings.py, urls.py)
    └── main\               <- the only app
```

`cd` into the inner `calen\` before running anything — every command and every relative path in `input.css` assumes that as the working directory.

## Commands

Development needs **two terminals**, both in the project root:

```bash
npm run tw                    # Tailwind CLI in --watch mode; leave running
python manage.py runserver    # dev server
```

`output.css` is only regenerated while the watcher runs. If styles look stale after editing templates, the watcher is probably off.

```bash
python manage.py test                              # all tests
python manage.py test main.tests.ClassName.test_x  # a single test
python manage.py makemigrations && python manage.py migrate
python manage.py createsuperuser
```

Translations (see **Internationalization** below):

```bash
python manage.py makemessages -l ar --ignore=node_modules   # rescan sources -> .po
python manage.py compilemessages                            # .po -> .mo, what Django loads
```

Environment: Django 6.0.6 on Python 3.13, SQLite (`db.sqlite3`), Tailwind v4.3.3 via npm. `requirements.txt` exists (Django alone) and there is no virtualenv. Git repo with remote `origin` → https://github.com/externoo/calen.git, **public** since 2026-09-04. The GitHub CLI (`gh`) is installed machine-wide via winget and authenticated as `externoo`.

## Environment variables

`settings.py` reads its secrets from the environment and **refuses to import without them**:

```python
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    raise ImproperlyConfigured("DJANGO_SECRET_KEY is not set. ...")
```

Locally they come from `.env`, parsed by a hand-rolled loader at the top of `settings.py` — no `python-dotenv`, which is why `requirements.txt` needs only Django. The loader uses `os.environ.setdefault`, so a real environment variable always wins over the file, and the whole block no-ops where no `.env` exists.

`.env` is gitignored and has never been committed; `.env.example` documents the three names (`DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`). **Consequence: any environment without a `.env` — CI, a deploy — must supply `DJANGO_SECRET_KEY` itself, or every management command dies before Django starts.**

## Tailwind ↔ Django wiring

Tailwind knows nothing about Django. Two independent chains have to both be intact, and each fails differently:

**Generation** — `static\src\input.css` (hand-written, ~4 lines) declares `@source` paths. The CLI scans those paths for class-name strings and writes `static\css\output.css` (generated; never edit).

**Serving** — `templates\base.html` links it via `{% static 'css/output.css' %}`; `STATICFILES_DIRS = [BASE_DIR / "static"]` is what lets Django find the project-level `static\` folder at all (its default is app-level `static\` only).

Consequences worth internalizing:

- **A new app's templates are invisible to Tailwind** until an `@source` line is added to `input.css`. Symptom: page is styled (base.html's classes work) but the new classes silently do nothing — no error.
- **Restart the watcher after editing `input.css`.** It watches templates, not its own config.
- **Dynamic class names never work**: `class="bg-{{ color }}-500"` generates nothing, because Tailwind scans template *text* and never executes Django code. Pass complete class strings from the view.
- **Customization lives in `input.css`** under `@theme { --color-brand: ...; }`. Tailwind v4 has no `tailwind.config.js`; ignore any tutorial that starts with `npx tailwindcss init`.

## Templates

`base.html` is project-level at `templates\base.html` (registered via `TEMPLATES[0]['DIRS']`), deliberately moved out of `main\` because it is shared site-wide. Pages extend it as `{% extends "base.html" %}` — no `main/` prefix.

App-specific pages stay app-level and keep the namespace folder: `main\templates\main\home.html`, referenced as `"main/home.html"`. `DIRS` is searched before app folders, so a project-level file of the same name overrides an app's (including Django admin's own templates).

All three template roots — `templates\`, `main\templates\` and `accounts\templates\` — are listed as `@source` paths in `input.css`.

## URLs

Each app owns a `urls.py`, pulled in from `calen\urls.py` — which imports no app code at all any more, only names modules as strings:

```python
path('accounts/', include('accounts.urls')),
path('', include('main.urls')),
```

**`main\urls.py` deliberately has no `app_name`**, so `home` and `day` stay un-namespaced; `accounts\urls.py` has one. The asymmetry is intentional and load-bearing: `app_name` does not *offer* a namespace, it **requires** one. Adding it to `main` would break `{% url 'home' %}` in the templates, `redirect("day", ...)` at the end of `main\views.py` and `reverse("day", ...)` in `DayViewTests` — all at once, all with `NoReverseMatch`. Namespacing `main` later is a deliberate change that updates every call site in the same commit.

A root-mounted include (`path('', include(...))`) goes **last** in `urlpatterns`: it is the broadest pattern, and a greedy pattern placed first shadows everything below it.

## Auth (the `accounts` app)

`accounts` owns the custom user and the whole login/registration flow.

- `CustomUser(AbstractUser)` with a UUIDv7 PK, set as `AUTH_USER_MODEL`. `uuid7` lives in `main\utils.py` — `accounts` imports it from there, so `main` is a dependency of `accounts`, not the other way round.
- Routes live in `accounts\urls.py`, mounted at `accounts/` via `include()`, with `app_name = "accounts"`. **Because of that namespace, templates must write `{% url 'accounts:login' %}`** — a bare `{% url 'login' %}` raises `NoReverseMatch`. `main`'s own `home`/`day` names are un-namespaced.
- Login/logout are Django's built-in `LoginView`/`LogoutView`; only `template_name` is supplied. Registration is ours, because Django ships no signup view: `CustomUserCreationForm` (subclasses `UserCreationForm` and retargets `Meta.model` to `CustomUser` — the stock form is bound to `auth.User`) plus a `CreateView`.
- `LOGIN_URL` / `LOGIN_REDIRECT_URL` / `LOGOUT_REDIRECT_URL` are set in settings. `LOGIN_REDIRECT_URL` must not be left at its `/accounts/profile/` default, which doesn't exist here.

### The whole site is login-only

`django.contrib.auth.middleware.LoginRequiredMiddleware` is in `MIDDLEWARE`, **after** `AuthenticationMiddleware` (it reads `request.user`, which the earlier one sets). This inverts the usual default: every view is protected, and you opt out with `@login_not_required`.

Consequences:

- **A new public view must be decorated** `@login_not_required`, or `@method_decorator(login_not_required, name="dispatch")` for a CBV. `RegisterView` carries this — without it nobody could ever sign up.
- Django's own auth views (`LoginView`, `LogoutView`, the password-reset set) and `AdminSite.login` already carry the decorator upstream, so they keep working untouched.
- The redirect preserves `?next=`, so a deep link survives the login round-trip.

### Two gotchas that cost time

- **Logout is POST-only** since Django 5.0. A plain `<a href>` gives 405; `base.html` uses a small `<form method="post">` with `{% csrf_token %}`.
- **`reverse_lazy` for class attributes, `reverse` inside methods.** A class body runs at import time, while the URLconf is still being built — plain `reverse()` there crashes at startup.

## Form styling

Django renders form widgets, so Tailwind classes can't be added in the template. Rather than fight that in Python (which would also mean subclassing Django's `AuthenticationForm` just to add CSS classes), form controls are styled by **element selector** in a `@layer components` block in `input.css` — `input[type=...]`, `form p`, `form label`, `.helptext`, `.errorlist`. One rule covers every form, including the ones Django owns.

`components` loses to `utilities` in Tailwind's cascade, so a utility class in the markup still overrides these defaults.

**Failure mode worth knowing:** when the Tailwind CLI hits an error it aborts the build and leaves the previous `output.css` in place. The site then looks completely normal, just unchanged — nothing in the browser tells you the build died. If a style edit seems to do nothing, read the watcher terminal.

## Internationalization (i18n / l10n)

English and Arabic, chosen per request by `LocaleMiddleware` and remembered in a cookie. `LANGUAGES` is a deliberate two-entry allowlist — Django's default is every language it ships, so a browser advertising `de` would otherwise get a half-German admin.

Requires **GNU gettext** (`xgettext`, `msgfmt`) on `PATH`; `makemessages` and `compilemessages` are thin wrappers around those binaries and Windows ships neither. Installed here at `AppData\Local\Programs\gettext-iconv\bin`.

There is **no `USE_L10N`** — removed in Django 5.0. Locale-aware date and number formatting is always on and cannot be switched off.

### The pipeline, and where it breaks

`.po` (hand-edited, committed) → `compilemessages` → `.mo` (binary, **also committed**) → loaded at runtime. **Django never reads the `.po`.** Editing translations without recompiling is the single most common "my translations don't work" cause, and it fails silently — old `.mo`, or none, and the site serves English.

`django.mo` is committed for the same reason as `output.css`: nothing generates it at deploy time. Same drawback too — it can go stale silently, and CI checks neither. `*.mo binary` in `.gitattributes` stops `* text=auto` guessing and corrupting it with an eol conversion.

`makemessages` **must** be run with `--ignore=node_modules`. Its default ignore list is only `CVS`, `.*`, `*~`, `*.pyc`, so without the flag it walks every Tailwind dependency and can scrape third-party strings into our catalogue with source references pointing into `node_modules`.

### Marking strings

`{% translate "..." %}` for literals, `{% blocktranslate %}` for anything containing a variable — the latter hands the translator a whole sentence with a named slot instead of a fragment that hardcodes English word order.

- **`{% load i18n %}` is required in every template that uses the tags**, including ones that `{% extends %}` a template which already loads it. `{% load %}` is not inherited. Symptom: `Invalid block tag 'translate'`.
- `blocktranslate` accepts only bare variable names inside the block — no attribute lookups, filters or tags. Bind first: `{% blocktranslate with year=date.year %}`.
- A placeholder (`%(year)s`) must survive verbatim into the translation. `#, python-format` makes `msgfmt` enforce it, so a mangled one fails at compile rather than as a runtime `KeyError`.
- **A missed marking never fails.** It renders as English forever, with nothing anywhere reporting it. The `.po` file is the audit: every `#:` line is a marked string, so what's absent is what you forgot.
- Marking is **static** — `xgettext` reads source text. `{% translate some.variable %}` is valid syntax that puts no `msgid` in the catalogue and so never translates.
- Identical strings collapse into one `msgid` with several `#:` references. When the same English word needs different translations by context, the tool is `pgettext("context", "text")`.
- Model `verbose_name`s already use `gettext_lazy`, so they are collected automatically — as are the `LANGUAGES` names in `settings.py`. Form labels from Django's own `AuthenticationForm`/`UserCreationForm` are translated upstream and need nothing.

### `calendar.month_name` is a trap

Python's stdlib `calendar` reads the **C locale**, which Django never sets. `month_name[1]` is `"January"` in every language, silently. Same for `day_abbr`.

The fix is to route through Django's own catalogue, which already contains all nineteen names in Arabic: the view passes a `date` object per month and the template formats it with `{{ month.date|date:"F" }}`, and weekday headers come from `django.utils.dates.WEEKDAYS_ABBR` (a dict keyed `0`=Monday, values `gettext_lazy`). **Nineteen translations for free, and none of them in our `.po`.**

`WEEKDAYS_ABBR` is rotated by `(firstweekday + offset) % 7` rather than hardcoded, so the header row cannot drift out of step with `Calendar(firstweekday=...)`.

### Overriding Django's own translations

Django's Arabic catalogue *transliterates* the Latin month names (`يناير`, `فبراير`) — the spellings used in Egypt and the Gulf, but not Arabic words. `main\dates.py` overrides all twelve with the Syriac-origin Levantine names (`كانون الثاني`, `شباط`, `آذار`…).

The mechanism is catalogue precedence: **`LOCALE_PATHS` is searched before an app's `locale\` and before Django's own**, so an entry with the same `msgid` wins. Two consequences worth holding on to:

- **It is project-wide, not local to the calendar grid.** The `date` filter's `F`, the admin's `date_hierarchy`, anything that renders a month name — all pick it up. `day.html`'s `{{ date|date:"l, j F Y" }}` was never touched and shows `آذار` too.
- **The `msgid`s must be referenced from real source** or `makemessages` marks them obsolete (`#~`) on the next rescan and the override silently evaporates. That is the whole reason `main\dates.py` exists as a module with twelve `gettext_lazy` calls rather than entries typed straight into the `.po`.

This is the general escape hatch for *any* Django string whose stock translation is wrong: mark the same `msgid` in our own source and translate it.

### The switcher

`set_language` is mounted at `i18n/setlang/` and wrapped: **`login_not_required(set_language)`**. Django exempts its own auth views and the admin login from `LoginRequiredMiddleware` but *not* this one, so the documented `include('django.conf.urls.i18n')` wiring produces a switcher that redirects anonymous visitors to the login page — exactly where a non-English speaker first needs it. Applying the decorator by call rather than by `@` is the only option for a view we don't own.

It is a POST form with `{% csrf_token %}`. `set_language` ignores GET by design (it changes how the whole site renders, so a link prefetch must not trigger it) — same reasoning as POST-only logout.

`LANGUAGE_CODE` is `'en'`, not `'en-us'`, so it matches the `LANGUAGES` key. Both work at runtime via Django's regional fallback, but the switcher compares the active code against those keys, and `'en' != 'en-us'` would leave the dropdown never marking the current language `selected` — with no error.

### RTL

`<html>` carries `lang` and `dir` driven by `{% get_current_language_bidi %}`, which reads `settings.LANGUAGES_BIDI` (ships with `ar`, `he`, `fa`, `ur`) rather than guessing from the code — so a future RTL language needs no further edit. `lang` matters independently of `dir`: screen-reader voice, hyphenation, font fallback.

Nothing else needed changing, because the project uses **no physical-direction utilities**. `flex`, `grid`, `justify-between`, `text-center` and `mx-auto` all follow `direction` on their own; only physical properties like `margin-left` don't.

**Keep it that way.** Prefer the logical utilities — `ms-`/`me-` over `ml-`/`mr-`, `ps-`/`pe-` over `pl-`/`pr-`, `text-start`/`text-end`, `border-s`/`border-e`, `start-`/`end-`, and `gap-x-` over `space-x-` (which uses physical margins). They compile to CSS logical properties and flip themselves. For the rare thing that must *not* flip, Tailwind has `rtl:` and `ltr:` variants.

Arabic has **six plural forms**; Django already wrote the correct `Plural-Forms` header into the `.po`. The first `{% blocktranslate count %}` will therefore have `msgstr[0]`…`msgstr[5]`. This is the argument against ever building plurals by string concatenation.

Windows console detail: printing Arabic from a script dies with `UnicodeEncodeError: 'charmap' codec` because the console defaults to cp1252. `PYTHONIOENCODING=utf-8` fixes it. Nothing to do with the app.

## Admin

Both models are registered, in the two different spellings — deliberately, since each is the right one for its case.

**`CustomUser` uses the stock `UserAdmin`** (`admin.site.register(CustomUser, UserAdmin)`), with nothing subclassed. This is not optional politeness: `password` is an ordinary `CharField` as far as introspection can see, so a plain `ModelAdmin` renders it as an editable text box and saves whatever you type as the "hash" — permanently locking that account out. `UserAdmin` swaps in `UserChangeForm`, whose `ReadOnlyPasswordHashField` is `disabled=True` (so a POST to it is ignored, not merely greyed out) and renders a truncated `safe_summary()` of the hash plus a link to `../password/`. It also brings `add_fieldsets`, so the *Add user* screen asks only for username + two password boxes.

`UserAdmin` was written against `auth.User`, but `ModelAdmin.get_form()` rebuilds the form against `self.model`, and `CustomUser` only *adds* an `id` field — so every field its `fieldsets` names still exists.

**`Commitment` uses `@admin.register(Commitment)` on a `ModelAdmin` subclass**, because it needs configuration: `list_display`, `list_filter`, `search_fields`, `date_hierarchy = "date"` (the year→month→day drill-down; the thing that makes a calendar app's admin usable), `autocomplete_fields = ("user",)` and `readonly_fields = ("created_at",)`.

Worth knowing:

- The decorator is **side-effect-only** — it calls `admin_site.register(...)` and returns the class untouched, so it is exactly equivalent to a bottom-of-file `admin.site.register(Commitment, CommitmentAdmin)`. Contrast `@method_decorator(...)` on `RegisterView`, which *replaces* the class.
- Registration happens **at import time**: `django.contrib.admin`'s app config auto-imports each app's `admin` module at startup. That is why the code must live in `admin.py`, and why a syntax error there takes down the whole admin.
- **`autocomplete_fields` couples the two admin classes.** It works only because the *referenced* admin defines `search_fields`, which `UserAdmin` does. Registering `CustomUser` without one raises `admin.E040`.
- **`python manage.py check` runs the admin checks** without a browser or server, and returns a stable `admin.Exxx` code that is searchable in the docs. Reach for it first when the admin misbehaves. (`runserver` runs the same checks, so a bad admin config stops the server outright rather than failing per-request.)
- Tuple gotcha, hit once already: `("text",)` is a one-tuple; `("text,")` is a string and yields `admin.E126`. Parentheses don't make a tuple — the comma does.

## Git workflow

Three kinds of branch, each with a different job:

- **`main`** — always deployable. Nothing is committed here directly; changes only *arrive* by merge. This is the branch CI will eventually gate.
- **`develop`** — the integration branch. Finished features land here first, so breakage surfaces before it reaches `main`.
- **`feature/<name>`** — one per task, cut from `develop`, merged back into `develop`, then deleted. Short-lived and disposable.

Both long-lived branches exist locally and on `origin`. Feature branches are created, pushed, PR'd, and deleted per task.

The loop:

```bash
git switch develop && git pull          # never branch from a stale develop
git switch -c feature/x
git add <files>                          # stage one coherent change at a time
git commit -m "subject" -m "body"        # imperative subject; body says *why*
git push -u origin feature/x             # -u only the first time
gh pr create --base develop --fill       # base must be develop; gh defaults to main
gh pr merge <n> --merge --delete-branch  # switches, pulls and deletes both copies
```

Releasing to `main` is a second PR, and it has a tail:

```bash
gh pr create -B main -t "..." -b "..."   # --fill titles it "develop" on multi-commit PRs
gh pr merge <n> --merge                  # NO --delete-branch — develop is long-lived
git merge origin/main && git push        # back-merge, from develop
```

**The back-merge is not optional.** Merging `develop` into `main` creates a merge commit that exists on `main` only, so `develop` is immediately one commit behind. Combined with "require branches to be up to date", the *next* release PR then opens as `BEHIND` and refuses to merge. Doing it right after each release keeps the branches level and the next PR `CLEAN`; skip it and use GitHub's **Update branch** button instead. Both times it has been a fast-forward, since `develop` had nothing `main` lacked.

Things worth remembering:

- **Creating a branch and publishing it are separate acts.** `git switch -c` is purely local; nothing reaches GitHub until `git push -u`. In `git branch -vv`, a branch with no `[origin/...]` bracket has never been pushed.
- **Uncommitted changes are not attached to a branch.** They live in the working tree, shared by every branch, and follow you across `git switch`. That is why in-progress work can be branched *after* the fact.
- **Squash when the branch is messy, merge-commit when it's curated.** A merge commit has two parents and keeps the fork visible in `git log --graph`; squash flattens it to one commit. Rebase-and-merge rewrites SHAs, so the local copies stop matching.
- **`git branch -d` is the safe delete** — it refuses if the commits survive nowhere. `-D` forces. If `-d` warns "merged to `refs/remotes/...` but not yet merged to HEAD", it means the local branch you're standing on hasn't pulled the merge yet; harmless, but pull first and the warning goes away.
- **`git fetch --prune`** deletes remote-tracking refs for branches GitHub no longer has. Without it, deleted branches linger locally as ghosts.

### The Tailwind watcher breaks `git pull`

`output.css` is committed but regenerated constantly, so the watcher leaves it dirty. A pull that touches it aborts with *"Your local changes would be overwritten by merge."* Stop the watcher (Ctrl-C) before pulling or switching branches. If it already happened, `git restore static/css/output.css` throws the local copy away — safe *only* because that file is a build artifact.

### Line endings

`.gitattributes` pins the policy **per repository** instead of per developer. `core.autocrlf=true` (Git for Windows' default) happens to do the right thing on this machine, but nothing in the project required it — a clone where it is off would start committing CRLF into history. The committed file removes that dependency.

`* text=auto` is the engine: LF in the repository, native endings in the working tree. On top of it, `*.sh eol=lf` (a CRLF shell script fails on Linux with `bad interpreter: /bin/bash^M`, and CI is Linux), `*.bat`/`*.cmd eol=crlf`, a `binary` block for image/font/sqlite extensions, and `static/css/output.css linguist-generated=true` — which collapses that file in GitHub PR diffs and drops it from the repo's language stats, so the noisiest file in the tree stops dominating both.

Adding this was safe **because the index was already all-LF** (`git ls-files --eol` showed no `i/crlf`). Had it not been, the change would have started with `git add --renormalize .` and a diff touching every line of every file. Check first; `git add --renormalize .` staging nothing is the proof there is no churn. `git check-attr text eol linguist-generated -- <path>` shows what the rules actually resolve to for a given file, which is the verification step worth not skipping.

**`warning: LF will be replaced by CRLF` still appears, and that is correct** — it is the checkout conversion doing its job. Silencing it would mean `* text=auto eol=lf`, which is a bad trade here: the editor on Windows saves CRLF by default, so files would show as modified on every save.

## CI

`.github\workflows\ci.yml` — the path is literal; GitHub scans `.github\workflows\` and ignores YAML anywhere else. The file's presence in the repo *is* the configuration, there is nothing to register.

It runs on `push` and `pull_request` (both: `push` gives feedback on feature branches, `pull_request` tests the *simulated merge* into the base, which is what branch protection gates on), on `ubuntu-latest`, with Python 3.13 — then `pip install -r requirements.txt`, `manage.py check`, `manage.py test`. Runs take ~20s.

Things that are the way they are on purpose:

- **`DJANGO_SECRET_KEY` is set as a job-level `env:` with a literal dummy value.** Required at all — see **Environment variables** above; without it both steps die on import. A literal, *not* a repository secret: the key only signs sessions against a throwaway in-memory test database, and repo secrets aren't exposed to pull requests from forks, so a secret would make the workflow fail for outside contributors.
- **The required check is named `test`, not `CI`.** `CI` is the workflow (`name:`); the check GitHub reports is the **job**, and the job has no `name:` key so it inherits the job id. Searching for `CI` in the branch-protection check picker finds nothing.
- **`check` and `test` are separate `run:` steps.** Separate steps get separate ✓/✗ rows, so the GitHub summary says *which* failed without opening a log. Steps abort the job on a nonzero exit, so a broken config stops before `test` floods the log with hundreds of errors sharing one root cause. Exit status is the entire interface — GitHub never parses output.
- **No `npm`/Tailwind step.** `output.css` is committed, so it is an *input* after checkout, not something CI must produce. Nothing under test reads it: `{% static %}` only builds a URL string and never opens the file, so the CSS could be deleted and all tests would still pass. Adding `npm ci` would import Node drift, registry outages and ~30s per run — failure modes uncorrelated with correctness, on what is now a *mandatory* merge gate. A red build nobody trusts is worse than no build.
- **Action versions are floating major tags** (`@v5`, `@v6`). Majors are where breaking changes live, which is exactly why the Node 20 → 24 runner deprecation needed a manual bump — the pin working correctly, not failing. `@main` would break unpredictably; a full SHA pin is stricter (and the right call for security-sensitive repos) at the cost of manual patch bumps.

Worth knowing: **`output.css` is not rebuilt or verified by CI**, so a stale one — edited templates with the watcher off — merges silently. The check for that would be building it and `git diff --exit-code static/css/output.css`; it needs a `.gitattributes` first or CRLF will make it always differ.

### Branch protection on `main`

A **ruleset** (`main protection`, id `22280700`) rather than classic branch protection — rulesets are the newer system and do the same job.

**The repo was made public on 2026-09-04 specifically to get this.** Rulesets and branch protection are both paywalled on private repos on GitHub Free; the API returns a bare `403 "Upgrade to GitHub Pro or make this repository public"`. The history was audited first — `.env` and `db.sqlite3` were never committed on any branch, and no `django-insecure-` key ever existed, because settings were env-var-based from the initial commit. A side benefit: public repos get unlimited Actions minutes.

What it enforces: `deletion`, `non_fast_forward`, `pull_request` (0 required approvals), and `required_status_checks` on `test` with `strict_required_status_checks_policy` (branch must be up to date, so green describes the *actual* merge, not a stale one).

Every one of these fails **silently** if wrong, which is why they're worth listing:

- **`enforcement` defaults to `Disabled`.** A ruleset with perfect rules and this left alone does nothing at all, with no warning.
- **Target branches start empty.** Set to `~DEFAULT_BRANCH` — survives a rename, unlike a literal `main` pattern.
- **The bypass list must be empty.** Repo admins bypass by default, and there is only one developer here, who is the admin. Anything in that list makes the whole ruleset advisory.
- **Required approvals must be `0`.** GitHub forbids approving your own PR, so `1` is a permanent self-lockout. Same trap, worse: `require_last_push_approval` demands approval from someone *other than the pusher*.
- **Status checks are two separate settings.** Ticking the rule turns the requirement on; the list of *which* checks are required starts empty, and saving with it empty is rejected.
- **`require_extra_approval_for_unattributed_changes` is on** and can't be seen from the UI list. Commits must be attributable to a GitHub account — i.e. `git config user.email` must be verified on `externoo`. All commits to date attribute correctly; committing from a machine with a different email would block the merge.

**Read the ruleset back with `gh api repos/externoo/calen/rulesets/22280700` rather than trusting the UI.** The API shows enforcement, targets, bypass actors and the exact check context (`{"context": "test", "integration_id": 15368}` — 15368 is GitHub Actions), which is how you catch a check name that saved as `CI / test` and would never match.

The ruleset targets `~DEFAULT_BRANCH` only, so **`develop` is deliberately ungated** — CI reports there but cannot block. That is the point of the branch: breakage is allowed to surface somewhere before `main`.

### Reading a PR's state

Two separate fields, answering two different questions. `mergeable` (`MERGEABLE` / `CONFLICTING` / `UNKNOWN`) is mechanical — can git do the merge at all. `mergeStateStatus` is policy — will GitHub permit it. A PR is routinely `MERGEABLE` and `BLOCKED` at the same time.

| `mergeStateStatus` | Meaning | Merge button |
|---|---|---|
| `CLEAN` | Everything required has passed | live |
| `UNSTABLE` | Checks pending or failing, but **none are required** | live |
| `BLOCKED` | A required rule is unsatisfied | dead |
| `BEHIND` | Head lacks the base's latest commits, with the strict policy on | dead |
| `DIRTY` | Real merge conflict | dead |
| `UNKNOWN` | Not computed yet | — |

`UNSTABLE` vs `BLOCKED` on *identical* pending checks is precisely the ungated/gated difference between `develop` and `main` — the clearest way to see the ruleset working. Watch it with `gh pr checks <n> --watch` and `gh pr view <n> --json mergeStateStatus`.

Caveat: PR #5 reported `BEHIND` and then went `CLEAN` with no branch update, which is not fully explained — `UNKNOWN` being served as a stale value while GitHub computed mergeability is the likely culprit, not a verified one.

## Current state

Working: the 2026 calendar grid (`home`), the `day` page with commitment create + list, the full auth flow, the admin for both models, and **English/Arabic translation with RTL** (see **Internationalization** above). `main\models.py` has an abstract `UUIDModel` plus `Commitment` (user FK, date, text, created_at).

`day` handles both GET and POST: `CommitmentForm` (a `ModelForm` on `text` alone) is saved with `commit=False` so the view can attach `user` and `date` before saving, then redirects to itself so a refresh doesn't resubmit. The list comes from `request.user.commitments` — the FK's `related_name`.

`main\tests.py` holds `DayViewTests` — three tests covering the whole `day` contract: the anonymous redirect to login, the logged-in GET (status, template, `date` in context), and the POST (a `Commitment` row is created with the right `user` and `date`, and the response redirects back to the same URL).

Two idioms in there worth reusing. `Commitment.objects.get()` with **no arguments** asserts "exactly one row exists" *and* returns it — `DoesNotExist` for zero, `MultipleObjectsReturned` for more — which only works because `TestCase` wraps each method in a transaction and rolls it back, so every test starts with empty tables and a fresh `setUp` user. And `assertRedirects` doesn't just check the 302: it follows the redirect and asserts the target returns 200, so it proves the destination is real (which needs the client to still be logged in).

The POST test's `user` and `date` assertions are the ones that earn their keep — they are the two fields nothing in the request sets, attached by hand between `save(commit=False)` and `save()`. Nothing asserts on `created_at`: it's `auto_now_add`, so testing it would be testing Django.

`accounts\tests.py` holds `RegisterViewTests` — three more, covering the registration contract: the anonymous GET returns 200 (the `@login_not_required` regression test — lose that decorator and `LoginRequiredMiddleware` bounces every would-be signup to the login page, silently), a valid POST creating exactly one user and redirecting to `accounts:login`, and a mismatched-password POST creating none. Six tests total.

Three things there worth reusing:

- **The POST dictionary is the *form's* field names, not the model's** — `password1`/`password2` exist only on `UserCreationForm`, which compares them and produces the single hashed `password`. Get a name wrong and the form is merely invalid: 200, no user, no error raised.
- **`check_password("...")`, never `assertEqual(user.password, "...")`.** The stored value is a PBKDF2 hash. That one line is what proves the password was hashed rather than saved raw.
- **Assert the error *field*, not its wording.** `assertIn("password2", response.context["form"].errors)` rather than the message text, which contains a typographic apostrophe (U+2019, not ASCII `'`) *and* is translated — so a text assertion would break the moment `LocaleMiddleware` and `.po` files land. And use `objects.count() == 0` to assert absence: the no-argument `get()` idiom raises `DoesNotExist` there, which reports as a test **error** with a traceback rather than a clean failure.

Not done yet:

- **`home` is the only untested view.** `day` and registration are covered; the calendar grid is not — and it now carries the weekday rotation and the per-month `date` objects, so there is more in it to get wrong than there used to be.
- **Nothing tests i18n at all.** Everything was verified by hand in throwaway scripts. The highest-value test is small: POST to `/i18n/setlang/` with `language=ar` as an **anonymous** user, then assert `dir="rtl"` in the response — that one guards the `login_not_required` wrapper on `set_language`, the same silent-lockout class as the `RegisterView` test.
- **No CD.** There is CI but nothing deploys anywhere, and no host has been chosen.
- **CI never checks that `output.css` or `django.mo` is fresh.** Two generated-but-committed files with the same failure mode now: edit the source with the watcher off (or skip `compilemessages`) and a stale artifact merges silently. The check is building each and `git diff --exit-code` on it; `.gitattributes` covers both, so it is unblocked.
- **Only `ar` is translated, and only the strings that existed on 2026-09-05.** Any new user-facing string needs marking, then `makemessages`, then `compilemessages`.
- **`Commitment` cannot be edited or deleted** — create and list only. The interesting part of adding `UpdateView`/`DeleteView` is ownership: `LoginRequiredMiddleware` proves *someone* is logged in, not that they own the row, so without an explicit check user A can delete user B's commitment by guessing a UUID.
- **`home` does not show which days have commitments.** Twelve months of bare numbers. One grouped query for the whole year (`values("date").annotate(Count("id"))`), not one per day — and complete class strings from the view, since `bg-{{ x }}-500` generates nothing.
- **Telegram notifications (wanted).** Link a Telegram bot to the site and message a user when a commitment is coming up. Rough shape: a bot token from `@BotFather` kept in `.env` alongside `DJANGO_SECRET_KEY` (never committed — see **Environment variables**), a `telegram_chat_id` field on `CustomUser` plus some way for a user to link their account (the usual trick is the site showing a one-time code the user sends to the bot, since Telegram will not reveal a chat id otherwise), and a management command that queries commitments due in a window and posts to the Bot API.

  **The real blocker is not the bot, it is that nothing runs on a schedule.** Everything here is request-driven; there is no host, no worker, no cron — so "when an event comes up" has nothing to fire it. A management command plus the host's scheduler is the simplest answer once there *is* a host, which makes this depend on **CD**. A scheduled GitHub Actions workflow could stand in for a cron, but it would need network access to a deployed database, so it does not dodge the dependency. Sending is the easy half: one HTTPS POST to `api.telegram.org`, no library required.

`static/css/output.css` is **committed on purpose** — `collectstatic` copies that file, it does not generate it. Regenerating it makes it show up in `git status` constantly; that is expected, not a problem.

## Session history (2026-09-05, part two — i18n)

First session run from **PyCharm** rather than VS Code. Nothing needed installing: GNU gettext was already on `PATH`, and Claude Code is the same CLI in any terminal. Noted that PyCharm **autosaves** — on focus change, on running anything, and after ~15s idle — so there is no unsaved-file state to worry about; its replacement for "close without saving" is **Local History** (right-click a file → Local History), a git-independent timestamped diff. Also noted that the Django plugin (template syntax, `manage.py` console) is a Pro feature and is not in this install's bundled plugin list.

Built the whole i18n/l10n feature in six steps, one at a time, verifying each: settings wiring → marking template strings → the month/weekday fix → `.po`/`.mo` → the switcher → RTL. The durable version of all of it is in **Internationalization** above.

Snags, each a good lesson:

- The `gettext_lazy` import **replaced** the three existing imports in `settings.py` instead of joining them, so `Path` was undefined. Lesson in reading a traceback: bottom-up, and the frame that matters is the deepest one *not* inside `site-packages`. Also that any error inside `settings.py` surfaces as a traceback about `settings.INSTALLED_APPS`, because that attribute access is what wakes the lazy settings object.
- `LOCALE_PATHS = (BASE_DIR / "locale")` — **the tuple gotcha again**, same as `("text,")` → `admin.E126` last time. Parentheses don't make a tuple, the comma does. Django type-checks this particular setting at startup, which is luckier than it sounds: most settings aren't checked at all.
- `from django.utils.dtaes import ...` — one transposed letter, forty frames of traceback.
- `{% block heading %}` got pasted at the top of `auth_base.html` while the original remained, giving `'block' tag with name 'heading' appears more than once`.
- `{{ month.name|date:"F" }}` after the view had switched the key to `date`. **Django resolves a missing context key to the empty string**, so this rendered twelve empty `<h2>`s: 200 OK, no error, tests green. Caught only by looking. This is `home` being the untested view, demonstrating itself.
- The language switcher was first placed **inside** the `{% if user.is_authenticated %}` branch, which defeats the whole point of exempting `set_language` from `LoginRequiredMiddleware`. Found while tidying the nav.
- `python manage.py check` **does not compile templates**, so it passed while three templates were broken. Rendering them is the only proof, which the six tests do for free.

Worth repeating: three of these failed *silently* (the missing context key, the switcher in the wrong branch, an unmarked string), and none of the three would be caught by anything currently in the repo.

Left at: PRs #16 → `develop` and #17 → `main`, both merged, back-merge done. Everything in **Internationalization** is live.

## Session history (2026-09-05)

Cleared the whole "small stuff" list: tests for `accounts`, then the two chores. Four PRs, two full trips through the release loop, no surprises.

**Registration tests** (PRs #10 → `develop`, #11 → `main`). Built one test at a time, running each before writing the next. Watched the first one *fail* on purpose by commenting out `@method_decorator(login_not_required, name="dispatch")` — `302 != 200`, exactly the silent lockout the test exists to catch. The durable lessons are folded into **Current state** above: form field names vs model field names, `check_password` over comparing the raw string, asserting the error field rather than its translated text, and `count() == 0` over `get()` for absence.

Also covered: why `User = get_user_model()` at module level is fine in a test module (the runner imports it after `django.setup()`) but a hazard in `models.py`, where it can fire before the app registry is ready — the same import-time/call-time split as `reverse` vs `reverse_lazy`.

**The two chores** (PRs #12 → `develop`, #13 → `main`), deliberately two commits on one branch. Trailing newlines first: `for f in ...; do printf '\n' >> "$f"; done`. The diff came back `4 insertions(+), 4 deletions(-)` rather than four pure insertions, which *is* the argument for the fix — appending the byte rewrites the last line, so git shows it deleted and re-added. Then `main\urls.py`, with the `app_name` trap explained before anything was written; see the new **URLs** section.

Two small process notes. The newly created `main\urls.py` was itself missing a trailing newline — spotted because `cat` ran the closing `]` straight into the next `echo` marker on the same line, which is the tell. `tail -c 1 <file> | xxd` is the check: `0a` good, anything else missing. PyCharm's **Settings → Editor → General → On Save → "Ensure every saved file ends with a line break"** stops it recurring. And `git add <file>` by name mattered here: `main\urls.py` was untracked, and `git commit -a` never stages untracked files — committing the `include('main.urls')` without the module would have been an instant `ModuleNotFoundError` in CI.

Predictions made before running, all confirmed: both release PRs opened `BLOCKED` + `MERGEABLE` (never `BEHIND`, because the previous back-merge had levelled the branches) and flipped to `CLEAN` on their own when `test` passed, with nothing done to unblock them. The PR into ungated `develop` showed `CLEAN`/`UNSTABLE` on the same kind of pending check. Both back-merges were fast-forwards. `gh pr checks` shows two runs per PR — the `on: push` one testing the branch tip and the `on: pull_request` one testing the simulated merge; the ruleset gates on the second.

Left at: `develop` and `origin/main` both at `8283f21`, `git log develop..origin/main` and the reverse both empty, working tree clean, thirteen PRs, four stale remote-tracking branches pruned. Local `main` is a stale pointer at `2d4b421` — harmless, since nothing is ever committed there; `git fetch origin main:main` freshens it without a checkout.

Next: features, which are now the whole gap. `home` marking days that have commitments is the smallest user-visible win and the natural next step; edit/delete for `Commitment` is the one that needs an ownership check. See **Current state**.

## Session history (2026-09-04)

Built the whole CI story: tests, the workflow, and the branch protection ruleset. See **CI** and **Environment variables** above for the durable versions.

Step 1, tests for the `day` view. The login-requirement and GET tests were already written; this session added the POST one. Explained the arrange/act/assert shape and why a POST test must assert **both** the database write and the HTTP response (one without the other passes while the view is half-broken); `force_login` vs `login` and why a test should fail for exactly one reason; `.get()` with no arguments as a one-line "exactly one row" assertion; why `user`/`date` are the assertions that matter and `created_at` isn't; and Post/Redirect/Get as the reason the redirect is load-bearing rather than decorative.

Step 2, the workflow. First draft had `jobs:` indented two spaces — a hard YAML parse error, since a dedent has to land on an already-open indentation level. Fixed, pushed, green in 18s. Then GitHub warned that `checkout@v4` and `setup-python@v5` still declare the deprecated `node20` runtime; bumped to `@v5`/`@v6`. Explained that this is the *runner's* Node executing action wrappers, nothing to do with this project's npm/Tailwind, and that needing a major bump is what a floating major tag is *for*.

Step 3, the ruleset — the session's real detour. Installed the GitHub CLI so GitHub-side state could be verified instead of taken on trust (`winget install --id GitHub.cli`; a first attempt returned exit 1602, which is UAC cancelled). `gh api` then answered the question the UI couldn't: `403 Upgrade to GitHub Pro or make this repository public`. Audited the history for secrets, found it clean, and made the repo public. Built the ruleset and read it back through the API — every rule saved correctly, including the `test` check bound to `integration_id 15368`.

Explained along the way: why a system package manager ignores the current directory while `npm install` doesn't (the `winget` vs `npm` vs `npm -g` scopes); the device-flow login blocking for 120s and being backgrounded, which is normal rather than a failure; and the classic-protection ↔ ruleset vocabulary map, where "do not allow bypassing" becomes "leave the bypass list empty".

Three recurring snags, all environmental: pasted commands wrapping onto a second line, so bash ran the trailing flag as its own command (twice — `--accept-visibility-change-consequences` and the `!` prefix needing to be the very first character); and `gh` not being on `PATH` in already-running shells after install, since winget's `PATH` edit can't reach backwards into them.

Left at: **all four steps done.** PR #2 merged `feature/ci` into `develop` (`44a32a9`) and PR #3 merged `develop` into `main` (`f8081ed`) — `main`, `develop` and local `main` are all in sync for the first time since August, and `feature/ci` is deleted locally and on `origin`.

PR #3 is the one worth remembering: `gh pr view 3` reported `mergeStateStatus: BLOCKED` while the check ran and `CLEAN` once it passed. Nothing was done to unblock it — the passing check flipped it. That is steps 1–3 working, observed rather than assumed. PR #2, targeting the ungated `develop`, was mergeable from the moment it opened.

Also worth noting: the final `git pull` on `main` was a **fast-forward**, because local `main` had no commits of its own. That is the "nothing is committed to `main` directly" rule showing up as an observable property — if it ever stops fast-forwarding, something was committed there that shouldn't have been.

After that, two more trips through the same loop, both deliberately small so the workflow itself was the exercise: PR #4/#5 synced the docs, and PR #6/#7 added `.gitattributes` (see **Line endings** above). Seven PRs total.

The workflow lessons those produced are all folded into **Git workflow** and **Branch protection on `main`** above: the back-merge that every release needs, the `CLEAN`/`UNSTABLE`/`BLOCKED`/`BEHIND` vocabulary, `--delete-branch` being right for feature branches and wrong for `develop`, and `--force-with-lease` over `--force` when amending an already-pushed commit.

One prediction confirmed: PR #7 opened `BLOCKED` but **not** `BEHIND`, because the back-merge after PR #5 had already levelled the branches. The mechanism behaves as described.

Left at: `main` and `develop` both at `e317877`, working tree clean, everything pushed. Nothing half-finished.

Next: the small ones first — trailing newlines, then `main\urls.py`, then tests for `accounts` (registration especially: `@login_not_required` failing there locks out every new user with no error anywhere). Features are the real gap — `Commitment` still cannot be edited or deleted, and `home` does not show which days have any. Telegram notifications are wanted (see **Current state**), but they are gated on there being a deployment with a scheduler.

## Session history (2026-08-28)

No feature work — the whole session was learning the git branching workflow end to end, using the already-written (but uncommitted) admin + day-commitments code as the payload. See the **Git workflow** section above for the durable version.

What happened: created `develop` and `feature/day-commitments`; discovered the working tree held *two* unrelated changes and split them into two commits using the staging area (`c4b1b5b` admin, `f1eba7e` day view); pushed `develop` first so the PR had a base to merge into; pushed the feature branch; opened PR #1 with the base switched from GitHub's default `main` to `develop`; merged it as a merge commit (`8b34c4b`) rather than a squash, because the two commits had been deliberately curated; then synced and cleaned up locally.

Explained along the way: that `!` in the Claude Code prompt runs a shell command rather than being part of the git command; the working tree → staging area → commit pipeline, and why `git add` is what lets two tangled changes become two commits; `git diff` vs `git diff --staged`; commit message conventions (imperative subject, body explains *why*); what `-u` / upstream tracking actually records, and reading the `[origin/...]` bracket in `git branch -vv`; that a PR is a GitHub concept git knows nothing about, and that its value here is being the hook CI will attach to; merge vs squash vs rebase; and why `git pull` doesn't happen automatically after a GitHub-side merge.

Three snags, each a good lesson and all documented above: the CRLF warning on `output.css`; the aborted `git pull` caused by the Tailwind watcher having regenerated `output.css`; and `CLAUDE.md` appearing to revert (it hadn't — local `develop` was simply three commits behind, so checkout gave the older copy). One piece of pure debris: a stray file named after part of a commit message, produced by accidentally hitting `s` (save) inside `less` while paging git output — deleted, unrelated to git.

Left at: branching workflow complete and understood. `develop` is at `8b34c4b`, `main` deliberately two commits behind. Next up, all on a `feature/ci`-style branch: (1) write tests for the `day` view, (2) add `.github\workflows\ci.yml`, (3) add a branch protection rule on `main` requiring CI to pass, then finally merge `develop` → `main` through that gate.

## Session history (2026-08-23)

Built the entire auth flow, one step at a time: added `accounts/templates` to `input.css` (a new app's templates are invisible to Tailwind until you do); `auth_base.html`, which extends `base.html` and declares fresh `heading`/`form` blocks for `login.html` and `register.html` to fill; `accounts\urls.py` + `include()` + the three `LOGIN_*` settings; `CustomUserCreationForm` + `RegisterView`; `LoginRequiredMiddleware` with `RegisterView` exempted; the nav's authenticated/anonymous split with the POST logout form; and the `@layer components` form styling.

Explained along the way: why an element cannot center itself with its own flex properties (so the auth card needs an outer positioning div and an inner decorating div); `reverse` vs `reverse_lazy`, and import-time vs request-time evaluation; why `UserCreationForm` must be subclassed for a custom user model; why logout became POST-only; and reading dotted settings paths as real folders to spot typos (a `django.contrib.messages.auth.middleware...` typo cost a debugging round).

Then did step 8, admin registration, in two halves: `CustomUser` with the stock `UserAdmin`, then `CommitmentAdmin` via `@admin.register`. Verified in the browser that the password renders as a read-only hash summary, that *User* is an autocomplete search box, and that *Created at* is absent from the add form. Explained what a decorator actually desugars to, and the difference between one that observes its target (`@admin.register`) and one that replaces it (`@method_decorator`). See the **Admin** section above for the details worth keeping.

Left at: step 8 complete. Next up is wiring `Commitment` into the `day` view — nothing user-facing reads or writes it yet.

## Session history (2026-08-21)

Set up Tailwind v4 in this project from nothing: created `static\{src,css}\`, installed `tailwindcss` + `@tailwindcss/cli`, wrote `input.css`, added `main` to `INSTALLED_APPS` (it was missing) and `STATICFILES_DIRS`, filled in the empty `base.html`, added the `home` view/route/template, then moved `base.html` to a project-level `templates\` folder and updated `DIRS`, the `extends` path, and `@source`.

Topics explained along the way, in case they come up again: what `input.css` vs `output.css` are and which one is hand-authored; OneDrive vs `node_modules`; restarting the watcher between sessions; what `STATIC_URL` / `STATICFILES_DIRS` do and how a static request resolves; every tag in `base.html` (especially the `viewport` meta tag, without which Tailwind's `sm:`/`md:` prefixes misbehave on phones); using Tailwind across multiple apps (`extends` links the stylesheet, `@source` populates it — both needed); whether to move `base.html` out of `main`; what `BASE_DIR` is and how `TEMPLATES['DIRS']` uses it; and the purpose of a per-app `urls.py` with `include()` (recommended once there are 3–4 routes or a second app).
