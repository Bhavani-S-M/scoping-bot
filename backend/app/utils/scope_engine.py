# app/utils/scope_engine.py
import json, re, logging, difflib, os, tempfile,anyio,pytesseract, openpyxl,tiktoken, pytz, graphviz

from calendar import monthrange
from pdfminer.high_level import extract_text as extract_pdf_text
from docx import Document
from pptx import Presentation
from io import BytesIO
from PIL import Image
from azure.search.documents.models import VectorizedQuery
from typing import Dict, Any, List
from datetime import datetime, timedelta
from app.utils import azure_blob
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app import models
from app.utils.ai_clients import (
    get_azure_openai_client,
    get_azure_openai_deployment,
    get_azure_openai_embedding_deployment,
    get_search_client,
)

logger = logging.getLogger(__name__)

# Init Azure services
client = get_azure_openai_client()
deployment = get_azure_openai_deployment()
emb_model = get_azure_openai_embedding_deployment()
search_client = get_search_client()

PROJECTS_BASE = "projects"


# Default Role Rates (USD/month)
ROLE_RATE_MAP: Dict[str, float] = {
    "Backend Developer": 3000.0,
    "Frontend Developer": 2800.0,
    "QA Analyst": 1800.0,
    "QA Engineer": 2000.0,
    "Data Engineer": 2800.0,
    "Data Analyst": 2200.0,
    "Data Architect": 3500.0,
    "UX Designer": 2500.0,
    "UI/UX Designer": 2600.0,
    "Project Manager": 3500.0,
    "Cloud Engineer": 3000.0,
    "BI Developer": 2700.0,
    "DevOps Engineer": 3200.0,
    "Security Administrator": 3000.0,
    "System Administrator": 2800.0,
    "Solution Architect": 4000.0,
}

#  helpers
def _strip_code_fences(s: str) -> str:
    m = re.search(r"```(?:json)?(.*?)```", s, flags=re.DOTALL | re.IGNORECASE)
    return m.group(1) if m else s

def _extract_json(s: str) -> dict:
    raw = _strip_code_fences(s or "")
    try:
        return json.loads(raw.strip())
    except Exception:
        start, end = raw.find("{"), raw.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(raw[start:end+1])
            except Exception:
                return {}
        return {}


async def _extract_text_from_files(files: List[dict]) -> str:
    results: List[str] = []

    async def _extract_single(f: dict) -> None:
        try:
            blob_bytes = await azure_blob.download_bytes(f["file_path"])
            suffix = os.path.splitext(f["file_name"])[-1].lower()

            def process_file() -> str:
                content = ""
                try:
                    if suffix == ".pdf":
                        # pdfminer needs a temp file
                        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                            tmp.write(blob_bytes)
                            tmp_path = tmp.name
                        try:
                            content = extract_pdf_text(tmp_path)
                        finally:
                            os.remove(tmp_path)

                    elif suffix == ".docx":
                        doc = Document(BytesIO(blob_bytes))
                        content = "\n".join(p.text for p in doc.paragraphs)

                    elif suffix == ".pptx":
                        prs = Presentation(BytesIO(blob_bytes))
                        texts = []
                        for slide in prs.slides:
                            for shape in slide.shapes:
                                if hasattr(shape, "text"):
                                    texts.append(shape.text)
                        content = "\n".join(texts)

                    elif suffix in [".xlsx", ".xlsm"]:
                        wb = openpyxl.load_workbook(BytesIO(blob_bytes))
                        sheet = wb.active
                        content = "\n".join(
                            " ".join(str(cell) if cell else "" for cell in row)
                            for row in sheet.iter_rows(values_only=True)
                        )

                    elif suffix in [".png", ".jpg", ".jpeg", ".tiff"]:
                        img = Image.open(BytesIO(blob_bytes))
                        content = pytesseract.image_to_string(img)

                    else:
                        # fallback plain text (requires temp file because openpyxl/docx won't apply)
                        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                            tmp.write(blob_bytes)
                            tmp_path = tmp.name
                        try:
                            with open(tmp_path, "r", encoding="utf-8", errors="ignore") as fh:
                                content = fh.read()
                        finally:
                            os.remove(tmp_path)

                except Exception as e:
                    logger.warning(f"Extraction failed for {f['file_name']}: {e}")

                return content.strip()

            text = await anyio.to_thread.run_sync(process_file)

            if text:
                results.append(text)
            else:
                logger.warning(f"Extracted no text from {f['file_name']}")

        except Exception as e:
            logger.warning(f"Failed to extract {f.get('file_name')} (path={f.get('file_path')}): {e}")

    # Run parallel with TaskGroup
    async with anyio.create_task_group() as tg:
        for f in files:
            tg.start_soon(_extract_single, f)

    return "\n\n".join(results)


