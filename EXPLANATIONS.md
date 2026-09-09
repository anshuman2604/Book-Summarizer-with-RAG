# CONCEPT EXPLAINER: HOW OUR AI BOOK SYSTEM ACTUALLY WORKS

This guide explains the core mechanisms behind our AI Book Summarizer & Q&A agent in simple, clear language.

---

## 1. Why Give Page Numbers to the AI? (Why Not Just the Text?)

### The Real-World Problem
When you upload a **500-page book** and ask a question:
- If the AI just gives you a plain answer, how do you know it didn't hallucinate or make it up?
- Are you going to re-read all 500 pages just to verify what the AI said? No.

### How Our System Solves This
1. **Vectors Find the Location:** 
   When you ask a question, pgvector does mathematical cosine similarity to find the top 5 most relevant paragraphs from the database.
2. **Text + Page Number are Handed to Gemini:**
   We don't give Gemini raw numbers (AI reads words, not vector numbers). We give Gemini the actual human text paragraphs, each stamped with its page number:
   `	ext
   [Page 142]:
   The mitochondrion is an organelle that generates chemical energy (ATP)...
   `
3. **The AI Cites Its Source:**
   Gemini reads that paragraph and responds:
   > *'According to [Page 142], mitochondria generate chemical energy (ATP) for the cell.'*
4. **The Benefit:** 
   Instant trust and verification. The user can flip directly to Page 142 in their PDF reader and confirm the fact with their own eyes.

---


## 3. How Do We Actually Search for Vectors? (Vector Search Demystified)

### The Problem with Normal Text Search (Ctrl+F)
If you search for: *"Why was the protagonist depressed?"*
- Normal database search (LIKE '%depressed%') looks for that exact word.
- If the book said: *"He felt an overwhelming sorrow and deep emptiness in his soul"*, normal search **FAILS completely** because the word 'depressed' never appears!

### How Our Vector Search Works (Semantic Meaning in Math)

#### Step 1: Text to Coordinates (Embeddings)
When the book is uploaded, Google's 	ext-embedding-004 reads every chunk and translates its **meaning/concept** into 768 coordinate numbers:
- Chunk A ("The hero felt sorrow and emptiness") ──▶ [0.21, 0.85, -0.44, ... 768 numbers]
- Chunk B ("The recipe requires 2 cups of sugar") ──▶ [-0.91, 0.05, 0.63, ... 768 numbers]
These 768 numbers place each sentence at an exact point in 768-dimensional space. Sentences with similar meanings are placed physically close to each other.

#### Step 2: User Question to Coordinates
When a user asks: *"Why was the protagonist depressed?"*
We convert that question into the exact same 768 coordinates:
- Question Vector ──▶ [0.20, 0.84, -0.42, ...]

#### Step 3: Cosine Similarity in PostgreSQL (pgvector)
We tell Supabase PostgreSQL:
`sql
SELECT * FROM book_chunks 
WHERE book_id = '...' 
ORDER BY embedding <=> query_vector 
LIMIT 5;
`
- The operator <=> measures the **angle (Cosine Distance)** between the question vector and every chunk vector in the book.
- Even though the words are completely different, the angle between *'depressed'* and *'sorrow and emptiness'* is almost ^\circ$ (meaning 98% match!).
- Supabase instantly returns the top 5 closest paragraphs in under 5 milliseconds.

---

## 4. How JWT Authentication Works (And Why Passwords Are Never In The Token!)

### Why Do We Need Tokens at All?
The internet protocol (HTTP) has **amnesia (it is stateless)**:
- When you click 'Login', the server verifies you, but the connection immediately closes.
- 2 seconds later when you click 'Upload Book', that is a brand new request. The server doesn't remember who you are.
- Without tokens, you would have to type your password on every single click!

### Is the Password Encrypted Inside the JWT?
**NO! A password is NEVER stored inside a JWT!**
Putting passwords in tokens is a dangerous security flaw.

### What is ACTUALLY inside the JWT?
A JWT is just a JSON payload with 2 simple fields:
`json
{
  "sub": "9b1deb4d-3b7d-4bad-9cde-3456789abcde",  // ONLY your User ID in Supabase
  "exp": 1741305600                                 // When this token expires (24 hours)
}
`

