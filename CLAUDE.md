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
# open the PR on GitHub — base must be develop, NOT main (GitHub defaults to main)
git switch develop && git pull
git branch -d feature/x && git fetch --prune
```

Things worth remembering:

- **Creating a branch and publishing it are separate acts.** `git switch -c` is purely local; nothing reaches GitHub until `git push -u`. In `git branch -vv`, a branch with no `[origin/...]` bracket has never been pushed.
- **Uncommitted changes are not attached to a branch.** They live in the working tree, shared by every branch, and follow you across `git switch`. That is why in-progress work can be branched *after* the fact.
- **Squash when the branch is messy, merge-commit when it's curated.** A merge commit has two parents and keeps the fork visible in `git log --graph`; squash flattens it to one commit. Rebase-and-merge rewrites SHAs, so the local copies stop matching.
- **`git branch -d` is the safe delete** — it refuses if the commits survive nowhere. `-D` forces. If `-d` warns "merged to `refs/remotes/...` but not yet merged to HEAD", it means the local branch you're standing on hasn't pulled the merge yet; harmless, but pull first and the warning goes away.
- **`git fetch --prune`** deletes remote-tracking refs for branches GitHub no longer has. Without it, deleted branches linger locally as ghosts.

### The Tailwind watcher breaks `git pull`

`output.css` is committed but regenerated constantly, so the watcher leaves it dirty. A pull that touches it aborts with *"Your local changes would be overwritten by merge."* Stop the watcher (Ctrl-C) before pulling or switching branches. If it already happened, `git restore static/css/output.css` throws the local copy away — safe *only* because that file is a build artifact.

Also expect `warning: LF will be replaced by CRLF` on every `output.css` operation. `core.autocrlf=true` (Git for Windows' default) stores LF in history and hands back CRLF on checkout; the Node-based Tailwind CLI writes LF. Harmless. A `.gitattributes` would pin this per file type instead of per developer — worth adding when CI (Linux) enters the picture.

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

## Current state

Working: the 2026 calendar grid (`home`), the `day` page with commitment create + list, the full auth flow, and the admin for both models. `main\models.py` has an abstract `UUIDModel` plus `Commitment` (user FK, date, text, created_at).

`day` handles both GET and POST: `CommitmentForm` (a `ModelForm` on `text` alone) is saved with `commit=False` so the view can attach `user` and `date` before saving, then redirects to itself so a refresh doesn't resubmit. The list comes from `request.user.commitments` — the FK's `related_name`.

`main\tests.py` holds `DayViewTests` — three tests covering the whole `day` contract: the anonymous redirect to login, the logged-in GET (status, template, `date` in context), and the POST (a `Commitment` row is created with the right `user` and `date`, and the response redirects back to the same URL).

Two idioms in there worth reusing. `Commitment.objects.get()` with **no arguments** asserts "exactly one row exists" *and* returns it — `DoesNotExist` for zero, `MultipleObjectsReturned` for more — which only works because `TestCase` wraps each method in a transaction and rolls it back, so every test starts with empty tables and a fresh `setUp` user. And `assertRedirects` doesn't just check the 302: it follows the redirect and asserts the target returns 200, so it proves the destination is real (which needs the client to still be logged in).

The POST test's `user` and `date` assertions are the ones that earn their keep — they are the two fields nothing in the request sets, attached by hand between `save(commit=False)` and `save()`. Nothing asserts on `created_at`: it's `auto_now_add`, so testing it would be testing Django.

Not done yet:

- **Tests cover the `day` view only.** `home` is untested, and so is the whole of `accounts` — `accounts\tests.py` is still the empty stub. Registration is the interesting target there: it is the one view carrying `@login_not_required`, so a regression would lock every new user out silently.
- **No `.gitattributes`.** CI is Linux and the repo is full of CRLF; needed before any check that diffs a generated file.
- **i18n / l10n** — `USE_I18N` is on and the models already use `gettext_lazy`, but there is no `LocaleMiddleware`, no `LOCALE_PATHS`, no translated templates, and no `.po` files.
- `main` still has no `urls.py`; its two routes are wired directly in `calen\urls.py`.
- Missing trailing newlines in `main\views.py`, `main\forms.py`, `main\admin.py`, `accounts\admin.py` (`\ No newline at end of file` in diffs). Cosmetic, but it makes future diffs noisier.

`static/css/output.css` is **committed on purpose** — `collectstatic` copies that file, it does not generate it. Regenerating it makes it show up in `git status` constantly; that is expected, not a problem.

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

Next: nothing is half-finished. Open items are the ones listed under **Current state** — `.gitattributes` first, since CI is Linux now, then tests for `accounts`.

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
