import json
import logging
import os
from datetime import UTC, datetime

from openai import AsyncAzureOpenAI

logger = logging.getLogger(__name__)

# Configure Azure OpenAI client
client = AsyncAzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
)

DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")


async def analyze_journal_entry(entry_id: str, entry_text: str) -> dict:
    """
    Analyze a journal entry using Azure OpenAI.

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
    logger.info("Analyzing journal entry %s", entry_id)

    prompt = (
        "Analyze the following journal entry and return a JSON object with these fields:\n"
        '- "sentiment": one of "positive", "negative", or "neutral"\n'
        '- "summary": a 2-sentence summary of the entry\n'
        '- "topics": a list of 2-4 key topics mentioned\n\n'
        "Return ONLY valid JSON, no markdown formatting.\n\n"
        f"Journal entry:\n{entry_text}"
    )

    response = await client.chat.completions.create(
        model=DEPLOYMENT,
        messages=[
            {
                "role": "system",
                "content": "You are a helpful assistant that analyzes journal entries. "
                "Always respond with valid JSON only.",
            },
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
