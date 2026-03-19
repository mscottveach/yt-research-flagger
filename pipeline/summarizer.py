"""
Summarize a YouTube transcript using Google Gemini.
The prompt is designed to preserve structural content: numbered tips,
named frameworks, specific examples, and concrete details.
"""

from google import genai
from pipeline.config import GEMINI_API_KEY, GEMINI_MODEL

# Max characters to send as transcript. Gemini 2.0 Flash supports 1M tokens.
# Most videos are well under this limit.
MAX_TRANSCRIPT_CHARS = 600_000

SYSTEM_PROMPT = """You are summarizing a YouTube video transcript for a personal research knowledge base. Your job is to produce notes that will help the viewer remember the video's content weeks later without rewatching it.

CRITICAL RULES — never break these:
1. If the video has a numbered list (e.g. "7 tips", "5 steps", "3 principles") — include ALL of them by name/title, not just the count.
2. If the video contains named frameworks, models, or systems — preserve the exact name and a one-line description.
3. If the video tells a story, case study, or uses a specific example — keep it as a concrete narrative, not abstracted away.
4. Include specific numbers, statistics, prices, or dates when they appear.
5. Preserve the speaker's terminology and vocabulary where it's distinctive.
6. Do NOT pad with generic observations ("the video discusses...", "the speaker explains...").
7. Keep the summary scannable — use bullets, not dense paragraphs.

Output this structure exactly (use these headers, skip a section if empty):

## Summary
2-3 sentences max. What is this video fundamentally about and why does it matter?

## Key Points
Bulleted list. If the video has a numbered structure, reproduce that structure here with every item.

## Examples & Case Studies
Concrete stories or examples mentioned. Keep the names, companies, outcomes.

## Frameworks & Concepts
Named models, techniques, or systems introduced (with brief definitions).

## Actionable Takeaways
What can the viewer actually do with this information?"""


def summarize(transcript: str, title: str = '') -> str:
    client = genai.Client(api_key=GEMINI_API_KEY)

    # Truncate if absurdly long (shouldn't happen normally)
    if len(transcript) > MAX_TRANSCRIPT_CHARS:
        transcript = transcript[:MAX_TRANSCRIPT_CHARS] + '\n\n[Transcript truncated]'

    user_message = f'Video title: {title}\n\nTranscript:\n{transcript}' if title else f'Transcript:\n{transcript}'

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        config={'system_instruction': SYSTEM_PROMPT},
        contents=user_message,
    )

    return response.text.strip()
