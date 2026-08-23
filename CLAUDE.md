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

Environment: Django 6.0.6 on Python 3.13, SQLite (`db.sqlite3`), Tailwind v4.3.3 via npm. `requirements.txt` exists; there is no virtualenv. Git repo with remote `origin` → https://github.com/externoo/calen.git.

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

## Current state

Working: the 2026 calendar grid (`home`), a bare day page (`day`), and the full auth flow. `main\models.py` has an abstract `UUIDModel` plus `Commitment` (user FK, date, text, created_at).

Not done yet:

- **Admin registration** — `accounts\admin.py` and `main\admin.py` are both still empty. `CustomUser` must be registered with `UserAdmin`, *not* a plain `ModelAdmin`: the generic one renders the password as an editable text box and saves whatever you type as plaintext, permanently locking that account out.
- **`Commitment` is unused by any view.** `day.html` shows only a date; nothing reads or writes commitments yet.
- **i18n / l10n** — `USE_I18N` is on and the models already use `gettext_lazy`, but there is no `LocaleMiddleware`, no `LOCALE_PATHS`, no translated templates, and no `.po` files.
- **CI/CD** — nothing yet.
- `main` still has no `urls.py`; its two routes are wired directly in `calen\urls.py`.

`static/css/output.css` is **committed on purpose** — `collectstatic` copies that file, it does not generate it. Regenerating it makes it show up in `git status` constantly; that is expected, not a problem.

## Session history (2026-08-23)

Built the entire auth flow, one step at a time: added `accounts/templates` to `input.css` (a new app's templates are invisible to Tailwind until you do); `auth_base.html`, which extends `base.html` and declares fresh `heading`/`form` blocks for `login.html` and `register.html` to fill; `accounts\urls.py` + `include()` + the three `LOGIN_*` settings; `CustomUserCreationForm` + `RegisterView`; `LoginRequiredMiddleware` with `RegisterView` exempted; the nav's authenticated/anonymous split with the POST logout form; and the `@layer components` form styling.

Explained along the way: why an element cannot center itself with its own flex properties (so the auth card needs an outer positioning div and an inner decorating div); `reverse` vs `reverse_lazy`, and import-time vs request-time evaluation; why `UserCreationForm` must be subclassed for a custom user model; why logout became POST-only; and reading dotted settings paths as real folders to spot typos (a `django.contrib.messages.auth.middleware...` typo cost a debugging round).

Left at: step 8, admin registration, not yet implemented.

## Session history (2026-08-21)

Set up Tailwind v4 in this project from nothing: created `static\{src,css}\`, installed `tailwindcss` + `@tailwindcss/cli`, wrote `input.css`, added `main` to `INSTALLED_APPS` (it was missing) and `STATICFILES_DIRS`, filled in the empty `base.html`, added the `home` view/route/template, then moved `base.html` to a project-level `templates\` folder and updated `DIRS`, the `extends` path, and `@source`.

Topics explained along the way, in case they come up again: what `input.css` vs `output.css` are and which one is hand-authored; OneDrive vs `node_modules`; restarting the watcher between sessions; what `STATIC_URL` / `STATICFILES_DIRS` do and how a static request resolves; every tag in `base.html` (especially the `viewport` meta tag, without which Tailwind's `sm:`/`md:` prefixes misbehave on phones); using Tailwind across multiple apps (`extends` links the stylesheet, `@source` populates it — both needed); whether to move `base.html` out of `main`; what `BASE_DIR` is and how `TEMPLATES['DIRS']` uses it; and the purpose of a per-app `urls.py` with `include()` (recommended once there are 3–4 routes or a second app).
