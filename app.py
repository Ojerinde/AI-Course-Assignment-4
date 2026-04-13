"""
app.py  ─  AI-Powered Quality Control Dashboard
================================================
Multimodal Agentic Workflow for Electronics Manufacturing QC.

Workflow Phases
───────────────
  Phase 1 : Multimodal Extraction  – VLM identifies PCB components (BOM)
  Phase 2 : Agentic Tool Use       – ReAct loop queries MIL-STD-105E tables
  Phase 3 : Validation & Approval  – Human-in-the-loop safety guardrail

Run:
  streamlit run app.py
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv  # reads .env automatically at startup

# ─────────────────────────────────────────────────────────────────────────────
# Path Bootstrap – ensure core/ is importable regardless of CWD
# ─────────────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# local dev: reads GROQ_API_KEY / GEMINI_API_KEY
load_dotenv(BASE_DIR / ".env")

from core.mil_std_tables import get_acceptance_criteria, get_sampling_code, list_aql_options  # noqa: E402
from core.vlm_extractor import extract_components  # noqa: E402


def _get_secret(key: str) -> str:
    """Read a secret from st.secrets (Streamlit Cloud) or os.environ (.env)."""
    import os
    try:
        return st.secrets.get(key, "")  # type: ignore[attr-defined]
    except Exception:
        return os.environ.get(key, "")


# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────
CIRCUITS_DIR = BASE_DIR / "assets" / "circuits"
OUTPUTS_DIR = BASE_DIR / "outputs"
DEFAULT_IMAGE_PATH = CIRCUITS_DIR / "24V_10A_SMPS_Circuit_Diagram.jpg"
CONFIDENCE_THRESHOLD = 0.80

OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

# ─────────────────────────────────────────────────────────────────────────────
# Page Config
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI-Powered QC Dashboard",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# Session State
# ─────────────────────────────────────────────────────────────────────────────


def _init_state():
    defaults = {
        "react_log":        [],
        "bom":              None,
        "sampling_result":  None,
        "criteria_result":  None,
        "human_approved":   False,
        "plan_finalised":   False,
        "inspection_plan":  None,
        "trace_log_lines":  [],
        "phase":            0,
        "extraction_done":  False,
        "reasoning_done":   False,
        "active_image_path": str(DEFAULT_IMAGE_PATH),
        "active_image_name": DEFAULT_IMAGE_PATH.name,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


_init_state()

# ─────────────────────────────────────────────────────────────────────────────
# Utility Functions
# ─────────────────────────────────────────────────────────────────────────────


def log_react(role: str, text: str):
    ts = datetime.now().strftime("%H:%M:%S")
    st.session_state.react_log.append({"ts": ts, "role": role, "text": text})
    labels = {
        "thought":     "💭 Thought",
        "action":      "⚙️  Action",
        "observation": "👁️  Observation",
        "system":      "🖥️  System",
    }
    prefix = labels.get(role, role)
    st.session_state.trace_log_lines.append(f"[{ts}] {prefix}: {text}")


def reset_workflow():
    keys = [
        "react_log", "bom", "sampling_result", "criteria_result",
        "human_approved", "plan_finalised", "inspection_plan",
        "trace_log_lines", "phase", "extraction_done", "reasoning_done",
    ]
    # Preserve image selection across reset
    saved_path = st.session_state.get("active_image_path")
    saved_name = st.session_state.get("active_image_name")
    for k in keys:
        if k in st.session_state:
            del st.session_state[k]
    _init_state()
    if saved_path:
        st.session_state.active_image_path = saved_path
        st.session_state.active_image_name = saved_name


def build_trace_md() -> str:
    lines = [
        "# AI-Powered QC Dashboard – Full Interaction Trace Log",
        f"\nGenerated: {datetime.now().isoformat()}\n",
        f"Standard: MIL-STD-105E  |  Circuit: {st.session_state.active_image_name}",
        "\n---\n",
    ]
    for line in st.session_state.trace_log_lines:
        lines.append(line)
        lines.append("")
    return "\n".join(lines)


def write_trace_log():
    path = OUTPUTS_DIR / "trace_log.md"
    path.write_text(build_trace_md(), encoding="utf-8")
    return path


def build_inspection_plan(lot_size, inspection_level, aql) -> dict:
    bom = st.session_state.bom or []
    flagged = [c for c in bom if c.get(
        "confidence", 1.0) < CONFIDENCE_THRESHOLD]
    return {
        "meta": {
            "generated_at":   datetime.now().isoformat(),
            "standard":       "MIL-STD-105E",
            "circuit_image":  st.session_state.active_image_name,
            "human_approved": True,
        },
        "lot_parameters": {
            "lot_size":         lot_size,
            "inspection_level": inspection_level,
            "aql_percent":      aql,
        },
        "sampling_code":       st.session_state.sampling_result,
        "acceptance_criteria": st.session_state.criteria_result,
        "bom_summary": {
            "total_components":          len(bom),
            "flagged_for_manual_review": len(flagged),
            "flagged_refs":              [c["ref"] for c in flagged],
        },
        "bill_of_materials": bom,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🔬 QC Dashboard")
    st.divider()

    # ── Circuit Image Section ──────────────────────────────────────────────────
    st.subheader("🖼️ Circuit Diagram")

    uploaded = st.file_uploader(
        "Upload your own circuit (JPG / PNG)",
        type=["jpg", "jpeg", "png"],
        help="Upload any circuit diagram to analyse. Leave blank to use the default 24V 10A SMPS.",
    )

    if uploaded is not None:
        # Save to assets/circuits/ so the path is stable on disk
        save_path = CIRCUITS_DIR / uploaded.name
        save_path.write_bytes(uploaded.getvalue())
        if st.session_state.active_image_path != str(save_path):
            st.session_state.active_image_path = str(save_path)
            st.session_state.active_image_name = uploaded.name
            reset_workflow()   # new image = fresh analysis
        st.success(f"Using uploaded: **{uploaded.name}**")
    else:
        if st.session_state.active_image_path != str(DEFAULT_IMAGE_PATH):
            st.session_state.active_image_path = str(DEFAULT_IMAGE_PATH)
            st.session_state.active_image_name = DEFAULT_IMAGE_PATH.name

    active_path = Path(st.session_state.active_image_path)
    if active_path.exists():
        st.image(
            str(active_path),
            caption=st.session_state.active_image_name,
            use_container_width=True,
        )
    else:
        st.warning(f"Image not found: {active_path.name}")

    st.divider()

    # ── Inspection Parameters ─────────────────────────────────────────────────
    st.subheader("⚙️ Inspection Parameters")

    lot_size = st.number_input(
        "Manufacturing Lot Size",
        min_value=2, max_value=500000, value=500, step=50,
        help="Number of units in the production lot",
    )
    inspection_level = st.selectbox(
        "Inspection Level",
        options=["I", "II", "III", "S1", "S2", "S3", "S4"],
        index=1,
        help="MIL-STD-105E inspection level (General: I/II/III, Special: S1-S4)",
    )
    aql = st.selectbox(
        "Acceptable Quality Level (AQL %)",
        options=["0.065", "0.10", "0.15", "0.25", "0.40",
                 "0.65", "1.0", "1.5", "2.5", "4.0", "6.5", "10"],
        index=6,
        help="Maximum tolerable defect rate (%)",
    )

    st.divider()

    # ── API Configuration ─────────────────────────────────────────────────────
    st.subheader("🔑 AI Configuration")
    provider = st.selectbox(
        "VLM Provider",
        options=["demo", "groq", "gemini"],
        format_func=lambda x: {
            "demo":   "🖥️  Demo (offline, no key needed)",
            "groq":   "⚡ Groq – Llama 4 Scout (free)",
            "gemini": "✨ Gemini (Google free tier)",
        }[x],
        help="Select the Vision-Language Model provider.",
    )

    # Gemini model selector – shown only when Gemini is chosen
    gemini_model = "auto"
    if provider == "gemini":
        gemini_model = st.selectbox(
            "Gemini Model",
            options=[
                "auto",
                "gemini-2.0-flash-lite",
                "gemini-2.0-flash",
                "gemini-1.5-flash",
                "gemini-1.5-pro",
            ],
            format_func=lambda x: {
                "auto":                "🔄 Auto (tries all free models)",
                "gemini-2.0-flash-lite": "2.0 Flash Lite  — best free tier",
                "gemini-2.0-flash":    "2.0 Flash",
                "gemini-1.5-flash":    "1.5 Flash",
                "gemini-1.5-pro":      "1.5 Pro",
            }[x],
            help="Pick a specific model, or leave on Auto to try all free models in order.",
        )

    # Pre-fill from .env / st.secrets so user doesn't have to paste key each time
    _env_key = {
        "demo":   "",
        "groq":   _get_secret("GROQ_API_KEY"),
        "gemini": _get_secret("GEMINI_API_KEY"),
    }[provider]

    api_key_input = st.text_input(
        "API Key" if provider != "demo" else "API Key (not needed for demo)",
        value=_env_key,
        type="password",
        placeholder={
            "demo":   "No key needed — running offline",
            "groq":   "gsk_...",
            "gemini": "AIza...",
        }[provider],
        disabled=(provider == "demo"),
        help={
            "demo":   "Demo mode — uses a realistic offline component list.",
            "groq":   "Free key at console.groq.com",
            "gemini": "Free key at aistudio.google.com",
        }[provider],
    )

    st.divider()
    if st.button("🔄 Reset Workflow", use_container_width=True):
        reset_workflow()
        st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# Main Panel
# ─────────────────────────────────────────────────────────────────────────────
st.title("🤖 AI-Powered Quality Control Dashboard")
st.caption(
    "Multimodal Agentic Workflow for Electronics Manufacturing  •  MIL-STD-105E Compliant")

tab_workflow, tab_bom, tab_plan, tab_trace = st.tabs(
    ["▶ Workflow", "📋 Bill of Materials", "📑 Inspection Plan", "📜 Trace Log"]
)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 – WORKFLOW
# ═══════════════════════════════════════════════════════════════════════════════
with tab_workflow:

    col_run, col_status = st.columns([2, 3])

    with col_run:
        st.subheader("Control Panel")
        run_phase1 = st.button(
            "🔍 Phase 1 – Extract Components (VLM)",
            disabled=(st.session_state.phase != 0),
            use_container_width=True,
        )
        run_phase2 = st.button(
            "🧠 Phase 2 – Agentic MIL-STD Lookup",
            disabled=(
                not st.session_state.extraction_done or st.session_state.reasoning_done),
            use_container_width=True,
        )
        st.info(
            f"**Lot:** {lot_size:,}  |  **Level:** {inspection_level}  |  **AQL:** {aql}%",
            icon="⚙️",
        )

    with col_status:
        phase_names = {
            0: "Idle",
            1: "Phase 1 – VLM Extraction",
            2: "Phase 2 – Agentic Reasoning",
            3: "Awaiting Human Approval",
            4: "✅ Complete",
        }
        st.metric("Workflow Phase", phase_names.get(
            st.session_state.phase, "—"))
        if st.session_state.bom:
            n = len(st.session_state.bom)
            nf = sum(1 for c in st.session_state.bom if c.get(
                "confidence", 1) < CONFIDENCE_THRESHOLD)
            st.metric("Components Identified", n)
            if nf:
                st.warning(
                    f"⚠️ {nf} component(s) below confidence {CONFIDENCE_THRESHOLD} — "
                    "flagged for manual review."
                )

    st.divider()

    # ── Live ReAct Log ─────────────────────────────────────────────────────────
    st.subheader("🔁 Live ReAct Agent Log")
    with st.container(border=True):
        if not st.session_state.react_log:
            st.caption(
                "Agent log will appear here once you start the workflow…")
        else:
            for entry in st.session_state.react_log:
                role, text, ts = entry["role"], entry["text"], entry["ts"]
                if role == "thought":
                    st.markdown(f"💭 **Thought** `{ts}`\n\n> {text}")
                elif role == "action":
                    st.markdown(f"⚙️ **Action** `{ts}`")
                    st.code(text)
                elif role == "observation":
                    st.markdown(f"👁️ **Observation** `{ts}`\n\n{text}")
                elif role == "system":
                    st.info(f"🖥️  {text}")
                st.divider()

    # ── Human Approval Guardrail ───────────────────────────────────────────────
    if st.session_state.phase == 3 and not st.session_state.human_approved:
        st.divider()
        st.subheader("🛡️ Human Approval Required")
        st.warning(
            "The agent has completed its reasoning and is **waiting for human authorisation** "
            "before finalising the inspection plan. Review the **Bill of Materials** tab and "
            "the sampling summary below, then approve or reject."
        )

        if st.session_state.sampling_result and st.session_state.criteria_result:
            sr = st.session_state.sampling_result
            cr = st.session_state.criteria_result
            with st.expander("📊 Pre-Approval Sampling Summary", expanded=True):
                st.markdown(f"""
