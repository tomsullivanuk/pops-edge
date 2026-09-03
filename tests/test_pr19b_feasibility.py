import hashlib
import json
import tempfile
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pr19b_feasibility as study


def _game(game_pk, start, home, away, home_score, away_score, *, status="Final", game_type="R", season="2026", doubleheader="N", game_number=1):
    return {
        "doubleHeader": doubleheader,
        "gameDate": start,
        "gameNumber": game_number,
        "gamePk": game_pk,
        "gameType": game_type,
        "officialDate": start[:10],
        "season": season,
        "status": {"abstractGameState": status, "detailedState": status},
        "teams": {
            "away": {"isWinner": away_score > home_score, "score": away_score, "team": {"id": away}},
            "home": {"isWinner": home_score > away_score, "score": home_score, "team": {"id": home}},
        },
    }


def _write_json_bytes(path, value, *, newline=False):
    body = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    if newline:
        body += b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    return hashlib.sha256(body).hexdigest()


def _add_page(root, index, provider, purpose, request_identity, payload):
    raw_body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    raw_digest = hashlib.sha256(raw_body).hexdigest()
    raw_path = root / "raw" / raw_digest[:2] / raw_digest
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(raw_body)
    normalized = {
        "completed_at": {"datetime_utc": f"2026-08-30T12:{index:02d}:00+00:00"},
        "disposition": "success",
        "endpoint": (
            f"https://statsapi.mlb.com/api/v1/schedule?date={request_identity}&sportId=1"
            if provider == "mlb-stats-api"
            else "https://example.invalid/markets"
        ),
        "partition": None,
        "partition_position": None,
        "provider": provider,
        "purpose": purpose,
        "record_kind": "pr17c2-supporting-session-page",
        "request_identity": request_identity,
        "schema_version": "1",
        "session_id": f"session:{index}",
        "started_at": {"datetime_utc": f"2026-08-30T12:{index:02d}:00+00:00"},
    }
    normalized_body = json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode()
    normalized_digest = hashlib.sha256(normalized_body).hexdigest()
    normalized_path = root / "normalized" / normalized_digest[:2] / f"{normalized_digest}.json"
    normalized_path.parent.mkdir(parents=True, exist_ok=True)
    normalized_path.write_bytes(normalized_body)
    manifest_digest = hashlib.sha256(f"manifest-{index}".encode()).hexdigest()
    manifest = {
        "acquired_at": {"datetime_utc": f"2026-08-30T12:{index:02d}:00+00:00"},
        "command": "refresh-retrospective-supporting-page",
        "design_authority": "supporting",
        "disposition": "success",
        "manifest_entry_id": f"operations-manifest:{manifest_digest}",
        "normalized_object_id": f"normalized:{normalized_digest}",
        "provider_id": provider,
        "raw_object_sha256": raw_digest,
    }
    _write_json_bytes(root / "manifest" / manifest_digest[:2] / f"{manifest_digest}.json", manifest)


def _tree_digest(root):
    return study.digest_value(
        [(str(path.relative_to(root)), hashlib.sha256(path.read_bytes()).hexdigest()) for path in sorted(root.rglob("*")) if path.is_file()]
    )


def _fixture_archive(tmp_path):
    root = tmp_path / "archive"
    games = [
        _game(1, "2026-04-01T20:00:00Z", 10, 20, 5, 3),
        _game(2, "2026-07-10T20:00:00Z", 20, 10, 2, 4),
        _game(3, "2026-08-10T20:00:00Z", 10, 20, 6, 1),
    ]
    for index, game in enumerate(games, 1):
        payload = {"dates": [{"date": game["officialDate"], "games": [game]}]}
        _add_page(root, index, "mlb-stats-api", "schedule", game["officialDate"], payload)
    _add_page(root, 9, "kalshi", "catalog", "market-page", {"markets": [{"marketPrice": 51}]})
    config = tmp_path / "config.json"
    config.write_text(
        json.dumps(
            {
                "mode": "activated",
                "namespace": "kalshi-mlb-prospective",
                "primary_root": str(root),
                "timezone_name": "America/New_York",
            }
        )
    )
    return root, config


def _resolved(game_pk, start, home, away, home_score, away_score, *, season="2026", disposition="eligible"):
    label = int(home_score > away_score) if disposition == "eligible" else None
    return study.ResolvedGame(
        game_pk,
        season,
        "R",
        start,
        start.date().isoformat(),
        home,
        away,
        1,
        "N",
        home_score if disposition == "eligible" else None,
        away_score if disposition == "eligible" else None,
        label,
        disposition,
        ("final",),
    )


def _model_rows(start_pk, count, split):
    rows = []
    for index in range(count):
        value = ((index % 7) - 3) / 5
        rows.append(
            {
                "features": [format(value, ".17g"), format(((index * 3) % 11 - 5) / 4, ".17g"), format(((index * 5) % 13 - 6) / 6, ".17g")],
                "game_pk": start_pk + index,
                "label": int(index % 3 != 0),
                "split": split,
            }
        )
    return rows


