from pathlib import Path

from agno.agent import Agent
from agno.embedder.google import GeminiEmbedder
from agno.knowledge.csv import CSVKnowledgeBase
from agno.models.google import Gemini
from agno.playground import Playground, serve_playground_app
from agno.storage.postgres import PostgresStorage
from agno.vectordb.pgvector import PgVector, SearchType

db_url = "postgresql+psycopg://ai:ai@localhost:5532/ai"

knowledge_base = CSVKnowledgeBase(
    path=Path("chatbot/csvs"),
    vector_db=PgVector(
        table_name="csv_documents",
        search_type=SearchType.hybrid,
        db_url=db_url,
        embedder=GeminiEmbedder(id="gemini-embedding-exp-03-07", dimensions=1536),
    ),
    num_documents=2,
)
# Load the knowledge base
knowledge_base.load(recreate=False)

rag_agent = Agent(
    name="RAG Agent",
    agent_id="rag-agent",
    model=Gemini(id="gemini-2.5-flash-preview-04-17"),
    knowledge=knowledge_base,
    search_knowledge=True,
    read_chat_history=True,
    storage=PostgresStorage(table_name="rag_agent_sessions", db_url=db_url),
    instructions=[
        "Always search your knowledge base first and use it if available.",
        "Important: Use tables where possible.",
    ],
    markdown=True,
)

app = Playground(agents=[rag_agent]).get_app()

if __name__ == "__main__":
    # Load the knowledge base: Comment after first run as the knowledge base is already loaded
    knowledge_base.load(upsert=True)

    serve_playground_app("chatbot.agentic_chatbot:app", reload=True)
