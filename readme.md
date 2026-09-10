# ⚖️ CyberLawGPT

**CyberLawGPT** is a free-to-run Retrieval-Augmented Generation (RAG) web application for asking questions about Pakistan's cyber-law provisions contained in the supplied **Prevention of Electronic Crimes Act, 2016 (PECA)** PDF.

The application uses:

- **Python**
- **Streamlit** — web UI
- **FAISS** — local vector similarity search
- **Sentence Transformers (`all-MiniLM-L6-v2`)** — local/free embeddings
- **Groq API** — LLM answer generation
- **PyMuPDF** — PDF extraction

The supplied PDF describes the Prevention of Electronic Crimes Act, 2016, including its scope and application to Pakistan and certain acts committed outside Pakistan that affect persons, property, information systems or data located in Pakistan.

> **Important:** CyberLawGPT is a source-grounded legal information tool, not a lawyer. It answers from the supplied PDF and should not be treated as a legal opinion or substitute for qualified legal advice. The application intentionally avoids inventing legal provisions when the retrieved source does not support an answer.

---

## 1. What the application does

### RAG pipeline

```text
PECA PDF
   ↓
Download on startup
   ↓
PyMuPDF text extraction
   ↓
Paragraph + overlapping chunking
   ↓
Sentence-Transformer embeddings
   ↓
FAISS IndexFlatIP
   ↓
User question
   ↓
Question embedding
   ↓
Top-K relevant PECA passages
   ↓
Strict source-grounded prompt
   ↓
Groq LLM
   ↓
Answer + retrieved source passages
```

The application does **not** send the whole PDF to Groq. It retrieves the most relevant passages first and sends those passages to the model.

---

## 2. UI options

The sidebar includes:

### Technicality
- **Plain English** — suitable for non-lawyers
- **Practical** — balanced explanation
- **Legal/Technical** — more legal terminology

### Response size
- Short
- Medium
- Detailed
- Very detailed

### Answer mode
- **Legal explanation**
- **Fact-pattern / case assessment**
- **Compliance guidance**
- **Section / penalty lookup**
- **Definitions**

### RAG controls
- Retrieved passages: 3–10
- Minimum similarity threshold

There is also a **Rebuild knowledge base** button.

---

## 3. Only three application files

Keep exactly these three files in the GitHub repository:

```text
CyberLawGPT/
├── app.py
├── requirements.txt
└── readme.md
```

The PDF is **not required to be committed to GitHub**.

On first startup, `app.py` downloads the supplied Google Drive PDF and stores it temporarily as:

```text
data/peca_source.pdf
```

`data/` is generated automatically at runtime and is not one of the three project files.

---

## 4. Google Drive PDF requirement

The application is configured with this source:

```text
https://drive.google.com/file/d/1iseg7L2rFVcd3W8IKhIRz3alNv9Yf_vX/view?usp=drive_link
```

For Streamlit Cloud, make sure the Google Drive file is accessible to the deployment. A private Drive file that requires your personal login will not be downloadable by Streamlit Cloud.

The code converts the Drive `/file/d/.../view` URL into a download request.

If Google Drive returns an HTML confirmation page instead of the PDF, the application stops rather than silently indexing invalid content.

---

# 5. Run locally

## Install

```bash
pip install -r requirements.txt
```

Set your Groq API key.

### Windows PowerShell

```powershell
$env:GROQ_API_KEY="YOUR_GROQ_API_KEY"
```

### Linux/macOS

```bash
export GROQ_API_KEY="YOUR_GROQ_API_KEY"
```

Run:

```bash
streamlit run app.py
```

Open the Streamlit URL shown in the terminal.

---

# 6. Run in Google Colab

Upload the three files to Colab or clone your GitHub repository.

Install dependencies:

```python
!pip install -r requirements.txt
```

Set the API key:

```python
import os
os.environ["GROQ_API_KEY"] = "YOUR_GROQ_API_KEY"
```

Run Streamlit:

```python
!streamlit run app.py &>/content/streamlit.log &
```

For a temporary public URL, you can use a tunnel service available in your Colab environment. The application itself does not require a paid server.

The first startup can take longer because the embedding model has to be downloaded and the PDF has to be extracted and embedded.

---

# 7. Deploy to Streamlit Community Cloud

1. Create a GitHub repository.
2. Add only:
   - `app.py`
   - `requirements.txt`
   - `readme.md`
3. Open Streamlit Community Cloud.
4. Create a new app.
5. Select your GitHub repository.
6. Set the main file to:

```text
app.py
```

7. Add the secret:

```toml
GROQ_API_KEY = "YOUR_GROQ_API_KEY"
```

8. Deploy.

The app downloads the PECA PDF and builds the FAISS index on startup.

---

# 8. Why the application is designed to reduce hallucination

This version intentionally uses several controls.

## A. Retrieval before generation

The LLM receives retrieved passages instead of being asked to answer from general knowledge.

## B. Strict source instruction

The prompt tells the model:

```text
Answer only from the supplied SOURCE EXCERPTS.
Do not invent sections, penalties, definitions, procedures,
authorities, dates, or legal conclusions.
```

## C. Abstention

If the retrieved material does not support the question, the model is instructed to say that the supplied PDF does not contain enough information.

## D. Temperature 0

Groq generation uses:

```python
temperature=0.0
```

This favors consistent answers for legal-information retrieval.

## E. Source display

The UI displays the passages retrieved from the PDF after every answer.

This lets the user inspect the evidence used for the answer.

---

# 9. Important limitation: "any question"

CyberLawGPT can answer a broad range of questions **when the supplied PECA PDF contains the relevant material**, such as:

