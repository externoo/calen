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

Environment: Django 6.0.6 on Python 3.13, SQLite (`db.sqlite3`), Tailwind v4.3.3 via npm. There is no `requirements.txt`, no virtualenv, and no git repo yet.

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

Both `templates\` and `main\templates\` are listed as `@source` paths in `input.css`.

## Current state

Deliberately minimal — a scaffold, not a built-out app. `models.py` and `admin.py` are empty, `main` has no `urls.py` (its single `home` view is wired directly in `calen\urls.py`), and `home.html` is a Tailwind smoke-test page. Expect to build most things from scratch.

When git is eventually initialized: `.gitignore` needs `node_modules/`, `db.sqlite3`, and `__pycache__/`, but `static/css/output.css` should be **committed** — `collectstatic` copies that file, it does not generate it.

## Session history (2026-08-21)

Set up Tailwind v4 in this project from nothing: created `static\{src,css}\`, installed `tailwindcss` + `@tailwindcss/cli`, wrote `input.css`, added `main` to `INSTALLED_APPS` (it was missing) and `STATICFILES_DIRS`, filled in the empty `base.html`, added the `home` view/route/template, then moved `base.html` to a project-level `templates\` folder and updated `DIRS`, the `extends` path, and `@source`.

Topics explained along the way, in case they come up again: what `input.css` vs `output.css` are and which one is hand-authored; OneDrive vs `node_modules`; restarting the watcher between sessions; what `STATIC_URL` / `STATICFILES_DIRS` do and how a static request resolves; every tag in `base.html` (especially the `viewport` meta tag, without which Tailwind's `sm:`/`md:` prefixes misbehave on phones); using Tailwind across multiple apps (`extends` links the stylesheet, `@source` populates it — both needed); whether to move `base.html` out of `main`; what `BASE_DIR` is and how `TEMPLATES['DIRS']` uses it; and the purpose of a per-app `urls.py` with `include()` (recommended once there are 3–4 routes or a second app).
