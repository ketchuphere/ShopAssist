🛍️ ShopAssist — E-commerce AI Assistant

An intelligent, retrieval-augmented AI assistant designed to handle high-volume e-commerce customer support queries with accuracy, memory, and zero hallucination.

🚀 Overview

ShopAssist is a LangGraph-powered AI system that combines:

📚 RAG (Retrieval-Augmented Generation) using ChromaDB
🧠 Conversation Memory using MemorySaver + thread_id
🔄 Multi-step reasoning workflow (routing, retrieval, tools, evaluation)
🛠️ Tool integration (pricing calculator, order status)
💬 Streamlit UI for real-time interaction

Unlike traditional chatbots, ShopAssist ensures:

Grounded answers from a verified knowledge base
No hallucinated policy responses
Context retention across multi-turn conversations
🧩 System Architecture
User Query
   ↓
memory_node        → stores conversation (sliding window)
   ↓
router_node        → decides: retrieve / tool / skip
   ↓
retrieval_node / tool_node / skip_node
   ↓
answer_node        → generates grounded response
   ↓
eval_node          → checks faithfulness (0.0–1.0)
   ↓
save_node          → saves response to memory
   ↓
END



⚙️ Tech Stack
LLM Runtime: Ollama (Phi3 / Llama3)
Embeddings: SentenceTransformers (all-MiniLM-L6-v2)
Vector DB: ChromaDB (in-memory)
Orchestration: LangGraph
Frontend: Streamlit
Memory: MemorySaver (thread-based persistence)



📂 Project Structure
.
├── agent.py                # Core logic (state, nodes, graph)
├── streamlit.py            # UI application
├── day13_capstone.ipynb    # Development notebook
├── requirements.txt
└── README.md



🧠 Features
  ✅ 1. Retrieval-Augmented Generation (RAG)
          10+ domain-specific documents
          Semantic search using embeddings
          Context-grounded answers
  ✅ 2. Multi-turn Memory
          Conversation tracked via thread_id
          Sliding window prevents token overflow
          Remembers user name and context
  ✅ 3. Intelligent Routing
        Automatically selects:
        retrieve → knowledge base
        tool → computation/API
        skip → memory-only queries
  ✅ 4. Tool Integration
        Price calculation
        Order tracking (mock API)
        Safe execution (no crashes)
✅ 5.  Self-Evaluation
        Faithfulness scoring (0–1)
        Retry mechanism for low-confidence answers
        📊 Capstone Requirements Coverage

Example Queries
“What is your return policy?” → Retrieval
“Calculate price after 10% discount” → Tool
“My name is Alex” → Memory
Red Team Tests
Out-of-scope → “I don’t know”
Prompt injection → blocked
False premise → corrected


▶️ How to Run
1. Install dependencies
pip install -r requirements.txt
2. Start Ollama
ollama pull phi3
ollama run phi3
3. Run Streamlit app
streamlit run streamlit.py
📈 Example Workflow
User: What is your return policy?
→ Routed to RETRIEVE
→ Relevant docs fetched
→ Answer generated from KB

⚠️ Limitations
Knowledge base is static (no live product data)
Tool responses are mocked (not real APIs)
Basic LLM prompting (can be improved)
🔮 Future Improvements
Integrate real e-commerce APIs (orders, inventory)
Add multilingual support
Improve RAG with hybrid search (BM25 + embeddings)
Deploy via FastAPI + Vercel
Add authentication & user profiles
