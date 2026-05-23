"""
Campaign Strategy Agent — Plans full marketing campaigns using context from
the RAG knowledge base (past campaigns, industry benchmarks).
"""
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
import os

CHROMA_URL = os.getenv("CHROMA_URL", "http://localhost:8001")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")

AGENT_PROMPT = """You are a senior B2B marketing strategist.
Given a business objective, create a detailed multi-channel campaign plan with:
1. Campaign goal and KPIs
2. Target audience definition
3. Channel mix (email, SMS, chat, web)
4. Content calendar (4–8 week timeline)
5. Lead nurture sequence (number of touches, cadence)
6. A/B test recommendations
7. Success metrics and reporting checkpoints

Use data from past campaign benchmarks when available.
Always output structured JSON + a human-readable summary."""

class CampaignStrategyAgent:
    def __init__(self, llm):
        self.llm = llm
        self.embeddings = OllamaEmbeddings(model="nomic-embed-text", base_url=OLLAMA_URL)
        self.vectorstore = Chroma(
            collection_name="campaign_knowledge",
            embedding_function=self.embeddings,
            persist_directory="/chroma/campaign_strategy"
        )

    async def run(self, state) -> dict:
        user_query = state.messages[-1].content
        # RAG: retrieve relevant past campaigns
        relevant_docs = self.vectorstore.similarity_search(user_query, k=3)
        context = "\n".join([d.page_content for d in relevant_docs])

        prompt = f"""Past campaign context:\n{context}\n\nUser request: {user_query}"""
        response = await self.llm.ainvoke([
            SystemMessage(content=AGENT_PROMPT),
            HumanMessage(content=prompt)
        ])
        from langchain_core.messages import AIMessage
        state.messages.append(AIMessage(content=response.content))
        return state

    async def ingest_campaign_result(self, campaign_data: dict):
        """Ingest completed campaign performance data into RAG for future learning."""
        doc_text = f"""
        Campaign: {campaign_data.get("name")}
        Goal: {campaign_data.get("goal")}
        Industry: {campaign_data.get("industry")}
        Open Rate: {campaign_data.get("open_rate")}%
        Click Rate: {campaign_data.get("click_rate")}%
        Conversion Rate: {campaign_data.get("conversion_rate")}%
        Learnings: {campaign_data.get("learnings")}
        """
        from langchain_core.documents import Document
        self.vectorstore.add_documents([Document(page_content=doc_text)])