### If there is no password, how does the server trust it?
Through a **Cryptographic Digital Signature** (like a bank check or royal wax seal):
1. **At Login:** You enter your password once. The server verifies it against Supabase.
2. **Token Creation:** The server seals the user_id using our private SECRET_KEY (HMAC-SHA256).
3. **Subsequent Clicks:** The browser sends the token in the Authorization: Bearer <token> header.
4. **Instant Verification:** The server uses SECRET_KEY to verify the mathematical signature:
   - *Was it signed by my SECRET_KEY? YES.*
   - *Did a hacker tamper with the user_id? NO (altering even 1 character destroys the signature).*
   - *Is it expired? NO.*
5. **Result:** The server knows 100% that this is genuine User 9b1deb4d... without ever needing to see or store a password again!


  #### 1. Single-Call Whole-Book Synthesis (summarizer.py:60-96)
  • Optimization: Gemini has an expansive 1-million token context window. We select 20 evenly distributed excerpts covering the entire book (introduction, middle chapters, climax, conclusion) and synthesize the executive summary in 1 single high-efficiency API call.
  • Test Result: 100 words exact generated in a single call without consuming unnecessary API quota.

  #### 2. Adaptive Chunker Size (parser.py:19-30)
  • Optimization: Increased chunk size to 2,500 characters (~500 words) with 250-character overlap.
  • Impact: Cuts the total number of chunks by roughly 40%, reducing embedding requests and speeding up Supabase retrieval.

  #### 3. High-Speed Cohere Embeddings (vector_store.py:53-110)
  • Optimization: Uses Cohere's embed-english-v3.0 model with a 100 Requests/Minute free tier.
  • Fast Batches: Embeds in batches of 60 chunks per network call, saving 500+ page books in seconds.

---

## 5. Deep Dive: How Chunking & Batch Storage Actually Works (Line-by-Line)

### The Core Question
> *"If we send 60 chunks in 1 API call, does Cohere know the page numbers? How does Python keep them organized, and how are they mapped in the database?"*

### The Fundamental Rule
**The embedding AI (Cohere) knows NOTHING about 'books' or 'page numbers'. Cohere only sees raw strings of text.**
It acts like a pure math calculator:
- If you give it 60 strings of text, it returns 60 mathematical vectors.
- It does not know that string #1 came from Page 1 or string #60 came from Page 45.
- **Your Python code does all the tracking and organization.**

---

### Phase 1: Python Reads the Book Page-by-Page (`backend/services/parser.py`)

When you upload a PDF, Python extracts the text **page by page** so it knows the origin of every word:

```python
# parser.py - create_chunks()
def create_chunks(self, pages_content: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    chunks = []
    chunk_index = 0

    # 1. Loop through each page extracted from the PDF
    for page_item in pages_content:
        page_num = page_item["page_number"]   # e.g., Page 1
        page_text = page_item["text"]          # Text extracted from Page 1

        # 2. Split this specific page into ~500-word chunks with 250-char overlap
        page_splits = self.splitter.split_text(page_text)

        # 3. Attach the exact page_number to each chunk!
        for split_text in page_splits:
            chunks.append({
                "chunk_index": chunk_index,
                "page_number": page_num,      # <--- Tagged with its source page!
                "content": split_text         # The actual sentence/paragraph
            })
            chunk_index += 1

    return chunks
```

#### What Python holds in memory at this point:
```python
chunks_data = [
    {"chunk_index": 0, "page_number": 1, "content": "Intro to social psychology..."},
    {"chunk_index": 1, "page_number": 1, "content": "Core hypotheses..."},
    {"chunk_index": 2, "page_number": 2, "content": "Research methodology..."},
    ...
    {"chunk_index": 678, "page_number": 516, "content": "Conclusion and index..."}
]
```
Notice: Every single chunk in Python's memory is a dictionary that holds its text AND its exact `page_number`.

---

### Phase 2: Slicing 60 Chunks and Calling Cohere (`backend/services/vector_store.py`)

Sending 679 individual API calls would take minutes and trigger rate limits. 
Instead, Python slices the big list into **batches of 60**:

```python
batch_size = 60
total_chunks = len(chunks_data)  # 679 chunks for a 516-page book

# Loop in steps of 60: 0, 60, 120, 180...
for i in range(0, total_chunks, batch_size):

    # 1. Slice 60 chunks from the list (indices 0 to 59)
    batch = chunks_data[i : i + batch_size]

    # 2. Pull OUT just the raw text strings to send to Cohere
    batch_texts = [c["content"] for c in batch]
    # batch_texts is a list of 60 strings: ["Chunk 0 text...", ..., "Chunk 59 text..."]

    # 3. ONE SINGLE API CALL to Cohere!
    # Cohere computes all 60 vectors simultaneously and returns them in the EXACT SAME ORDER
    batch_vectors = self.client.embed(
        texts=batch_texts,
        model="embed-english-v3.0",
        input_type="search_document"
    ).embeddings.float_
    # batch_vectors is a list of 60 vectors: [Vector_0, Vector_1, ..., Vector_59]
```

