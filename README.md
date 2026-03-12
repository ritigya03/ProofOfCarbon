# 🌍 ProofOfCarbon

**ProofOfCarbon** is an agentic AI system that verifies carbon credit projects and prevents greenwashing by combining multi-agent reasoning, privacy-preserving fraud intelligence, and immutable blockchain audit trails.

Carbon markets rely heavily on trust, yet many carbon credit claims are exaggerated, unverifiable, or misleading. ProofOfCarbon introduces a transparent, AI-driven verification pipeline with cryptographic proof.

---

## 🚨 Problem Statement

Carbon credits are widely used by companies to offset emissions and claim sustainability.  
However, the ecosystem faces major challenges:

- Greenwashing through exaggerated or false claims
- Weak and opaque verification processes
- Lack of historical baseline validation
- No tamper-proof record of verification outcomes

These issues undermine climate action and investor confidence.

---

## 💡 Solution Overview

ProofOfCarbon acts as an **AI-powered carbon credit auditor**.

It verifies carbon credit projects using a **team of specialized AI agents**, each responsible for analyzing a different trust dimension.  
The final verification result is then **anchored on blockchain**, ensuring integrity, transparency, and auditability.

---

## 🧠 System Architecture

### 1. Agentic AI Verification Layer

ProofOfCarbon employs a modular multi-agent architecture:

- **Project Analysis Agent**  
  Extracts project claims, location, timeline, and promised emission reductions from reports.

- **Satellite Evidence Agent**  
  Validates land-use or forest-cover changes using satellite indicators (mocked or external).

- **Historical Baseline Agent**  
  Determines whether the claimed reduction would likely have occurred without carbon credit funding.

- **Fraud Reasoning Agent**  
  Identifies suspicious patterns using shared global fraud intelligence.

- **Verifier Agent**  
  Aggregates all findings into a trust score, risk classification, and explanation.

---

### 2. Machine Learning (Conceptual Layer)

To improve fraud detection, ProofOfCarbon integrates **Machine Learning (ML)** at the architecture level:

- Carbon registries train fraud detection models on historical project data
- Learned fraud patterns are used to identify suspicious claims across the ecosystem
- Continuous improvement of detection accuracy through shared intelligence

This enables collaborative intelligence while maintaining a focus on project integrity.

---

### 3. Blockchain Audit Trail

After AI verification:

- The verification report is hashed
- The hash, trust score, and timestamp are stored on-chain
- Results become immutable and publicly verifiable

This creates a **tamper-proof audit trail** for carbon credit verification.

---

## 🧱 Tech Stack

### AI & Backend
- Python
- LLM APIs (OpenAI / Groq)
- Agent-based reasoning architecture

### Frontend
- Next.js (App Router)
- TypeScript
- Tailwind CSS
- Framer Motion (animations)

### Blockchain
- Solidity smart contracts
- Polygon Amoy / Sepolia testnet
- Ethers.js or Viem

### Privacy & Trust
- Machine Learning (architecture-level integration)
- On-chain verification hashes (no sensitive data stored)

---

## 🔄 End-to-End Workflow
Carbon Project Report
↓
Agentic AI Verification
↓
Trust Score + Risk Explanation
↓
Verification Report Hash
↓
Blockchain Storage
↓
Public, Immutable Audit Record


---

## 📂 Data Management & Caching

ProofOfCarbon uses a multi-tier spatial data strategy to ensure high performance and reliability:

### 1. Static Reference Data
The following files are included in the repository to provide an initial baseline:
- `data/reference/india_forest_cover.geojson`: National forest cover (derived from OSM).
- `data/reference/india_protected_areas.geojson`: Map of national parks and reserves.
- `data/reference/*.csv`: Permanence scores and historical deforestation rates.

### 2. On-Demand State Caching
When a project is analyzed in a new state, the system automatically fetches the latest forest geometry from the **OSM Overpass API**.
- **Performance**: The first fetch for a state takes ~30-90s.
- **Caching**: Results are saved to `backend/data/reference/cache/forest_<state>.geojson`. Subsequent requests for the same state are nearly instantaneous (<1s).

### 3. Dynamic AOI (Area of Interest) Files
During verification, the system clips the state-level data to the specific project boundary (BBox).
- **Files**: `forest_aoi_<state>.geojson` are generated dynamically.
- **Purpose**: These localized subsets are used for the final spatial calculation and are sent to the frontend for visualization on the results map.
- **Latency**: Using AOI subsets significantly reduces the payload size and improves UI rendering speed.

---

## 🏆 Why ProofOfCarbon Matters

- Prevents greenwashing with objective verification
- Combines AI reasoning with cryptographic trust
- Privacy-preserving and regulation-friendly
- Scalable across global carbon markets
- Transparent and explainable by design

---

## ⚠️ Disclaimer

This project is a prototype built for demonstration and research purposes.  

---

## 🚀 Getting Started

Follow these steps to set up ProofOfCarbon on your local machine.

### 1. Clone the Repository
```bash
git clone https://github.com/ritigya03/ProofOfCarbon.git
cd ProofOfCarbon
```

### 2. Backend Setup (FastAPI)
Prerequisites: **Python 3.10+**

```bash
cd backend
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

**Configure Environment:**
Create a `.env` file in the `backend/` directory (see [.env.example](.env.example) for reference):
```env
GROQ_API_KEY=your_key_here  # or OPENAI_API_KEY
RPC_URL=https://rpc-amoy.polygon.technology
GEE_SERVICE_ACCOUNT_EMAIL=...
GEE_SERVICE_ACCOUNT_KEY='{"type": "service_account", ...}'
```

**Run Backend:**
```bash
python api/main.py
# Server will start on http://localhost:8000
```

### 3. Frontend Setup (React + Vite)
Prerequisites: **Node.js 18+**

```bash
cd ../frontend
npm install
```

**Configure Environment:**
Create a `.env` file in the `frontend/` directory:
```env
VITE_API_URL=http://localhost:8000
```

**Run Frontend:**
```bash
npm run dev
# App will be live at http://localhost:8080
```

---

## 📌 Future Work

- Real-time satellite data integration
- Live machine learning across registries
- Knowledge graph visualization for fraud patterns
- DAO-based governance for verification standards

---

## 📜 License

MIT License