def test_freeze_is_read_only_market_independent_and_ordered(tmp_path):
    archive, config = _fixture_archive(tmp_path)
    before = _tree_digest(archive)
    result = study.freeze_study(
        config_path=config,
        output_dir=tmp_path / "output",
        source_revision="1" * 40,
        source_tree="2" * 40,
    )
    assert _tree_digest(archive) == before
    assert result["split_counts"] == {"training": 1, "validation": 1, "test": 1}
    snapshot = study.read_json(tmp_path / "output" / "source_snapshot_manifest.json")
    assert {page["provider"] for page in snapshot["pages"]} == {"mlb-stats-api"}
    seal = study.read_json(tmp_path / "output" / "protocol_seal.json")
    assert [event["sequence"] for event in seal["freeze_sequence"]] == [1, 2]
    evidence = study.read_json(tmp_path / "output" / "freeze_evidence.json")
    assert evidence["fitting_performed"] is False
    assert evidence["test_aggregate_calculated"] is False
    test_features = study.read_json(tmp_path / "output" / "test_features.json")
    assert "label" not in test_features[0]


def test_market_field_and_provenance_scan_fails_closed():
    assert study._scan_prohibited_fields({"nested": {"market_price": 0.5}}) == ["$.nested.market_price"]
    assert study._scan_prohibited_fields({"gamePk": 1, "score": 4}) == []


def test_eight_hour_proxy_includes_equality_and_excludes_later_start():
    target_start = datetime(2026, 8, 10, 20, tzinfo=timezone.utc)
    target = _resolved(100, target_start, 1, 2, 5, 4)
    boundary = target_start - timedelta(hours=6)
    included = _resolved(1, boundary - timedelta(hours=8), 1, 3, 2, 1)
    too_late = _resolved(2, boundary - timedelta(hours=8) + timedelta(seconds=1), 1, 4, 8, 0)
    history, tied = study._team_history(1, target, (included, too_late, target))
    assert [item[1] for item in history] == [1]
    assert tied is False


def test_same_season_only_and_target_outcome_separation():
    target_start = datetime(2026, 8, 10, 20, tzinfo=timezone.utc)
    target = _resolved(100, target_start, 1, 2, 5, 4)
    prior = _resolved(1, target_start - timedelta(days=2), 1, 3, 2, 1)
    prior_other_season = _resolved(2, target_start - timedelta(days=3), 1, 4, 99, 0, season="2025")
    first, issue = study.feature_snapshot(target, (prior, prior_other_season, target))
    changed_target = replace(target, home_score=0, away_score=10, label=0)
    second, second_issue = study.feature_snapshot(changed_target, (prior, prior_other_season, changed_target))
    assert issue is second_issue is None
    assert first == second


def test_recent_ten_equal_start_tie_fails_closed():
    target_start = datetime(2026, 8, 20, 20, tzinfo=timezone.utc)
    target = _resolved(100, target_start, 1, 99, 5, 4)
    histories = []
    for index in range(11):
        start = target_start - timedelta(days=20 - index)
        if index == 1:
            start = target_start - timedelta(days=20)
        histories.append(_resolved(index + 1, start, 1, 20 + index, 3, 2))
    features, issue = study.feature_snapshot(target, tuple(histories) + (target,))
    assert features is None
    assert issue == "recent_ten_schedule_tie"


def test_invalid_statuses_remain_visible():
    for status, expected in (("Postponed", "postponed"), ("Suspended", "suspended_or_resumed"), ("Cancelled", "cancelled")):
        observation = study.GameObservation(
            1,
            "2026",
            "R",
            datetime(2026, 5, 1, 20, tzinfo=timezone.utc),
            "2026-05-01",
            10,
            20,
            1,
            "N",
            status.lower(),
            None,
            None,
            None,
            None,
            "a" * 64,
        )
        assert study.resolve_game(1, (observation,)).disposition == expected


def test_schedule_revision_and_outcome_ambiguity_fail_closed():
    base = study.GameObservation(
        1,
        "2026",
        "R",
        datetime(2026, 5, 1, 20, tzinfo=timezone.utc),
        "2026-05-01",
        10,
        20,
        1,
        "N",
        "final",
        5,
        4,
        True,
        False,
        "a" * 64,
    )
    revised = replace(base, scheduled_start=base.scheduled_start + timedelta(hours=1), source_raw_digest="b" * 64)
    assert study.resolve_game(1, (base, revised)).disposition == "schedule_evolution_ambiguous"
    conflict = replace(base, home_score=2, away_score=7, home_is_winner=False, away_is_winner=True, source_raw_digest="c" * 64)
    assert study.resolve_game(1, (base, conflict)).disposition == "outcome_ambiguous"