def _normalize_role_name(name: str) -> str:
    if not name:
        return "TBD"
    low = name.strip().lower()
    for key in ROLE_RATE_MAP.keys():
        if key.lower() in low or low in key.lower():
            return key
    matches = difflib.get_close_matches(name, ROLE_RATE_MAP.keys(), n=1, cutoff=0.6)
    return matches[0] if matches else "TBD"




def _rag_retrieve(query: str, k: int = 3, expand_neighbors: bool = True) -> List[Dict]:
    """
    Retrieve semantically similar chunks for RAG.
    Trims results so total tokens <= model context limit (with buffer).
    """
    global emb_model

    if not search_client or not client:
        return []

    try:
        # Embedding for query
        q_emb = client.embeddings.create(model=emb_model, input=query).data[0].embedding

        # Vector query
        vector_query = VectorizedQuery(
            vector=q_emb,
            fields="text_vector",
        )

        results = search_client.search(
            search_text=query,
            vector_queries=[vector_query],
            select=["chunk_id", "parent_id", "chunk", "title"],
            top=k
        )

        hits = []
        for doc in results:
            hits.append({
                "id": doc["chunk_id"],
                "parent_id": doc.get("parent_id"),
                "content": doc["chunk"],
                "title": doc.get("title")
            })

        # Expand neighbors
        if expand_neighbors and hits:
            expanded = []
            for h in hits:
                expanded.append(h)
                if "_" in h["id"]:
                    try:
                        base, idx = h["id"].rsplit("_", 1)
                        idx = int(idx)
                        for nid in [f"{base}_{idx-1}", f"{base}_{idx+1}"]:
                            try:
                                neighbor = search_client.get_document(nid)
                                if neighbor:
                                    expanded.append({
                                        "id": neighbor["chunk_id"],
                                        "parent_id": neighbor.get("parent_id"),
                                        "content": neighbor["chunk"],
                                        "title": neighbor.get("title")
                                    })
                            except Exception:
                                pass
                    except Exception:
                        pass
            hits = expanded

        # Group by parent_id
        grouped = {}
        for h in hits:
            grouped.setdefault(h["parent_id"], []).append(h)

        # ---- Token budget check ----
        model_name = deployment   # ✅ fixed
        tokenizer = tiktoken.encoding_for_model(model_name)
        context_limit = 128000
        max_tokens = context_limit - 4000 
        used_tokens = 0

        ordered = []
        for pid, docs in grouped.items():
            safe_chunks = []
            for d in docs:
                tokens = len(tokenizer.encode(d["content"]))
                if used_tokens + tokens > max_tokens:
                    break
                safe_chunks.append(d)
                used_tokens += tokens

            if safe_chunks:
                ordered.append({
                    "parent_id": pid,
                    "chunks": safe_chunks,
                    "title": safe_chunks[0].get("title")
                })

        logger.info(f"RAG retrieve kept {used_tokens} tokens (limit {max_tokens})")

        return ordered

    except Exception as e:
        logger.warning(f"RAG retrieve failed: {e}")
        return []


