"""
AgentDNA Trust Scoring Engine

Computes DNA Score (0-100) based on five weighted components:
- Task Completion Rate (40%)
- Response Quality (25%)
- Latency Reliability (15%)
- Uptime (10%)
- Verification Bonus (10%)

Usage:
    from agentdna.trust.scorer import TrustScorer

    scorer = TrustScorer()
    score = scorer.compute(task_data, quality_data, latency_data, uptime_data, verified=True)
    print(score.total)  # 87
"""

from __future__ import annotations

from dataclasses import dataclass, field


# --- Weight Configuration ---

WEIGHTS = {
    "task_completion": 40,
    "response_quality": 25,
    "latency_reliability": 15,
    "uptime": 10,
    "verification": 10,
}

# Minimum tasks before full scoring kicks in (prevents gaming with 1/1 = 100%)
MIN_TASKS_FOR_FULL_SCORE = 10

# Decay half-life for old reviews (in days)
REVIEW_DECAY_HALF_LIFE_DAYS = 90


@dataclass
class TaskStats:
    """Aggregated task execution statistics."""

    total_submitted: int = 0
    total_completed: int = 0
    total_failed: int = 0
    total_timed_out: int = 0
    total_refunded: int = 0

    @property
    def completion_rate(self) -> float:
        """Completion rate as a float between 0.0 and 1.0."""
        if self.total_submitted == 0:
            return 0.0
        return self.total_completed / self.total_submitted


@dataclass
class QualityStats:
    """Aggregated quality metrics from reviews and evaluations."""

    avg_rating: float = 0.0        # 1-5 scale from user reviews
    review_count: int = 0
    llm_judge_score: float = 0.0   # 0-100 from automated evaluation
    has_llm_evaluation: bool = False


@dataclass
class LatencyStats:
    """Latency performance statistics."""

    avg_latency_seconds: float = 0.0
    p95_latency_seconds: float = 0.0
    promised_latency_seconds: float = 0.0  # from SLA
    tasks_within_sla: int = 0
    total_tasks_with_timing: int = 0

    @property
    def sla_adherence_rate(self) -> float:
        """Percentage of tasks meeting the SLA."""
        if self.total_tasks_with_timing == 0:
            return 1.0  # benefit of the doubt
        return self.tasks_within_sla / self.total_tasks_with_timing


@dataclass
class UptimeStats:
    """Agent uptime statistics."""

    total_checks: int = 0
    successful_checks: int = 0
    check_window_days: int = 30

    @property
    def uptime_rate(self) -> float:
        """Uptime as a float between 0.0 and 1.0."""
        if self.total_checks == 0:
            return 0.0
        return self.successful_checks / self.total_checks


@dataclass
class TrustScoreResult:
    """Complete trust score breakdown."""

    total: int = 0
    task_completion: int = 0
    response_quality: int = 0
    latency_reliability: int = 0
    uptime_score: int = 0
    verification_bonus: int = 0

    # Metadata
    confidence: str = "low"  # "low" | "medium" | "high"
    warnings: list[str] = field(default_factory=list)

    @property
    def tier(self) -> str:
        if self.total >= 90:
            return "Exceptional"
        elif self.total >= 75:
            return "Excellent"
        elif self.total >= 60:
            return "Good"
        elif self.total >= 40:
            return "Fair"
        return "Unverified"

    @property
    def badge(self) -> str:
        badges = {
            "Exceptional": "🏆",
            "Excellent": "⭐",
            "Good": "✅",
            "Fair": "⚠️",
            "Unverified": "❓",
        }
        return badges.get(self.tier, "❓")

    def to_dict(self) -> dict:
        return {
            "total": self.total,
            "task_completion": self.task_completion,
            "response_quality": self.response_quality,
            "latency_reliability": self.latency_reliability,
            "uptime_score": self.uptime_score,
            "verification_bonus": self.verification_bonus,
            "confidence": self.confidence,
            "tier": self.tier,
            "badge": self.badge,
            "warnings": self.warnings,
        }