| Parameter        | Value |
|:-----------------|:------|
| Lot Size         | {sr.get("lot_size", lot_size):,} |
| Lot Range        | {sr.get("lot_range", "—")} |
| Inspection Level | {sr.get("inspection_level", inspection_level)} |
| Code Letter      | **{sr.get("code_letter", "—")}** |
| Sample Size      | **{cr.get("sample_size", "—")} units** |
| AQL              | {cr.get("aql", aql)}% |
| Accept if ≤      | {cr.get("acceptance_number", "—")} defects |
| Reject if ≥      | {cr.get("rejection_number", "—")} defects |
                """)

        col_a, col_r = st.columns(2)
        with col_a:
            if st.button("✅ Approve Inspection Plan", type="primary", use_container_width=True):
                st.session_state.human_approved = True
                log_react(
                    "system", "Human operator APPROVED the inspection plan.")
                st.rerun()
        with col_r:
            if st.button("❌ Reject — Restart Workflow", use_container_width=True):
                log_react(
                    "system", "Human operator REJECTED the plan. Workflow reset.")
                reset_workflow()
                st.rerun()

    # ── Finalise ──────────────────────────────────────────────────────────────
    if st.session_state.human_approved and not st.session_state.plan_finalised:
        plan = build_inspection_plan(lot_size, inspection_level, aql)
        st.session_state.inspection_plan = plan
        st.session_state.plan_finalised = True
        st.session_state.phase = 4
        log_react("system", "Inspection plan finalised and ready for download.")
        write_trace_log()
        st.rerun()

    if st.session_state.plan_finalised:
        st.success(
            "✅ Plan finalised! Switch to the **Inspection Plan** tab to download.")


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 1 EXECUTION
# ═══════════════════════════════════════════════════════════════════════════════
if run_phase1 and st.session_state.phase == 0:
    st.session_state.phase = 1
    _img_name = st.session_state.active_image_name
    log_react("system",
              f"Workflow started — Circuit: {_img_name}, "
              f"Lot size={lot_size:,}, Level={inspection_level}, AQL={aql}%")

    _provider_labels = {
        "demo":   "offline demo",
        "groq":   "Groq Llama 4 Scout",
        "gemini": "Gemini 2.0 Flash",
    }
    log_react("thought",
              f"I need to identify all components in the circuit diagram '{_img_name}'. "
              f"I will use a Vision-Language Model ({_provider_labels[provider]}) with "
              "3 embedded few-shot examples to ensure the output conforms to the required "
              "JSON schema. Research shows few-shot prompting improves accuracy by ~15-25%.")
    log_react("action",
              f"extract_components(\n"
              f"  image='{_img_name}',\n"
              f"  provider='{provider}',\n"
              + (f"  gemini_model='{gemini_model}',\n" if provider == "gemini" else "")
              + f"  few_shot_examples=3\n)")

    _active_key = (api_key_input or "").strip()
    progress = st.progress(0, text="Initialising VLM…")
    status_ph = st.empty()
    components = None
    step = 0

    for update in extract_components(
        st.session_state.active_image_path,
        api_key=_active_key or None,
        provider=provider,
        gemini_model=gemini_model,
    ):
        step += 1
        msg = update.get("message", "")
        if msg:
            progress.progress(min(step * 14, 90), text=msg)
            status_ph.info(f"🔄 {msg}")

        if update["status"] == "done":
            components = update["components"]
            log_react("observation",
                      f"VLM extracted **{len(components)} components**. "
                      "Few-shot schema applied — structured JSON validated. "
                      "Confidence scores assigned to each component.")
        elif update["status"] == "error":
            log_react("observation",
                      f"Extraction error: {update.get('message', '')}")
            st.error(update.get("message", "Unknown error"))
            st.session_state.phase = 0

    if components:
        st.session_state.bom = components
        st.session_state.extraction_done = True
        nf = sum(1 for c in components if c.get(
            "confidence", 1) < CONFIDENCE_THRESHOLD)
        log_react("thought",
                  f"Phase 1 complete. {len(components)} components extracted; "
                  f"{nf} below confidence threshold {CONFIDENCE_THRESHOLD} — flagged for manual review. "
                  "Ready to proceed to Phase 2: MIL-STD-105E table lookups.")

    progress.progress(100, text="Phase 1 complete.")
    status_ph.success(
        f"✅ Phase 1 complete — {len(components or [])} components extracted.")
    time.sleep(0.8)
    st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 2 EXECUTION – ReAct tool-use loop
# ═══════════════════════════════════════════════════════════════════════════════
if run_phase2 and st.session_state.extraction_done and not st.session_state.reasoning_done:
    st.session_state.phase = 2

    log_react("thought",
              f"I have lot size={lot_size:,} and inspection level='{inspection_level}'. "
              "Step 1: consult MIL-STD-105E **Table I** (p.13) to obtain the sample-size "
              "code letter that maps to this production lot.")
    time.sleep(0.3)

    log_react("action",
              f"get_sampling_code(\n  lot_size={lot_size},\n  level='{inspection_level}'\n)")
    time.sleep(0.4)

    sr = get_sampling_code(lot_size, inspection_level)
    st.session_state.sampling_result = sr

    if "error" in sr:
        log_react("observation", f"Tool error: {sr['error']}")
        st.error(sr["error"])
        st.session_state.phase = 1
        st.rerun()

    log_react("observation",
              f"**Table I result** — Lot range {sr['lot_range']} "
              f"at Level {sr['inspection_level']} "
              f"→ Code Letter: **{sr['code_letter']}**\n\n"
              f"*{sr['table_ref']}*")

    code = sr["code_letter"]
    log_react("thought",
              f"Code letter '{code}' obtained from Table I. "
              f"Step 2: query **Table II-A** (p.14) with code='{code}' and AQL={aql}% "
              "to determine the sample size and acceptance/rejection numbers.")
    time.sleep(0.3)

    log_react("action",
              f"get_acceptance_criteria(\n  code_letter='{code}',\n  aql='{aql}'\n)")
    time.sleep(0.4)

    cr = get_acceptance_criteria(code, aql)

    if "error" in cr:
        available = list_aql_options(code)
        log_react("observation",
                  f"AQL '{aql}%' is not tabulated for code '{code}'. "
                  f"Available AQLs: {available}. Selecting closest available AQL automatically.")
        if available:
            fallback = available[-1]
            log_react("thought",
                      f"Retrying Table II-A with fallback AQL='{fallback}%'.")
            log_react("action",
                      f"get_acceptance_criteria(\n  code_letter='{code}',\n  aql='{fallback}'\n)")
            cr = get_acceptance_criteria(code, fallback)

    st.session_state.criteria_result = cr

    if "error" in cr:
        log_react("observation", f"Tool error: {cr['error']}")
        st.error(cr["error"])
        st.session_state.phase = 1
        st.rerun()

    log_react("observation",
              f"**Table II-A result** — Code **{cr['code_letter']}**, AQL **{cr['aql']}%**\n\n"
              f"- Sample Size: **{cr['sample_size']} units**\n"
              f"- Acceptance Number (Ac): **{cr['acceptance_number']}**\n"
              f"- Rejection Number (Re): **{cr['rejection_number']}**\n\n"
              f"**Verdict Rule:** {cr['verdict_rule']}\n\n"
              f"*{cr['table_ref']}*")

    log_react("thought",
              "I now have all required data: full BOM from Phase 1 and a complete "
              "MIL-STD-105E sampling plan. Per safety protocol, I must NOT finalise "
              "the inspection plan autonomously. Pausing for Human Approval.")
    time.sleep(0.2)
    log_react(
        "system", "Agent suspended — awaiting Human Approval before writing the final plan.")

    st.session_state.reasoning_done = True
    st.session_state.phase = 3
    st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 – BILL OF MATERIALS
# ═══════════════════════════════════════════════════════════════════════════════
with tab_bom:
    st.subheader("📋 Extracted Bill of Materials (BOM)")

    if not st.session_state.bom:
        st.info(
            "Run **Phase 1** in the Workflow tab to extract components from the circuit diagram.")
    else:
        import pandas as pd  # noqa: PLC0415

        df = pd.DataFrame(st.session_state.bom)
        df["confidence"] = df["confidence"].apply(lambda x: round(float(x), 2))
        df["status"] = df["confidence"].apply(
            lambda x: "⚠️ Manual Review" if x < CONFIDENCE_THRESHOLD else "✅ OK"
        )
        df = df.rename(columns={
            "ref":         "Reference",
            "type":        "Component Type",
            "value":       "Value / Part No.",
            "description": "Functional Description",
            "confidence":  "Confidence",
            "status":      "Status",
        })

        def _highlight_row(row):
            colour = "#fff3cd" if row["Confidence"] < CONFIDENCE_THRESHOLD else ""
            return [f"background-color: {colour}" if colour else ""] * len(row)

        styled = df.style.apply(_highlight_row, axis=1).format(
            {"Confidence": "{:.2f}"})
        st.dataframe(styled, use_container_width=True, hide_index=True)

        flagged = df[df["Status"] == "⚠️ Manual Review"]
        if not flagged.empty:
            st.warning(
                f"**{len(flagged)} component(s) flagged** for manual review "
                f"(confidence < {CONFIDENCE_THRESHOLD}): "
                + ", ".join(flagged["Reference"].tolist())
            )
        st.caption(
            f"Total: {len(df)}  •  Flagged: {len(flagged)}  •  "
            f"Confidence threshold: {CONFIDENCE_THRESHOLD}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 – INSPECTION PLAN
# ═══════════════════════════════════════════════════════════════════════════════
with tab_plan:
    st.subheader("📑 Finalised Inspection Plan")

    if not st.session_state.plan_finalised:
        if st.session_state.phase == 3:
            st.warning(
                "⏳ Awaiting Human Approval. Return to the **Workflow** tab to approve.")
        elif st.session_state.phase in (1, 2):
            st.info("Workflow in progress — please wait…")
        else:
            st.info("Complete all workflow phases to generate the inspection plan.")
    else:
        plan = st.session_state.inspection_plan
        sr = plan["sampling_code"]
        cr = plan["acceptance_criteria"]

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Code Letter",  sr.get("code_letter", "—"))
        c2.metric("Sample Size",  f"{cr.get('sample_size', '—')} units")
        c3.metric("Accept if ≤",
                  f"{cr.get('acceptance_number', '—')} defects")
        c4.metric("Reject if ≥",  f"{cr.get('rejection_number', '—')} defects")

        st.divider()
        plan_json = json.dumps(plan, indent=2)
        st.code(plan_json, language="json")

        col_dl1, col_dl2 = st.columns(2)
        with col_dl1:
            st.download_button(
                "⬇️ Download inspection_plan.json",
                data=plan_json,
                file_name="inspection_plan.json",
                mime="application/json",
                use_container_width=True,
            )
        with col_dl2:
            trace_path = OUTPUTS_DIR / "trace_log.md"
            if trace_path.exists():
                st.download_button(
                    "⬇️ Download trace_log.md",
                    data=trace_path.read_text(encoding="utf-8"),
                    file_name="trace_log.md",
                    mime="text/markdown",
                    use_container_width=True,
                )


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4 – TRACE LOG
# ═══════════════════════════════════════════════════════════════════════════════
with tab_trace:
    st.subheader("📜 Full Interaction Trace Log")

    if not st.session_state.trace_log_lines:
        st.info("The trace log will be populated as the workflow executes.")
    else:
        trace_md = build_trace_md()
        st.code(trace_md, language="markdown")
        st.download_button(
            "⬇️ Download trace_log.md",
            data=trace_md,
            file_name="trace_log.md",
            mime="text/markdown",
        )
