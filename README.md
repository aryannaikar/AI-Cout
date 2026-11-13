# ⚖️ AI Court of India

An autonomous judicial reasoning and multi-agent courtroom simulation system modeled after the legal and constitutional framework of the Supreme Court and High Courts of India.

---

## 📋 Quick Start Guide

### 1. Prerequisites
- **Python 3.10+** (Tested on Python 3.13)
- **Node.js 18+** (Tested on v24.x)
- *(Optional)* **Ollama** or **NVIDIA NIM API** for LLM inference.

---

### 2. Configure Environment (`.env`)

Check or edit the `.env` file in the project root:

```env
# Choose provider: 'ollama', 'nvidia', or 'mock'
LLM_PROVIDER=ollama

# Option A: Local Ollama (Default)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3:latest

# Option B: NVIDIA Cloud NIM API
NVIDIA_API_KEY=your_nvidia_api_key_here
NVIDIA_MODEL=meta/llama-3.2-11b-vision-instruct
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
```

> 💡 **Tip for quick testing without any setup**:  
> Set `LLM_PROVIDER=mock` in `.env` for zero-network deterministic testing and instant UI demonstration!

---

### 3. Step 1: Start the Backend (FastAPI)

Open a terminal and run:

```bash
# Navigate to backend folder
cd backend

# Run the FastAPI server via Uvicorn
uvicorn app.main:app --reload --port 8000
```
python -m uvicorn app.main:app --reload --port 8000

*(Alternatively from project root: `python backend/app/main.py`)*

#### Verify Backend:
- **API Health**: [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)
- **LLM Diagnostic**: [http://127.0.0.1:8000/api/health/llm](http://127.0.0.1:8000/api/health/llm)
- **Interactive Swagger Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

### 4. Step 2: Start the Frontend (Vite + React)

Open a second terminal and run:

```bash
# Navigate to frontend folder
cd frontend

# Start Vite dev server
npm run dev
```

> ⚠️ **Windows PowerShell Note**:  
> If PowerShell blocks `npm` with a script execution policy warning (`npm.ps1 cannot be loaded`), use:
> ```powershell
> npm.cmd run dev
> ```
> or run: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`

Once started, open your browser at:
👉 **[http://localhost:5173](http://localhost:5173)**

---

### 5. Running the Simulation in the UI

1. Open the web interface at **`http://localhost:5173`**.
2. Upload a case packet PDF or paste case facts:
   - A pre-built sample case packet is available at:  
     `data/cases/case_packet/Jai_Bhagwan_Evidence_Packet.pdf`
3. Click **Start Court Proceedings**.
4. Observe the live multi-agent simulation:
   - Case Intake & Parsing Agent
   - Legal Research & Precedent Retriever (RAG)
   - Prosecution & Defense Arguments
   - Bench Deliberation & Final Written Judgment

---

### 6. Running Tests

To run the automated test suite:

```bash
# Run tests targeting the tests/ directory
pytest tests/
```
*(Pytest automatically uses `LLM_PROVIDER=mock` to ensure fast, hermetic, zero-cost execution).*

---

### 7. Project Architecture

```
AI-Court-of-India/
├── backend/
│   └── app/
│       ├── agents/          # CaseAgent, Prosecutor, Defense, Bench
│       ├── api/             # FastAPI court routes & SSE streaming
│       ├── core/            # Centralized LLM Provider (Ollama / NVIDIA / Mock)
│       ├── graph/           # LangGraph courtroom simulation pipeline
│       ├── models/          # Pydantic schemas (packet, arguments, judgment)
│       ├── rag/             # Legal corpus loader, chunker, ChromaDB retriever
│       └── services/        # Judgment writer & PDF generator
├── data/
│   ├── cases/               # Case packets (strictly separated from ground truth)
│   ├── legal_corpus/        # Indian Penal Code, CrPC, Evidence Act documents
│   └── vectorstore/         # ChromaDB persistence
├── frontend/                # React 19 + TypeScript + Vite UI
└── tests/                   # Pytest test suite
```
"# AI-Cout" 
