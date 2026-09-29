"""
Ask ExiomAI a list of questions for real and print what came
back, to judge answer quality by eye after a prompt or
routing change.

    python live_eval.py                        # evals/questions.txt
    python live_eval.py my_questions.txt --stream --parallel 2

Runs the app in-process against the live Explorer and the
real AI provider (OPENAI_API_KEY from .env). For each
question it prints the route, the source footer, the time,
every answer call (with its web-search mode), and the
answer.

COST: every question that reaches the AI is billed: a router
call plus one to three answer calls, and web searches at
about $0.01 each. The default list costs a few cents.

LIMITS: the OpenAI project's tokens-per-minute cap applies.
Above --parallel 2 a small project hits it, and those
answers come back as "too much attention" errors.

A manual tool like loadtest.py: pytest does not collect it,
and it is not deployed.
"""

import argparse
import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "questions",
        nargs="?",
        default=str(Path(__file__).parent / "evals" / "questions.txt")
    )
    parser.add_argument("--stream", action="store_true")
    parser.add_argument("--parallel", type=int, default=2)
    args = parser.parse_args()

    os.environ.setdefault("EXIOM_USAGE_DB", "off")
    os.environ.setdefault("EXIOM_CLIENT_WEB_SEARCHES_PER_DAY", "1000")

    import app

    # Take one complete Explorer reading first, background
    # pages included.
    app.live_data.get_network_stats()
    app.live_data.wait_for_page_refreshes()
    app.live_data.cache.pop("network_stats", None)

    # (line, question) -> answer calls. A thread handles one
    # line at a time, so the line is kept per thread.
    calls = {}
    current = threading.local()
    provider = app.ai_provider
    generate, stream_generate = provider.generate, provider.stream_generate

    def logged_generate(**request):
        result = generate(**request)
        calls.setdefault((current.line, request["question"]), []).append(
            (request["web_search"], result["answer"])
        )
        return result

    def logged_stream(**request):
        parts = []

        for chunk in stream_generate(**request):
            parts.append(chunk)
            yield chunk

        calls.setdefault((current.line, request["question"]), []).append(
            (request["web_search"], "".join(parts))
        )

    provider.generate = logged_generate
    provider.stream_generate = logged_stream

    client = app.app.test_client()

    lines = [
        line.strip()
        for line in Path(args.questions).read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]

    def ask(index, question, conversation):
        path = "/ask/stream" if args.stream else "/ask"
        response = client.post(
            path,
            json={"question": question, "conversation": conversation},
            # One client per line, so per-client limits don't bite.
            environ_base={"REMOTE_ADDR": f"10.0.{index // 250}.{index % 250 + 1}"}
        )

        if not args.stream:
            return response.get_json() or {}

        reply = {}
        text = ""

        for raw in response.get_data(as_text=True).splitlines():
            if raw.startswith("data: "):
                frame = json.loads(raw[len("data: "):])
                text += frame.get("text", "")

                if frame["type"] in ("message", "done", "error"):
                    reply.update(frame)

        if text:
            reply["answer"] = text

        return reply

    def run(item):
        index, line = item
        current.line = index
        conversation = []
        results = []

        for question in (part.strip() for part in line.split("||")):
            started = time.time()
            reply = ask(index, question, conversation)
            results.append((question, reply, time.time() - started))
            conversation += [
                {"role": "user", "content": question},
                {"role": "assistant", "content": reply.get("answer", "")},
            ]

        return index, results

    with ThreadPoolExecutor(max(1, args.parallel)) as pool:
        for index, results in pool.map(run, enumerate(lines)):
            for question, reply, seconds in results:
                print(
                    f"\n### {question}\n"
                    f"[{reply.get('route')}/{reply.get('scope', '')}"
                    f" source={reply.get('source', '-')} {seconds:.1f}s]"
                )

                for search, text in calls.get((index, question), []):
                    print(f"  call web_search={search}: {text[:60]!r}")

                print(reply.get("answer"))

    return 0


if __name__ == "__main__":
    sys.exit(main())