# ---------- Prompt ----------
def _build_scope_prompt(rfp_text: str, kb_chunks: List[str], project=None, model_name: str = "gpt-4o") -> str:
    import datetime, tiktoken

    # Tokenizer
    tokenizer = tiktoken.encoding_for_model(model_name)

    # Safe token budget (GPT-4o = 128k, keep ~4k for completion & system messages)
    context_limit = 128000
    max_total_tokens = context_limit - 4000
    used_tokens = 0

    # Trim RFP text
    rfp_tokens = tokenizer.encode(rfp_text or "")
    if len(rfp_tokens) > 3000:   # still enforce cap on huge RFPs
        rfp_tokens = rfp_tokens[:3000]
    rfp_text = tokenizer.decode(rfp_tokens)
    used_tokens += len(rfp_tokens)

    # Trim KB context
    safe_kb_chunks = []
    for ch in kb_chunks or []:
        tokens = tokenizer.encode(ch)
        if used_tokens + len(tokens) > max_total_tokens:
            break
        safe_kb_chunks.append(ch)
        used_tokens += len(tokens)

    kb_context = "\n\n".join(safe_kb_chunks) if safe_kb_chunks else "(no KB context found)"

    # ---------- Project user fields ----------
    name = (getattr(project, "name", "") or "").strip()
    domain = (getattr(project, "domain", "") or "").strip()
    complexity = (getattr(project, "complexity", "") or "").strip()
    tech_stack = (getattr(project, "tech_stack", "") or "").strip()
    use_cases = (getattr(project, "use_cases", "") or "").strip()
    compliance = (getattr(project, "compliance", "") or "").strip()
    duration = str(getattr(project, "duration", "") or "").strip()

    user_context = (
        "Some overview fields have been provided by the user.\n"
        "Treat these user-provided values as the source of truth.\n"
        "Only fill in fields that are blank — do NOT overwrite the given values.\n\n"
        f"Project Name: {name or '(infer if missing)'}\n"
        f"Domain: {domain or '(infer if missing)'}\n"
        f"Complexity: {complexity or '(infer if missing)'}\n"
        f"Tech Stack: {tech_stack or '(infer if missing)'}\n"
        f"Use Cases: {use_cases or '(infer if missing)'}\n"
        f"Compliance: {compliance or '(infer if missing)'}\n"
        f"Duration (months): {duration or '(infer if missing)'}\n\n"
    )

    today_str = datetime.date.today().isoformat()  # yyyy-mm-dd

    # ---------- Final Prompt ----------
    return (
        "You are an expert AI project planner.\n"
        "Use the RFP/project text as the **primary source**, but enrich missing fields "
        "with the Knowledge Base context (if relevant).\n"
        "Return ONLY valid JSON (no prose, no markdown, no commentary).\n\n"
        "Output schema:\n"
        "{\n"
        '  "overview": {\n'
        '    "Project Name": string,\n'
        '    "Domain": string,\n'
        '    "Complexity": string,\n'
        '    "Tech Stack": string,\n'
        '    "Use Cases": string,\n'
        '    "Compliance": string,\n'
        '    "Duration": number\n'
        "  },\n"
        '  "activities": [\n'
        '    {\n'
        '      "ID": int,\n'
        '      "Activities": string,\n'
        '      "Description": string | null,\n'
        '      "Owner": string | null,\n'
        '      "Resources": string | null,\n'
        '      "Start Date": "yyyy-mm-dd",\n'
        '      "End Date": "yyyy-mm-dd",\n'
        '      "Effort Months": int\n'
        "    }\n"
        "  ],\n"
        '  "resourcing_plan": []\n'
        "}\n\n"
        f"-Rules:\n"
        f"- The first activity must always start today ({today_str}).\n"
        "- **Allow maximum parallel execution**: activities with no dependency must overlap instead of running sequentially."
        "- Use dependencies only when necessary (e.g., testing depends on development)."
        "- Project duration must always be **under 12 months**.\n"
        "- Auto-calculate **End Date = Start Date + Effort Months**.\n"
        "- Auto-calculate **overview.Duration** as the total span in months from the earliest Start Date to the latest End Date.\n"
        "- `Complexity` should be simple, medium, or large.\n"
        "- **Always assign at least one Resource**."
        "- Distinguish `Owner` (responsible lead role) and `Resources` (supporting roles)."
        "- `Owner` and `Resources` must be valid IT roles (e.g., Backend Developer, AI Engineer, QA Engineer, etc.)."
        "- `Owner` is always a role who manages that particular activity (not a personal name).\n"
        "- `Resources` must contain only roles which are required for that particular activity, distinct from `Owner`.\n"
        "- If `Resources` is missing, fallback to the same `Owner` role.\n"
        "- Use less activities and resources as much as possible.\n"
        "- Effort Months should be small integers 0.5 to 2 months not more than this.\n"
        "- IDs must start from 1 and increment sequentially.\n"
        "- Use USD for all rates.\n"
        "- If the RFP or KB text lacks detail, infer the missing pieces logically."
        "- Include all relevant roles and activities that ensure delivery of the project scope."
        "- Keep all field names exactly as in the schema.\n"

        f"{user_context}"
        f"RFP / Project Files Content:\n{rfp_text}\n\n"
        f"Knowledge Base Context (for enrichment only):\n{kb_context}\n"
    )


# Post-clean (raw AI output)


def _parse_date_safe(val: Any, fallback: datetime = None) -> datetime:
    """Try to parse a date string; return fallback if invalid."""
    if not val:
        return fallback
    try:
        return datetime.strptime(str(val), "%Y-%m-%d")
    except Exception:
        return fallback

