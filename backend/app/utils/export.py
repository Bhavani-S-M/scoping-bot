# app/utils/export.py
from __future__ import annotations
import io, json
from datetime import datetime, timezone, timedelta
from typing import Any, Dict
from reportlab.platypus import Image as RLImage
import xlsxwriter
from app.utils import azure_blob
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Table, TableStyle,
    Spacer, PageBreak, LongTable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.graphics.charts.piecharts import Pie
from reportlab.lib.enums import TA_CENTER

# Theme 
THEME = {
    "header_bg": "#BDD7EE",
    "zebra1": "#FFFFFF",
    "zebra2": "#E1E9EE",
    "total_bg": "#C6E0B4",
    "palette": ["#8DA6D7", "#E2DBBB", "#97BAEB", "#F28282", "#B9E7EB", "#E0C0A8"]
}

# Default Role rate
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

# JSON Export
def generate_json_data(scope: Dict[str, Any]) -> Dict[str, Any]:
    return scope

# Excel Export
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
            "ID", "Activities", "Description", "Owner",
            "Resources", "Start Date", "End Date", "Effort (months)", "DurationTemp"
        ]
        ws_a.write_row("A1", headers, fmt_th)

        ws_a.set_column("A:A", 5)
        ws_a.set_column("B:B", 25) 
        ws_a.set_column("C:D", 30)  
        ws_a.set_column("E:E", 20)  
        ws_a.set_column("F:I", 15)   

        starts, ends = [], []
        for r, a in enumerate(data.get("activities", []), start=2):
            zfmt = fmt_z1 if r % 2 else fmt_z2
            ws_a.write(r-1, 0, a.get("ID"), zfmt)
            ws_a.write(r-1, 1, a.get("Activities"), zfmt)
            ws_a.write(r-1, 2, a.get("Description"), zfmt)
            ws_a.write(r-1, 3, a.get("Owner"), zfmt)
            ws_a.write(r-1, 4, a.get("Resources"), zfmt)
            try:
                s = datetime.fromisoformat(a["Start Date"])
                ws_a.write_datetime(r-1, 5, s, fmt_date)
                starts.append(s)
            except:
                ws_a.write_blank(r-1, 5, None, fmt_date)
            try:
                e = datetime.fromisoformat(a["End Date"])
                ws_a.write_datetime(r-1, 6, e, fmt_date)
                ends.append(e)
            except:
                ws_a.write_blank(r-1, 6, None, fmt_date)

        last_a = len(data.get("activities", [])) + 1

        # Column Formulas
        if data.get("activities"):
            ws_a.add_table(
                f"A1:I{last_a}",   # Now 9 columns instead of 10
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

            # ------- Gantt chart --------
            if starts and ends:
                gantt = wb.add_chart({"type": "bar", "subtype": "stacked"})
                gantt.add_series({
                    "name": "Start",
                    "categories": f"='Activities'!$B$2:$B${last_a}",  # Activities col
                    "values": f"='Activities'!$F$2:$F${last_a}",      # Start Date col
                    "fill": {"none": True},
                    "border": {"none": True}
                })
                gantt.add_series({
                    "name": "Duration",
                    "categories": f"='Activities'!$B$2:$B${last_a}",  # Activities col
                    "values": f"='Activities'!$I$2:$I${last_a}",      # DurationTemp col
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

                ws_a.insert_chart("K1", gantt, {"x_scale": 2.2, "y_scale": 1.6})


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
# PDF EXPORT
async def generate_pdf(scope: Dict[str, Any]) -> io.BytesIO:
    data = scope or {}
    buf = io.BytesIO()
    W, H = landscape(A4)
    doc = SimpleDocTemplate(
        buf, pagesize=(W * 1.1, H * 2),
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

    # -------- Architecture Diagram --------
    arch_path = data.get("architecture_diagram")
    if arch_path:
        try:
            # Download image bytes from blob
            img_bytes = await azure_blob.download_bytes(arch_path)
            img_buf = io.BytesIO(img_bytes)

            # Section header
            elems.append(Paragraph("<b>System Architecture</b>", styles["Heading2"]))

            # ---- Improved image rendering ----
            img = RLImage(img_buf)

            # Dynamically scale image width
            max_width = 780  # fits within your current A4 landscape scaling
            aspect = img.imageHeight / float(img.imageWidth)
            new_height = max_width * aspect

            img.drawWidth = max_width
            img.drawHeight = new_height

            # Left align cleanly using Table (ReportLab trick)
            img_table = Table([[img]], colWidths=[max_width], hAlign="LEFT")
            img_table.setStyle(TableStyle([
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]))

            elems.append(img_table)
            elems.append(Spacer(1, 0.6 * cm))

        except Exception as e:
            print(f"⚠️ Failed to embed architecture diagram: {e}")

    # -------- Overview --------
    ov = data.get("overview", {})
    if ov:
        ov_rows = [["Field", "Value"]] + [[k, str(v)] for k, v in ov.items()]
        tbl = Table(ov_rows, colWidths=[110, 700], repeatRows=1)
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
        elems.append(Spacer(1, 0.6 * cm))

    # -------- Activities --------
    activities = data.get("activities", [])
    if activities:
        headers = [
            "ID", "Activities", "Description", "Owner",
            "Resources", "Start Date", "End Date", "Effort Months"
        ]
        rows = [headers]
        parsed = []
        for idx, a in enumerate(activities, start=1):
            try:
                s = datetime.fromisoformat(a["Start Date"])
                e = datetime.fromisoformat(a["End Date"])
                parsed.append((a, s, e))
            except Exception:
                pass
            rows.append([
                idx,  # auto incremental ID
                Paragraph(a.get("Activities", ""), wrap),
                Paragraph(a.get("Description", ""), wrap),
                Paragraph(a.get("Owner", ""), wrap),
                Paragraph(a.get("Resources", ""), wrap),
                a.get("Start Date", ""),
                a.get("End Date", ""),
                a.get("Effort Months", "")
            ])

        t = Table(rows, repeatRows=1,
                  colWidths=[25, 150, 200, 100, 120, 70, 70, 90])
        ts = TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(THEME["header_bg"])),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ])
        for i in range(1, len(rows)):
            ts.add("BACKGROUND", (0, i), (-1, i),
                   colors.HexColor(THEME["zebra1" if i % 2 else "zebra2"]))
        t.setStyle(ts)
        t.hAlign = "LEFT"
        elems.append(Paragraph("<b>Activities Breakdown</b>", styles["Heading2"]))
        elems.append(t)
        elems.append(Spacer(1, 0.6 * cm))

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
                    label = (a["Activities"] or "")[:35]
                    d.add(Rect(x, y, w, 10, fillColor=colors.HexColor("#4D96FF")))
                    d.add(String(x+w+4, y+2, label, fontSize=6))
                elems.append(Paragraph("<b>Project Timeline</b>", styles["Heading2"]))
                elems.append(d)
                elems.append(Spacer(1, 0.6 * cm))
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

        # Collect rows
        tot_eff = tot_cost = 0
        pie_labels, pie_vals = [], []
        base_rows = []
        for idx, r in enumerate(merged_res, start=1):  # <-- auto incremental ID
            tot_eff += r["Efforts"]; tot_cost += r["Cost"]
            pie_labels.append(r["Resources"]); pie_vals.append(r["Cost"])
            base_rows.append([
                idx,
                Paragraph(r["Resources"], wrap),
                f"${r['Rate/month']:,.2f}",
                *[f"{v:.2f}" for v in r["months"]], 
                f"{r['Efforts']:.2f}",
                f"${r['Cost']:,.2f}"
            ])

        base_rows.append(
            ["Total", "", ""] + [""]*len(mkeys) +
            [f"{tot_eff:.2f}", f"${tot_cost:,.2f}"]
        )

        # ---- Split into chunks if too wide ----
        MAX_MONTH_COLS = 10
        for start in range(0, len(mkeys), MAX_MONTH_COLS):
            month_chunk = mkeys[start:start+MAX_MONTH_COLS]

            sub_rows = []
            for row in base_rows:
                fixed = row[:3]
                months = row[3:3+len(mkeys)]
                end = row[-2:]
                sub_months = months[start:start+MAX_MONTH_COLS]
                sub_rows.append(fixed + sub_months + end)

            header = ["ID", "Resources", "Rate/month"] + month_chunk + ["Efforts", "Cost"]
            sub_rows.insert(0, header)

            t2 = LongTable(sub_rows, repeatRows=1,
                        colWidths=[30, 90, 70] + [55]*len(month_chunk) + [50, 65])
            ts2 = TableStyle([
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(THEME["header_bg"])),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("BACKGROUND", (0, len(sub_rows)-1), (-1, len(sub_rows)-1),
                colors.HexColor(THEME["total_bg"]))
            ])
            for i in range(1, len(sub_rows)-1):
                ts2.add("BACKGROUND", (0, i), (-1, i),
                        colors.HexColor(THEME["zebra1" if i % 2 else "zebra2"]))
            t2.setStyle(ts2)
            t2.hAlign = "LEFT"

            elems.append(Paragraph("<b>Resourcing Plan</b>", styles["Heading2"]))
            elems.append(t2)
            elems.append(Spacer(1, 0.6*cm))

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

    # Build PDF
    doc.build(elems)
    buf.seek(0)
    return buf
