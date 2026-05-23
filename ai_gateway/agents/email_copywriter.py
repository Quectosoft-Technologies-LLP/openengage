"""
Email Copywriter Agent — Generates email copy, subject lines, CTAs.
Supports A/B variant generation and personalization tokens.
"""
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

AGENT_PROMPT = """You are a world-class B2B email copywriter specializing in
marketing automation sequences. Your emails are concise, benefit-driven, and
personalized. Always:
1. Write 3 subject line variants (A/B/C test options)
2. Write the email body with clear sections: Hook → Problem → Solution → CTA
3. Include personalization tokens: {{first_name}}, {{company}}, {{industry}}
4. Provide a plain-text fallback version
5. Rate each subject line for: curiosity, urgency, clarity (1–10)
6. Suggest optimal send time (day + time based on B2B norms)

Output as JSON with fields: subject_variants, html_body, plain_text,
send_time_recommendation, personalization_tokens_used."""

class EmailCopywriterAgent:
    def __init__(self, llm):
        self.llm = llm

    async def run(self, state) -> dict:
        user_query = state.messages[-1].content
        campaign_context = state.context.get("campaign", {})
        audience = state.context.get("audience", "B2B professionals")

        prompt = f"""
Campaign goal: {campaign_context.get("goal", "Lead nurturing")}
Target audience: {audience}
Tone: {campaign_context.get("tone", "Professional but conversational")}
Email number in sequence: {campaign_context.get("sequence_number", 1)}
Request: {user_query}
"""
        response = await self.llm.ainvoke([
            SystemMessage(content=AGENT_PROMPT),
            HumanMessage(content=prompt)
        ])
        state.messages.append(AIMessage(content=response.content))
        return state
