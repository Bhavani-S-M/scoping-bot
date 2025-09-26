# app/utils/scope_engine.py
import json, re, logging, difflib, os, tempfile
from pdfminer.high_level import extract_text as extract_pdf_text
from docx import Document
from pptx import Presentation
import openpyxl
from PIL import Image
import pytesseract
from azure.search.documents.models import VectorizedQuery
from typing import Dict, Any, List
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from app.models import ProjectFile
from app.utils import azure_blob
from app.config import config
import tiktoken
from app.utils.ai_clients import (
    get_azure_openai_client,
    get_azure_openai_deployment,
    get_search_client,
)

logger = logging.getLogger(__name__)

# Init Azure services
client = get_azure_openai_client()
deployment = get_azure_openai_deployment()
search_client = get_search_client()

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

def _extract_text_from_files(files: List[ProjectFile]) -> str:
    chunks = []
    for f in files:
        try:
            blob_bytes = azure_blob.download_bytes(f.file_path)
            suffix = os.path.splitext(f.file_name)[-1].lower()
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(blob_bytes)
                tmp_path = tmp.name

            content = ""
            if suffix in [".pdf"]:
                try:
                    content = extract_pdf_text(tmp_path)
                except Exception as e:
                    logger.warning(f"PDF extract failed {f.file_name}: {e}")

            elif suffix in [".docx"]:
                try:
                    doc = Document(tmp_path)
                    content = "\n".join([p.text for p in doc.paragraphs])
                except Exception as e:
                    logger.warning(f"DOCX extract failed {f.file_name}: {e}")

            elif suffix in [".pptx"]:
                try:
                    prs = Presentation(tmp_path)
                    content = "\n".join(
                        [shape.text for slide in prs.slides for shape in slide.shapes if hasattr(shape, "text")]
                    )
                except Exception as e:
                    logger.warning(f"PPTX extract failed {f.file_name}: {e}")

            elif suffix in [".xlsx", ".xlsm"]:
                try:
                    wb = openpyxl.load_workbook(tmp_path)
                    sheet = wb.active
                    rows = []
                    for row in sheet.iter_rows(values_only=True):
                        rows.append(" ".join([str(cell) if cell else "" for cell in row]))
                    content = "\n".join(rows)
                except Exception as e:
                    logger.warning(f"Excel extract failed {f.file_name}: {e}")

            elif suffix in [".png", ".jpg", ".jpeg", ".tiff"]:
                try:
                    img = Image.open(tmp_path)
                    content = pytesseract.image_to_string(img)
                except Exception as e:
                    logger.warning(f"OCR failed {f.file_name}: {e}")

            else:
                # fallback: assume plain text
                try:
                    with open(tmp_path, "r", encoding="utf-8", errors="ignore") as fh:
                        content = fh.read()
                except Exception:
                    pass

            if content and content.strip():
                chunks.append(content)

            os.remove(tmp_path)
        except Exception as e:
            logger.warning(f"Failed to extract {f.file_name}: {e}")
    return "\n\n".join(chunks)


