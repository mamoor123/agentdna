"""
🧬 AgentDNA Demo — Run this to show off the product

Usage:
    pip install agentdna-sdk
    python demo.py
"""

from agentdna import observe, get_stats
import time
import random


# --- Simulated AI agents ---

@observe(name="transcriber", tags={"model": "whisper-v3"})
def transcribe(audio_path: str) -> str:
    """Simulated audio transcription agent."""
    time.sleep(random.uniform(0.1, 0.4))
    if random.random() < 0.08:
        raise ValueError(f"Unsupported audio format: {audio_path.split('.')[-1]}")
    return f"[Transcribed] Hello from {audio_path}"


@observe(name="summarizer", tags={"model": "gpt-4"})
def summarize(text: str) -> str:
    """Simulated text summarization agent."""
    time.sleep(random.uniform(0.2, 0.8))
    if random.random() < 0.05:
        raise TimeoutError("LLM timeout after 30s")
    return f"[Summary] {text[:50]}..."


@observe(name="fact-checker", tags={"model": "claude-3"})
def fact_check(claim: str) -> dict:
    """Simulated fact-checking agent."""
    time.sleep(random.uniform(0.3, 1.2))
    if random.random() < 0.1:
        raise ConnectionError("API rate limit exceeded")
    return {"claim": claim, "verdict": "True", "confidence": 0.94}


# --- Run the demo ---

def main():
    print("\n🧬 AgentDNA — Sentry for AI Agents\n")
    print("Simulating 50 agent calls...\n")

    tasks = [
        ("audio_1.wav", "meeting_notes.txt", "The earth is round"),
        ("podcast.mp3", "research_paper.pdf", "Water boils at 100°C"),
        ("interview.wav", "blog_post.md", "AI will replace all jobs"),
        ("voicemail.mp3", "report.txt", "The moon landing was real"),
        ("lecture.wav", "article.md", "Python is the best language"),
    ]

    for i in range(10):
        audio, doc, claim = random.choice(tasks)

        try:
            transcript = transcribe(audio)
            summary = summarize(transcript)
            result = fact_check(claim)
        except Exception:
            pass  # observe tracks failures automatically

    # --- Show the results ---

    print("=" * 50)
    print("📊 AGENTDNA STATS (persisted to SQLite)")
    print("=" * 50)

    all_stats = get_stats()

    for name, stats in all_stats.items():
        total = stats["total_calls"]
        rate = stats["success_rate"]
        avg = stats["avg_latency_ms"]
        p95 = stats["p95_latency_ms"]
        errors = stats["error_types"]

        # Health bar
        bar = "█" * int(rate * 10) + "░" * (10 - int(rate * 10))
        health = "✅" if rate >= 0.95 else "⚠️" if rate >= 0.8 else "🔴"

        print(f"\n  📌 {name}")
        print(f"     {health} {bar} {rate:.0%}  |  {total} calls")
        print(f"     ⏱️  avg {avg:.0f}ms  p95 {p95:.0f}ms")

        if errors:
            print(f"     ❌ Errors: {', '.join(f'{k}({v})' for k, v in errors.items())}")

    print(f"\n{'=' * 50}")
    print("💾 All stats saved to ~/.agentdna/observe.db")
    print("🔍 Run 'agentdna stats' anytime to view them")
    print()


if __name__ == "__main__":
    main()
