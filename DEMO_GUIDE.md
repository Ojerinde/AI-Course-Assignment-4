# AI-Powered Quality Control Dashboard

## Demo & Deployment Guide

---

## Project Structure

```
Ass 4/
├── app.py                          ← Streamlit entry point (run this)
├── .env                            ← Your API keys (GROQ + Gemini)
├── requirements.txt                ← All Python dependencies
├── DEMO_GUIDE.md                   ← This file
│
├── core/                           ← Business logic (imported by app.py)
│   ├── __init__.py
│   ├── mil_std_tables.py           ← MIL-STD-105E Table I & II-A lookup engine
│   └── vlm_extractor.py            ← VLM component extraction (Groq / Gemini / Demo)
│
├── assets/
│   ├── circuits/                   ← Circuit diagram images
│   │   └── 24V_10A_SMPS_Circuit_Diagram.jpg   ← Default circuit (used if nothing uploaded)
│   └── standards/
│       └── MIL_STD_105E legible copy.pdf      ← Reference standard document
│
└── outputs/                        ← Generated files land here
    ├── inspection_plan.json        ← Created after workflow completes
    └── trace_log.md                ← Full ReAct interaction history
```

---

## Part 1 — Deployment Steps

### Step 1 — Prerequisites

Make sure you have Python 3.10 or higher installed.

```bash
python --version
```

### Step 2 — Install Dependencies

From the `Ass 4/` folder, run:

```bash
pip install -r requirements.txt
```

This installs: `streamlit`, `pandas`, `pdfplumber`, `groq`, `google-genai`, `Pillow`, `python-dotenv`.

### Step 3 — Configure API Keys

Your `.env` file is already set up with both keys:

```
GROQ_API_KEY=
GEMINI_API_KEY=
```

> **Note:** These keys are loaded automatically by the app at startup. You never need to type them manually — just paste them into the sidebar API Key field when you choose Groq or Gemini.

### Step 4 — Launch the App

```bash
cd "c:\Users\Joel\Desktop\Beihang University\AI\Practice\Ass 4"
streamlit run app.py
```

Your browser will open automatically at **http://localhost:8501**

---

## Part 2 — Screen Recording Demo Script

Follow these steps in order. Each step has a plain-English explanation for your voiceover.

---

### Step 1 — Show the Landing Screen (30 sec)

**What to do:** Open the browser. Point to the full layout.

**Say:**

> "This is the AI-Powered Quality Control Dashboard. It implements a Multimodal Agentic Workflow for electronics manufacturing. On the left is the sidebar — it shows the circuit diagram we are analysing, along with all the inspection parameters. On the right we have four tabs: Workflow, Bill of Materials, Inspection Plan, and Trace Log."

---

### Step 2 — Show the Circuit Image Upload (20 sec)

**What to do:** Point to the "Upload your own circuit" widget at the top of the sidebar.

**Say:**

> "The app supports any circuit diagram. Right now it's using the default — a 24V 10A Switch-Mode Power Supply. But you can upload any JPG or PNG circuit and the AI will analyse it instead. The default image is stored in `assets/circuits/` and is used automatically if nothing is uploaded."

**Optional:** Upload a different circuit to show it updating live, then reset back to the default.

---

### Step 3 — Configure Inspection Parameters (20 sec)

**What to do:** Slowly adjust the Lot Size to 500, confirm Inspection Level is II, AQL is 1.0%.

**Say:**

> "These three parameters drive the MIL-STD-105E lookup. Lot Size of 500 means we manufactured 500 units. Inspection Level II is the standard general inspection level. AQL of 1% means we are willing to accept a maximum of 1% defective units."

---

### Step 4 — Select a VLM Provider (15 sec)

**What to do:** Change the dropdown from Demo to Groq or Gemini. Paste the key.

**Say:**

> "For the AI vision analysis, I can use Groq — which runs the Llama 4 Scout model — or Google Gemini 2.0 Flash. Both are free-tier services that require no payment. I'll paste my API key here. In demo mode, the app uses a pre-built realistic component list so it works offline too."

---

### Step 5 — Run Phase 1: VLM Extraction (60 sec)

**What to do:** Click **"Phase 1 – Extract Components (VLM)"**. Watch the progress bar and the ReAct log populate in real time.

**Say:**

> "Phase 1 launches the Multimodal AI. The circuit diagram image is encoded and sent to the Vision-Language Model with a specially crafted prompt. Notice the ReAct log — this is the agent's live reasoning feed."

**Point to each entry as it appears:**

> - 💭 **Thought** — "The agent is deciding its strategy. It tells us it will use 3 few-shot examples embedded in the prompt to improve accuracy by 15 to 25 percent."
> - ⚙️ **Action** — "The agent calls the extract_components tool, sending the image and specifying the provider."
> - 👁️ **Observation** — "The model has responded. It extracted 25 components and validated the JSON schema."

---