def _parse_date(s: str) -> datetime | None:
    try:
        return datetime.strptime(s, "%Y-%m-%d")
    except Exception:
        return None

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
    
    if not search_client or not client:
        return []

    try:
        # Embedding for query
        emb_model = getattr(config, "AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-large")
        q_emb = client.embeddings.create(model=emb_model, input=query).data[0].embedding

        # Vector query
        vector_query = VectorizedQuery(
            vector=q_emb,
            fields="text_vector",
        )

        # Hybrid search
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
        model_name = "gpt-4o"  # Azure GPT-4o deployment
        tokenizer = tiktoken.encoding_for_model(model_name)
        context_limit = 128000
        max_tokens = context_limit - 4000  # keep 4k buffer for system + completion
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
    """
    Build the RAG prompt safely with token budget enforcement.
    - rfp_text: raw text from project files
    - kb_chunks: list of strings (already flattened from RAG)
    - project: optional Project object with user-provided fields
    - model_name: model to use for tokenizer (default gpt-4o)
    """

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
        '      "id": int,\n'
        '      "story": string | null,\n'
        '      "Activities": string,\n'
        '      "Description": string | null,\n'
        '      "Owner": string | null,\n'
        '      "Depends on": string | null,\n'
        '      "Start Date": "yyyy-mm-dd",\n'
        '      "End Date": "yyyy-mm-dd",\n'
        '      "Effort Months": int\n'
        "    }\n"
        "  ],\n"
        '  "resourcing_plan": []\n'
        "}\n\n"
        "Rules:\n"
        "- `Owner` is the person responsible for managing the activity (for display only — not used for costing).\n"
        "- `Depends on` are the people or roles who will execute that activity (used for costing).\n"
        "- Do NOT include the Owner again inside `Depends on`. They must be distinct.\n"
        "- Only if `Depends on` is completely missing, then use the Owner as a fallback.\n"
        "- `Duration` is number of months. Use real month names (Jan 2025, Feb 2025,...)\n"
        "- Use 5–10 activities and 3–5 resources.\n"
        "- Activities use months (Effort Months).\n"
        "- Use small integer IDs starting from 1.\n"
        "- Use USD for rate.\n"
        "- Keep all field names exactly as in the schema.\n\n"
        f"{user_context}"
        f"RFP / Project Files Content:\n{rfp_text}\n\n"
        f"Knowledge Base Context (for enrichment only):\n{kb_context}\n"
    )



# Post-clean (raw AI output)
def _clean_scope(data: Dict[str, Any], project=None) -> Dict[str, Any]:
    if not isinstance(data, dict):
        return {}

    today = datetime.now()
    cursor = 0
    min_start, max_end = None, None
    resource_month_map: Dict[str, float] = {}
    missing_roles: Dict[str, float] = {}
    id_to_owner = {str(a.get("id") or a.get("ID")): a.get("Owner") for a in data.get("activities") or []}

    # =====================================================
    # ACTIVITIES
    # =====================================================
    for idx, a in enumerate(data.get("activities", []) or [], start=1):
        a["id"] = idx
        months_effort = max(1.0, float(a.get("Effort Months") or 1))
        a["Effort Months"] = months_effort

        # Default Owner
        if not a.get("Owner"):
            a["Owner"] = "Unassigned"

        # --- Collect raw Depends on ---
        dep_raw = a.get("Depends on") or ""
        dep_list = [r.strip() for r in dep_raw.split(",") if r.strip()]
        if not dep_list:
            dep_list = [a.get("Owner") or "TBD"]

        # Resolve IDs -> Owners if AI used IDs in Depends on
        dep_list = [id_to_owner.get(d, d) for d in dep_list]

        # --- Merge Owner + Depends into a single set ---
        roles_for_activity = set(dep_list + [a["Owner"]])

        normalized_deps = []
        for r in roles_for_activity:
            normalized = _normalize_role_name(r)
            if normalized == "TBD":
                role = (r or "Unknown Role").title().strip()
                missing_roles[role] = 2000.0
                normalized = role

            # Add effort once per unique role
            resource_month_map[normalized] = resource_month_map.get(normalized, 0) + months_effort

            # Keep for cleaned Depends on (skip owner so it doesn’t repeat)
            if r != a["Owner"]:
                normalized_deps.append(normalized)

        a["Depends on"] = ", ".join(normalized_deps)

        # --- Dates ---
        start = _parse_date(a.get("Start Date") or "") or (today + timedelta(days=int(cursor * 30)))
        end = _parse_date(a.get("End Date") or "") or (start + timedelta(days=int(months_effort * 30) - 1))
        a["Start Date"], a["End Date"] = start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")
        cursor += months_effort

        min_start = min(min_start or start, start)
        max_end = max(max_end or end, end)

    # =====================================================
    # DURATION & MONTH LABELS
    # =====================================================
    user_duration = int(data.get("overview", {}).get("Duration") or 0)
    months = user_duration if user_duration > 0 else max(
        1, round(((max_end or today) - (min_start or today)).days / 30)
    )
    base_date = min_start or today
    month_labels = [(base_date + relativedelta(months=i)).strftime("%b %Y") for i in range(months)]

    # =====================================================
    # RESOURCING PLAN (UNIQUE ROLES)
    # =====================================================
    resourcing_plan = []
    seen_roles = set()
    for i, (rname, total_months) in enumerate(resource_month_map.items(), start=1):
        if rname in seen_roles:
            continue  # skip duplicates
        seen_roles.add(rname)

        eff = max(1, round(total_months))
        rate = ROLE_RATE_MAP.get(rname, missing_roles.get(rname, 2000.0))
        cost = round(rate * eff, 2)

        # Spread efforts across months
        base, rem = divmod(eff, months)
        monthly = [base + (1 if j < rem else 0) for j in range(months)]

        resourcing_plan.append({
            "id": len(resourcing_plan) + 1,
            "Resources": rname,
            "Rate/month": rate,
            "Efforts": eff,
            **{m: v for m, v in zip(month_labels, monthly)},
            "cost": cost
        })

    data["resourcing_plan"] = resourcing_plan
    data.setdefault("overview", {})["Duration"] = months
    data["_missing_roles"] = missing_roles

    # =====================================================
    # MERGE USER-PROVIDED PROJECT FIELDS
    # =====================================================
    if project:
        ov = data.setdefault("overview", {})
        if getattr(project, "name", None):         ov["Project Name"] = project.name
        if getattr(project, "domain", None):       ov["Domain"] = project.domain
        if getattr(project, "complexity", None):   ov["Complexity"] = project.complexity
        if getattr(project, "tech_stack", None):   ov["Tech Stack"] = project.tech_stack
        if getattr(project, "use_cases", None):    ov["Use Cases"] = project.use_cases
        if getattr(project, "compliance", None):   ov["Compliance"] = project.compliance
        if getattr(project, "duration", None):     ov["Duration"] = project.duration or ov.get("Duration", months)

    return data



