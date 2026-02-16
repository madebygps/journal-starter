import json
import os
from datetime import UTC, datetime

from openai import OpenAI

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://models.inference.ai.azure.com")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


async def analyze_journal_entry(entry_id: str, entry_text: str) -> dict:
    """
    Analyze a journal entry using the OpenAI-compatible API.

    Args:
        entry_id: The ID of the journal entry being analyzed
        entry_text: The combined text of the journal entry (work + struggle + intention)

    Returns:
        dict with keys:
            - entry_id: ID of the analyzed entry
            - sentiment: "positive" | "negative" | "neutral"
            - summary: 2 sentence summary of the entry
            - topics: list of 2-4 key topics mentioned
            - created_at: timestamp when the analysis was created
    """
    client = OpenAI(
        api_key=OPENAI_API_KEY,
        base_url=OPENAI_BASE_URL,
    )

    prompt = (
        "Analyze the following journal entry. Return a JSON object with exactly these keys:\n"
        '- "sentiment": one of "positive", "negative", or "neutral"\n'
        '- "summary": a 2-sentence summary of the entry\n'
        '- "topics": a list of 2 to 4 key topics mentioned\n\n'
        "Return ONLY valid JSON, no other text.\n\n"
        f"Journal entry:\n{entry_text}"
    )

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": "You are a helpful assistant that analyzes journal entries and returns structured JSON."},
            {"role": "user", "content": prompt},
        ]
    )

    content = response.choices[0].message.content or "{}"
    # Strip markdown code fences if present
    content = content.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[1] if "\n" in content else content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

    analysis = json.loads(content)

    return {
        "entry_id": entry_id,
        "sentiment": analysis.get("sentiment", "neutral"),
        "summary": analysis.get("summary", ""),
        "topics": analysis.get("topics", []),
        "created_at": datetime.now(UTC).isoformat(),
    }