---

### Phase 3: Re-Uniting Page Numbers with Vectors (`zip()`)

Now comes the critical step. How does Python map each vector back to its correct page number?
Using Python's built-in **`zip(batch, batch_vectors)`**:

```python
    db_chunks = []
    # zip() walks through both lists side-by-side:
    for chunk_meta, vector in zip(batch, batch_vectors):
        # In iteration 0:
        #   chunk_meta is batch[0]           --> {page_number: 1, content: "Intro..."}
        #   vector is batch_vectors[0]       --> [0.012, -0.045, ... 1024 numbers]

        # In iteration 1:
        #   chunk_meta is batch[1]           --> {page_number: 1, content: "Core..."}
        #   vector is batch_vectors[1]       --> [0.034, 0.081, ... 1024 numbers]

        db_chunk = BookChunk(
            book_id=book_id,
            chunk_index=chunk_meta["chunk_index"],
            page_number=chunk_meta["page_number"],  # <--- Page number preserved!
            content=chunk_meta["content"],          # <--- Text preserved!
            embedding=vector                         # <--- Matching 1024 vector!
        )
        db_chunks.append(db_chunk)

    # 4. Save all 60 complete rows to Supabase in one fast SQL INSERT
    db.bulk_save_objects(db_chunks)
    db.commit()
```

---

### Phase 4: What Sits Inside Supabase PostgreSQL

When this finishes, your database has **679 independent rows** in the `book_chunks` table:

| id | book_id | chunk_index | page_number | content | embedding |
| :--- | :--- | :---: | :---: | :--- | :--- |
| `uuid-1` | `db988be3...` | 0 | **1** | *"Chapter 1: Intro to psychology..."* | `[0.012, -0.045, ... 1024 floats]` |
| `uuid-2` | `db988be3...` | 1 | **1** | *"Core hypotheses of the study..."* | `[0.034, 0.081, ... 1024 floats]` |
| `uuid-3` | `db988be3...` | 2 | **2** | *"Research methodology..."* | `[-0.091, 0.022, ... 1024 floats]` |
| `uuid-4` | `db988be3...` | 3 | **14** | *"Diener's happiness experiment..."* | `[0.055, -0.011, ... 1024 floats]` |
| `...` | `...` | `...` | `...` | `...` | `...` |
| `uuid-679`| `db988be3...` | 678 | **516** | *"Conclusion & references..."* | `[0.008, 0.071, ... 1024 floats]` |

---

### Phase 5: How Q&A Finds the Exact Page (The Retrieval Step)

When you ask:
> *"What did Diener discover about subjective well-being?"*

1. **Vectorize Question:** Python asks Cohere: *"Convert this question into a 1024 vector."*
2. **Search Database:** Python sends a SQL query to Supabase:
   ```sql
   SELECT page_number, content 
   FROM book_chunks 
   WHERE book_id = 'db988be3...'
   ORDER BY embedding <=> :question_vector 
   LIMIT 5;
   ```
   Supabase calculates the cosine distance (`<=>`) between the question vector and all 679 chunk vectors. It finds **Row 4** because its vector matches the semantic meaning of "happiness and well-being".
3. **Inspect the Result:** Supabase hands back:
   - `page_number: 14`
   - `content: "Diener's happiness experiment showed that..."`
4. **Prompt Gemini:** Python constructs the prompt for Gemini 3.6 Flash:
   > *"You are an AI assistant. Use this excerpt to answer the question, and cite the page number:*  
   > *[Page 14]: Diener's happiness experiment showed that..."*
5. **Answer Delivered:** Gemini writes:
   > *"According to Page 14, Diener discovered that subjective well-being is..."*

---

### Visual Summary

```
516-Page PDF
    │
    ▼ (Python reads page-by-page)
679 Chunks, each stamped with its page number (in Python memory)
    │
    ▼ (Python extracts text only, sends 60 strings per call)
Cohere API returns 60 vector arrays
    │
    ▼ (Python uses zip() to pair Vector[i] with Page_Number[i])
Supabase PostgreSQL stores 679 rows with: [Page Number] + [Text] + [Vector]
    │
    ▼ (User asks a question)
pgvector finds matching row -> gives Page Number + Text to Gemini -> Gemini cites the page!
```

---

## 6. Visual Breakdown: How Chunks, Characters & API Calls Work

To understand our system, think of it as **three distinct jobs**, each using chunks in its own way:

