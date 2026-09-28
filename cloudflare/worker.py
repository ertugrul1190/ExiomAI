# ---------------------------------------------------------
# CLOUDFLARE WORKERS ENTRY POINT
# ---------------------------------------------------------
#
# See "Task Docs/Cloudflare Workers Deployment.md". build.sh
# copies this file and the app into src/; nothing in the app
# changes for Workers:
#
# * fetch   runs app.py through the WSGI adapter, with the
#           usage limits pointed at UsageHubObject.
# * UsageHubObject, one Durable Object, holds the limits,
#           the ledger and the Explorer reading for every
#           copy (usage_hub.py).
# * scheduled, the Cron Trigger, reads the Explorer every
#           20 seconds into the hub, so requests never wait
#           on it (Handoff §4.2).
# ---------------------------------------------------------

import asyncio
import concurrent.futures
import contextvars
import json
import os
import threading
import time

# Snapshotted at deploy. openai itself cannot be (os.urandom
# at import), its heavy dependencies can.
import anyio  # noqa: F401
import flask  # noqa: F401
import httpx2  # noqa: F401
import pydantic  # noqa: F401
import requests  # noqa: F401
import werkzeug  # noqa: F401

import js
from pyodide.ffi import run_sync
from workers import DurableObject, WorkerEntrypoint, wsgi


# Workers cannot start threads. The Explorer fetches run
# inline instead; only the cron reaches them in normal use.
class _InlineExecutor(concurrent.futures.Executor):

    def __init__(self, *args, **kwargs):
        pass

    def submit(self, fn, /, *args, **kwargs):
        future = concurrent.futures.Future()

        try:
            future.set_result(fn(*args, **kwargs))

        except BaseException as error:
            future.set_exception(error)

        return future


def _inline_start(self):
    self.run()


concurrent.futures.ThreadPoolExecutor = _InlineExecutor
threading.Thread.start = _inline_start


# The one hub every copy shares.
HUB_NAME = "usage"

# The cron reads the Explorer this often, inside LiveData's
# 30 second window, three times per one-minute trigger.
READING_INTERVAL_SECONDS = 20


def _copy_env(env, secrets=False):
    """
    Vars and secrets arrive with the first event, not at
    import; app.py reads them from os.environ at import. Only
    the app gets the OpenAI key; the hub and the cron need
    the EXIOM_* settings alone.
    """

    raw = getattr(env, "_env", env)

    for name in js.Object.keys(raw):
        value = getattr(raw, name)

        if not isinstance(value, str):
            continue

        if name.startswith("EXIOM_") or (secrets and name == "OPENAI_API_KEY"):
            os.environ.setdefault(name, value)


def _hub_call(env):
    namespace = env.USAGE_HUB

    def call(op, args):
        stub = namespace.getByName(HUB_NAME)
        message = json.dumps({"op": op, "args": args})

        return json.loads(run_sync(stub.exchange(message)))

    return call


class _OneContextBody:
    """
    The adapter pulls each chunk of a streamed body in a new
    asyncio task, and each task has its own copy of the
    context variables. Flask's request context, pushed by
    stream_with_context in the first chunk, is then missing
    from the last one and the stream ends in an error. Every
    step of one response runs in the same context instead.
    """

    def __init__(self, context, body):
        self._context = context
        self._body = body
        self._chunks = context.run(iter, body)

    def __iter__(self):
        return self

    def __next__(self):
        return self._context.run(next, self._chunks)

    def close(self):
        close = getattr(self._body, "close", None)

        if close is not None:
            self._context.run(close)


def _wrap_app(app):
    """
    The adapter sets no REMOTE_ADDR. CF-Connecting-IP is set
    by Cloudflare and cannot be forged by a client.
    """

    def wrapped(environ, start_response):
        environ["REMOTE_ADDR"] = environ.get("HTTP_CF_CONNECTING_IP", "")

        context = contextvars.copy_context()
        body = context.run(app, environ, start_response)

        return _OneContextBody(context, body)

    return wrapped


_app = None


def _load_app(env):
    global _app

    if _app is None:
        _copy_env(env, secrets=True)

        import app as app_module
        import remote_usage

        remote_usage.install(app_module, _hub_call(env))
        _app = _wrap_app(app_module.app)

    return _app


_live_data = None


def _refresh_reading(call):
    """
    One Explorer reading into the hub. A failure is stored
    too (for its short window), unless the hub still holds a
    good reading (UsageHub.put_reading).
    """

    global _live_data

    if _live_data is None:
        from live_data import LiveData

        _live_data = LiveData()

    live = _live_data

    # Background pages are read from copies; take the first
    # ones now so the first reading is complete.
    for name, page in live.pages.items():
        if page.get("background") and name not in live._page_copies:
            live._refresh_page_in_background(name, page["path"])

    live.cache.pop("network_stats", None)
    live._refresh_locked()

    call("put_reading", {"item": live.cache["network_stats"]})


class Default(WorkerEntrypoint):

    async def fetch(self, request):
        return await wsgi.fetch(_load_app(self.env), request, self.env)

    async def scheduled(self, controller, env=None, ctx=None):
        _copy_env(self.env)
        call = _hub_call(self.env)
        started = time.time()

        for step in range(3):

            try:
                _refresh_reading(call)

            except Exception as error:
                print("EXIOM Explorer refresh failed:", type(error).__name__, error)

            if step < 2:
                delay = started + (step + 1) * READING_INTERVAL_SECONDS - time.time()

                if delay > 0:
                    await asyncio.sleep(delay)


class UsageHubObject(DurableObject):

    def __init__(self, ctx, env):
        super().__init__(ctx, env)
        _copy_env(env)

        from usage_hub import UsageHub

        sql = getattr(ctx, "_ctx", ctx).storage.sql

        def run(query, params):
            return sql.exec(query, *params).raw().toArray().to_py()

        self.hub = UsageHub(run)

    async def exchange(self, message):
        return self.hub.call(str(message))
