"""Simple load test for NFR2 (95 % of page requests answered in under 1.5 s).

Simulates parallel users who open the start page, ask for recommendations with
filters, open a game page and search. Uses only the standard library.

Usage:
    python scripts/load_test.py --base-url http://localhost:8000 --users 20 --rounds 25
"""

import argparse
import json
import random
import statistics
import threading
import time
import urllib.request

PAGES = [
    "/",
    "/how-it-works",
    "/recommend?skill={a}",
    "/recommend?skill={a}&skill={b}",
    "/recommend?skill={a}&skill={b}&skill={c}&price_model=free",
    "/games/{game}",
    "/search?q={query}",
]


def fetch(url: str) -> tuple[int, float]:
    start = time.perf_counter()
    with urllib.request.urlopen(url, timeout=30) as response:
        response.read()
        status = response.status
    return status, time.perf_counter() - start


def user(base: str, rounds: int, skills: list[str], games: list[str], timings: list, errors: list, lock: threading.Lock):
    rng = random.Random()
    for _ in range(rounds):
        a, b, c = rng.sample(skills, 3)
        game = rng.choice(games)
        path = rng.choice(PAGES).format(a=a, b=b, c=c, game=game, query=game.split("-")[0])
        try:
            status, seconds = fetch(base + path)
        except Exception as exc:  # noqa: BLE001  (every failure counts as an error)
            with lock:
                errors.append(f"{path}: {exc}")
            continue
        with lock:
            timings.append(seconds)
            if status != 200:
                errors.append(f"{path}: HTTP {status}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--users", type=int, default=20)
    parser.add_argument("--rounds", type=int, default=25, help="requests per user")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")

    with urllib.request.urlopen(base + "/api/skills") as response:
        skills = [s["slug"] for s in json.load(response)]
    with urllib.request.urlopen(base + "/api/recommendations?skill=" + "&skill=".join(skills[:3])) as response:
        games = [g["slug"] for g in json.load(response)] or ["unknown"]

    timings: list[float] = []
    errors: list[str] = []
    lock = threading.Lock()
    threads = [
        threading.Thread(target=user, args=(base, args.rounds, skills, games, timings, errors, lock)) for _ in range(args.users)
    ]
    started = time.perf_counter()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    duration = time.perf_counter() - started

    timings.sort()
    p95 = timings[int(len(timings) * 0.95) - 1] if timings else float("nan")
    print(f"Parallel users:   {args.users}")
    print(f"Requests:         {len(timings) + len(errors)} in {duration:.1f} s ({len(timings) / duration:.1f} per second)")
    print(f"Errors:           {len(errors)}")
    print(f"Median:           {statistics.median(timings) * 1000:.0f} ms")
    print(f"95th percentile:  {p95 * 1000:.0f} ms")
    print(f"Maximum:          {timings[-1] * 1000:.0f} ms")
    print(f"NFR2 (p95 < 1.5 s): {'passed' if p95 < 1.5 and not errors else 'FAILED'}")
    for line in errors[:10]:
        print("  ", line)


if __name__ == "__main__":
    main()
