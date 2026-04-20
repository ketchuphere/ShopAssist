import os
import re
from typing import TypedDict, List
from datetime import datetime, timedelta

import chromadb
from sentence_transformers import SentenceTransformer
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

llm = ChatOllama(
    model="phi3",
    temperature=0
)

FAITHFULNESS_THRESHOLD = 0.7
MAX_EVAL_RETRIES = 2
SLIDING_WINDOW = 6
TOP_K_RESULTS = 3

embedder = SentenceTransformer("all-MiniLM-L6-v2")

class CapstoneState(TypedDict):
    question: str
    messages: List[dict]
    route: str
    retrieved: str
    sources: List[str]
    tool_result: str
    answer: str
    faithfulness: float
    eval_retries: int
    user_name: str
    legal_domain: str


def build_collection(documents):

    client = chromadb.Client()

    try:
        client.delete_collection("legal_kb_agent")
    except:
        pass

    collection = client.create_collection("legal_kb_agent")

    texts = [d["text"].strip() for d in documents]

    collection.add(
        ids=[d["id"] for d in documents],
        documents=texts,
        embeddings=embedder.encode(texts).tolist(),
        metadatas=[
            {
                "topic": d["topic"],
                "category": d["category"]
            }
            for d in documents
        ],
    )

    return collection


def build_graph(collection):

    def retrieve(query, n=TOP_K_RESULTS):

        qe = embedder.encode(query).tolist()

        res = collection.query(
            query_embeddings=[qe],
            n_results=n,
            include=["documents", "metadatas", "distances"]
        )

        parts = []
        sources = []

        for i in range(len(res["documents"][0])):

            parts.append(
                f"[{res['metadatas'][0][i]['topic']}]\n{res['documents'][0][i]}"
            )

            sources.append(
                res["metadatas"][0][i]["topic"]
            )

        return {
            "context": "\n\n---\n\n".join(parts),
            "sources": sources
        }


    def memory_node(state):

        q = state["question"]

        messages = state.get("messages", [])

        name = state.get("user_name", "")

        messages.append({
            "role": "user",
            "content": q
        })

        if len(messages) > SLIDING_WINDOW:

            messages = messages[-SLIDING_WINDOW:]

        if "my name is" in q.lower():

            try:

                name = (
                    q.lower()
                    .split("my name is")[1]
                    .strip()
                    .split()[0]
                    .strip(".,!?")
                    .capitalize()
                )

            except:

                pass

        return {
            "messages": messages,
            "user_name": name
        }


    def router_node(state):

        response = llm.invoke([

            HumanMessage(
                content=f"""
Classify:
retrieve
tool
memory_only

Question:
{state["question"]}

Reply one word only.
"""
            )

        ])

        route = response.content.strip().lower()

        if route not in ["retrieve", "tool", "memory_only"]:

            route = "retrieve"

        return {
            "route": route
        }


    def retrieval_node(state):

        result = retrieve(state["question"])

        return {
            "retrieved": result["context"],
            "sources": result["sources"],
            "legal_domain": result["sources"][0] if result["sources"] else ""
        }


    def skip_retrieval_node(state):

        return {
            "retrieved": "",
            "sources": [],
            "legal_domain": ""
        }


    def tool_node(state):

        q = state["question"].lower()

        today = datetime.now()

        try:

            m = re.search(r"(\d+)\s*days?", q)

            if m and ("deadline" in q or "days" in q):

                n = int(m.group(1))

                dl = today + timedelta(days=n)

                result = (
                    f"Today is {today.strftime('%d %B %Y')}. "
                    f"Deadline: {dl.strftime('%d %B %Y')}."
                )

            else:

                result = (
                    f"Today is {today.strftime('%d %B %Y')} "
                    f"({today.strftime('%A')})."
                )

        except Exception as e:

            result = f"Date error: {str(e)}"

        return {
            "tool_result": result
        }


    def answer_node(state):

        ctx = ""

        if state.get("retrieved"):

            ctx += f"\nCONTEXT:\n{state['retrieved']}"

        if state.get("tool_result"):

            ctx += f"\nTOOL:\n{state['tool_result']}"

        if not ctx:

            ctx = "\n(No context retrieved.)"

        retry_instruction = ""

        if state.get("eval_retries", 0) > 0:

            retry_instruction = (
                f"\nRetry {state.get('eval_retries')} "
                f"use only context."
            )

        system_prompt = f"""
You are an Indian legal assistant.

Use ONLY the provided context.

{retry_instruction}

{ctx}
"""

        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=state["question"])
        ])

        return {
            "answer": response.content.strip()
        }


    def eval_node(state):

        answer = state.get("answer", "")

        context = state.get("retrieved", "")

        retries = state.get("eval_retries", 0)

        if not context.strip():

            return {
                "faithfulness": 1.0,
                "eval_retries": retries
            }

        prompt = f"""
Score faithfulness 0-1.

CONTEXT:
{context[:1200]}

ANSWER:
{answer}

Reply number only.
"""

        try:

            r = llm.invoke([HumanMessage(content=prompt)])

            numbers = re.findall(
                r"\d+\.?\d*",
                r.content
            )

            score = (
                float(numbers[0])
                if numbers
                else 0.5
            )

            score = max(0.0, min(1.0, score))

        except:

            score = 0.5

        return {
            "faithfulness": score,
            "eval_retries": retries + 1
        }


    def save_node(state):

        messages = state.get("messages", [])

        messages.append({
            "role": "assistant",
            "content": state.get("answer", "")
        })

        return {
            "messages": messages
        }


    def route_decision(state):

        route = state.get("route", "retrieve")

        if route == "tool":

            return "tool"

        if route == "memory_only":

            return "skip"

        return "retrieve"


    def eval_decision(state):

        faithfulness = state.get("faithfulness", 0.0)

        retries = state.get("eval_retries", 0)

        if (
            faithfulness >= FAITHFULNESS_THRESHOLD
            or retries >= MAX_EVAL_RETRIES
        ):

            return "save"

        return "answer"


    graph = StateGraph(CapstoneState)

    graph.add_node("memory", memory_node)
    graph.add_node("router", router_node)
    graph.add_node("retrieve", retrieval_node)
    graph.add_node("skip", skip_retrieval_node)
    graph.add_node("tool", tool_node)
    graph.add_node("answer", answer_node)
    graph.add_node("eval", eval_node)
    graph.add_node("save", save_node)

    graph.set_entry_point("memory")

    graph.add_edge("memory", "router")

    graph.add_edge("retrieve", "answer")

    graph.add_edge("skip", "answer")

    graph.add_edge("tool", "answer")

    graph.add_edge("answer", "eval")

    graph.add_edge("save", END)

    graph.add_conditional_edges(
        "router",
        route_decision,
        {
            "retrieve": "retrieve",
            "tool": "tool",
            "skip": "skip"
        }
    )

    graph.add_conditional_edges(
        "eval",
        eval_decision,
        {
            "answer": "answer",
            "save": "save"
        }
    )

    return graph.compile(
        checkpointer=MemorySaver()
    )