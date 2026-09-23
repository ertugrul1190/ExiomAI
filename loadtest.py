"""
Concurrency / load test for a running EXIOM AI server.

    python loadtest.py --url http://127.0.0.1:8000 \\
        --concurrency 20 --requests 200

    python loadtest.py --url https://your-host --stream \\
        --question "what is staking" --max-p95-ms 8000

Reports status codes, latency percentiles, time to first
byte (for --stream: time to the first SSE frame, which is
when text starts appearing) and throughput.

COST: the default question is a greeting, which the fast path
answers for free. Any --question that reaches the AI is a
real, billed call (router + answer) per request. Answer reuse makes repeats of
one identical question cheap, but not free.

LIMITS: every request comes from this machine, so the usage
controller will answer 429 once one client's per-minute
allowance is spent. That is the limiter working; 429s are
counted separately and never fail the run.

Exit status is 1 when any request failed at the transport
level, with a 5xx, or with a stream that broke part-way
(still HTTP 200, but ending in an error frame), or when
--max-p95-ms is exceeded.
Like test_explorer.py, this is a manual tool: pytest does not
collect it, but tests/test_concurrency.py drives it against
an in-process server.
"""

import argparse
import itertools
import json
import math
import sys
import threading
import time

from concurrent.futures import ThreadPoolExecutor

import requests


DEFAULT_QUESTION = "hello"


def percentile(samples, fraction):
    """
    Nearest-rank percentile of an already sorted list.
    """

    if not samples:
        return 0.0

    rank = max(1, min(len(samples), math.ceil(round(fraction * len(samples), 9))))

    return samples[rank - 1]


def read_stream(response):
    """
    Returns (answer, seconds to first frame or None, error).

    error is None for a clean stream. A stream that broke
    after it opened still has HTTP 200; its in-band error
    frame is the only sign, so it is reported here.
    """

    started = time.perf_counter()
    first_frame = None
    answer = []
    error = None

    for line in response.iter_lines(decode_unicode=True):

        if not line or not line.startswith("data: "):
            continue

        if first_frame is None:
            first_frame = time.perf_counter() - started

        try:
            frame = json.loads(line[len("data: "):])

        except ValueError:
            error = f"malformed frame: {line[:80]}"
            continue

        if frame.get("type") == "delta":
            answer.append(frame.get("text", ""))

        elif frame.get("type") == "message":
            answer.append(str(frame.get("answer", "")))

        elif frame.get("type") == "error":
            error = "error frame: " + str(frame.get("answer", ""))[:120]

    return "".join(answer), first_frame, error


def one_request(session, base_url, question, stream, timeout):

    path = "/ask/stream" if stream else "/ask"

    started = time.perf_counter()

    result = {
        "question": question,
        "status": None,
        "latency_ms": None,
        "ttfb_ms": None,
        "answer": "",
        "error": None,
    }

    try:

        response = session.post(
            base_url.rstrip("/") + path,
            json={"question": question, "conversation": []},
            timeout=timeout,
            stream=stream,
        )

        headers_at = time.perf_counter()

        result["status"] = response.status_code

        content_type = response.headers.get("Content-Type", "")

        if stream and content_type.startswith("text/event-stream"):

            answer, first_frame, stream_error = read_stream(response)

            result["answer"] = answer
            result["error"] = stream_error
            result["ttfb_ms"] = (
                (headers_at - started + first_frame) * 1000
                if first_frame is not None
                else None
            )

        else:

            result["ttfb_ms"] = (headers_at - started) * 1000

            try:
                result["answer"] = str(response.json().get("answer", ""))

            except ValueError:
                result["answer"] = response.text

    except (requests.RequestException, ValueError) as error:

        result["error"] = f"{type(error).__name__}: {error}"

    result["latency_ms"] = (time.perf_counter() - started) * 1000

    return result


def run_load(
    base_url,
    questions=(DEFAULT_QUESTION,),
    concurrency=10,
    total=100,
    stream=False,
    timeout=120,
):
    """
    Send `total` requests, at most `concurrency` at a time,
    cycling through `questions`. Returns (results, seconds).
    """

    local = threading.local()

    def session():
        # One keep-alive session per worker thread; a Session
        # is not safe to share between threads.
        if not hasattr(local, "session"):
            local.session = requests.Session()

        return local.session

    plan = list(itertools.islice(itertools.cycle(questions), total))

    started = time.perf_counter()

    with ThreadPoolExecutor(max_workers=concurrency) as pool:

        results = list(pool.map(
            lambda question: one_request(
                session(), base_url, question, stream, timeout
            ),
            plan
        ))

    return results, time.perf_counter() - started


def summarize(results, elapsed):

    latencies = sorted(
        r["latency_ms"] for r in results
        if r["status"] == 200 and not r["error"]
    )

    first_bytes = sorted(
        r["ttfb_ms"] for r in results
        if r["status"] == 200 and r["ttfb_ms"] is not None
    )

    statuses = {}

    for r in results:
        key = r["status"] if r["status"] is not None else "transport_error"
        statuses[key] = statuses.get(key, 0) + 1

    def spread(samples):
        return {
            name: round(percentile(samples, fraction), 1)
            for name, fraction in (
                ("p50", 0.50),
                ("p90", 0.90),
                ("p95", 0.95),
                ("p99", 0.99),
                ("max", 1.00),
            )
        }

    failures = [
        r for r in results
        if r["error"] or (r["status"] or 0) >= 500
    ]

    return {
        "requests": len(results),
        "seconds": round(elapsed, 2),
        "throughput_rps": round(len(results) / elapsed, 2) if elapsed else 0.0,
        "statuses": statuses,
        "latency_ms": spread(latencies),
        "ttfb_ms": spread(first_bytes),
        "failures": len(failures),
        "failure_samples": [
            r["error"] or f"HTTP {r['status']}: {r['answer'][:120]}"
            for r in failures[:5]
        ],
    }


def main(argv=None):

    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])

    parser.add_argument("--url", default="http://127.0.0.1:5000")
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--stream", action="store_true")
    parser.add_argument("--timeout", type=float, default=120)
    parser.add_argument(
        "--question",
        action="append",
        help="repeatable; defaults to a free fast-path greeting"
    )
    parser.add_argument(
        "--max-p95-ms",
        type=float,
        help="fail when successful-request p95 latency exceeds this"
    )

    args = parser.parse_args(argv)

    if args.concurrency < 1 or args.requests < 1:
        parser.error("--concurrency and --requests must be at least 1")

    questions = args.question or [DEFAULT_QUESTION]

    if args.question:
        print(
            f"WARNING: up to {2 * args.requests} billed AI calls "
            "(router + answer per request; fewer when reused).",
            file=sys.stderr
        )

    results, elapsed = run_load(
        args.url,
        questions,
        args.concurrency,
        args.requests,
        args.stream,
        args.timeout,
    )

    report = summarize(results, elapsed)

    print(json.dumps(report, indent=2))

    too_slow = (
        args.max_p95_ms is not None
        and report["latency_ms"]["p95"] > args.max_p95_ms
    )

    return 1 if report["failures"] or too_slow else 0


if __name__ == "__main__":
    sys.exit(main())
