import os
import re
import io
import hashlib
from pathlib import Path

import requests
import fitz  # PyMuPDF
import faiss
import numpy as np
import streamlit as st
from sentence_transformers import SentenceTransformer
from groq import Groq

APP_NAME = "CyberLawGPT"
PDF_URL = "https://drive.google.com/file/d/1iseg7L2rFVcd3W8IKhIRz3alNv9Yf_vX/view?usp=drive_link"
PDF_PATH = Path("data/peca_source.pdf")
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

st.set_page_config(
    page_title=APP_NAME,
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

def drive_download_url(url: str) -> str:
    m = re.search(r"/file/d/([^/]+)", url)
    if m:
        return f"https://drive.usercontent.google.com/download?id={m.group(1)}&export=download&confirm=t"
    return url

@st.cache_resource(show_spinner=False)
def download_pdf() -> str:
    PDF_PATH.parent.mkdir(parents=True, exist_ok=True)
    if PDF_PATH.exists() and PDF_PATH.stat().st_size > 10000:
        return str(PDF_PATH)

    r = requests.get(drive_download_url(PDF_URL), timeout=60, allow_redirects=True)
    r.raise_for_status()
    content = r.content

    # Google Drive may return an HTML confirmation page for some files.
    if not content.startswith(b"%PDF"):
        raise RuntimeError(
            "The Google Drive link did not return a PDF. Make the file accessible "
            "to anyone with the link, then restart the app."
        )

    PDF_PATH.write_bytes(content)
    return str(PDF_PATH)

def normalize(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def detect_section(text: str) -> str:
    patterns = [
        r"\b(\d+[A-Z]?)\.\s+([A-Z][A-Za-z][^\n]{2,90})",
        r"\bsection\s+(\d+[A-Z]?)\b",
    ]
    for p in patterns:
        m = re.search(p, text, re.I)
        if m:
            if len(m.groups()) >= 2:
                return f"Section {m.group(1)} — {m.group(2).strip().rstrip('.')}"
            return f"Section {m.group(1)}"
    return "Section not identified"

def extract_chunks(pdf_path: str, chunk_chars: int = 1800, overlap: int = 300):
    doc = fitz.open(pdf_path)
    chunks = []

    for page_no, page in enumerate(doc, start=1):
        text = normalize(page.get_text("text"))
        if not text:
            continue

        # Split into paragraphs first, then make bounded chunks.
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        current = ""

        for para in paragraphs:
            if len(current) + len(para) + 2 <= chunk_chars:
                current = f"{current}\n\n{para}".strip()
            else:
                if current:
                    chunks.append({
                        "text": current,
                        "page": page_no,
                        "section": detect_section(current),
                    })
                tail = current[-overlap:] if current else ""
                current = f"{tail}\n\n{para}".strip()

                # Handle a single very long paragraph.
                while len(current) > chunk_chars * 1.5:
                    piece = current[:chunk_chars]
                    chunks.append({
                        "text": piece,
                        "page": page_no,
                        "section": detect_section(piece),
                    })
                    current = current[chunk_chars - overlap:]

        if current:
            chunks.append({
                "text": current,
                "page": page_no,
                "section": detect_section(current),
            })

    return chunks

@st.cache_resource(show_spinner=False)
def build_knowledge_base():
    pdf_path = download_pdf()
    chunks = extract_chunks(pdf_path)

    if not chunks:
        raise RuntimeError("No readable text was extracted from the PDF.")

    model = SentenceTransformer(EMBED_MODEL)
    texts = [c["text"] for c in chunks]
    embeddings = model.encode(
        texts,
        batch_size=32,
        show_progress_bar=False,
        normalize_embeddings=True,
    ).astype("float32")

    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)

    return model, index, chunks

def retrieve(question, model, index, chunks, top_k=6, min_score=0.20):
    q = model.encode([question], normalize_embeddings=True).astype("float32")
    scores, ids = index.search(q, min(top_k, len(chunks)))

    results = []
    for score, idx in zip(scores[0], ids[0]):
        if idx < 0:
            continue
        item = chunks[int(idx)].copy()
        item["score"] = float(score)
        if item["score"] >= min_score:
            results.append(item)

    return results

def build_context(results):
    blocks = []
    for i, r in enumerate(results, start=1):
        blocks.append(
            f"[SOURCE {i} | PDF page {r['page']} | {r['section']} | similarity {r['score']:.3f}]\n"
            f"{r['text']}"
        )
    return "\n\n".join(blocks)

def response_limit(size):
    return {"Short": 450, "Medium": 850, "Detailed": 1400, "Very detailed": 2200}[size]

def make_prompt(question, context, technicality, response_size, mode):
    return f"""
You are CyberLawGPT, a source-grounded legal information assistant.

SOURCE OF LAW:
The user-provided PDF is the controlling source for this answer. It is the
Prevention of Electronic Crimes Act, 2016 (PECA), as contained in the uploaded PDF.
Do not silently replace it with another edition, later amendment, court decision,
or general internet knowledge.

CORE RULES:
1. Answer only from the supplied SOURCE EXCERPTS.
2. Do not invent sections, penalties, definitions, procedures, authorities, dates,
   or legal conclusions.
3. If the excerpts do not contain enough information, say:
   "The supplied PECA PDF does not provide enough information to answer this point."
4. Distinguish what the Act says from practical explanation.
5. For a fact pattern, explain which provisions may be relevant, but do not claim
   that a person is legally guilty or that a court will reach a particular result.
6. When mentioning a legal provision, include its section number and PDF page when
   supported by the excerpts.
7. If the user asks about a law outside the supplied PDF, clearly say that this
   application is currently limited to the supplied PECA PDF.
8. Never fabricate a citation. Use only SOURCE numbers/pages shown below.
9. Keep the response within approximately {response_limit(response_size)} words.
10. Technicality: {technicality}.
11. Answer mode: {mode}.

USER QUESTION:
{question}

SOURCE EXCERPTS:
{context}
"""

def ask_groq(question, context, technicality, response_size, mode):
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not set. Add it to Streamlit Secrets or your environment.")

    client = Groq(api_key=api_key)
    prompt = make_prompt(question, context, technicality, response_size, mode)

    completion = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a careful retrieval-grounded legal information assistant. "
                    "Never use facts that are absent from the supplied excerpts."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.0,
        max_tokens=3000,
    )
    return completion.choices[0].message.content.strip()

