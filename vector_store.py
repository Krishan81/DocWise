import numpy as np
import faiss

import prompts

EMBEDDING_MODEL = "gemini-embedding-001"
GENERATION_MODEL = "gemini-3.6-flash"

# Cosine similarity ranges from -1 to 1. A chunk below this is treated as
# "not actually relevant" and dropped rather than forced into the answer.
DEFAULT_MIN_SIMILARITY = 0.55


def create_embeddings(client, chunks):
    texts = [chunk["text"] for chunk in chunks]

    response = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=texts
    )

    embeddings = [embedding.values for embedding in response.embeddings]

    return np.array(embeddings, dtype="float32")


def create_faiss_index(embeddings):
    """
    Builds a cosine-similarity index.

    We normalize every vector to unit length and use an inner-product
    index (IndexFlatIP). For normalized vectors, inner product IS cosine
    similarity, and it stays in a fixed, interpretable [-1, 1] range no
    matter which embedding model is used — unlike raw L2 distance, whose
    scale depends on the model's output magnitude.
    """

    faiss.normalize_L2(embeddings)

    dimension = embeddings.shape[1]

    index = faiss.IndexFlatIP(dimension)
    index.add(embeddings)

    return index


def embed_query(client, query):
    response = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=query
    )

    query_embedding = np.array(
        [response.embeddings[0].values],
        dtype="float32"
    )

    faiss.normalize_L2(query_embedding)

    return query_embedding


def search_faiss(client, index, chunks, query, top_k=5,
                  min_similarity=DEFAULT_MIN_SIMILARITY):
    if index is None or index.ntotal == 0:
        return []

    query_embedding = embed_query(client, query)
    actual_k = min(top_k, index.ntotal)

    similarities, indices = index.search(query_embedding, actual_k)

    results = []

    for similarity, index_number in zip(similarities[0], indices[0]):

        if index_number == -1:
            continue

        if similarity < min_similarity:
            continue

        results.append({
            "chunk": chunks[index_number],
            "similarity": float(similarity)
        })

    return results


def generate_query_variants(client, question, num_variants=2):
    """Asks the model for a couple of alternate phrasings of the question."""

    prompt = prompts.query_expansion_prompt(question, num_variants)

    response = client.models.generate_content(
        model=GENERATION_MODEL,
        contents=prompt
    )

    lines = [
        line.strip("-• ").strip()
        for line in response.text.strip().split("\n")
        if line.strip()
    ]

    return lines[:num_variants]


def multi_query_search(client, index, chunks, question, top_k=5,
                        min_similarity=DEFAULT_MIN_SIMILARITY,
                        expand_query=False):
    """
    Searches with the original question, and optionally also with a couple
    of LLM-generated rephrasings, then merges and deduplicates the results.

    expand_query defaults to False because it costs one extra Gemini call
    per question. Pass expand_query=True from the caller if you want the
    retrieval-quality boost and are fine with the added latency/cost.
    """

    best_by_chunk = {}

    def add_results(results):
        for result in results:
            key = id(result["chunk"])
            existing = best_by_chunk.get(key)
            if existing is None or result["similarity"] > existing["similarity"]:
                best_by_chunk[key] = result

    add_results(
        search_faiss(client, index, chunks, question,
                     top_k=top_k, min_similarity=min_similarity)
    )

    if expand_query:
        try:
            variants = generate_query_variants(client, question)
        except Exception:
            variants = []

        for variant in variants:
            add_results(
                search_faiss(client, index, chunks, variant,
                             top_k=top_k, min_similarity=min_similarity)
            )

    merged = sorted(
        best_by_chunk.values(),
        key=lambda r: r["similarity"],
        reverse=True
    )

    return merged[:top_k]


def create_context(results):
    context = ""

    for i, result in enumerate(results):
        chunk = result["chunk"]

        context += f"SOURCE {i + 1}\n"
        context += f"DOCUMENT: {chunk['document_name']}\n"
        context += f"PAGE: {chunk['start_page']}"

        if chunk["start_page"] != chunk["end_page"]:
            context += f"-{chunk['end_page']}"

        context += "\n"
        context += chunk["text"]
        context += "\n\n"

    return context


def create_chat_history(messages, max_messages=6):
    history = ""

    for message in messages[-max_messages:]:
        history += f"{message['role'].upper()}: {message['content']}\n"

    return history


def generate_answer(client, question, context, chat_history=""):
    prompt = prompts.answer_prompt(question, context, chat_history)

    response = client.models.generate_content(
        model=GENERATION_MODEL,
        contents=prompt
    )

    return response.text


def detect_document_type(client, document_text):
    text = document_text[:12000]
    prompt = prompts.document_type_prompt(text)

    response = client.models.generate_content(
        model=GENERATION_MODEL,
        contents=prompt
    )

    return response.text.strip()


def detect_risks(client, document_text):
    text = document_text[:30000]
    prompt = prompts.risk_prompt(text)

    response = client.models.generate_content(
        model=GENERATION_MODEL,
        contents=prompt
    )

    return response.text


def compare_documents(client, documents):
    document_text = ""

    for document in documents:
        document_text += f"\n\nDOCUMENT: {document['name']}\n"

        for page in document["pages"]:
            document_text += f"\nPage {page['page']}:\n"
            document_text += page["text"]

    prompt = prompts.comparison_prompt(document_text)

    response = client.models.generate_content(
        model=GENERATION_MODEL,
        contents=prompt
    )

    return response.text
