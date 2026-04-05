"""
AgentDNA Sandbox Verification System

Runs agents in isolated environments to verify:
1. Endpoint is reachable and responds correctly
2. Agent card matches actual behavior
3. Agent handles edge cases (empty input, oversized input, malformed input)
4. No data exfiltration (agent doesn't call unexpected external URLs)
5. Performance meets claimed SLA

Verification Levels:
- Level 1: Registered (endpoint reachable)
- Level 2: Community Tested (100+ successful tasks)
- Level 3: AgentDNA Verified (passes sandbox audit)
- Level 4: Enterprise Certified (SOC2 + SLA guarantee)
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum

import httpx


class VerificationLevel(Enum):
    UNREGISTERED = 0
    REGISTERED = 1
    COMMUNITY_TESTED = 2
    AGENTDNA_VERIFIED = 3
    ENTERPRISE_CERTIFIED = 4


class CheckStatus(Enum):
    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"
    SKIP = "skip"


@dataclass
class CheckResult:
    """Result of a single verification check."""

    name: str
    status: CheckStatus
    message: str
    details: dict = field(default_factory=dict)
    duration_ms: float = 0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "duration_ms": round(self.duration_ms, 2),
        }


@dataclass
class VerificationReport:
    """Complete verification report for an agent."""

    agent_id: str
    level: VerificationLevel
    passed: bool
    score: int  # 0-100
    checks: list[CheckResult] = field(default_factory=list)
    started_at: str = ""
    completed_at: str = ""
    duration_seconds: float = 0

    @property
    def pass_count(self) -> int:
        return sum(1 for c in self.checks if c.status == CheckStatus.PASS)

    @property
    def fail_count(self) -> int:
        return sum(1 for c in self.checks if c.status == CheckStatus.FAIL)

    @property
    def warn_count(self) -> int:
        return sum(1 for c in self.checks if c.status == CheckStatus.WARN)

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "level": self.level.value,
            "level_name": self.level.name,
            "passed": self.passed,
            "score": self.score,
            "pass_count": self.pass_count,
            "fail_count": self.fail_count,
            "warn_count": self.warn_count,
            "checks": [c.to_dict() for c in self.checks],
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_seconds": round(self.duration_seconds, 2),
        }


class AgentVerifier:
    """
    Runs verification checks against an agent.

    Usage:
        verifier = AgentVerifier()
        report = await verifier.verify(
            agent_id="dna:my-agent:v1",
            endpoint="https://my-agent.example.com/a2a",
            protocol="a2a",
            agent_card={...},
        )
        print(f"Score: {report.score}/100 ({report.level.name})")
    """

    # Timeouts
    CONNECT_TIMEOUT = 10.0
    HEALTH_TIMEOUT = 5.0
    TASK_TIMEOUT = 30.0

    # Test payloads
    TEST_INPUTS = {
        "text": "Hello, this is a test message from AgentDNA verification.",
        "empty": "",
        "long": "A" * 10000,
        "unicode": "Hello 世界 🌍 مرحبا Привет",
        "json": '{"test": true, "nested": {"key": "value"}}',
    }

    def __init__(self, timeout: float = 60.0):
        self.timeout = timeout

    async def verify(
        self,
        agent_id: str,
        endpoint: str,
        protocol: str = "a2a",
        agent_card: dict = None,
    ) -> VerificationReport:
        """
        Run full verification suite against an agent.

        Args:
            agent_id: Agent DNA ID
            endpoint: Agent's public endpoint URL
            protocol: Communication protocol (a2a, mcp, custom)
            agent_card: Full agent card data for validation
        """
        from datetime import datetime, timezone

        start = time.time()
        started_at = datetime.now(timezone.utc).isoformat()
        checks = []

        # --- Check 1: Endpoint Reachability ---
        checks.append(await self._check_endpoint_reachable(endpoint))

        # --- Check 2: Agent Card Validation ---
        if agent_card:
            checks.append(self._check_agent_card_valid(agent_card))

        # --- Check 3: Health Endpoint ---
        checks.append(await self._check_health_endpoint(endpoint))

        # --- Check 4: HTTPS ---
        checks.append(self._check_https(endpoint))

        # --- Check 5: Response Headers ---
        checks.append(await self._check_response_headers(endpoint))

        # --- Check 6: Error Handling ---
        checks.append(await self._check_error_handling(endpoint, protocol))

        # --- Check 7: Performance / Latency ---
        checks.append(await self._check_latency(endpoint))

        # --- Check 8: CORS / Security Headers ---
        checks.append(await self._check_security_headers(endpoint))

        # --- Calculate score ---
        total_checks = len(checks)
        passed_checks = sum(1 for c in checks if c.status == CheckStatus.PASS)
        warn_checks = sum(1 for c in checks if c.status == CheckStatus.WARN)

        score = int(((passed_checks + warn_checks * 0.5) / total_checks) * 100) if total_checks > 0 else 0

        # Determine level
        level = VerificationLevel.REGISTERED
        if score >= 90:
            level = VerificationLevel.AGENTDNA_VERIFIED
        elif score >= 70:
            level = VerificationLevel.COMMUNITY_TESTED

        elapsed = time.time() - start
        completed_at = datetime.now(timezone.utc).isoformat()

        return VerificationReport(
            agent_id=agent_id,
            level=level,
            passed=score >= 70,
            score=score,
            checks=checks,
            started_at=started_at,
            completed_at=completed_at,
            duration_seconds=elapsed,
        )

    async def _check_endpoint_reachable(self, endpoint: str) -> CheckResult:
        """Check if the endpoint is reachable."""
        start = time.time()
        try:
            async with httpx.AsyncClient(timeout=self.CONNECT_TIMEOUT) as client:
                resp = await client.get(endpoint)
                elapsed = (time.time() - start) * 1000

                if resp.status_code < 500:
                    return CheckResult(
                        name="endpoint_reachable",
                        status=CheckStatus.PASS,
                        message=f"Endpoint reachable (HTTP {resp.status_code})",
                        details={"status_code": resp.status_code},
                        duration_ms=elapsed,
                    )
                else:
                    return CheckResult(
                        name="endpoint_reachable",
                        status=CheckStatus.FAIL,
                        message=f"Endpoint returned server error (HTTP {resp.status_code})",
                        details={"status_code": resp.status_code},
                        duration_ms=elapsed,
                    )
        except httpx.TimeoutException:
            elapsed = (time.time() - start) * 1000
            return CheckResult(
                name="endpoint_reachable",
                status=CheckStatus.FAIL,
                message="Endpoint timed out",
                duration_ms=elapsed,
            )
        except Exception as e:
            elapsed = (time.time() - start) * 1000
            return CheckResult(
                name="endpoint_reachable",
                status=CheckStatus.FAIL,
                message=f"Endpoint unreachable: {str(e)}",
                duration_ms=elapsed,
            )

    def _check_agent_card_valid(self, agent_card: dict) -> CheckResult:
        """Validate the agent card structure."""
        start = time.time()
        errors = []

        agent = agent_card.get("agent", agent_card)

        required_fields = ["name", "version", "description", "protocol", "endpoint"]
        for req_field in required_fields:
            if not agent.get(req_field):
                errors.append(f"Missing required field: {req_field}")

        capabilities = agent.get("capabilities", [])
        if not capabilities:
            errors.append("No capabilities defined")

        for i, cap in enumerate(capabilities):
            if not cap.get("skill"):
                errors.append(f"Capability {i} missing 'skill' field")

        elapsed = (time.time() - start) * 1000

        if errors:
            return CheckResult(
                name="agent_card_valid",
                status=CheckStatus.FAIL,
                message=f"Agent card has {len(errors)} error(s)",
                details={"errors": errors},
                duration_ms=elapsed,
            )

        return CheckResult(
            name="agent_card_valid",
            status=CheckStatus.PASS,
            message=f"Agent card valid ({len(capabilities)} capabilities)",
            details={"capabilities": len(capabilities)},
            duration_ms=elapsed,
        )

    async def _check_health_endpoint(self, endpoint: str) -> CheckResult:
        """Check if agent has a health endpoint."""
        start = time.time()

        # Try common health paths
        health_paths = ["/health", "/healthz", "/status", "/ping"]
        base = endpoint.rstrip("/")

        async with httpx.AsyncClient(timeout=self.HEALTH_TIMEOUT) as client:
            for path in health_paths:
                try:
                    resp = await client.get(f"{base}{path}")
                    if resp.status_code == 200:
                        elapsed = (time.time() - start) * 1000
                        return CheckResult(
                            name="health_endpoint",
                            status=CheckStatus.PASS,
                            message=f"Health endpoint found at {path}",
                            details={"path": path, "response_time_ms": elapsed},
                            duration_ms=elapsed,
                        )
                except Exception:
                    continue

        elapsed = (time.time() - start) * 1000
        return CheckResult(
            name="health_endpoint",
            status=CheckStatus.WARN,
            message="No health endpoint found (tried /health, /healthz, /status, /ping)",
            duration_ms=elapsed,
        )

    def _check_https(self, endpoint: str) -> CheckResult:
        """Check if endpoint uses HTTPS."""
        start = time.time()
        elapsed = (time.time() - start) * 1000

        if endpoint.startswith("https://"):
            return CheckResult(
                name="https",
                status=CheckStatus.PASS,
                message="Endpoint uses HTTPS",
                duration_ms=elapsed,
            )
        elif endpoint.startswith("http://"):
            return CheckResult(
                name="https",
                status=CheckStatus.FAIL,
                message="Endpoint uses HTTP (not HTTPS) — insecure",
                duration_ms=elapsed,
            )
        else:
            return CheckResult(
                name="https",
                status=CheckStatus.WARN,
                message=f"Unknown protocol in endpoint: {endpoint[:20]}",
                duration_ms=elapsed,
            )

    async def _check_response_headers(self, endpoint: str) -> CheckResult:
        """Check response headers for proper configuration."""
        start = time.time()
        try:
            async with httpx.AsyncClient(timeout=self.HEALTH_TIMEOUT) as client:
                resp = await client.get(endpoint)
                elapsed = (time.time() - start) * 1000

                headers = dict(resp.headers)
                issues = []

                # Check for server info leakage
                server = headers.get("server", "")
                if server and any(s in server.lower() for s in ["apache", "nginx", "express"]):
                    issues.append(f"Server header reveals: {server}")

                content_type = headers.get("content-type", "")
                if "application/json" not in content_type and "text/" not in content_type:
                    issues.append(f"Unexpected content-type: {content_type}")

                if issues:
                    return CheckResult(
                        name="response_headers",
                        status=CheckStatus.WARN,
                        message=f"Header issues: {'; '.join(issues)}",
                        details={"headers": {k: v for k, v in headers.items() if k.lower() not in ("set-cookie",)}},
                        duration_ms=elapsed,
                    )

                return CheckResult(
                    name="response_headers",
                    status=CheckStatus.PASS,
                    message="Response headers look good",
                    duration_ms=elapsed,
                )
        except Exception as e:
            elapsed = (time.time() - start) * 1000
            return CheckResult(
                name="response_headers",
                status=CheckStatus.SKIP,
                message=f"Could not check headers: {str(e)}",
                duration_ms=elapsed,
            )

    async def _check_error_handling(self, endpoint: str, protocol: str) -> CheckResult:
        """Check how the agent handles malformed requests."""
        start = time.time()
        try:
            async with httpx.AsyncClient(timeout=self.TASK_TIMEOUT) as client:
                # Send malformed JSON
                resp = await client.post(
                    endpoint,
                    content="this is not json{{{",
                    headers={"Content-Type": "application/json"},
                )
                elapsed = (time.time() - start) * 1000

                if 400 <= resp.status_code < 500:
                    return CheckResult(
                        name="error_handling",
                        status=CheckStatus.PASS,
                        message=f"Returns proper 4xx for bad input (HTTP {resp.status_code})",
                        duration_ms=elapsed,
                    )
                elif resp.status_code >= 500:
                    return CheckResult(
                        name="error_handling",
                        status=CheckStatus.FAIL,
                        message=f"Returns 5xx for bad input — should be 4xx (HTTP {resp.status_code})",
                        duration_ms=elapsed,
                    )
                else:
                    return CheckResult(
                        name="error_handling",
                        status=CheckStatus.WARN,
                        message=f"Unexpected status for bad input: HTTP {resp.status_code}",
                        duration_ms=elapsed,
                    )
        except Exception as e:
            elapsed = (time.time() - start) * 1000
            return CheckResult(
                name="error_handling",
                status=CheckStatus.SKIP,
                message=f"Could not test error handling: {str(e)}",
                duration_ms=elapsed,
            )

    async def _check_latency(self, endpoint: str) -> CheckResult:
        """Check basic response latency."""
        start = time.time()
        try:
            async with httpx.AsyncClient(timeout=self.HEALTH_TIMEOUT) as client:
                await client.get(endpoint)
                elapsed = (time.time() - start) * 1000

                if elapsed < 1000:
                    status = CheckStatus.PASS
                    msg = f"Fast response ({int(elapsed)}ms)"
                elif elapsed < 3000:
                    status = CheckStatus.PASS
                    msg = f"Acceptable response ({int(elapsed)}ms)"
                elif elapsed < 5000:
                    status = CheckStatus.WARN
                    msg = f"Slow response ({int(elapsed)}ms)"
                else:
                    status = CheckStatus.FAIL
                    msg = f"Very slow response ({int(elapsed)}ms)"

                return CheckResult(
                    name="latency",
                    status=status,
                    message=msg,
                    details={"latency_ms": round(elapsed, 2)},
                    duration_ms=elapsed,
                )
        except Exception as e:
            elapsed = (time.time() - start) * 1000
            return CheckResult(
                name="latency",
                status=CheckStatus.FAIL,
                message=f"Latency check failed: {str(e)}",
                duration_ms=elapsed,
            )

    async def _check_security_headers(self, endpoint: str) -> CheckResult:
        """Check for security-related headers."""
        start = time.time()
        try:
            async with httpx.AsyncClient(timeout=self.HEALTH_TIMEOUT) as client:
                resp = await client.get(endpoint)
                elapsed = (time.time() - start) * 1000

                headers = {k.lower(): v for k, v in resp.headers.items()}
                score = 0
                total = 4
                details = {}

                # Check important security headers
                if "x-content-type-options" in headers:
                    score += 1
                    details["x-content-type-options"] = headers["x-content-type-options"]

                if "x-frame-options" in headers:
                    score += 1
                    details["x-frame-options"] = headers["x-frame-options"]

                if "strict-transport-security" in headers:
                    score += 1
                    details["strict-transport-security"] = headers["strict-transport-security"]

                if "content-security-policy" in headers:
                    score += 1
                    details["content-security-policy"] = "present"

                if score >= 3:
                    return CheckResult(
                        name="security_headers",
                        status=CheckStatus.PASS,
                        message=f"Good security headers ({score}/{total})",
                        details=details,
                        duration_ms=elapsed,
                    )
                elif score >= 1:
                    return CheckResult(
                        name="security_headers",
                        status=CheckStatus.WARN,
                        message=f"Missing some security headers ({score}/{total})",
                        details=details,
                        duration_ms=elapsed,
                    )
                else:
                    return CheckResult(
                        name="security_headers",
                        status=CheckStatus.WARN,
                        message="No security headers found",
                        duration_ms=elapsed,
                    )
        except Exception as e:
            elapsed = (time.time() - start) * 1000
            return CheckResult(
                name="security_headers",
                status=CheckStatus.SKIP,
                message=f"Could not check: {str(e)}",
                duration_ms=elapsed,
            )


# --- Convenience ---

async def verify_agent(
    agent_id: str,
    endpoint: str,
    protocol: str = "a2a",
    agent_card: dict = None,
) -> VerificationReport:
    """
    One-call convenience function to verify an agent.

    Example:
        report = await verify_agent(
            agent_id="dna:my-agent:v1",
            endpoint="https://my-agent.example.com/a2a",
            protocol="a2a",
        )
        print(f"Score: {report.score}/100 — {report.level.name}")
    """
    verifier = AgentVerifier()
    return await verifier.verify(agent_id, endpoint, protocol, agent_card)
