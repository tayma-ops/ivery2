"""End-to-end checks with a temporary DB, disposable accounts and localhost only."""

import json, os, secrets, socket, subprocess, sys, tempfile, time, urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "test-results"
OUT.mkdir(exist_ok=True)


def signup(page, url):
    page.goto(url + "/accounts/signup/")
    page.locator("[name=username]").fill("browser_" + secrets.token_hex(5))
    page.locator("[name=first_name]").fill("عميل اختبار")
    page.locator("[name=email]").fill("browser@example.test")
    password = secrets.token_urlsafe(22)
    page.locator("[name=password1]").fill(password)
    page.locator("[name=password2]").fill(password)
    page.locator("form.panel button").click()
    page.wait_for_url(url + "/")
    page.wait_for_load_state("networkidle")


def post(page, path, body):
    return page.evaluate(
        """async ({path,body})=>{const csrf=document.cookie.split('; ').find(x=>x.startsWith('csrftoken='))?.split('=')[1]||'';const r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json','X-CSRFToken':csrf},body:JSON.stringify(body)});return {status:r.status,body:await r.json()};}""",
        {"path": path, "body": body},
    )


def layout(page):
    for width in [1440, 768, 390, 320]:
        page.set_viewport_size({"width": width, "height": 1000})
        assert page.evaluate(
            "document.documentElement.scrollWidth<=innerWidth"
        ), f"Horizontal overflow at {width}"
    page.set_viewport_size({"width": 1440, "height": 1000})


def run(page, url, browser):
    signup(page, url)
    expect(page.locator('body>a[href="/bookings/"]')).to_be_visible()
    layout(page)
    page.screenshot(path=str(OUT / "home.png"), full_page=True)
    page.locator("#specialty").select_option(index=1)
    page.locator("#city").select_option(index=1)
    tomorrow = (
        datetime.now(timezone(timedelta(hours=3))).date() + timedelta(days=1)
    ).isoformat()
    page.locator("#appointment-date").fill(tomorrow)
    page.locator("#mwaSearchBtn").click()
    page.locator(".appointment-times button").first.click()
    page.locator("#patient-name").fill("مراجع اختبار")
    page.locator("#patient-phone").fill("0500000000")
    page.screenshot(path=str(OUT / "appointment.png"), full_page=True)
    page.locator("#appointment-form button[type=submit]").click()
    page.wait_for_url("**/bookings/")
    expect(page.locator("h1")).to_have_text("حجوزاتي")

    # A separate authenticated browser must observe the first user's booking.
    second = browser.new_context(locale="ar-SA", timezone_id="Asia/Riyadh")
    second.route(
        "**/*",
        lambda route: (
            route.continue_()
            if route.request.url.startswith((url, "data:", "blob:"))
            else route.abort()
        ),
    )
    other = second.new_page()
    signup(other, url)
    resources = page.evaluate("fetch('/api/resources/').then(r=>r.json())")["resources"]
    resource = next(r for r in resources if r["id"] == resources[0]["id"])
    records = page.evaluate("fetch('/api/bookings/').then(r=>r.json())")["bookings"]
    record = records[0]
    data = {
        "token": secrets.token_hex(16),
        "resource": resource["id"],
        "service": record["serviceId"],
        "date": record["date"],
        "time": record["time"],
        "customer": "مستخدم آخر",
        "phone": "0500000000",
    }
    assert post(other, "/api/bookings/create/", data)["status"] == 409
    assert other.evaluate("fetch('/api/bookings/').then(r=>r.json())")["bookings"] == []
    assert (
        post(page, "/api/bookings/" + str(record["id"]) + "/cancel/", {})["status"]
        == 200
    )
    assert post(other, "/api/bookings/create/", data)["status"] == 201

    # Two independent requests must not reserve the same remaining time.
    import concurrent.futures, urllib.error

    available = other.evaluate(
        "params=>fetch('/api/availability/?'+new URLSearchParams(params)).then(r=>r.json())",
        {
            "resource": resource["id"],
            "service": record["serviceId"],
            "date": record["date"],
        },
    )
    clock = next(s["time"] for s in available["slots"] if s["available"])

    def attempt(cookies):
        payload = {**data, "token": secrets.token_hex(16), "time": clock}
        cookie = "; ".join(c["name"] + "=" + c["value"] for c in cookies)
        csrf = next(c["value"] for c in cookies if c["name"] == "csrftoken")
        req = urllib.request.Request(
            url + "/api/bookings/create/",
            data=json.dumps(payload).encode(),
            headers={
                "Content-Type": "application/json",
                "Cookie": cookie,
                "X-CSRFToken": csrf,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=25) as response:
                return response.status
        except urllib.error.HTTPError as error:
            return error.code

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        codes = list(
            pool.map(attempt, [page.context.cookies(), other.context.cookies()])
        )
    assert sorted(codes) == [201, 409], codes
    second.close()


def main():
    with tempfile.TemporaryDirectory(prefix="portfolio-browser-") as temporary:
        env = os.environ.copy()
        env.update(
            {
                "DJANGO_DB_PATH": str(Path(temporary) / "test.sqlite3"),
                "DJANGO_SECRET_KEY": secrets.token_urlsafe(64),
                "DJANGO_DEBUG": "1",
                "DJANGO_ALLOWED_HOSTS": "127.0.0.1,localhost",
                "OPENAI_API_KEY": "your_test_disabled",
            }
        )
        for args in [["migrate", "--noinput"], ["seed_demo"]]:
            result = subprocess.run(
                [sys.executable, "-B", "manage.py", *args],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            if result.returncode:
                raise RuntimeError(result.stderr)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        url = f"http://127.0.0.1:{port}"
        with (OUT / "server.log").open("w", encoding="utf-8") as log:
            process = subprocess.Popen(
                [
                    sys.executable,
                    "-B",
                    "manage.py",
                    "runserver",
                    f"127.0.0.1:{port}",
                    "--noreload",
                ],
                cwd=ROOT,
                env=env,
                stdout=log,
                stderr=log,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            try:
                for attempt in range(100):
                    try:
                        with urllib.request.urlopen(
                            url + "/accounts/signup/", timeout=1
                        ):
                            break
                    except Exception:
                        if process.poll() is not None:
                            raise RuntimeError(
                                (OUT / "server.log").read_text(encoding="utf-8")
                            )
                        time.sleep(0.1)
                else:
                    raise RuntimeError("Local server did not start")
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=True)
                    errors = []
                    context = browser.new_context(
                        locale="ar-SA",
                        timezone_id="Asia/Riyadh",
                        reduced_motion="reduce",
                        viewport={"width": 1440, "height": 1000},
                    )
                    context.route(
                        "**/*",
                        lambda route: (
                            route.continue_()
                            if route.request.url.startswith((url, "data:", "blob:"))
                            else route.abort()
                        ),
                    )
                    page = context.new_page()
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    try:
                        run(page, url, browser)
                        assert not errors, errors
                    except Exception:
                        page.screenshot(path=str(OUT / "failure.png"), full_page=True)
                        raise
                    finally:
                        browser.close()
                result = {
                    "passed": True,
                    "javascript_errors": errors,
                    "database": "temporary",
                    "external_requests": "blocked",
                    "original_database_modified": False,
                }
                (OUT / "browser-result.json").write_text(
                    json.dumps(result, indent=2), encoding="utf-8"
                )
                print(json.dumps(result))
            finally:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()


if __name__ == "__main__":
    main()