def test_missing_outcome_and_doubleheader_ambiguity_remain_visible():
    base = study.GameObservation(
        1,
        "2026",
        "R",
        datetime(2026, 5, 1, 20, tzinfo=timezone.utc),
        "2026-05-01",
        10,
        20,
        1,
        "N",
        "scheduled",
        None,
        None,
        None,
        None,
        "a" * 64,
    )
    assert study.resolve_game(1, (base,)).disposition == "outcome_unresolved"
    ambiguous_doubleheader = replace(
        base,
        status="final",
        home_score=5,
        away_score=4,
        home_is_winner=True,
        away_is_winner=False,
        game_number=None,
        doubleheader="S",
    )
    assert study.resolve_game(1, (ambiguous_doubleheader,)).disposition == "doubleheader_ambiguous"


def test_model_is_input_order_independent_and_split_isolated():
    training = _model_rows(1, 45, "training")
    validation = _model_rows(100, 24, "validation")
    common = {
        "dependency_identity": {"python": "test"},
        "protocol_digest": "a" * 64,
        "dataset_digest": "b" * 64,
        "source_revision": "c" * 40,
        "source_tree": "d" * 40,
        "code_digest": "e" * 64,
    }
    forward = study.fit_model_bundle(training, validation, **common)
    reverse = study.fit_model_bundle(list(reversed(training)), list(reversed(validation)), **common)
    assert forward == reverse
    changed_validation = [
        dict(row, features=[format(float(row["features"][0]) + index / 100, ".17g"), *row["features"][1:]])
        for index, row in enumerate(validation)
    ]
    changed = study.fit_model_bundle(training, changed_validation, **common)
    assert changed["scaler"] == forward["scaler"]
    assert changed["primary_estimator"] == forward["primary_estimator"]


def test_metrics_bootstrap_and_classification_are_deterministic():
    report, briers = study.metric_report(["0.2", "0.8", "0.4", "0.6"], [0, 1, 1, 0])
    reverse, reverse_briers = study.metric_report(["0.6", "0.4", "0.8", "0.2"], [0, 1, 1, 0])
    assert report["brier"] == reverse["brier"]
    assert report["wace"] == reverse["wace"]
    seed = {"fixed": "identity"}
    interval = study.paired_bootstrap(briers, seed)
    assert interval == study.paired_bootstrap(list(reversed(briers)), seed)
    model = {"brier": "0.20", "log_loss": "0.60"}
    baselines = {"a": {"brier": "0.21", "log_loss": "0.60"}, "b": {"brier": "0.22", "log_loss": "0.61"}}
    assert study.classify_signal(model, baselines, {"a": {"lower": "0"}, "b": {"lower": "0.01"}}) == "BASIC SIGNAL"
    assert study.classify_signal(model, baselines, {"a": {"lower": "0.001"}, "b": {"lower": "0.01"}}) == "CREDIBLE SIGNAL"
    equal_baseline = dict(baselines, a={"brier": "0.20", "log_loss": "0.60"})
    assert study.classify_signal(model, equal_baseline, {"a": {"lower": "1"}, "b": {"lower": "1"}}) == "NO BASIC SIGNAL"


def test_second_test_evaluation_is_refused_before_any_work(tmp_path):
    output = tmp_path / "sealed"
    output.mkdir()
    (output / "test_opened.marker.json").write_text("{}")
    try:
        study.evaluate_once(output_dir=output)
    except study.FeasibilityError as exc:
        assert "second evaluation" in str(exc)
    else:
        raise AssertionError("second sealed-test evaluation was not refused")


def load_tests(loader, standard_tests, pattern):
    suite = unittest.TestSuite()
    temporary_tests = (test_freeze_is_read_only_market_independent_and_ordered, test_second_test_evaluation_is_refused_before_any_work)
    ordinary_tests = (
        test_market_field_and_provenance_scan_fails_closed,
        test_eight_hour_proxy_includes_equality_and_excludes_later_start,
        test_same_season_only_and_target_outcome_separation,
        test_recent_ten_equal_start_tie_fails_closed,
        test_invalid_statuses_remain_visible,
        test_schedule_revision_and_outcome_ambiguity_fail_closed,
        test_missing_outcome_and_doubleheader_ambiguity_remain_visible,
        test_model_is_input_order_independent_and_split_isolated,
        test_metrics_bootstrap_and_classification_are_deterministic,
    )
    for function in ordinary_tests:
        suite.addTest(unittest.FunctionTestCase(function, description=function.__name__))
    for function in temporary_tests:
        def run_with_temporary(function=function):
            with tempfile.TemporaryDirectory() as directory:
                function(Path(directory))
        suite.addTest(unittest.FunctionTestCase(run_with_temporary, description=function.__name__))
    return suite