def main():
    st.title("⚖️ CyberLawGPT")
    st.caption("RAG-based Pakistan cyber-law assistant • Source-grounded on the supplied PECA PDF")

    with st.sidebar:
        st.header("Answer Settings")
        technicality = st.select_slider(
            "Technicality",
            options=["Plain English", "Practical", "Legal/Technical"],
            value="Practical",
        )
        response_size = st.select_slider(
            "Response size",
            options=["Short", "Medium", "Detailed", "Very detailed"],
            value="Medium",
        )
        mode = st.selectbox(
            "Answer mode",
            [
                "Legal explanation",
                "Fact-pattern / case assessment",
                "Compliance guidance",
                "Section / penalty lookup",
                "Definitions",
            ],
        )
        top_k = st.slider("Retrieved passages", 3, 10, 6)
        min_score = st.slider("Minimum similarity", 0.10, 0.50, 0.20, 0.05)

        st.divider()
        st.markdown("**Knowledge source**")
        st.write("User-supplied Prevention of Electronic Crimes Act, 2016 PDF")
        st.caption("The PDF is downloaded and embedded on first startup.")

        if st.button("Rebuild knowledge base"):
            st.cache_resource.clear()
            st.rerun()

    try:
        with st.spinner("Loading PECA PDF and building FAISS embeddings..."):
            model, index, chunks = build_knowledge_base()
    except Exception as e:
        st.error(f"Knowledge-base startup failed: {e}")
        st.stop()

    st.success(f"Knowledge base ready: {len(chunks)} passages indexed.")

    examples = [
        "What is unauthorized access under the Act?",
        "What punishment is provided for cyber stalking?",
        "What does the Act say about spamming?",
        "Someone accessed my account without permission. Which section may be relevant?",
    ]

    if "question" not in st.session_state:
        st.session_state.question = ""

    st.subheader("Ask a question")
    cols = st.columns(4)
    for col, example in zip(cols, examples):
        if col.button(example, use_container_width=True):
            st.session_state.question = example

    question = st.text_area(
        "Your question",
        value=st.session_state.question,
        height=120,
        placeholder="Ask about an offence, definition, penalty, investigation power, procedure, or a fact pattern under the supplied PECA PDF.",
    )

    if st.button("🔎 Analyze with CyberLawGPT", type="primary", use_container_width=True):
        if not question.strip():
            st.warning("Please enter a question.")
            return

        with st.spinner("Retrieving relevant PECA provisions..."):
            results = retrieve(
                question.strip(), model, index, chunks,
                top_k=top_k, min_score=min_score
            )

        if not results:
            st.warning(
                "No sufficiently similar passage was retrieved. Try different wording "
                "or lower the minimum similarity."
            )
            return

        context = build_context(results)

        try:
            with st.spinner("Generating source-grounded answer with Groq..."):
                answer = ask_groq(
                    question.strip(), context, technicality,
                    response_size, mode
                )
        except Exception as e:
            st.error(f"Groq request failed: {e}")
            return

        st.markdown("### Answer")
        st.markdown(answer)

        with st.expander("📚 Retrieved legal sources"):
            for i, r in enumerate(results, start=1):
                st.markdown(
                    f"**Source {i} — PDF page {r['page']} — {r['section']} — "
                    f"similarity {r['score']:.3f}**"
                )
                st.write(r["text"])

        st.caption(
            "Legal-information notice: CyberLawGPT is a retrieval-based information "
            "tool, not a lawyer or a substitute for professional legal advice. "
            "The answer is limited to the supplied PDF."
        )

if __name__ == "__main__":
    main()
