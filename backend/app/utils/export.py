# app/utils/export.py
from __future__ import annotations
import io, json
from datetime import datetime, timezone, timedelta
from typing import Any, Dict

import xlsxwriter
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Table, TableStyle,
    Spacer, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.graphics.charts.piecharts import Pie
from reportlab.lib.enums import TA_CENTER

# ----------------------------------------------------------------------
# Theme + Role Rates
# ----------------------------------------------------------------------
THEME = {
    "header_bg": "#BDD7EE",
    "zebra1": "#FFFFFF",
    "zebra2": "#E1E9EE",
    "total_bg": "#C6E0B4",
    "palette": ["#8DA6D7", "#E2DBBB", "#97BAEB", "#F28282", "#B9E7EB", "#E0C0A8"]
}

ROLE_RATE_MAP: Dict[str, float] = {
    "Backend Developer": 3000.0, "Frontend Developer": 2800.0,
    "QA Analyst": 1800.0, "QA Engineer": 2000.0,
    "Data Engineer": 2800.0, "Data Analyst": 2200.0,
    "Data Architect": 3500.0, "UX Designer": 2500.0,
    "UI/UX Designer": 2600.0, "Project Manager": 3500.0,
    "Cloud Engineer": 3000.0, "BI Developer": 2700.0,
    "DevOps Engineer": 3200.0, "Security Administrator": 3000.0,
    "System Administrator": 2800.0, "Solution Architect": 4000.0
}

IST = timezone(timedelta(hours=5, minutes=30))


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
def _to_float(v, d=0.0):
    try: return float(str(v).replace(",","").strip())
    except: return d

def _to_int(v, d=0):
    try: return int(float(v))
    except: return d

def _safe_str(v, d=""): 
    return d if v is None else str(v)

def _parse_date_safe(val: str, default: datetime | None = None) -> datetime | None:
    try:
        return datetime.fromisoformat(val) if val else default
    except Exception:
        return default


