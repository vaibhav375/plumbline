"""Register the checker's /chat endpoint as a chat agent on Agentverse, so ASI:One can find it.

Run once, and again after changing the endpoint or the description:
    AGENTVERSE_API_KEY=... AGENT_SEED_PHRASE=... uv run python scripts/register_agent.py https://<checker>/chat
The seed phrase must be the same one the checker runs with (it is the agent's identity).
"""

import os
import sys

from uagents_core.utils.registration import RegistrationRequestCredentials, register_chat_agent

from plumbline.agent import identity

README = """# Plumbline: brand compliance checks for marketing posts

Send the text of a social post, email, ad or product page. Plumbline checks it against a brand's
own rulebook and fact ledger and replies with each problem it can prove: the rule or fact ID, the
exact words, and the approved wording to use instead. It never invents a claim, and it says what it
did not check.

This demo uses **Aurelle Skin, a fictional skincare brand**. Its claims (for example "clinically
proven", "60% in 2 weeks", "100% natural") are checked against Aurelle's evidence; Indian
advertising rules (ASCI) and accessibility basics are checked too.
"""

endpoint = sys.argv[1]
seed = os.environ["AGENT_SEED_PHRASE"]
register_chat_agent(
    name="Plumbline brand compliance checker",
    endpoint=endpoint,
    active=True,
    credentials=RegistrationRequestCredentials(
        agent_seed_phrase=seed, agentverse_api_key=os.environ["AGENTVERSE_API_KEY"]
    ),
    description="Checks marketing copy against a brand's rules and evidence, with cited fixes.",
    readme=README,
    starter_prompts=[
        "Check this post: Meet the NEW Aurelle Vitamin-C serum! Clinically proven to fade dark "
        "spots by 60% in just 2 weeks. 100% natural and eco-friendly.",
        "Check this caption: Gifted by Aurelle! I tried the SPF 50 Daily Sunscreen all week.",
    ],
    metadata={
        "categories": ["marketing", "compliance", "content review"],
        "tags": ["brand compliance", "advertising claims", "ASCI", "accessibility", "copy review"],
        "is_public": "True",
    },
)
print(f"Registered {identity(seed).address} at {endpoint}")