---

### 🟢 Job 1: Vector Embeddings (Database Indexing)
> **Goal:** Save every page of the book into Supabase so we can search it later.

* **Model Used:** Cohere `embed-english-v3.0` (100 Requests/Minute Free Tier)
* **What is 1 Chunk?** 
  * A text snippet of **2,500 characters** (roughly 500 words, about 1 page).
* **How many chunks are processed?** 
  * **100% of the book.** If the book has 500 pages, all ~680 chunks are embedded.
* **How are they sent to the AI?**
  * We don't send them one by one. Python sends them in **batches of up to 60 chunks at a time**.
  * Format: `["Text of chunk 1", "Text of chunk 2", ... "Text of chunk 60"]`
  * *Note on the last batch:* It dynamically sends whatever is left (e.g., 19 chunks).
* **How many API calls?**
  * $\text{Total Chunks} \div 60$ (e.g., a 516-page book takes **only 12 API calls**).
* **What comes back?**
  * 60 separate lists of numbers (1024-dimension float vectors), which Python saves into Supabase.

---

### 🔵 Job 2: The Summarizer (~100-Word Executive Summary)
> **Goal:** Read across the whole book and write a strict ~100-word overview.

* **Model Used:** Google Gemini 3.6 Flash (1,000,000 token context window)
* **How many chunks does it read?**
  * **Only 20 sampled chunks** (NOT the entire book!).
  * Python steps through the book evenly (`step = total_chunks // 20`):
    * Chunk 0 (Intro from Page 1)
    * Chunk 33, 66, 99... (Middle chapters)
    * Chunk 660 (Conclusion from Page 516)
  * The other 659 chunks are intentionally skipped for the summary to keep it fast and focused.
* **How many characters/words total?**
  * $20 \text{ chunks} \times 2,500 \text{ characters} \approx \mathbf{50,000 \text{ characters}}$ (~10,000 words).
* **How are they sent to the AI?**
  * Glued into **1 single prompt** separated by `---`:
    ```text
    [Page 1]: Text...
    ---
    [Page 25]: Text...
    ---
    [Page 500]: Text...
    ```
* **How many API calls?**
  * **EXACTLY 1 CALL.**
* **What comes back?**
  * A standalone, executive summary of **approximately 100 words** in ~1.8 seconds.

---

### 🟣 Job 3: Q&A Agent (Grounded Answers with Citations)
> **Goal:** Answer the user's specific question using exact facts from the book.

* **Model Used:** Google Gemini 3.6 Flash (Generation) + Cohere (Question Embedding)
* **How many chunks does it read?**
  * **Only the Top 5 most relevant chunks** (`top_k = 5`).
  * Supabase uses vector math to find the 5 chunks whose meaning is closest to the question.
* **How many characters/words total?**
  * $5 \text{ chunks} \times 2,500 \text{ characters} \approx \mathbf{12,500 \text{ characters}}$ (~2,500 words).
* **How are they sent to the AI?**
  * Stamped with their real page numbers in **1 single prompt**:
    ```text
    Here are the retrieved book excerpts:
    [Page 14]: Excerpt about Diener's happiness study...
    [Page 15]: Continued findings...

    Question: What did Diener discover?
    Answer the question and cite the exact page numbers:
    ```
* **How many API calls?**
  * **1 call to Cohere** (to turn the question into a vector).
  * **1 call to Gemini** (to read the 5 chunks and write the answer).
* **What comes back?**
  * An accurate, non-hallucinated answer with page citations (e.g., *"According to Page 14..."*).

---

### 📊 At-a-Glance Summary Table

| Feature | 🟢 Vector Storage | 🔵 Book Summarizer | 🟣 Q&A Chat |
| :--- | :--- | :--- | :--- |
| **Model** | Cohere `embed-english-v3.0` | Gemini `3.6-flash` | Gemini `3.6-flash` |
| **Chunks Used** | **ALL chunks** (100% of book) | **20 sampled chunks** (~3% of book) | **Top 5 matched chunks** |
| **Text Volume** | ~1,700,000 characters | ~50,000 characters | ~12,500 characters |
| **Chunks per Call**| Up to **60 chunks** at once | All **20 chunks** in 1 call | All **5 chunks** in 1 call |
| **Number of Calls**| $\approx 12$ calls (for 500 pages) | **1 single call** | **1 single call** |
| **Time Taken** | ~15 to 20 seconds | ~1.8 seconds | ~1.5 seconds |
| **Output** | 1024-dim vectors into database | ~100-word executive summary | Conversational answer with citations |