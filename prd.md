# Product Requirements Document (PRD)

## Product Name
**LEO-Chat (Law Enforcement Operations Chat)**  
A secure, local intelligence tool that enables law enforcement personnel to efficiently query and analyze press releases from the U.S. Attorney's Office for the Central District of California—fully on their local machine.

---

## 1. Overview

### 1.1 Product Summary
This application empowers law enforcement officers and analysts to quickly search and analyze a locally hosted corpus of legal news articles from the U.S. Attorney's Office (Central District of California). Using Retrieval-Augmented Generation (RAG), it provides rapid access to case precedents, enforcement actions, and investigative outcomes. The system operates entirely locally, ensuring operational security and data privacy.

### 1.2 Target Audience
- **Law Enforcement Officers** needing quick reference to similar cases or precedents
- **Intelligence Analysts** researching patterns in criminal activities or prosecution strategies
- **Task Force Members** requiring offline access to historical case information
- **Investigative Teams** seeking context for current investigations

### 1.3 Objectives
1. Provide **rapid intelligence gathering** capabilities for law enforcement operations
2. Ensure **operational security** by running **entirely locally** without external APIs
3. Create an **intuitive interface** that helps officers quickly find relevant case information
4. Enable **pattern recognition** across multiple cases and investigations

---

## 2. Key Features