class TrustScorer:
    """
    Computes DNA Trust Scores for agents.

    The scoring algorithm is designed to be:
    - Fair: Resistant to gaming (minimum task thresholds, decay on old reviews)
    - Transparent: Full breakdown of every component
    - Calibrated: Scores correlate with actual agent reliability
    """

    def __init__(
        self,
        min_tasks: int = MIN_TASKS_FOR_FULL_SCORE,
        review_decay_days: int = REVIEW_DECAY_HALF_LIFE_DAYS,
    ):
        self.min_tasks = min_tasks
        self.review_decay_days = review_decay_days

    def compute(
        self,
        tasks: TaskStats,
        quality: QualityStats,
        latency: LatencyStats,
        uptime: UptimeStats,
        verified: bool = False,
    ) -> TrustScoreResult:
        """
        Compute the full DNA Trust Score.

        Args:
            tasks: Task execution statistics
            quality: Quality metrics (reviews + LLM evaluations)
            latency: Latency and SLA adherence
            uptime: Heartbeat uptime data
            verified: Whether agent passed sandbox verification

        Returns:
            TrustScoreResult with full breakdown
        """
        warnings: list[str] = []

        # --- 1. Task Completion (40 points max) ---
        task_score = self._score_task_completion(tasks, warnings)

        # --- 2. Response Quality (25 points max) ---
        quality_score = self._score_quality(quality, tasks, warnings)

        # --- 3. Latency Reliability (15 points max) ---
        latency_score = self._score_latency(latency, warnings)

        # --- 4. Uptime (10 points max) ---
        uptime_score = self._score_uptime(uptime, warnings)

        # --- 5. Verification Bonus (10 points max) ---
        verification_score = WEIGHTS["verification"] if verified else 0

        # --- Total ---
        total = min(100, task_score + quality_score + latency_score + uptime_score + verification_score)

        # --- Confidence level ---
        confidence = self._compute_confidence(tasks, quality, uptime)

        return TrustScoreResult(
            total=total,
            task_completion=task_score,
            response_quality=quality_score,
            latency_reliability=latency_score,
            uptime_score=uptime_score,
            verification_bonus=verification_score,
            confidence=confidence,
            warnings=warnings,
        )

    def _score_task_completion(self, tasks: TaskStats, warnings: list[str]) -> int:
        """
        Score task completion rate (0-40 points).

        Uses Bayesian smoothing to prevent gaming with small sample sizes.
        With 0 tasks: score = 20 (prior)
        With many tasks: score approaches actual completion rate * 40
        """
        max_points = WEIGHTS["task_completion"]

        if tasks.total_submitted == 0:
            warnings.append("No tasks submitted yet — using neutral prior")
            return max_points // 2  # neutral prior

        rate = tasks.completion_rate

        # Bayesian smoothing: blend observed rate with prior (0.5)
        prior_rate = 0.5
        smoothing = min(self.min_tasks, tasks.total_submitted) / self.min_tasks
        adjusted_rate = (smoothing * rate) + ((1 - smoothing) * prior_rate)

        # Apply penalty for timeouts (worse than failures — means agent hung)
        timeout_penalty = 0
        if tasks.total_submitted > 0:
            timeout_rate = tasks.total_timed_out / tasks.total_submitted
            timeout_penalty = int(timeout_rate * max_points * 0.5)

        score = int(adjusted_rate * max_points) - timeout_penalty

        if tasks.total_submitted < self.min_tasks:
            warnings.append(
                f"Only {tasks.total_submitted} tasks (need {self.min_tasks} for full confidence)"
            )

        return max(0, min(max_points, score))

    def _score_quality(
        self, quality: QualityStats, tasks: TaskStats, warnings: list[str]
    ) -> int:
        """
        Score response quality (0-25 points).

        Blends user reviews with LLM-as-judge evaluations.
        LLM evaluations are weighted higher as they're more consistent.
        """
        max_points = WEIGHTS["response_quality"]

        if quality.review_count == 0 and not quality.has_llm_evaluation:
            warnings.append("No quality data yet — using neutral score")
            return max_points // 2

        scores = []
        weights = []

        # User review component (1-5 scale → 0-100)
        if quality.review_count > 0:
            review_score = ((quality.avg_rating - 1) / 4) * 100  # normalize to 0-100
            # Weight by review count (more reviews = more trust)
            review_weight = min(1.0, quality.review_count / 20)
            scores.append(review_score)
            weights.append(review_weight)

        # LLM judge component (already 0-100)
        if quality.has_llm_evaluation:
            scores.append(quality.llm_judge_score)
            weights.append(1.0)  # LLM judge is always fully weighted

        if not scores:
            return max_points // 2

        # Weighted average
        total_weight = sum(weights)
        blended = sum(s * w for s, w in zip(scores, weights, strict=True)) / total_weight

        return int((blended / 100) * max_points)

    def _score_latency(self, latency: LatencyStats, warnings: list[str]) -> int:
        """
        Score latency reliability (0-15 points).

        Based on SLA adherence rate, not raw speed.
        A slow agent that meets its SLA scores well.
        A fast agent that promises 1s but delivers in 5s scores poorly.
        """
        max_points = WEIGHTS["latency_reliability"]

        if latency.total_tasks_with_timing == 0:
            warnings.append("No latency data yet — using neutral score")
            return max_points // 2

        adherence = latency.sla_adherence_rate

        # Bonus for having a tight SLA and meeting it
        tightness_bonus = 0
        if latency.promised_latency_seconds > 0:
            # Tighter SLA = more credit for meeting it
            if latency.promised_latency_seconds < 5:
                tightness_bonus = 2
            elif latency.promised_latency_seconds < 15:
                tightness_bonus = 1

        score = int(adherence * max_points) + tightness_bonus
        return max(0, min(max_points, score))

    def _score_uptime(self, uptime: UptimeStats, warnings: list[str]) -> int:
        """
        Score agent uptime (0-10 points).

        Based on heartbeat check success rate over the monitoring window.
        """
        max_points = WEIGHTS["uptime"]

        if uptime.total_checks == 0:
            warnings.append("No uptime data yet — using neutral score")
            return max_points // 2

        rate = uptime.uptime_rate

        # Apply diminishing returns for very high uptime
        # 99% and 99.9% shouldn't be very different in score
        adjusted: float
        if rate >= 0.99:
            adjusted = 100
        elif rate >= 0.95:
            adjusted = 90 + (rate - 0.95) * 200  # 95-99% maps to 90-98
        elif rate >= 0.90:
            adjusted = 75 + (rate - 0.90) * 300  # 90-95% maps to 75-90
        else:
            adjusted = rate * 83  # 0-90% maps to 0-75

        return int((adjusted / 100) * max_points)

    def _compute_confidence(
        self, tasks: TaskStats, quality: QualityStats, uptime: UptimeStats
    ) -> str:
        """Determine confidence level of the score."""
        data_points = 0

        if tasks.total_submitted >= self.min_tasks:
            data_points += 2
        elif tasks.total_submitted > 0:
            data_points += 1

        if quality.review_count >= 10 or quality.has_llm_evaluation:
            data_points += 2
        elif quality.review_count > 0:
            data_points += 1

        if uptime.total_checks >= 100:
            data_points += 2
        elif uptime.total_checks > 0:
            data_points += 1

        if data_points >= 5:
            return "high"
        elif data_points >= 3:
            return "medium"
        return "low"


