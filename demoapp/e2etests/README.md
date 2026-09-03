# End-to-end tests

These tests drive the compiled React client (`client/**`) in a real Chromium
browser through [Playwright](https://playwright.dev/python/), against a live
Django server running the demo application.

They complement `unittests/`, which only exercises the Python side.

## Setup

```shell
pip install -e ".[e2e,image]"
playwright install chromium
npm install --include=dev
npm run buildall          # populates finder/static/finder/{js,css}
```

The last step is not optional: the tests interact with the bundled application,
so stale or missing assets make them fail.

## Running

```shell
pytest demoapp/e2etests --ds=demoapp.e2etests.settings
```

A bare `pytest` only collects `unittests/` (see `pytest.ini`), because these
tests need their own settings module.

Useful switches while writing tests:

| Variable                | Effect                                       |
|-------------------------|----------------------------------------------|
| `PLAYWRIGHT_HEADED=1`   | show the browser window                      |
| `PLAYWRIGHT_SLOW_MO=250`| delay each interaction by 250 ms             |

## How it is wired up

* `settings.py` extends `demoapp.settings`, but keeps the database, the media
  files and the generated assets in `workdir/e2e/`, so a local development
  server is never disturbed.
* `urls.py` serves `MEDIA_URL` unconditionally. Django forces `DEBUG = False`
  while tests run, hence `static()` in `demoapp.urls` contributes nothing and
  the browser could not load any thumbnail.
* `demoapp.middleware.AutoLoginMiddleware` logs in the first user found in the
  database. The `admin_user` fixture creates that user up front, which keeps the
  browser session deterministic and gives the tests an owner for their objects.
* Every test needs `@pytest.mark.django_db(transaction=True)`: the live server
  runs in its own thread and does not see data inside an uncommitted
  transaction. As a consequence the database is flushed after each test, so the
  `ambit` fixture re-creates the ambit whenever it is missing.
* The `page` fixture records uncaught exceptions, `console.error()` calls and
  responses with a status of 500 or above. `fail_on_browser_errors` turns those
  into test failures; opt out of the JavaScript part with
  `@pytest.mark.allow_js_errors`.
* A failing test leaves a Playwright trace in `workdir/e2e/traces`. Inspect it
  with `playwright show-trace workdir/e2e/traces/<test name>.zip`.

## Selecting elements

Both `<finder-file-select>` and `<finder-folder-select>` render into an open
shadow root. Playwright pierces those with ordinary CSS selectors, so
`page.locator('finder-file-select ul.files-browser > li')` works as written.

The menu bar of the folder admin labels its buttons through tooltips only, which
are not in the DOM until hovered. The tests therefore address them by the
attributes that are always present:

* layout buttons: `nav li[role="menuitem"][aria-selected]`, in the order
  tiles, mosaic, list, columns, gallery
* action buttons: `nav li[role="menuitem"][aria-disabled]`, in the order
  cut, paste, trash