# ----------------------------------------------------------------------
# Normalize Scope
# ----------------------------------------------------------------------
def normalize_scope(scope: Dict[str, Any]) -> Dict[str, Any]:
    import copy
    data = copy.deepcopy(scope or {})
    ov = data.get("overview") or {}

    # Collect activity dates
    start_dates, end_dates = [], []
    for a in data.get("activities") or []:
        s = _parse_date_safe(a.get("Start Date"))
        e = _parse_date_safe(a.get("End Date"))
        if s: start_dates.append(s)
        if e: end_dates.append(e)

    min_start = min(start_dates) if start_dates else datetime.utcnow()
    max_end = max(end_dates) if end_dates else min_start

    # Shift into future if needed
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    if min_start < today:
        offset = (today - min_start).days
        for a in data.get("activities") or []:
            s = _parse_date_safe(a.get("Start Date"))
            e = _parse_date_safe(a.get("End Date"))
            if s:
                s = s + timedelta(days=offset)
                a["Start Date"] = s.strftime("%Y-%m-%d")
            if e:
                e = e + timedelta(days=offset)
                a["End Date"] = e.strftime("%Y-%m-%d")

        # Recompute bounds
        start_dates = [_parse_date_safe(a.get("Start Date")) for a in data.get("activities") if a.get("Start Date")]
        end_dates = [_parse_date_safe(a.get("End Date")) for a in data.get("activities") if a.get("End Date")]
        start_dates = [s for s in start_dates if s]
        end_dates = [e for e in end_dates if e]
        min_start = min(start_dates) if start_dates else today
        max_end = max(end_dates) if end_dates else min_start

    diff_days = max(1, (max_end - min_start).days)
    activity_months = max(1, round(diff_days / 30))
    user_duration = _to_int(ov.get("Duration"))
    duration = max(user_duration, activity_months) if user_duration > 0 else activity_months

    data["overview"] = {
        "Project Name": _safe_str(ov.get("Project Name") or "Untitled Project"),
        "Domain": _safe_str(ov.get("Domain") or ""),
        "Complexity": _safe_str(ov.get("Complexity") or ""),
        "Tech Stack": _safe_str(ov.get("Tech Stack") or ""),
        "Use Cases": _safe_str(ov.get("Use Cases") or ""),
        "Compliance": _safe_str(ov.get("Compliance") or ""),
        "Duration": duration,
        "Generated At": _safe_str(
            ov.get("Generated At") or datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        ),
    }

    # Month labels
    month_labels = []
    cur = datetime(min_start.year, min_start.month, 1)
    while cur <= max_end:
        month_labels.append(cur.strftime("%b %Y"))
        cur = datetime(
            cur.year + (1 if cur.month == 12 else 0),
            1 if cur.month == 12 else cur.month + 1,
            1,
        )

    acts, role_month_map = [], {}

    # Activities
    for idx, a in enumerate(data.get("activities") or [], start=1):
        s = _parse_date_safe(a.get("Start Date"), min_start)
        e = _parse_date_safe(a.get("End Date"), s or min_start)
        if e < s: e = s
        dur_days = max(1, (e - s).days)
        total_months = round(dur_days / 30.0, 2)

        # Month span
        span_months, curm = [], datetime(s.year, s.month, 1)
        while curm <= e:
            span_months.append(curm.strftime("%b %Y"))
            curm = datetime(
                curm.year + (1 if curm.month == 12 else 0),
                1 if curm.month == 12 else curm.month + 1,
                1,
            )

        # Roles
        raw_deps = [d.strip() for d in str(a.get("Depends on") or "").split(",") if d.strip()]
        all_roles = set(raw_deps + [a.get("Owner") or "Unassigned"])
        per_role = total_months / len(all_roles) if all_roles else total_months

        norm_deps = []
        for r in all_roles:
            match = next((k for k in ROLE_RATE_MAP if k.lower() in r.lower() or r.lower() in k.lower()), r.title())
            if r in raw_deps: norm_deps.append(match)
            if match not in role_month_map:
                role_month_map[match] = {m: 0.0 for m in month_labels}
            for m in span_months:
                role_month_map[match][m] += per_role

        acts.append({
            "ID": idx,
            "Story": _safe_str(a.get("Story")),
            "Activities": _safe_str(a.get("Activities")),
            "Description": _safe_str(a.get("Description")),
            "Owner": _safe_str(a.get("Owner")),
            "Depends on": ", ".join(norm_deps),
            "Start Date": s.strftime("%Y-%m-%d"),
            "End Date": e.strftime("%Y-%m-%d"),
            "Effort Months": total_months,
        })

    data["activities"] = acts

    # Resourcing
    user_res = {r.get("Resources", "").strip().lower(): r for r in (scope.get("resourcing_plan") or [])}
    res = []
    for idx, (role, month_map) in enumerate(role_month_map.items(), start=1):
        urow = user_res.get(role.strip().lower())
        monthly = {m: _to_float(urow.get(m, month_map[m]) if urow else month_map[m]) for m in month_labels}
        eff = round(sum(monthly.values()), 1)
        rate = _to_float((urow or {}).get("Rate/month") or ROLE_RATE_MAP.get(role, 2000.0))
        cost = round(eff * rate, 2)
        res.append({
            "ID": idx,
            "Resources": role,
            "Rate/month": rate,
            **{m: round(monthly[m], 1) for m in month_labels},
            "Efforts": eff,
            "Cost": cost,
        })

    data["resourcing_plan"] = res
    return data


# ----------------------------------------------------------------------
# JSON Export
# ----------------------------------------------------------------------
def generate_json_data(scope: Dict[str, Any]) -> Dict[str, Any]:
    return normalize_scope(scope)