- What is unauthorized access?
- What is unauthorized copying/transmission?
- What is interference with an information system?
- What is critical infrastructure?
- What is electronic forgery?
- What is electronic fraud?
- What is identity-information misuse?
- What is unauthorized interception?
- What is cyber stalking?
- What is spamming?
- What is spoofing?
- What does the Act say about malicious code?
- What investigative powers are described?
- What does the Act say about preservation of data?
- What does it say about traffic data?
- What does it say about search/seizure?
- What does it say about content-data disclosure?
- What does it say about confidentiality?
- What does it say about international cooperation?
- What does it say about prosecution and trial?

It should **not** pretend to know the answer if the supplied PDF does not contain the relevant rule.

For example, if asked about a completely different Pakistani statute, the correct behavior is to state that the current knowledge base is limited to the supplied PECA PDF.

---

# 10. Legal-source scope

The uploaded document identifies itself as the **Prevention of Electronic Crimes Act, 2016** and states that it extends to the whole of Pakistan. It also contains provisions concerning application to certain acts committed outside Pakistan when the relevant Pakistani person, property, information system or data is affected.

The application treats the supplied document as its controlling source rather than silently mixing it with internet sources.

This is important because cyber-law provisions can be amended or interpreted by courts over time. A production legal product should therefore maintain a versioned legal-document library.

---

# 11. Suggested production upgrades

This MVP intentionally remains simple enough for free Streamlit deployment.

For a professional version, consider adding:

### Legal document versioning

```text
PECA 2016
PECA amendments
Rules
Official notifications
Court judgments
```

Each document should have:

```text
document_name
version
effective_date
source
page
section
```

### Better legal retrieval

Use hybrid retrieval:

```text
BM25 / keyword search
        +
FAISS vector search
        ↓
reranker
        ↓
LLM
```

This can improve retrieval for exact section numbers and legal terminology.

### Citation enforcement

Return structured internal metadata such as:

```text
section
subsection
page
document
```

Then render citations independently from the LLM output rather than asking the LLM to invent citation formatting.

### Evaluation dataset

Create a test set containing:

```text
Question
Expected section
Expected answer points
Expected source page
```

Measure:

- retrieval recall
- citation accuracy
- answer faithfulness
- abstention accuracy
- hallucination rate

### Authentication

Add user login before using CyberLawGPT for confidential legal work.

### Audit logging

For professional deployments, consider storing:

```text
question
retrieved passages
answer
model
document version
timestamp
```

Do not store sensitive user information without an appropriate privacy/security design.

---

# 12. Security recommendations

Do not put the Groq API key directly in `app.py`.

Use:

- Streamlit Secrets for Streamlit Cloud
- environment variables for local/Colab

Never commit:

```text
GROQ_API_KEY=...
```

to GitHub.

Also avoid sending confidential case information to an external LLM unless your organization's legal, privacy and security requirements permit it.

---

# 13. Free-tier considerations

The core stack is designed to avoid paid infrastructure:

| Component | Cost approach |
|---|---|
| Streamlit | Community Cloud |
| FAISS | Free/open-source |
| Sentence Transformers | Free/open-source |
| PyMuPDF | Free/open-source |
| Python | Free |
| Groq | API account/free availability subject to Groq's current limits |
| PDF storage | Downloaded at runtime |

The embedding model is downloaded at startup, so the first deployment may be slower than later reruns.

Free hosting providers can have resource, sleep, memory and request limits. These are platform limits rather than application requirements.

---

# 14. Current architecture

```text
                    ┌──────────────────────┐
                    │ Google Drive PECA PDF│
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │      PyMuPDF         │
                    │   Text extraction    │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Chunking + metadata  │
                    │ page + section       │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Sentence Transformer │
                    │ all-MiniLM-L6-v2     │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │        FAISS         │
                    │  local vector index  │
                    └──────────┬───────────┘
                               │
                 User question│
                               ▼
                    ┌──────────────────────┐
                    │ Semantic retrieval   │
                    │      Top-K           │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Strict RAG prompt    │
                    │ source-only rules    │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │      Groq LLM        │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Answer + Sources     │
                    └──────────────────────┘
```

---

# 15. Troubleshooting

## `GROQ_API_KEY is not set`

Set the environment variable locally/Colab or add:

```toml
GROQ_API_KEY = "YOUR_KEY"
```

to Streamlit Secrets.

## Google Drive download fails

Check that the PDF can be accessed without your personal Google login.

## FAISS installation fails

Use a Python environment supported by the current `faiss-cpu` package. Streamlit Cloud normally installs packages from `requirements.txt`.

## First startup is slow

Expected behavior. The application has to:

1. download the PDF
2. download the embedding model
3. extract the PDF
4. generate embeddings
5. build the FAISS index

The Streamlit resource cache prevents rebuilding these resources on every normal interaction.

## Answer says information is insufficient

This is intentional. Try:

- increasing Retrieved passages
- lowering Minimum similarity
- using the legal term or section number
- asking a more specific question

---

# 16. Files

### `app.py`

Main Streamlit application, PDF downloader, parser, chunker, embedding pipeline, FAISS retrieval and Groq generation.

### `requirements.txt`

Python dependencies.

### `readme.md`

Installation, deployment, architecture and usage documentation.

---

## Disclaimer

CyberLawGPT provides **source-grounded legal information from the supplied PDF**. It does not determine guilt, liability, enforceability, or the outcome of a real case. Laws, amendments, rules and judicial interpretations can change. For a real dispute, investigation, complaint, prosecution, compliance decision or legal proceeding, consult a qualified Pakistani legal professional and verify the current official law.
