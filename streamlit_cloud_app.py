import os
import re
from collections import Counter
from typing import List, Tuple

import streamlit as st
from pypdf import PdfReader


def get_gemini_api_key() -> str | None:
    secret_key = st.secrets.get("GEMINI_API_KEY", "")
    if secret_key:
        return str(secret_key).strip()
    env_key = os.getenv("GEMINI_API_KEY", "")
    return env_key.strip() or None


def extract_text_from_pdf(file_obj) -> str:
    reader = PdfReader(file_obj)
    pages: List[str] = []
    for page in reader.pages:
        pages.append((page.extract_text() or "").strip())
    return "\n\n".join(page for page in pages if page).strip()


def chunk_text(text: str, chunk_size: int = 1400, overlap: int = 200) -> List[str]:
    clean = re.sub(r"\s+", " ", text).strip()
    if not clean:
        return []

    chunks: List[str] = []
    start = 0
    step = max(1, chunk_size - overlap)
    while start < len(clean):
        end = start + chunk_size
        chunks.append(clean[start:end])
        start += step
    return chunks


def tokenize(text: str) -> List[str]:
    return [token for token in re.findall(r"[a-zA-Z0-9]{3,}", text.lower())]


def retrieve_chunks(query: str, chunks: List[str], top_k: int = 4) -> List[Tuple[int, float, str]]:
    query_tokens = tokenize(query)
    if not query_tokens:
        return []
    query_counts = Counter(query_tokens)
    scored: List[Tuple[int, float, str]] = []
    for idx, chunk in enumerate(chunks):
        chunk_counts = Counter(tokenize(chunk))
        overlap_score = 0.0
        for token, q_count in query_counts.items():
            if token in chunk_counts:
                overlap_score += float(min(q_count, chunk_counts[token]))
        length_penalty = max(len(chunk.split()), 1)
        score = overlap_score / (length_penalty ** 0.5)
        if score > 0:
            scored.append((idx, score, chunk))
    scored.sort(key=lambda row: row[1], reverse=True)
    return scored[:top_k]


def answer_with_gemini(question: str, contexts: List[str], gemini_api_key: str) -> str:
    try:
        import google.generativeai as genai
    except Exception as exc:
        return f"Gemini client import failed: {exc}"

    genai.configure(api_key=gemini_api_key)
    model = genai.GenerativeModel("gemini-2.5-flash")
    context_block = "\n\n---\n\n".join(contexts)
    prompt = (
        "You are answering questions about an uploaded document. "
        "Use only the provided context. If the answer is missing, say so clearly.\n\n"
        f"Question:\n{question}\n\n"
        f"Context:\n{context_block}"
    )
    response = model.generate_content(prompt)
    text = getattr(response, "text", "") or ""
    if text.strip():
        return text.strip()
    return "Gemini returned an empty response."


def main() -> None:
    st.set_page_config(page_title="DocuSynth Free Demo", page_icon="📄", layout="wide")
    st.title("DocuSynth Free Streamlit Demo")
    st.caption(
        "Lightweight standalone demo for Streamlit Community Cloud. "
        "This is separate from the full Dockerized DocuSynth platform."
    )

    uploaded_file = st.file_uploader("Upload a PDF", type=["pdf"])
    if not uploaded_file:
        st.info("Upload a PDF to begin.")
        return

    with st.spinner("Extracting text from PDF..."):
        try:
            raw_text = extract_text_from_pdf(uploaded_file)
        except Exception as exc:
            st.error(f"Failed to read PDF: {exc}")
            return

    if not raw_text:
        st.warning("No extractable text found in this PDF.")
        return

    chunks = chunk_text(raw_text)
    st.success(f"Loaded document with {len(raw_text):,} characters and {len(chunks)} chunks.")

    with st.expander("Preview extracted text"):
        st.text(raw_text[:2500] + ("..." if len(raw_text) > 2500 else ""))

    question = st.text_input("Ask a question about the uploaded PDF")
    top_k = st.slider("Retrieved chunks", min_value=1, max_value=8, value=4)
    if not question.strip():
        return

    matches = retrieve_chunks(question, chunks, top_k=top_k)
    if not matches:
        st.warning("No relevant chunks found using lightweight retrieval.")
        return

    selected_chunks = [chunk for _, _, chunk in matches]
    gemini_api_key = get_gemini_api_key()

    st.subheader("Retrieved Context")
    for rank, (idx, score, chunk) in enumerate(matches, start=1):
        st.markdown(f"**Chunk {rank}** (source #{idx + 1}, score {score:.4f})")
        st.write(chunk[:900] + ("..." if len(chunk) > 900 else ""))

    st.subheader("Answer")
    if not gemini_api_key:
        st.warning(
            "LLM answering is disabled because `GEMINI_API_KEY` is not set in Streamlit "
            "secrets or environment variables. Showing retrieved chunks only."
        )
        return

    with st.spinner("Generating answer with Gemini..."):
        try:
            answer = answer_with_gemini(question, selected_chunks, gemini_api_key)
        except Exception as exc:
            st.error(f"Gemini request failed: {exc}")
            st.info("Showing retrieved chunks above for manual review.")
            return
    st.write(answer)


if __name__ == "__main__":
    main()
