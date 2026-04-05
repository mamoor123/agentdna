"""Tests for the Trust Scoring Engine."""

import pytest

from agentdna.trust.scorer import (
    LatencyStats,
    QualityStats,
    TaskStats,
    TrustScorer,
    TrustScoreResult,
    UptimeStats,
    compute_trust_score,
)


class TestTrustScoreResult:
    def test_tier_exceptional(self):
        r = TrustScoreResult(total=95)
        assert r.tier == "Exceptional"
        assert r.badge == "🏆"

    def test_tier_excellent(self):
        r = TrustScoreResult(total=80)
        assert r.tier == "Excellent"
        assert r.badge == "⭐"

    def test_tier_good(self):
        r = TrustScoreResult(total=65)
        assert r.tier == "Good"
        assert r.badge == "✅"

    def test_tier_fair(self):
        r = TrustScoreResult(total=45)
        assert r.tier == "Fair"
        assert r.badge == "⚠️"

    def test_tier_unverified(self):
        r = TrustScoreResult(total=20)
        assert r.tier == "Unverified"
        assert r.badge == "❓"

    def test_boundary_90(self):
        r = TrustScoreResult(total=90)
        assert r.tier == "Exceptional"

    def test_boundary_75(self):
        r = TrustScoreResult(total=75)
        assert r.tier == "Excellent"

    def test_to_dict(self):
        r = TrustScoreResult(total=85, task_completion=35, response_quality=22)
        d = r.to_dict()
        assert d["total"] == 85
        assert d["tier"] == "Excellent"
        assert d["badge"] == "⭐"


class TestTaskStats:
    def test_completion_rate(self):
        t = TaskStats(total_submitted=100, total_completed=95)
        assert t.completion_rate == 0.95

    def test_completion_rate_zero(self):
        t = TaskStats()
        assert t.completion_rate == 0.0

    def test_completion_rate_perfect(self):
        t = TaskStats(total_submitted=50, total_completed=50)
        assert t.completion_rate == 1.0


class TestLatencyStats:
    def test_sla_adherence(self):
        l = LatencyStats(tasks_within_sla=90, total_tasks_with_timing=100)
        assert l.sla_adherence_rate == 0.9

    def test_sla_no_data(self):
        l = LatencyStats()
        assert l.sla_adherence_rate == 1.0  # benefit of the doubt


class TestUptimeStats:
    def test_uptime_rate(self):
        u = UptimeStats(total_checks=1000, successful_checks=997)
        assert u.uptime_rate == pytest.approx(0.997)

    def test_uptime_no_data(self):
        u = UptimeStats()
        assert u.uptime_rate == 0.0


class TestTrustScorer:
    def setup_method(self):
        self.scorer = TrustScorer()

    def test_no_data_returns_neutral(self):
        """With no data, scores should be neutral (half of max)."""
        result = self.scorer.compute(
            tasks=TaskStats(),
            quality=QualityStats(),
            latency=LatencyStats(),
            uptime=UptimeStats(),
        )
        # Each component should be ~half of max
        assert 15 <= result.task_completion <= 25  # half of 40 = 20
        assert 10 <= result.response_quality <= 15  # half of 25 = 12
        assert 5 <= result.latency_reliability <= 10  # half of 15 = 7
        assert 3 <= result.uptime_score <= 7  # half of 10 = 5
        assert result.confidence == "low"

    def test_perfect_agent(self):
        """Perfect agent should score near 100."""
        result = self.scorer.compute(
            tasks=TaskStats(
                total_submitted=100,
                total_completed=100,
                total_failed=0,
                total_timed_out=0,
            ),
            quality=QualityStats(
                avg_rating=5.0,
                review_count=50,
                llm_judge_score=95,
                has_llm_evaluation=True,
            ),
            latency=LatencyStats(
                tasks_within_sla=100,
                total_tasks_with_timing=100,
                promised_latency_seconds=5.0,
            ),
            uptime=UptimeStats(
                total_checks=1000,
                successful_checks=999,
            ),
            verified=True,
        )
        assert result.total >= 90
        assert result.tier == "Exceptional"
        assert result.confidence == "high"

    def test_poor_agent(self):
        """Poor agent should score low."""
        result = self.scorer.compute(
            tasks=TaskStats(
                total_submitted=100,
                total_completed=30,
                total_failed=50,
                total_timed_out=20,
            ),
            quality=QualityStats(
                avg_rating=1.5,
                review_count=20,
            ),
            latency=LatencyStats(
                tasks_within_sla=20,
                total_tasks_with_timing=100,
            ),
            uptime=UptimeStats(
                total_checks=500,
                successful_checks=300,
            ),
        )
        assert result.total <= 50
        assert result.tier in ("Fair", "Unverified")

    def test_verification_bonus(self):
        """Verified agent should get +10 points."""
        tasks = TaskStats(total_submitted=50, total_completed=45)
        quality = QualityStats(avg_rating=4.0, review_count=10)
        latency = LatencyStats(tasks_within_sla=45, total_tasks_with_timing=50)
        uptime = UptimeStats(total_checks=100, successful_checks=98)

        unverified = self.scorer.compute(tasks, quality, latency, uptime, verified=False)
        verified = self.scorer.compute(tasks, quality, latency, uptime, verified=True)

        assert verified.total - unverified.total == 10

    def test_warnings_on_low_data(self):
        """Should warn when there's insufficient data."""
        result = self.scorer.compute(
            tasks=TaskStats(total_submitted=3, total_completed=3),
            quality=QualityStats(),
            latency=LatencyStats(),
            uptime=UptimeStats(),
        )
        assert len(result.warnings) > 0

    def test_timeout_penalty(self):
        """Agents with many timeouts should be penalized."""
        good = self.scorer.compute(
            tasks=TaskStats(total_submitted=100, total_completed=90, total_failed=10),
            quality=QualityStats(),
            latency=LatencyStats(),
            uptime=UptimeStats(),
        )
        bad = self.scorer.compute(
            tasks=TaskStats(total_submitted=100, total_completed=90, total_timed_out=10),
            quality=QualityStats(),
            latency=LatencyStats(),
            uptime=UptimeStats(),
        )
        # Timeouts should be penalized more than failures
        assert bad.task_completion < good.task_completion


class TestComputeTrustScore:
    def test_convenience_function(self):
        """The convenience function should work end-to-end."""
        score = compute_trust_score(
            total_submitted=150,
            total_completed=142,
            avg_rating=4.6,
            review_count=45,
            uptime_checks=720,
            uptime_successes=715,
            verified=True,
        )
        assert score.total > 70
        assert score.tier in ("Excellent", "Exceptional", "Good")

    def test_convenience_function_minimal(self):
        """Should work with minimal data."""
        score = compute_trust_score(total_submitted=5, total_completed=4)
        assert 0 <= score.total <= 100