# ---------- Excel ----------
def generate_xlsx(scope: Dict[str, Any]) -> io.BytesIO:
    try:
        from xlsxwriter.utility import xl_col_to_name
        data = scope
        buf = io.BytesIO()
        wb = xlsxwriter.Workbook(buf, {"in_memory": True})

        # ---------- Formats ----------
        fmt_th = wb.add_format({
            "bold": True, "bg_color": THEME["header_bg"],
            "border": 1, "align": "center", "text_wrap": True
        })
        fmt_z1 = wb.add_format({"border": 1, "bg_color": THEME["zebra1"]})
        fmt_z2 = wb.add_format({"border": 1, "bg_color": THEME["zebra2"]})
        fmt_date = wb.add_format({"border": 1, "num_format": "yyyy-mm-dd"})
        fmt_num = wb.add_format({"border": 1, "num_format": "0.00"})
        fmt_money = wb.add_format({"border": 1, "num_format": "$#,##0.00"})
        fmt_total = wb.add_format({"bold": True, "border": 1, "bg_color": THEME["total_bg"]})

        # --------- Overview ----------
        ws_ov = wb.add_worksheet("Overview")
        ws_ov.write_row("A1", ["Field", "Value"], fmt_th)
        for i, (k, v) in enumerate(data.get("overview", {}).items(), start=2):
            zfmt = fmt_z1 if i % 2 else fmt_z2
            ws_ov.write(f"A{i}", k, zfmt)
            ws_ov.write(f"B{i}", str(v), zfmt)

        ws_ov.set_column("A:A", 20)
        ws_ov.set_column("B:B", 100)

        # -------- Activities ----------
        ws_a = wb.add_worksheet("Activities")
        headers = [
            "ID", "Story", "Activities", "Description", "Owner",
            "Depends on", "Start Date", "End Date", "Effort (months)", "DurationTemp"
        ]
        ws_a.write_row("A1", headers, fmt_th)
        ws_a.set_column("A:A", 5)
        ws_a.set_column("B:B", 15)
        ws_a.set_column("C:F", 30)
        ws_a.set_column("G:J", 12)

        starts, ends = [], []
        for r, a in enumerate(data.get("activities", []), start=2):
            zfmt = fmt_z1 if r % 2 else fmt_z2
            ws_a.write(r-1, 0, a.get("ID"), zfmt)
            ws_a.write(r-1, 1, a.get("Story"), zfmt)
            ws_a.write(r-1, 2, a.get("Activities"), zfmt)
            ws_a.write(r-1, 3, a.get("Description"), zfmt)
            ws_a.write(r-1, 4, a.get("Owner"), zfmt)
            ws_a.write(r-1, 5, a.get("Depends on"), zfmt)
            try:
                s = datetime.fromisoformat(a["Start Date"])
                ws_a.write_datetime(r-1, 6, s, fmt_date)
                starts.append(s)
            except:
                ws_a.write_blank(r-1, 6, None, fmt_date)
            try:
                e = datetime.fromisoformat(a["End Date"])
                ws_a.write_datetime(r-1, 7, e, fmt_date)
                ends.append(e)
            except:
                ws_a.write_blank(r-1, 7, None, fmt_date)

        last_a = len(data.get("activities", [])) + 1

        # ✅ Only add structured table if there are activities
        if data.get("activities"):
            ws_a.add_table(
                f"A1:J{last_a}",
                {
                    "name": "ActivitiesTable",
                    "columns": [
                        {"header": h} if h not in ("Effort (months)", "DurationTemp") else (
                            {
                                "header": "Effort (months)",
                                "formula": (
                                    'IF(AND([@[Start Date]]<>"",[@[End Date]]<>""),'
                                    '([@[End Date]]-[@[Start Date]])/30,"")'
                                )
                            } if h == "Effort (months)" else
                            {
                                "header": "DurationTemp",
                                "formula": (
                                    'IF(AND([@[Start Date]]<>"",[@[End Date]]<>""),'
                                    '[@[End Date]]-[@[Start Date]],"")'
                                ),
                                "format": fmt_num
                            }
                        )
                        for h in headers
                    ],
                    "style": "Table Style Medium 2",
                    "autofilter": True
                }
            )

            # ✅ Only add Gantt chart if valid dates exist
            if starts and ends:
                gantt = wb.add_chart({"type": "bar", "subtype": "stacked"})
                gantt.add_series({
                    "name": "Start",
                    "categories": f"='Activities'!$C$2:$C${last_a}",
                    "values": f"='Activities'!$G$2:$G${last_a}",
                    "fill": {"none": True},
                    "border": {"none": True}
                })
                gantt.add_series({
                    "name": "Duration",
                    "categories": f"='Activities'!$C$2:$C${last_a}",
                    "values": f"='Activities'!$J$2:$J${last_a}",
                    "fill": {"color": "#4D96FF"},
                    "border": {"color": "#4D96FF"}
                })

                gantt.set_title({"name": "Project Gantt Chart"})
                gantt.set_x_axis({
                    "date_axis": True,
                    "num_format": "mmm yyyy",
                    "major_unit": 30,
                    "major_unit_type": "days"
                })
                gantt.set_y_axis({"reverse": True})
                gantt.set_legend({"none": True})

                ws_a.insert_chart("L1", gantt, {"x_scale": 2.2, "y_scale": 1.6})

        # -------- Resources Plan --------
        ws_r = wb.add_worksheet("Resources Plan")
        if data.get("resourcing_plan"):
            month_keys = [k for k in data["resourcing_plan"][0] if len(k.split()) == 2]
            res_headers = ["Resources", "Rate/month"] + month_keys + ["Efforts", "Cost"]
            ws_r.write_row("A1", res_headers, fmt_th)
            ws_r.set_column("A:A", 25)
            ws_r.set_column("B:B", 12)
            for i in range(2, 2 + len(month_keys)):
                ws_r.set_column(i, i, 10)
            ws_r.set_column(2 + len(month_keys), 2 + len(month_keys), 10)
            ws_r.set_column(3 + len(month_keys), 3 + len(month_keys), 14)

            for r, row in enumerate(data["resourcing_plan"], start=2):
                zfmt = fmt_z1 if r % 2 else fmt_z2
                ws_r.write(r-1, 0, row["Resources"], zfmt)
                ws_r.write_number(r-1, 1, row.get("Rate/month", 2000.0), fmt_money)
                for j, m in enumerate(month_keys, start=2):
                    ws_r.write_number(r-1, j, row.get(m, 0.0), fmt_num)

            last_r = len(data["resourcing_plan"]) + 1

            # Table
            ws_r.add_table(
                f"A1:{xl_col_to_name(len(res_headers)-1)}{last_r}",
                {
                    "name": "ResourcesTable",
                    "columns": [
                        {"header": h} if h not in ("Efforts", "Cost") else (
                            {
                                "header": "Efforts",
                                "formula": "+".join(f"[@[{m}]]" for m in month_keys)
                            } if h == "Efforts" else
                            {
                                "header": "Cost",
                                "formula": "=[@Efforts]*[@[Rate/month]]"
                            }
                        )
                        for h in res_headers
                    ],
                    "style": "Table Style Medium 2",
                    "autofilter": True,
                    "total_row": True
                }
            )

            # Formulas
            efforts_col = 2 + len(month_keys)
            cost_col = 3 + len(month_keys)
            efforts_letter = xl_col_to_name(efforts_col)
            cost_letter = xl_col_to_name(cost_col)

            for r in range(2, last_r+1):
                month_cols = [xl_col_to_name(j) for j in range(2, 2+len(month_keys))]
                sum_expr = "+".join([f"{c}{r}" for c in month_cols])
                ws_r.write_formula(r-1, efforts_col, f"={sum_expr}", fmt_num)
                ws_r.write_formula(r-1, cost_col, f"=B{r}*{efforts_letter}{r}", fmt_money)

            # Totals
            for c in range(len(res_headers)):
                if c == 0:
                    ws_r.write(last_r, c, "Total", fmt_total)
                else:
                    ws_r.write_blank(last_r, c, None, fmt_total)
            ws_r.write_formula(
                last_r, efforts_col,
                f"=SUBTOTAL(109,{efforts_letter}2:{efforts_letter}{last_r})",
                fmt_total
            )
            ws_r.write_formula(
                last_r, cost_col,
                f"=SUBTOTAL(109,{cost_letter}2:{cost_letter}{last_r})",
                fmt_total
            )

            # Pie chart
            pie = wb.add_chart({"type": "pie"})
            pie.add_series({
                "categories": f"='Resources Plan'!$A$2:$A${last_r}",
                "values": f"='Resources Plan'!${cost_letter}$2:${cost_letter}${last_r}",
                "data_labels": {"percentage": True, "value": True, "category": True}
            })
            pie.set_title({"name": "Cost by Role"})
            ws_r.insert_chart("M1", pie, {"x_scale": 1.5, "y_scale": 1.5})

        wb.close()
        buf.seek(0)
        return buf

    except Exception as e:
        import traceback
        out = io.BytesIO()
        wb = xlsxwriter.Workbook(out)
        ws = wb.add_worksheet("Error")
        ws.write(0, 0, "Error generating Excel")
        ws.write(1, 0, str(e))
        ws.write(2, 0, traceback.format_exc())
        wb.close()
        out.seek(0)
        return out

