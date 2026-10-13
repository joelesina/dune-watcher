import os, re, urllib.request
from playwright.sync_api import sync_playwright

URL = "https://www.biografenvue.dk/movies/1000050581-dune-del-3-the-imax-experience/"
TARGET = "2026-12-16"
REFERENCE = "2026-12-15"
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

chosen = False
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(locale="da-DK")
    page.on("response", on_response)
    page.goto(URL, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(8000)
    for label in ["Tillad alle", "Accepter alle", "Accepter"]:
        try:
            page.get_by_text(label).first.click(timeout=2000)
            break
        except Exception:
            pass
    try:
        page.get_by_text("Vælg en biograf").first.click(timeout=5000)
        page.wait_for_timeout(1500)
        page.get_by_text("Vue Fisketorvet").first.click(timeout=5000)
        page.wait_for_timeout(10000)
        chosen = True
    except Exception as e:
        print("Cinema selection failed:", e)
    browser.close()

blob = "\n".join(bodies)

def timed_hits(date):
    pattern = r'"(\w+)"\s*:\s*"' + date + r'T(?!00:00)\d\d:\d\d[^"]*"'
    return re.findall(pattern, blob)

target_hits = timed_hits(TARGET)
ref_hits = timed_hits(REFERENCE)

print("Responses:", len(bodies), "| Fisketorvet selected:", chosen)
print("16 Dec timed hits:", target_hits, "| 15 Dec timed hits:", ref_hits)

if target_hits:
    notify("DUNE 3: 16 Dec showing found", f"Timed entry under {sorted(set(target_hits))}. Fisketorvet selected: {chosen}. Check the page.", "urgent")
elif TEST:
    notify("Dune watcher test", f"Fisketorvet selected: {chosen}. Responses: {len(bodies)}. 15 Dec timed hits: {len(ref_hits)} {sorted(set(ref_hits))}. 16 Dec timed hits: 0.")