### Step 6 — Review the Bill of Materials Tab (30 sec)

**What to do:** Click the **"📋 Bill of Materials"** tab.

**Say:**

> "Here is the full Bill of Materials — every component the AI found in the circuit. Each row has the reference designator, component type, value or part number, a functional description, and a confidence score. Rows highlighted in yellow have a confidence below 0.8 — these are automatically flagged for manual review by a human engineer. This is the engineering safety guardrail."

**Point to a flagged row:**

> "For example, the heatsink here has a confidence of 0.79 — just below our threshold. The system flags it rather than silently accepting it."

---

### Step 7 — Run Phase 2: Agentic MIL-STD Lookup (60 sec)

**What to do:** Go back to **▶ Workflow** tab. Click **"Phase 2 – Agentic MIL-STD Lookup"**. Watch the ReAct log continue.

**Say:**

> "Phase 2 is the agentic reasoning loop. The agent now has the lot size and inspection level, and it needs to consult the MIL-STD-105E standard — a US military and industrial inspection specification."

**Point to each log entry:**

> - 💭 **Thought** — "The agent reasons: I have lot size 500 at Level II. I need to look up Table I on page 13."
> - ⚙️ **Action: get_sampling_code** — "It calls a tool that reads Table I. Lot range 281–500 at Level II maps to Code Letter H."
> - 👁️ **Observation** — "Code Letter H confirmed."
> - 💭 **Thought** — "Now I need Table II-A with code H and AQL 1%."
> - ⚙️ **Action: get_acceptance_criteria** — "Table II-A lookup: Code H, AQL 1% → Sample 50 units, accept if 1 or fewer defects, reject if 2 or more."
> - 💭 **Thought** — "I have everything. But I must not finalise alone — I need human approval."
> - 🖥️ **System** — "Agent suspended."

**Say:**

> "This is the ReAct pattern — Reason, then Act, then Observe — repeating until the task is complete. The agent used two real tool calls that read actual standard tables."

---

### Step 8 — Human Approval Guardrail (20 sec)

**What to do:** Point to the approval section. Read the summary table. Click ✅ **Approve**.

**Say:**

> "Before the report is written, the system requires a human to approve. This is the Human-in-the-Loop design — the AI cannot finalise autonomously. A quality manager reviews the sampling plan: we will inspect 50 units from this lot, and accept if we find 1 or fewer defects. I'll click Approve."

---

### Step 9 — Download the Inspection Plan (20 sec)

**What to do:** Click the **"📑 Inspection Plan"** tab. Point to the four metric cards, the JSON, and the download button.

**Say:**

> "The finalised inspection plan is now ready. Code Letter H, Sample Size 50, Accept ≤ 1 defect, Reject ≥ 2 defects. The full JSON can be downloaded — this becomes the formal inspection order that goes to the factory floor. It includes the complete BOM, the MIL-STD parameters, and the timestamp."

---

### Step 10 — Show the Trace Log (15 sec)

**What to do:** Click the **"📜 Trace Log"** tab. Scroll through it.

**Say:**

> "Finally, the Trace Log captures the complete interaction history — every Thought, Action and Observation with timestamps. This is the traceability record required by quality management systems like ISO 9001. It's automatically saved to the `outputs/` folder and can be downloaded as a Markdown file for the project report."

---

## Part 3 — Key Technical Points to Mention

| Concept              | What it demonstrates                                                                   |
| :------------------- | :------------------------------------------------------------------------------------- |
| Multimodal AI        | The VLM reads a raw image — no manual component entry                                  |
| Few-Shot Prompting   | 3 examples in the system prompt improve JSON accuracy ~15-25%                          |
| ReAct Pattern        | Agent reasons → acts → observes in a loop, like a human expert                         |
| Tool Use             | Two real functions called by the agent: `get_sampling_code`, `get_acceptance_criteria` |
| MIL-STD-105E         | Industry standard for statistical sampling in manufacturing                            |
| Confidence Threshold | Components below 0.8 confidence are escalated to humans, not auto-accepted             |
| Human-in-the-Loop    | Agent cannot finalise a plan without explicit human sign-off                           |
| Traceability         | Full audit trail generated automatically for compliance                                |

---

## Troubleshooting

| Error                               | Fix                                                                                |
| :---------------------------------- | :--------------------------------------------------------------------------------- |
| `ModuleNotFoundError: groq`         | Run `pip install groq`                                                             |
| `ModuleNotFoundError: google.genai` | Run `pip install google-genai`                                                     |
| `404 model not found` (Gemini)      | Make sure you are using `gemini-2.0-flash`, not `gemini-1.5-flash`                 |
| `Expecting value` (JSON parse)      | Model response was cut short — the `max_tokens` fix is already applied             |
| Image not found                     | Make sure your image is in `assets/circuits/` or use the upload widget             |
| App won't start                     | Make sure you are in the `Ass 4/` folder: `cd "Ass 4"` then `streamlit run app.py` |
