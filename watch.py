import os, re, urllib.request
from playwright.sync_api import sync_playwright

URL = "https://www.biografenvue.dk/movies/1000050581-dune-del-3-the-imax-experience/"
DATE = "2026-12-16"
TOPIC = os.environ["NTFY_TOPIC"]
TEST = os.environ.get("TEST_MODE") == "1"

def notify(title, msg, priority="default"):
    req = urllib.request.Request(
        f"https://ntfy.sh/{TOPIC}",
        data=msg.encode("utf-8"),
        headers={"Title": title, "Priority": priority, "Click": URL},
    )
    urllib.request.urlopen(req)

bodies = []

def on_response(r):
    try:
        if "json" in r.headers.get("content-type", "") or "graphql" in r.url:
            bodies.append(r.text())
    except Exception:
        pass

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(locale="da-DK")
    page.on("response", on_response)
    page.goto(URL, wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(5000)
    browser.close()

blob = "\n".join(bodies)
dates = sorted(set(re.findall(r"2026-\d\d-\d\d", blob)))
found = DATE in blob
fisketorvet = "fisketorvet" in blob.lower()

print("JSON responses:", len(bodies))
print("Dates seen:", dates)
print("Found 16 Dec:", found, "| Fisketorvet mentioned:", fisketorvet)

if found:
    extra = "Fisketorvet mentioned." if fisketorvet else "Fisketorvet not confirmed, check."
    notify("DUNE 3 TICKETS LIVE", f"A showing on 16 Dec has appeared. {extra}", "urgent")
elif TEST:
    notify("Dune watcher test", f"Working. JSON responses: {len(bodies)}. Dates seen: {dates[:8]}. 16 Dec: not yet.")
