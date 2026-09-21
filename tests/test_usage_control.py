import usage_control


def test_cost_estimate_applies_the_cached_input_discount():
    meter = usage_control.CostMeter()

    full_price = meter.estimate_cost("gpt-5-nano", 1_000_000, 0, 0)
    all_cached = meter.estimate_cost("gpt-5-nano", 1_000_000, 1_000_000, 0)

    assert full_price == 0.05
    assert all_cached == 0.005


def test_unknown_model_falls_back_to_default_rates():
    meter = usage_control.CostMeter()

    assert meter.estimate_cost("some-future-model", 1_000_000, 0, 0) > 0


def test_record_usage_accepts_provider_objects():

    class Details:
        cached_tokens = 400
        reasoning_tokens = 50

    class Usage:
        input_tokens = 1000
        output_tokens = 100
        input_tokens_details = Details()
        output_tokens_details = Details()

    meter = usage_control.CostMeter()
    recorded = meter.record_usage("gpt-5-nano", Usage(), "answer")

    assert recorded["input_tokens"] == 1000
    assert recorded["cached_input_tokens"] == 400
    assert recorded["reasoning_tokens"] == 50
    assert meter.snapshot()["by_route"]["answer"]["calls"] == 1


def test_record_usage_survives_missing_usage():
    meter = usage_control.CostMeter()

    recorded = meter.record_usage("gpt-5-nano", None, "answer")

    assert recorded["input_tokens"] == 0
    assert meter.snapshot()["provider_calls"] == 1


def test_record_usage_survives_rubbish_values():
    meter = usage_control.CostMeter()

    recorded = meter.record_usage(
        "gpt-5-nano",
        {"input_tokens": "oops", "output_tokens": -5},
        "answer"
    )

    assert recorded["input_tokens"] == 0
    assert recorded["output_tokens"] == 0


def test_snapshot_reports_free_response_rate():
    meter = usage_control.CostMeter()

    meter.record_free_response("greeting")
    meter.record_usage("gpt-5-nano", {"input_tokens": 10}, "answer")

    snapshot = meter.snapshot()

    assert snapshot["free_responses"] == 1
    assert snapshot["free_response_rate"] == 0.5
    assert snapshot["by_route"]["greeting"]["calls"] == 1


def test_snapshot_of_an_idle_meter_is_safe():
    assert usage_control.CostMeter().snapshot()["free_response_rate"] == 0.0


# ---------------------------------------------------------
# USAGE CONTROLLER
# ---------------------------------------------------------

class FakeClock:

    def __init__(self):
        self.value = 1_700_000_000.0

    def __call__(self):
        return self.value

    def advance(self, seconds):
        self.value += seconds


def build_controller(clock, **overrides):
    settings = {
        "requests_per_minute": 3,
        "requests_per_day": 10,
        "client_tokens_per_day": 1000,
        "global_tokens_per_day": 5000,
    }

    settings.update(overrides)

    return usage_control.UsageController(now=clock, **settings)


def test_requests_within_the_limit_are_allowed():
    controller = build_controller(FakeClock())

    assert controller.check("client").allowed


def test_burst_is_paced_per_minute():
    clock = FakeClock()
    controller = build_controller(clock)

    for _ in range(3):
        assert controller.check("client").allowed

    decision = controller.check("client")

    assert not decision.allowed
    assert decision.reason == "client_rate"
    assert decision.retry_after > 0


def test_pacing_window_recovers():
    clock = FakeClock()
    controller = build_controller(clock)

    for _ in range(3):
        controller.check("client")

    clock.advance(61)

    assert controller.check("client").allowed


def test_clients_are_paced_independently():
    controller = build_controller(FakeClock())

    for _ in range(3):
        controller.check("noisy")

    assert controller.check("quiet").allowed


def test_daily_request_ceiling_applies():
    clock = FakeClock()
    controller = build_controller(clock, requests_per_day=2)

    controller.check("client")
    controller.check("client")

    assert controller.check("client").reason == "client_daily_requests"


def test_client_token_budget_applies():
    controller = build_controller(FakeClock())

    controller.record_tokens("client", 1500)

    assert controller.check("client").reason == "client_daily_tokens"


def test_global_token_budget_protects_every_client():
    controller = build_controller(FakeClock())

    controller.record_tokens("whoever", 5000)

    assert controller.check("someone_else").reason == "global_daily_tokens"


def test_budgets_reset_on_a_new_day():
    clock = FakeClock()
    controller = build_controller(clock)

    controller.record_tokens("client", 5000)

    assert not controller.check("client").allowed

    clock.advance(86400)

    assert controller.check("client").allowed


def test_record_tokens_ignores_rubbish():
    controller = build_controller(FakeClock())

    controller.record_tokens("client", None)
    controller.record_tokens("client", -10)

    assert controller.check("client").allowed


def test_missing_client_id_is_still_tracked():
    controller = build_controller(FakeClock(), requests_per_minute=1)

    assert controller.check(None).allowed
    assert not controller.check(None).allowed