# ---------- -------PDF ------------------
def generate_pdf(scope: Dict[str, Any]) -> io.BytesIO:
    data = scope or {}
    buf = io.BytesIO()
    W, H = landscape(A4)
    doc = SimpleDocTemplate(
        buf, pagesize=(W * 1.2, H * 2),
        leftMargin=1 * cm, rightMargin=1 * cm,
        topMargin=1 * cm, bottomMargin=1 * cm
    )

    styles = getSampleStyleSheet()
    wrap = styles["Normal"]
    wrap.fontSize = 7
    wrap.leading = 9
    elems = []

    # -------- Title --------
    title_style = ParagraphStyle(
        name="CenterHeading", fontSize=18, leading=22, alignment=TA_CENTER,
        textColor=colors.HexColor("#333366"), spaceAfter=12, spaceBefore=12
    )
    project_name = data.get("overview", {}).get("Project Name", "Untitled Project")
    elems.append(Paragraph(project_name, title_style))

    # -------- Overview --------
    ov = data.get("overview", {})
    if ov:
        ov_rows = [["Field", "Value"]] + [[k, str(v)] for k, v in ov.items()]
        tbl = Table(ov_rows, colWidths=[120, 700], repeatRows=1)
        ts_ov = TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(THEME["header_bg"])),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ])
        for i in range(1, len(ov_rows)):
            ts_ov.add(
                "BACKGROUND", (0, i), (-1, i),
                colors.HexColor(THEME["zebra1" if i % 2 else "zebra2"])
            )
        tbl.setStyle(ts_ov)
        tbl.hAlign = "LEFT"
        elems.append(Paragraph("<b>Project Overview</b>", styles["Heading2"]))
        elems.append(tbl)
        elems.append(Spacer(1, 0.4 * cm))

    # -------- Activities --------
    activities = data.get("activities", [])
    if activities:
        headers = ["ID", "Story", "Activities", "Description", "Owner",
                   "Depends on", "Start", "End", "Effort"]
        rows = [headers]
        parsed = []
        for a in activities:
            try:
                s = datetime.fromisoformat(a["Start Date"])
                e = datetime.fromisoformat(a["End Date"])
                parsed.append((a, s, e))
            except Exception:
                pass
            rows.append([
                a.get("ID", ""),
                Paragraph(a.get("Story", ""), wrap),
                Paragraph(a.get("Activities", ""), wrap),
                Paragraph(a.get("Description", ""), wrap),
                Paragraph(a.get("Owner", ""), wrap),
                Paragraph(a.get("Depends on", ""), wrap),
                a.get("Start Date", ""),
                a.get("End Date", ""),
                a.get("Effort Months", "")
            ])

        t = Table(rows, repeatRows=1,
                  colWidths=[25, 90, 90, 120, 70, 100, 60, 60, 40])
        ts = TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(THEME["header_bg"])),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ])
        for i in range(1, len(rows)):
            ts.add("BACKGROUND", (0, i), (-1, i),
                   colors.HexColor(THEME["zebra1" if i % 2 else "zebra2"]))
        t.setStyle(ts)
        elems.append(Paragraph("<b>Activities Breakdown</b>", styles["Heading2"]))
        elems.append(t)
        elems.append(Spacer(1, 0.4 * cm))

        # ----- Gantt chart -----
        if parsed:
            parsed.sort(key=lambda x: x[1])
            batches = [parsed[i:i + 20] for i in range(0, len(parsed), 20)]
            for bi, batch in enumerate(batches, start=1):
                min_s = min(s for _, s, _ in batch)
                max_e = max(e for _, _, e in batch)
                total_days = max(1, (max_e - min_s).days)
                px_per_day = 620.0 / total_days
                d = Drawing(780, (len(batch) * 20) + 80)
                # Month grid
                cur = datetime(min_s.year, min_s.month, 1)
                while cur <= max_e:
                    x = 80 + (cur - min_s).days * px_per_day
                    d.add(Rect(x, 30, 0.5, len(batch) * 20 + 30,
                               fillColor=colors.lightgrey, strokeColor=colors.lightgrey))
                    d.add(String(x+2, 10, cur.strftime("%b %Y"),
                                 fontSize=6, fillColor=colors.grey))
                    cur = datetime(cur.year + (1 if cur.month == 12 else 0),
                                   1 if cur.month == 12 else cur.month+1, 1)
                # Bars
                for i, (a, s, e) in enumerate(batch):
                    y = 50 + i * 20
                    x = 80 + (s - min_s).days * px_per_day
                    w = max(1, (e - s).days) * px_per_day
                    label = (a["Activities"] or a["Story"] or "")[:35]
                    d.add(Rect(x, y, w, 10, fillColor=colors.HexColor("#4D96FF")))
                    d.add(String(x+w+4, y+2, label, fontSize=6))
                elems.append(Paragraph("<b>Project Timeline</b>", styles["Heading2"]))
                elems.append(d)
                elems.append(Spacer(1, 0.3 * cm))
                if bi < len(batches):
                    elems.append(PageBreak())

    # -------- Resourcing Plan --------
    plan = data.get("resourcing_plan", [])
    if plan and isinstance(plan[0], dict):
        mkeys = [k for k in plan[0].keys() if len(k.split()) == 2]
    else:
        mkeys = []

    if plan:
        merged = {}
        for r in plan:
            rk = r["Resources"].lower()
            eff = float(r.get("Efforts", 0))
            cost = float(r.get("Cost", eff * r.get("Rate/month", 2000)))
            if rk not in merged:
                merged[rk] = {
                    "Resources": r["Resources"], "Efforts": eff,
                    "Rate/month": r["Rate/month"], "Cost": cost,
                    "months": [float(r.get(m, 0)) for m in mkeys]
                }
            else:
                m = merged[rk]
                m["Efforts"] += eff
                m["Cost"] += cost
                m["months"] = [
                    x+y for x, y in zip(m["months"], [float(r.get(m, 0)) for m in mkeys])
                ]

        merged_res = sorted(merged.values(), key=lambda x: x["Cost"], reverse=True)
        rows = [["ID", "Resources", "Rate/month"] + mkeys + ["Efforts", "Cost"]]
        tot_eff = tot_cost = 0
        pie_labels, pie_vals = [], []

        for i, r in enumerate(merged_res, start=1):
            tot_eff += r["Efforts"]; tot_cost += r["Cost"]
            pie_labels.append(r["Resources"]); pie_vals.append(r["Cost"])
            rows.append([
                i, Paragraph(r["Resources"], wrap), f"${r['Rate/month']:,.2f}",
                *[int(v) for v in r["months"]], r["Efforts"], f"${r['Cost']:,.2f}"
            ])
        rows.append(["Total", "", ""] + [""]*len(mkeys) +
                    [tot_eff, f"${tot_cost:,.2f}"])

        t2 = Table(rows, repeatRows=1,
                   colWidths=[30, 120, 70] + [60]*len(mkeys) + [50, 65])
        ts2 = TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(THEME["header_bg"])),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("BACKGROUND", (0, len(rows)-1), (-1, len(rows)-1),
             colors.HexColor(THEME["total_bg"]))
        ])
        for i in range(1, len(rows)-1):
            ts2.add("BACKGROUND", (0, i), (-1, i),
                    colors.HexColor(THEME["zebra1" if i % 2 else "zebra2"]))
        t2.setStyle(ts2)
        elems.append(Paragraph("<b>Resourcing Plan</b>", styles["Heading2"]))
        elems.append(t2)
        elems.append(Spacer(1, 0.4*cm))

        # Pie chart
        if pie_labels:
            d2 = Drawing(400, 250)
            pie = Pie()
            pie.x, pie.y = 100, 20
            pie.width, pie.height = 200, 200
            pie.data = pie_vals
            pie.labels = pie_labels
            pal = THEME["palette"]
            for i in range(len(pie.labels)):
                pie.slices[i].fillColor = colors.HexColor(pal[i % len(pal)])
            d2.add(pie)
            elems.append(Paragraph("<b>Cost Projection</b>", styles["Heading2"]))
            elems.append(d2)

    # -------- Build PDF --------
    doc.build(elems)
    buf.seek(0)
    return buf
