# ---------------------------------------------------------
# GUNICORN
# ---------------------------------------------------------
#
# Loaded automatically by `gunicorn app:app` when started
# from this directory.
#
# Why threads: almost all of a request's time is spent
# waiting on OpenAI or the Explorer, and an SSE stream holds
# its worker for the whole answer. With the default sync
# worker one stream blocks one whole process. gthread serves
# workers x threads requests at once, and threads share the
# per-process caches and usage counters (see "Task Docs/
# Task 10 - Cost Optimization.md"), so fewer, wider
# processes also mean more cache hits and an exact
# per-worker budget.
#
# Every value is overridable from the environment. This file
# deliberately imports nothing from the application.
# ---------------------------------------------------------

import os


def _int(name, fallback):
    try:
        return max(1, int(os.getenv(name, fallback)))
    except ValueError:
        return fallback


bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"

worker_class = "gthread"
workers = _int("WEB_CONCURRENCY", 2)
threads = _int("GUNICORN_THREADS", 8)

# Under gthread this is a worker liveness check (a worker
# whose main loop stops responding is restarted), not a
# per-request limit. Requests are bounded by the provider
# timeouts and deadlines in ai_provider.py.
timeout = _int("GUNICORN_TIMEOUT", 120)

# Lets in-flight answers finish on deploy or restart.
graceful_timeout = _int("GUNICORN_GRACEFUL_TIMEOUT", 30)

# Above a typical load balancer idle timeout, so the balancer
# closes idle connections first and never races us.
keepalive = _int("GUNICORN_KEEPALIVE", 75)

# Worker recycling stays OFF. Usage limits and the daily
# token ceilings live in each worker's memory ("Task Docs/
# Task 10 - Cost Optimization.md"), so a recycled worker
# would hand every client a fresh budget. Only enable it together with
# a shared store for those counters.
max_requests = 0

# Request-head limits, stated explicitly (these are
# gunicorn's own defaults except the header count, which is
# halved: the app reads a handful of headers). Oversized
# heads are refused before reaching Flask. Body size is
# bounded by the app (EXIOM_MAX_REQUEST_BYTES).
limit_request_line = 4094
limit_request_fields = 50
limit_request_field_size = 8190

# The access log records method, path and status only: the
# question travels in the POST body, never in a URL.
accesslog = "-"
errorlog = "-"