def generate_project_scope(project) -> dict:
    if client is None or deployment is None:
        logger.warning("Azure OpenAI not configured")
        return {}

    # ---- Model + tokenizer setup ----
    model_name = "gpt-4o"  # Azure GPT-4o deployment
    tokenizer = tiktoken.encoding_for_model(model_name)
    context_limit = 128000
    max_total_tokens = context_limit - 4000  # leave 4k headroom for system + completion
    used_tokens = 0

    # ---------- Extract RFP ----------
    rfp_text = ""
    try:
        if getattr(project, "files", None):
            rfp_text = _extract_text_from_files(project.files)
    except Exception as e:
        logger.warning(f"File extraction failed: {e}")

    # Trim RFP text
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

    # Filter out empty/None values and join with a space
    fallback_text = " ".join(f for f in fallback_fields if f and str(f).strip())

    # After extracting file + fallback text
    if not (rfp_text and rfp_text.strip()) and not (fallback_text and fallback_text.strip()):
        logger.warning("No meaningful RFP text or project fields provided — returning skeleton scope")
        return {
            "overview": {
                "Project Name": "Untitled Project",
                "Domain": "TBD",
                "Complexity": "TBD",
                "Tech Stack": "TBD",
                "Use Cases": "TBD",
                "Compliance": "TBD",
                "Duration": 1
            },
            "activities": [],
            "resourcing_plan": []
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
        f"Final RFP tokens: {len(rfp_tokens)}, "
        f"KB tokens: {used_tokens - len(rfp_tokens)}, "
        f"Total: {used_tokens} / {max_total_tokens}"
    )

    # ---------- Build + query ----------
    prompt = _build_scope_prompt(rfp_text, kb_chunks, project, model_name=model_name)

    try:
        resp = client.chat.completions.create(
            model=deployment,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        raw = _extract_json(resp.choices[0].message.content.strip())
        return _clean_scope(raw, project=project)
    except Exception as e:
        logger.error(f"Azure OpenAI scope generation failed: {e}")
        return {}
