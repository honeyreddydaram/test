"""Optional OpenAI-compatible LLM adapter. Offline seed fallback needs no key."""

import json
import os
import urllib.request
from .engine import validate_generated, ITEMS, SKILLS


def generate(propose=None):
    if propose is None:
        if not os.getenv("LLM_API_KEY"):
            raise RuntimeError("No LLM configured; use the reviewed seed bank.")
        request = urllib.request.Request(
            os.getenv("LLM_URL", "https://api.openai.com/v1/chat/completions"),
            data=json.dumps(
                {
                    "model": os.getenv("LLM_MODEL", "gpt-4.1-mini"),
                    "messages": [
                        {
                            "role": "user",
                            "content": "Choose one exercise template below. Return JSON with its exact skill, type, prompt, options plus explanation copied exactly from its rule. Templates: "
                            + json.dumps(
                                [
                                    {
                                        **{
                                            k: i[k]
                                            for k in (
                                                "skill",
                                                "type",
                                                "prompt",
                                                "options",
                                            )
                                        },
                                        "rule": SKILLS[i["skill"]]["rule"],
                                    }
                                    for i in ITEMS
                                    if i["type"] != "writing"
                                ]
                            ),
                        }
                    ],
                    "response_format": {"type": "json_object"},
                }
            ).encode(),
            headers={
                "Authorization": "Bearer " + os.environ["LLM_API_KEY"],
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            candidate = json.loads(
                json.load(response)["choices"][0]["message"]["content"]
            )
    else:
        candidate = propose()
    accepted = validate_generated(candidate)
    if candidate.get("explanation") != SKILLS[accepted["skill"]]["rule"]:
        raise ValueError("Explanation does not match the curated rule.")
    return {**accepted, "explanation": candidate["explanation"]}