def _safe_str(val: Any) -> str:
    return str(val).strip() if val is not None else ""

def _to_float(val: Any, default: float = 0.0) -> float:
    try:
        return float(val)
    except Exception:
        return default
    
def _build_architecture_prompt(rfp_text: str, kb_chunks: List[str], project=None) -> str:
    name = (getattr(project, "name", "") or "Untitled Project").strip()
    domain = (getattr(project, "domain", "") or "General").strip()
    tech = (getattr(project, "tech_stack", "") or "Modern Web + Cloud Stack").strip()

    return f"""
You are a senior enterprise cloud architect.
Design a **modern, minimal, color-coded, horizontally aligned system architecture diagram**
with elegant UI styling and balanced spacing, based on the following project context.

Project Name: {name}
Domain: {domain}
Tech Stack: {tech}

RFP Text:
{rfp_text}

Knowledge Base Context:
{kb_chunks}

### Design Goals
- Output **ONLY valid Graphviz DOT syntax** (no markdown or commentary)
- Start with `digraph Architecture {{` and end with `}}`
- **Horizontal flow (Left → Right)** using `rankdir=LR`
- Use a **clean, modern visual theme** with subtle gradients and soft colors
- Organize into the following **clusters (sections)**:
  1. **Frontend / User Touchpoints** → color: `#E3F2FD` (blue tint)
  2. **Backend / Services** → color: `#E8F5E9` (green tint)
  3. **Data / Storage / APIs** → color: `#FFFDE7` (yellow tint)
  4. **AI / Analytics Layer** → color: `#F3E5F5` (purple tint)
  5. **Security / Monitoring** → color: `#ECEFF1` (gray tint)
- Include meaningful node labels (e.g. “React Frontend”, “FastAPI Backend”, “Azure Blob Storage”, “Azure OpenAI”)
- Keep under **15 nodes total**
- Maintain smooth, **logical arrow flow (Frontend → Backend → Data → AI → Outputs)**
- Use **orthogonal connectors (`splines=ortho`)** and avoid overlapping lines
- Make it look visually balanced and presentation-grade

### Styling Rules
- **Overall graph:**
  - `dpi=200`, `ranksep=1.3`, `nodesep=1.3`
  - `bgcolor="white"`
- **Clusters:**
  - `style="filled,rounded"`
  - `fontname="Helvetica-Bold"`
  - `fontsize=13`
  - Rounded corners and soft color fills (no dark outlines)
- **Nodes:**
  - `fontname="Helvetica"`
  - `fontsize=12`
  - Rounded shapes with pastel backgrounds
  - Distinct shapes per layer:
    - `box` → UI/Frontend
    - `box3d` → Backend/API services
    - `cylinder` → Databases or Storage
    - `hexagon` → APIs / Pipelines
    - `ellipse` → AI / Analytics
    - `diamond` → Security / Control Gateways
- **Edges:**
  - `color="#607D8B"`, `penwidth=1.5`, `arrowsize=0.9`
  - Smooth orthogonal flow with minimum crossings

### Example Layout
digraph Architecture {{
  rankdir=LR;
  graph [dpi=200, fontname="Helvetica", bgcolor="white", nodesep=1.2, ranksep=1.2, splines=ortho];

  node [style="rounded,filled", color="#B0BEC5", fontname="Helvetica", fontsize=12, penwidth=1.2];

  subgraph cluster_frontend {{
    label="Frontend / Touchpoints";
    style="filled,rounded";
    fillcolor="#E3F2FD";
    web [label="React Web App", shape=box, fillcolor="#BBDEFB"];
    mobile [label="Mobile App", shape=box, fillcolor="#BBDEFB"];
  }}

  subgraph cluster_backend {{
    label="Backend / Internal Services";
    style="filled,rounded";
    fillcolor="#E8F5E9";
    api [label="FastAPI Service", shape=box3d, fillcolor="#C8E6C9"];
    auth [label="Auth / User Service", shape=box3d, fillcolor="#C8E6C9"];
  }}

  subgraph cluster_data {{
    label="Data / Storage / APIs";
    style="filled,rounded";
    fillcolor="#FFFDE7";
    blob [label="Azure Blob Storage", shape=cylinder, fillcolor="#FFF9C4"];
    db [label="PostgreSQL DB", shape=cylinder, fillcolor="#FFF9C4"];
    search [label="Azure AI Search", shape=hexagon, fillcolor="#FFF9C4"];
  }}

  subgraph cluster_ai {{
    label="AI / Analytics Layer";
    style="filled,rounded";
    fillcolor="#F3E5F5";
    openai [label="Azure OpenAI", shape=ellipse, fillcolor="#E1BEE7"];
    reports [label="Power BI / Analytics Dashboard", shape=ellipse, fillcolor="#E1BEE7"];
  }}

  subgraph cluster_security {{
    label="Security / Monitoring";
    style="filled,rounded";
    fillcolor="#ECEFF1";
    monitor [label="Azure Monitor / Grafana", shape=diamond, fillcolor="#CFD8DC"];
    keyvault [label="Azure Key Vault", shape=diamond, fillcolor="#CFD8DC"];
  }}

  # Flow Connections
  web -> api -> db -> search -> openai -> reports;
  mobile -> api;
  api -> monitor;
  search -> keyvault;
}}
"""



