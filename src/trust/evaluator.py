"""
LLM-as-Judge Quality Evaluator

Automatically evaluates agent output quality using an LLM.
Used to supplement user reviews with consistent, scalable quality signals.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional

import httpx


JUDGE_PROMPT = """You are an expert evaluator of AI agent outputs.

Rate the following agent output on a scale of 0-100 based on these criteria:

1. **Accuracy** (0-30): Is the output correct and factual?
2. **Completeness** (0-25): Does it fully address the task?
3. **Clarity** (0-20): Is it well-structured and easy to understand?
4. **Relevance** (0-15): Does it stay on-topic?
5. **Efficiency** (0-10): Is it concise without losing substance?

Respond ONLY with valid JSON:
{{
  "accuracy": <0-30>,
  "completeness": <0-25>,
  "clarity": <0-20>,
  "relevance": <0-15>,
  "efficiency": <0-10>,
  "total": <0-100>,
  "reasoning": "<brief explanation>"
}}

## Task
{task_description}

## Agent Output
{agent_output}

## Expected Quality (if known)
{expected_quality}"""


@dataclass
class EvaluationResult:
    """Result of an LLM-as-judge evaluation."""

    total: int = 0
    accuracy: int = 0
    completeness: int = 0
    clarity: int = 0
    relevance: int = 0
    efficiency: int = 0
    reasoning: str = ""
    raw_response: str = ""

    def to_dict(self) -> dict:
        return {
            "total": self.total,
            "accuracy": self.accuracy,
            "completeness": self.completeness,
            "clarity": self.clarity,
            "relevance": self.relevance,
            "efficiency": self.efficiency,
            "reasoning": self.reasoning,
        }


class QualityEvaluator:
    """
    Evaluates agent output quality using an LLM judge.

    Usage:
        evaluator = QualityEvaluator(model="gpt-4o-mini")
        result = evaluator.evaluate(
            task_description="Transcribe this audio file",
            agent_output="Meeting transcript: ...",
        )
        print(result.total)  # 85
    """

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        api_key: str = "",
        api_base: str = "https://api.openai.com/v1",
    ):
        self.model = model
        self.api_key = api_key
        self.api_base = api_base.rstrip("/")

    def evaluate(
        self,
        task_description: str,
        agent_output: str,
        expected_quality: str = "No reference available — evaluate on merit alone",
    ) -> EvaluationResult:
        """
        Evaluate agent output quality.

        Args:
            task_description: What the agent was asked to do
            agent_output: The agent's actual output
            expected_quality: Optional description of expected output

        Returns:
            EvaluationResult with score breakdown
        """
        prompt = JUDGE_PROMPT.format(
            task_description=task_description,
            agent_output=agent_output[:2000],  # truncate for token savings
            expected_quality=expected_quality,
        )

        try:
            response = self._call_llm(prompt)
            return self._parse_response(response)
        except Exception as e:
            return EvaluationResult(
                total=50,  # neutral fallback
                reasoning=f"Evaluation failed: {str(e)}",
            )

    def evaluate_batch(
        self,
        evaluations: list[dict],
    ) -> list[EvaluationResult]:
        """
        Evaluate multiple outputs in batch.

        Args:
            evaluations: List of dicts with 'task_description' and 'agent_output'

        Returns:
            List of EvaluationResults
        """
        results = []
        for eval_data in evaluations:
            result = self.evaluate(
                task_description=eval_data.get("task_description", ""),
                agent_output=eval_data.get("agent_output", ""),
                expected_quality=eval_data.get("expected_quality", ""),
            )
            results.append(result)
        return results

    def _call_llm(self, prompt: str) -> str:
        """Call the LLM API."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,  # low temp for consistent scoring
            "max_tokens": 300,
        }

        resp = httpx.post(
            f"{self.api_base}/chat/completions",
            headers=headers,
            json=payload,
            timeout=30.0,
        )
        resp.raise_for_status()

        data = resp.json()
        return data["choices"][0]["message"]["content"]

    def _parse_response(self, raw: str) -> EvaluationResult:
        """Parse LLM response into EvaluationResult."""
        # Strip markdown code blocks if present
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = "\n".join(cleaned.split("\n")[1:])
        if cleaned.endswith("```"):
            cleaned = "\n".join(cleaned.split("\n")[:-1])
        cleaned = cleaned.strip()

        try:
            data = json.loads(cleaned)
            return EvaluationResult(
                total=min(100, max(0, data.get("total", 50))),
                accuracy=min(30, max(0, data.get("accuracy", 15))),
                completeness=min(25, max(0, data.get("completeness", 12))),
                clarity=min(20, max(0, data.get("clarity", 10))),
                relevance=min(15, max(0, data.get("relevance", 7))),
                efficiency=min(10, max(0, data.get("efficiency", 5))),
                reasoning=data.get("reasoning", ""),
                raw_response=raw,
            )
        except (json.JSONDecodeError, KeyError):
            return EvaluationResult(
                total=50,
                reasoning=f"Failed to parse evaluation: {raw[:200]}",
                raw_response=raw,
            )