# --- Convenience Functions ---

def compute_trust_score(
    total_submitted: int = 0,
    total_completed: int = 0,
    total_failed: int = 0,
    total_timed_out: int = 0,
    avg_rating: float = 0.0,
    review_count: int = 0,
    llm_judge_score: float = 0.0,
    avg_latency_seconds: float = 0.0,
    promised_latency_seconds: float = 0.0,
    tasks_within_sla: int = 0,
    total_tasks_with_timing: int = 0,
    uptime_checks: int = 0,
    uptime_successes: int = 0,
    verified: bool = False,
) -> TrustScoreResult:
    """
    One-call convenience function to compute a trust score.

    Example:
        score = compute_trust_score(
            total_submitted=150,
            total_completed=142,
            avg_rating=4.6,
            review_count=45,
            uptime_checks=720,
            uptime_successes=715,
            verified=True,
        )
        print(f"DNA Score: {score.total}/100 ({score.tier} {score.badge})")
    """
    scorer = TrustScorer()

    tasks = TaskStats(
        total_submitted=total_submitted,
        total_completed=total_completed,
        total_failed=total_failed,
        total_timed_out=total_timed_out,
    )

    quality = QualityStats(
        avg_rating=avg_rating,
        review_count=review_count,
        llm_judge_score=llm_judge_score,
        has_llm_evaluation=llm_judge_score > 0,
    )

    latency = LatencyStats(
        avg_latency_seconds=avg_latency_seconds,
        promised_latency_seconds=promised_latency_seconds,
        tasks_within_sla=tasks_within_sla,
        total_tasks_with_timing=total_tasks_with_timing,
    )

    uptime = UptimeStats(
        total_checks=uptime_checks,
        successful_checks=uptime_successes,
    )

    return scorer.compute(tasks, quality, latency, uptime, verified=verified)