async def generate_architecture(
    db: AsyncSession,
    project,
    rfp_text: str,
    kb_chunks: List[str],
    blob_base_path: str,
) -> tuple[models.ProjectFile | None, str]:
    """
    Generate a visually clean, high-quality architecture diagram (PNG)
    from RFP + KB context, upload to Azure Blob Storage,
    save record in ProjectFile, and return (db_file, blob_path).
    Each project's diagram is unique based on its RFP/domain context.
    """
    if client is None or deployment is None:
        logger.warning("Azure OpenAI not configured — skipping architecture generation")
        return None, ""

    prompt = _build_architecture_prompt(rfp_text, kb_chunks, project)

    try:
        # --- Step 1: Ask Azure OpenAI for Graphviz DOT code ---
        resp = await anyio.to_thread.run_sync(
            lambda: client.chat.completions.create(
                model=deployment,
                messages=[
                    {"role": "system", "content": "You are an expert cloud software architect."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
            )
        )
        dot_code = resp.choices[0].message.content.strip()

        # --- Step 2: Clean and validate DOT code ---
        dot_code = re.sub(r"```[a-zA-Z]*", "", dot_code).replace("```", "").strip()
        dot_code = dot_code.strip("`").strip()

        if not dot_code.lower().startswith("digraph"):
            dot_code = f"digraph Architecture {{\n{dot_code}\n}}"

        # --- Step 3: Inject clean styling preamble (with embedded DPI + font) ---
        style_preamble = """
digraph Architecture {
    graph [
        dpi=200,
        fontname="Helvetica",
        fontsize=12,
        bgcolor="white",
        rankdir=LR,
        splines=ortho,
        nodesep=1.3,
        ranksep=1.2,
        pad=0.6
    ];

    node [
        style="rounded,filled",
        fontname="Helvetica-Bold",
        fontsize=13,
        fillcolor="#F9FAFB",
        color="#B0BEC5",
        penwidth=1.3,
        margin=0.25
    ];

    edge [
        color="#607D8B",
        arrowsize=0.9,
        penwidth=1.5,
        fontname="Helvetica",
        fontsize=11,
        fontcolor="#374151"
    ];
"""

        dot_inner = re.sub(r"(?is)^digraph\s+\w+\s*\{|\}$", "", dot_code.strip()).strip()
        dot_code = style_preamble + dot_inner + "\n}"

        # --- Step 4: Render DOT → High-resolution PNG ---
        try:
            graph = graphviz.Source(dot_code, engine="dot")  # neat layout engine
            tmp_png = tempfile.NamedTemporaryFile(delete=False, suffix=".png")

            # Just render — Graphviz uses internal anti-aliasing when dpi=200 is set above
            graph.render(tmp_png.name, format="png", cleanup=True)

            png_path = tmp_png.name + ".png"
        except Exception as e:
            logger.error(f"Graphviz rendering failed: {e}\n--- DOT Snippet ---\n{dot_code[:600]}")
            return None, ""

        # --- Step 5: Upload PNG to Azure Blob ---
        blob_name = f"{blob_base_path}/architecture_{project.id}.png"
        with open(png_path, "rb") as fh:
            png_bytes = fh.read()
        await azure_blob.upload_bytes(png_bytes, blob_name)

        try:
            os.remove(png_path)
        except FileNotFoundError:
            pass

        # --- Step 6: Replace old record if exists ---
        result = await db.execute(
            select(models.ProjectFile).filter(
                models.ProjectFile.project_id == project.id,
                models.ProjectFile.file_name == "architecture.png",
            )
        )
        old_file = result.scalars().first()
        if old_file:
            try:
                await azure_blob.delete_blob(old_file.file_path)
                await db.delete(old_file)
                await db.commit()
            except Exception as e:
                logger.warning(f"Failed to delete old architecture.png: {e}")

        # --- Step 7: Save new ProjectFile record ---
        db_file = models.ProjectFile(
            project_id=project.id,
            file_name="architecture.png",
            file_path=blob_name,
        )
        db.add(db_file)
        await db.commit()
        await db.refresh(db_file)

        logger.info(f"Clean architecture diagram generated and stored at {blob_name}")
        return db_file, blob_name

    except Exception as e:
        logger.error(f"Architecture generation failed: {e}")
        return None, ""


# --- Cleaner ---

def clean_scope(data: Dict[str, Any], project=None) -> Dict[str, Any]:
    if not isinstance(data, dict):
        return {}

    ist = pytz.timezone("Asia/Kolkata")
    today = datetime.now(ist).replace(hour=0, minute=0, second=0, microsecond=0)

    activities: List[Dict[str, Any]] = []
    start_dates, end_dates = [], []
    role_month_map: Dict[str, Dict[str, float]] = {}
    role_order: List[str] = []

    # --- Helper: compute monthly allocation based on actual days in month ---
    def month_effort(s: datetime, e: datetime) -> Dict[str, float]:
        cur = s
        month_eff = {}
        while cur <= e:
            year, month = cur.year, cur.month
            days_in_month = monthrange(year, month)[1]
            start_day = cur.day if cur.month == s.month else 1
            end_day = e.day if cur.month == e.month else days_in_month
            days_count = end_day - start_day + 1
            month_eff[f"{cur.strftime('%b %Y')}"] = round(days_count / 30.0, 2)
            # move to next month
            if month == 12:
                cur = datetime(year + 1, 1, 1)
            else:
                cur = datetime(cur.year, cur.month + 1, 1)
        return month_eff

    # --- Process activities ---
    for idx, a in enumerate(data.get("activities") or [], start=1):
        owner = a.get("Owner") or "Unassigned"

        # Parse dependencies
        raw_deps = [d.strip() for d in str(a.get("Resources") or "").split(",") if d.strip()]

        # 🚫 Remove owner from resources if duplicated
        raw_deps = [r for r in raw_deps if r.lower() != owner.lower()]

        # Owner always included, then other resources
        roles = [owner] + raw_deps

        s = _parse_date_safe(a.get("Start Date"), today)
        e = _parse_date_safe(a.get("End Date"), s + timedelta(days=30))
        if e < s:
            e = s + timedelta(days=30)

        # --- allocate per month (no splitting among roles) ---
        month_alloc = month_effort(s, e)
        for role in roles:
            if role not in role_month_map:
                role_month_map[role] = {}
                role_order.append(role)
            for m, eff in month_alloc.items():
                role_month_map[role][m] = role_month_map[role].get(m, 0.0) + eff

        dur_days = max(1, (e - s).days)
        activities.append({
            "ID": idx,
            "Activities": _safe_str(a.get("Activities")),
            "Description": _safe_str(a.get("Description")),
            "Owner": owner,
            "Resources": ", ".join(raw_deps), 
            "Start Date": s,
            "End Date": e,
            "Effort Months": round(dur_days / 30.0, 2),
        })

        start_dates.append(s)
        end_dates.append(e)

    # --- Sort activities ---
    activities.sort(key=lambda x: x["Start Date"])
    for idx, a in enumerate(activities, start=1):
        a["ID"] = idx
        a["Start Date"] = a["Start Date"].strftime("%Y-%m-%d")
        a["End Date"] = a["End Date"].strftime("%Y-%m-%d")

    # --- Project span & month labels ---
    min_start = min(start_dates) if start_dates else today
    max_end = max(end_dates) if end_dates else min_start
    duration = max(1.0, round(max(1, (max_end - min_start).days) / 30.0, 2))

    month_labels = []
    cur = datetime(min_start.year, min_start.month, 1)
    while cur <= max_end:
        month_labels.append(cur.strftime("%b %Y"))
        if cur.month == 12:
            cur = datetime(cur.year + 1, 1, 1)
        else:
            cur = datetime(cur.year, cur.month + 1, 1)

    # --- Resourcing Plan ---
    resourcing_plan = []
    for idx, role in enumerate(role_order, start=1):
        month_map = role_month_map[role]
        month_efforts = {m: round(month_map.get(m, 0.0), 2) for m in month_labels}
        total_effort = round(sum(month_efforts.values()), 2)
        if total_effort <= 0:
            continue
        rate = ROLE_RATE_MAP.get(role, 2000.0)
        cost = round(total_effort * rate, 2)
        plan_entry = {
            "ID": idx,
            "Resources": role,
            "Rate/month": rate,
            **month_efforts,
            "Efforts": total_effort,
            "Cost": cost
        }
        resourcing_plan.append(plan_entry)

    # --- Overview ---
    ov = data.get("overview") or {}
    data["overview"] = {
        "Project Name": _safe_str(ov.get("Project Name") or getattr(project, "name", "Untitled Project")),
        "Domain": _safe_str(ov.get("Domain") or getattr(project, "domain", "")),
        "Complexity": _safe_str(ov.get("Complexity") or getattr(project, "complexity", "")),
        "Tech Stack": _safe_str(ov.get("Tech Stack") or getattr(project, "tech_stack", "")),
        "Use Cases": _safe_str(ov.get("Use Cases") or getattr(project, "use_cases", "")),
        "Compliance": _safe_str(ov.get("Compliance") or getattr(project, "compliance", "")),
        "Duration": duration,
        "Generated At": datetime.now(ist).strftime("%Y-%m-%d %H:%M %Z"),
    }

    data["activities"] = activities
    data["resourcing_plan"] = resourcing_plan
    return data


async def generate_project_scope(db: AsyncSession, project) -> dict:
    """
    Generate project scope + architecture diagram + store architecture in DB + return combined JSON.
    """
    if client is None or deployment is None:
        logger.warning("Azure OpenAI not configured")
        return {}

    model_name = deployment
    tokenizer = tiktoken.encoding_for_model(model_name)
    context_limit = 128000
    max_total_tokens = context_limit - 4000
    used_tokens = 0

    # ---------- Extract RFP ----------
    rfp_text = ""
    try:
        files: List[dict] = []
        if getattr(project, "files", None):
            try:
                files = [{"file_name": f.file_name, "file_path": f.file_path} for f in project.files]
            except Exception as e:
                logger.warning(f" Could not access project.files: {e}")
                files = []
        if files:
            rfp_text = await _extract_text_from_files(files)
    except Exception as e:
        logger.warning(f"File extraction for project {getattr(project, 'id', None)}")

    # ---------- Trim RFP text ----------
    rfp_tokens = tokenizer.encode(rfp_text or "")
    if len(rfp_tokens) > 3000:
        rfp_tokens = rfp_tokens[:3000]
    rfp_text = tokenizer.decode(rfp_tokens)
    used_tokens += len(rfp_tokens)

    # ---------- Retrieve KB context ----------
    fallback_fields = [
        getattr(project, "name", None),
        getattr(project, "domain", None),
        getattr(project, "complexity", None),
        getattr(project, "tech_stack", None),
        getattr(project, "use_cases", None),
        getattr(project, "compliance", None),
        str(getattr(project, "duration", "")) if getattr(project, "duration", None) else None,
    ]
    fallback_text = " ".join(f for f in fallback_fields if f and str(f).strip())

    if not (rfp_text.strip() or fallback_text.strip()):
        return {
            "overview": {
                "Project Name": "Untitled Project",
                "Domain": "TBD",
                "Complexity": "TBD",
                "Tech Stack": "TBD",
                "Use Cases": "TBD",
                "Compliance": "TBD",
                "Duration": 1,
            },
            "activities": [],
            "resourcing_plan": [],
            "architecture_diagram": None,
        }

    kb_results = _rag_retrieve(rfp_text or fallback_text)
    kb_chunks = []
    stop = False
    for group in kb_results:
        for ch in group["chunks"]:
            chunk_tokens = len(tokenizer.encode(ch["content"]))
            if used_tokens + chunk_tokens > max_total_tokens:
                stop = True
                break
            kb_chunks.append(ch["content"])
            used_tokens += chunk_tokens
        if stop:
            break

    logger.info(
        f"Final RFP tokens: {len(rfp_tokens)}, KB tokens: {used_tokens - len(rfp_tokens)}, Total: {used_tokens}/{max_total_tokens}"
    )

    # ---------- Build + query ----------
    prompt = _build_scope_prompt(rfp_text, kb_chunks, project, model_name=model_name)

    try:
        # Step 1: Generate scope
        resp = await anyio.to_thread.run_sync(
            lambda: client.chat.completions.create(
                model=deployment,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
        )
        raw = _extract_json(resp.choices[0].message.content.strip())
        cleaned_scope = clean_scope(raw, project=project)

        # Step 2: Generate + store architecture diagram
        try:
            blob_base_path = f"{PROJECTS_BASE}/{getattr(project, 'id', 'unknown')}"
            db_file, arch_blob = await generate_architecture(
                db, project, rfp_text, kb_chunks, blob_base_path
            )
            cleaned_scope["architecture_diagram"] = arch_blob or None
        except Exception as e:
            logger.warning(f"Architecture diagram generation failed: {e}")
            cleaned_scope["architecture_diagram"] = None

        return cleaned_scope

    except Exception as e:
        logger.error(f"Azure OpenAI scope generation failed: {e}")
        return {}



async def regenerate_from_instructions(draft: dict, instructions: str) -> dict:
    """
    If instructions are provided → call Azure OpenAI to regenerate.
    If no instructions → just clean the draft.
    """
    if not instructions or not instructions.strip():
        return clean_scope(draft)

    if client is None or deployment is None:
        logger.warning("Azure OpenAI not configured")
        return clean_scope(draft)

    prompt = f"""
You are a project scoping assistant.
You are given the current draft JSON scope and user instructions.
Update the JSON accordingly while keeping valid JSON structure.

Instructions:
{instructions}

Draft Scope (JSON):
{json.dumps(draft, indent=2)}

Return ONLY valid JSON.
"""

    try:
        resp = await anyio.to_thread.run_sync(
            lambda: client.chat.completions.create(
                model=deployment,
                messages=[
                    {"role": "system", "content": "You are a strict JSON generator."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
            )
        )

        raw_text = resp.choices[0].message.content.strip()
        updated = _extract_json(raw_text)
        return clean_scope(updated)

    except Exception as e:
        logger.error(f"Regeneration failed: {e}")
        return clean_scope(draft)


async def finalize_scope(
    db: AsyncSession,
    project_id: str,
    scope_data: dict
) -> tuple[models.ProjectFile, dict]:
    """
    Clean and finalize scope JSON, update project metadata, and store finalized_scope.json in blob.
    """

    logger.info(f"📌 Finalizing scope (engine) for project {project_id}...")

    #  Clean the draft
    cleaned = clean_scope(scope_data)
    overview = cleaned.get("overview", {})

    # ---- Update project metadata ----
    result = await db.execute(
        select(models.Project)
        .options(selectinload(models.Project.files))
        .filter(models.Project.id == project_id)
    )
    db_project = result.scalars().first()

    if db_project and overview:
        db_project.name = overview.get("Project Name") or db_project.name
        db_project.domain = overview.get("Domain") or db_project.domain
        db_project.complexity = overview.get("Complexity") or db_project.complexity
        db_project.tech_stack = overview.get("Tech Stack") or db_project.tech_stack
        db_project.use_cases = overview.get("Use Cases") or db_project.use_cases
        db_project.compliance = overview.get("Compliance") or db_project.compliance
        db_project.duration = str(overview.get("Duration") or db_project.duration)
        await db.commit()
        await db.refresh(db_project)

    # ---- Remove old finalized scope if exists ----
    result = await db.execute(
        select(models.ProjectFile).filter(
            models.ProjectFile.project_id == project_id,
            models.ProjectFile.file_name == "finalized_scope.json"
        )
    )
    old_file = result.scalars().first()
    if old_file:
        try:
            await azure_blob.delete_blob(old_file.file_path)
            await db.delete(old_file)
            await db.commit()
        except Exception as e:
            logger.warning(f" Failed to delete old finalized_scope.json: {e}")

    # ---- Upload new finalized scope ----
    blob_name = f"{PROJECTS_BASE}/{project_id}/finalized_scope.json"
    await azure_blob.upload_bytes(
        json.dumps(cleaned, ensure_ascii=False, indent=2).encode("utf-8"),
        blob_name
    )

    db_file = models.ProjectFile(
        project_id=project_id,
        file_name="finalized_scope.json",
        file_path=blob_name,
    )
    db.add(db_file)
    await db.commit()
    await db.refresh(db_file)

    logger.info(f" Finalized scope stored for project {project_id}")
    return db_file, {**cleaned, "_finalized": True}