1. **Web Scraping**  
   - Automatically scrape the [U.S. Attorney's Office – Central District of CA News Page](https://www.justice.gov/usao-cdca/pr) to gather all recent articles.  
   - Parse and store relevant text (titles, content, links).

2. **Local Vector Embeddings**  
   - Use **Sentence-Transformers (e.g., `all-MiniLM-L6-v2`)** to generate embeddings for each chunk of text.  
   - Ensure embeddings are computed and stored locally.

3. **FAISS Indexing & Retrieval**  
   - Maintain a **FAISS** index for efficient similarity search.  
   - On user query, retrieve the **top-N** most relevant chunks.

4. **Chunking & Preprocessing**  
   - Split articles into **overlapping chunks** (configurable size, e.g., 300 words with 50-word overlap).  
   - Enhance relevance by preserving context in each chunk.

5. **Chat-Style Query Interface**  
   - Users input queries in a **simple chat interface** (CLI, Streamlit, or Gradio for a prototype).  
   - The system returns the best possible answer, plus a **side panel** listing relevant document excerpts or links.

6. **Local Generative Model (Optional for Prototype)**  
   - (Optional) Integrate a small local generative model (e.g., GPT2, LLaMA 2 7B quantized) to produce natural language answers from retrieved context.  
   - Alternatively, for the early prototype, provide direct chunk retrieval and highlight relevant text.

7. **Secure, Offline Deployment**  
   - No external API calls—**all** data processing, storage, and inference remain offline.  
   - Suitable for environments that handle sensitive or classified data.

---

## 3. Functional Requirements

1. **Scraping**  
   1.1 The system shall fetch HTML pages from the specified news URL.  
   1.2 The system shall parse links to individual article pages and extract relevant text (e.g., paragraphs).  
   1.3 The system shall store scraped data in a structured format (JSON, pickle, or database).

2. **Preprocessing**  
   2.1 The system shall split articles into chunks of a defined size (in words or tokens).  
   2.2 The system shall allow configurable overlap (e.g., 50 words) to maintain context.

3. **Indexing**  
   3.1 The system shall generate **embeddings** for each chunk using the local `sentence-transformers/all-MiniLM-L6-v2` model.  
   3.2 The system shall store embeddings in a **FAISS** index locally.  
   3.3 The system shall provide a means to re-build the index if new articles are scraped.

4. **Retrieval**  
   4.1 The system shall accept a user query and embed it locally using the same embedding model.  
   4.2 The system shall query the FAISS index to retrieve the top relevant chunks (default top-N = 3–5).  
   4.3 The system shall return chunk excerpts along with their source article URLs/titles.

5. **Response Generation** (for a more advanced prototype)  
   5.1 The system may optionally feed the retrieved excerpts + user query into a local generative model.  
   5.2 If a local LLM is used, no calls to external AI endpoints or APIs shall be made.

6. **User Interface**  
   6.1 The system shall provide a minimal chat-like interface that:  
   - Lets the user type a question.  
   - Displays the generated answer in a main content area.  
   6.2 The system shall have a side panel that, when opened, shows the top relevant document chunks and links.

7. **Security / Privacy**  
   7.1 All data, including embeddings and indexes, shall remain on the local machine.  
   7.2 No calls to third-party or cloud-based APIs for inference or storage.  
   7.3 The system shall allow an offline mode (no internet connection required) once data is scraped and stored.

---

## 4. Non-Functional Requirements

1. **Performance**  
   - Embedding generation should run in **reasonable time** on an M2 MacBook Air (with CPU or Apple Silicon MPS acceleration).  
   - Query latency should be **under 2 seconds** for top-N retrieval from a corpus of ~ hundreds or thousands of articles.

2. **Scalability**  
   - The FAISS index should handle growth in the number of articles without significant slowdown.  
   - The system should maintain performance for up to **tens of thousands** of chunks (fine for M2 with enough storage).

3. **Usability**  
   - Prototype UI must be **straightforward and intuitive**—text box for input, quick output display.  
   - Side panel must clearly identify relevant document titles/links for user reference.

4. **Maintainability**  
   - Modular code structure (scraping, preprocessing, indexing, retrieval, UI) to ease updates and debugging.  
   - Clear versioning to handle changes in the website's layout or the embedding model.

5. **Reliability**  
   - The application should handle network failures gracefully during scraping.  
   - The user should be able to re-run or re-index at any time.

6. **Legal & Ethical**  
   - Respect robots.txt and Terms of Service for scraping the site.  
   - Store only publicly available content; do not modify or misrepresent official announcements.

---

## 5. Technical Architecture

1. **Data Pipeline**  
   - **Scraper**: Uses `requests` + `BeautifulSoup` to download and parse article content.  
   - **Chunking & Preprocessing**: Splits each article into overlapping segments.  
   - **Embedding**: Generates vector representations (768-dim for MiniLM) with SentenceTransformers.  
   - **Indexing**: Stores vectors in a local FAISS index along with metadata (e.g., article ID, chunk offset).

2. **Query Flow**  
   - **User Query** → Local embedding → FAISS similarity search → Return top-N chunks + metadata → Summarize or directly show chunks.  
   - (Optional) If a local generative LLM is integrated, the chunk texts are injected into a prompt to produce a final, natural-language answer.

3. **Local Deployment**  
   - Code runs within a **Python virtual environment**.  
   - No external calls except for initial scraping from `justice.gov`.  
   - The system can be used offline once the data is collected.

4. **UI**  
   - **CLI or Web**: For a simpler prototype, a command-line interface or **Streamlit/Gradio** for a more user-friendly chat experience.  
   - **Side Panel**: Displays relevant articles with a short excerpt or link to the full text.

---

## 6. Implementation Plan

1. **Setup Development Environment**  
   - Configure Python 3.10+ with `virtualenv` or Conda on Mac M2.  
   - Install required packages (`requests`, `beautifulsoup4`, `faiss-cpu`, `sentence-transformers`, `torch`, etc.).

2. **Scraping & Data Collection**  
   - Implement `scrape_articles()` to gather titles, links, and article text.  
   - Test against the target site to ensure correct data extraction.

3. **Chunking & Embedding**  
   - Implement a chunking function (e.g., 300 words with 50-word overlap).  
   - Use `SentenceTransformer("all-MiniLM-L6-v2")` to embed chunks.  
   - Convert embeddings to `float32` and store them alongside chunk metadata (title, URL, text).

4. **FAISS Index Creation**  
   - Build a `IndexFlatL2` or more advanced index as needed.  
   - Add all chunk embeddings, store to disk (`faiss_index.index`).

5. **Retrieval & Query Script**  
   - Implement a function to load the index and retrieve top-N chunks based on a new query's embedding.  
   - Print or return relevant metadata to confirm correct retrieval.

6. **(Optional) Generative Answering**  
   - Integrate a local LLM (or a minimal T5/GPT2 for a prototype).  
   - Construct a prompt from the user's query + retrieved chunks.  
   - Generate an answer offline.

7. **UI / Prototype Demo**  
   - Use **Streamlit** or **Gradio** for a quick chat-like interface.  
   - Display the final answer in a main panel, with a collapsible side panel listing retrieved chunks.

8. **Testing & Validation**  
   - Confirm correctness of chunk retrieval.  
   - Evaluate user queries (e.g., "What recent cases involve bank fraud?") for relevance.  
   - Ensure performance is acceptable on MacBook Air M2.

---

## 7. Acceptance Criteria

1. **Scraping Completes**  
   - The system successfully scrapes all article links from the news page without errors.  
   - At least 90% of the article text is properly captured and chunked.

2. **Local Index**  
   - FAISS index is built with no errors and can be saved/loaded from disk.  
   - Querying with a relevant test question returns accurate chunks from the correct articles.

3. **Basic Q&A**  
   - The user can type a question, and the system returns top-N relevant article excerpts in under 2 seconds (for a typical system size).  
   - (Optional) If a local generative model is integrated, the system provides a coherent answer referencing the relevant chunk(s).

4. **UI Visibility**  
   - A minimal but functional interface (CLI or web) is operational.  
   - The user can see which article(s) were used in generating the answer.

5. **No External API Usage**  
   - The code does not send documents or queries to any external service for inference.

---

## 8. Risks & Mitigations

1. **Website Structure Changes**  
   - **Risk**: The scraping logic may break if the news site updates its HTML.  
   - **Mitigation**: Maintain flexible CSS selectors and re-check them regularly.

2. **Performance on M2**  
   - **Risk**: Large-scale data sets or bigger models might exceed hardware constraints.  
   - **Mitigation**: Use smaller, optimized models (MiniLM, 8-bit quantization if needed).

3. **Incomplete or Inconsistent Articles**  
   - **Risk**: Some articles have minimal text or different formatting.  
   - **Mitigation**: Implement robust text extraction and handle empty or partial content gracefully.

4. **Generative Model Accuracy**  
   - **Risk**: If the local LLM is too small, answers may be less fluent or inaccurate.  
   - **Mitigation**: Provide direct retrieved chunks as fallback or consider a more capable local model (e.g., LLaMA 2 7B).

---

## 9. Future Enhancements

1. **Advanced Retrieval**  
   - Experiment with a hybrid approach (BM25 + Vector) to improve search accuracy.  
   - Add a cross-encoder re-ranking step for improved precision.

2. **Chunk Summarization**  
   - Summarize top chunks before showing them to the user for clarity.

3. **Role-Based Access**  
   - If expanded to classified documents, incorporate user authentication and per-document access controls.

4. **Knowledge Graph Integration**  
   - For structured legal entities or relationships, consider building a knowledge graph with Neo4j or similar.

5. **Fine-Tuning**  
   - Fine-tune or LoRA-adapt a local model on a larger set of legal texts for domain-specific improvements.

---

## 10. Timeline & Milestones

1. **Week 1**:  
   - Environment Setup, Python Packages, Basic Scraping  
   - Validate scraping coverage for all articles.

2. **Week 2**:  
   - Implement Chunking, Embedding, FAISS Index  
   - Test retrieval with sample queries.

3. **Week 3**:  
   - (Optional) Integrate a lightweight local generative model  
   - Develop a simple UI (Streamlit/Gradio).

4. **Week 4**:  
   - Conduct end-to-end testing  
   - Collect user feedback and refine.

---

## 11. Conclusion

By implementing a local RAG pipeline that scrapes, chunks, embeds, and indexes recent legal news articles, this system will provide a **secure, offline** way to explore and query the U.S. Attorney's Office for the Central District of California's public statements and press releases. The chat-like interface with a side panel displaying relevant document excerpts ensures transparency, accuracy, and user trust in the results.
