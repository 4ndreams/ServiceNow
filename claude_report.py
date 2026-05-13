import os
import json
import anthropic


def _leer_chartjs() -> str:
    ruta = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chart.min.js")
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"WARNING: No se pudo leer chart.min.js: {e}")
        return ""


def _generar_textos(datos: dict) -> dict:
    """Claude solo genera los textos interpretativos, nada más."""
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    aa = datos["anio_actual"]
    ap = datos["anio_anterior"]
    mt = datos["mejora_2025_2026"]
    at = datos["automatizacion"]
    rt = datos["resumen_tiempos"]

    prompt = f"""Eres analista de datos para AFP Capital, equipo ServiceNow.
Genera SOLO un JSON con textos interpretativos cortos para un dashboard de tickets.
Sin explicaciones, sin markdown, solo el JSON.

DATOS:
- {ap}: {datos['ritm_por_anio'].get(ap,0)} RITM, SLA prom {datos['sla_prom_por_anio'].get(ap,'N/A')} hrs
- {aa}: {datos['ritm_por_anio'].get(aa,0)} RITM, SLA prom {datos['sla_prom_por_anio'].get(aa,'N/A')} hrs
- Mejora SLA: {mt.get('pct_mejora',0)*100:.1f}% vs baseline 30hrs
- HH ahorradas: {mt.get('hh_ahorradas_total',0):.0f} hrs
- Días-persona ahorrados: {mt.get('dias_persona',0):.1f}
- SLA aprobación {ap}: {datos['sla_aprob_prom_por_anio'].get(ap,'N/A')} hrs
- SLA aprobación {aa}: {datos['sla_aprob_prom_por_anio'].get(aa,'N/A')} hrs
- Pre-automatización (Ene-Mar {aa}): {at['pre']['total']} tickets, SLA prom {at['pre']['sla_prom']} hrs
- Post-automatización (Abr-May {aa}): {at['post']['total']} tickets, SLA prom {at['post']['sla_prom']} hrs
- Mejora automatización: {at.get('pct_mejora',0)*100:.1f}%

Devuelve SOLO este JSON exacto con los textos (máximo 2 oraciones cada uno):
{{
  "resumen_ejecutivo": "texto de 1-2 oraciones resumiendo el rendimiento general",
  "tendencia_sla": "texto sobre la tendencia del SLA mensual",
  "impacto_mejora": "texto sobre el impacto cuantificado de la mejora",
  "automatizacion": "texto sobre el impacto de la automatización en Cuentas de Servicio Cloud",
  "recomendacion": "texto con una recomendación concreta basada en los datos"
}}"""

    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}]
    )

    texto = msg.content[0].text.strip()
    if texto.startswith("```"):
        texto = texto.split("\n", 1)[1].rsplit("```", 1)[0]

    try:
        return json.loads(texto)
    except Exception:
        return {
            "resumen_ejecutivo": f"En {aa} se procesaron {datos['ritm_por_anio'].get(aa,0)} tickets con un SLA promedio de {datos['sla_prom_por_anio'].get(aa,'N/A')} horas hábiles.",
            "tendencia_sla": "Ver gráfico de tendencia mensual para el detalle por período.",
            "impacto_mejora": f"Se han ahorrado {mt.get('hh_ahorradas_total',0):.0f} horas hábiles equivalentes a {mt.get('dias_persona',0):.1f} días-persona.",
            "automatizacion": f"La automatización redujo el SLA de {at['pre']['sla_prom']} a {at['post']['sla_prom']} horas hábiles promedio.",
            "recomendacion": "Continuar monitoreando los grupos con mayor SLA para identificar oportunidades de mejora."
        }


def _esc(s):
    """Escapa un string para usarlo seguro en JavaScript."""
    if s is None:
        return ""
    return str(s).replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ").replace("\r", "")


def generar_html(datos: dict) -> str:
    print("📦 Cargando Chart.js...")
    chartjs = _leer_chartjs()

    print("🤖 Generando textos con Claude...")
    textos = _generar_textos(datos)
    print("✅ Textos generados")

    aa = datos["anio_actual"]
    ap = datos["anio_anterior"]
    rm = datos["resumen_mes"]
    mt = datos["mejora_2025_2026"]
    at = datos["automatizacion"]
    rt = datos["resumen_tiempos"]

    # Meses ordenados
    meses_ap = sorted([m for m in rm if m.startswith(ap)])
    meses_aa = sorted([m for m in rm if m.startswith(aa)])
    labels_mes = ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic']

    # Datos volumetría y SLA mensual
    vol_ap  = [rm.get(m, {}).get("vol", 0)  for m in meses_ap]
    vol_aa  = [rm.get(m, {}).get("vol", 0)  for m in meses_aa]
    sla_ap  = [rm.get(m, {}).get("sla")     for m in meses_ap]
    sla_aa  = [rm.get(m, {}).get("sla")     for m in meses_aa]

    # Padding para que ambos tengan 12 meses
    def pad12(lst, fill="null"):
        return lst + [None] * (12 - len(lst))

    vol_ap12 = pad12(vol_ap, 0)
    vol_aa12 = pad12(vol_aa, 0)
    sla_ap12 = pad12(sla_ap)
    sla_aa12 = pad12(sla_aa)

    def js_arr(lst):
        return "[" + ",".join("null" if v is None else str(v) for v in lst) + "]"

    # Top 10 cuellos de botella año actual
    top10 = datos["top_cuellos_anio_actual"][:10]
    top10_labels = [_esc(r["numero"]) for r in top10]
    top10_data   = [r["sla"] for r in top10]
    top10_colors = ["'#dc2626'" if v > 200 else "'#f59e0b'" if v > 100 else "'#10b981'" for v in top10_data]

    # SLA aprobación vs tarea por año
    sla_t_ap = datos["sla_tarea_prom_por_anio"].get(ap) or 0
    sla_t_aa = datos["sla_tarea_prom_por_anio"].get(aa) or 0
    sla_a_ap = datos["sla_aprob_prom_por_anio"].get(ap) or 0
    sla_a_aa = datos["sla_aprob_prom_por_anio"].get(aa) or 0

    # Cumplimiento SLA
    cump = datos["cumplimiento_grupo"]
    cump_labels = [_esc(c["grupo"]) for c in cump]
    cump_data   = [round(c["pct"]*100, 1) for c in cump]

    # Análisis por grupo
    grupos = datos["analisis_grupo"]
    grupo_labels = [_esc(g["grupo"]) for g in grupos]
    grupo_data   = [g["sla_prom"] or 0 for g in grupos]

    # Aprobadores
    aprobadores = sorted(datos["analisis_aprobadores"], key=lambda x: x["sla_prom"] or 0, reverse=True)[:10]
    aprob_labels = [_esc(a["aprobador"]) for a in aprobadores]
    aprob_data   = [a["sla_prom"] or 0 for a in aprobadores]

    # Formularios
    formularios = datos["analisis_elemento"]
    form_labels  = [_esc(f["elemento"]) for f in formularios]
    form_pct_a   = [round((f["pct_aprob"] or 0)*100, 1) for f in formularios]
    form_pct_p   = [round((f["pct_post"] or 0)*100, 1) for f in formularios]

    # Pre/post automatización
    sla_pre  = at["pre"]["sla_prom"] or 0
    sla_post = at["post"]["sla_prom"] or 0

    # Tabla top 20 por año
    def tabla_rows(lista):
        rows = ""
        for i, r in enumerate(lista[:20]):
            cuello = r.get("cuello","")
            cuello_pill = ""
            if cuello == "Tarea":
                cuello_pill = "<span class='pill pill-r'>🔧 Tarea</span>"
            elif cuello == "Aprobacion":
                cuello_pill = "<span class='pill pill-y'>⚠ Aprob.</span>"
            else:
                cuello_pill = "<span class='pill pill-g'>—</span>"

            sla_v = r.get("sla") or 0
            sla_cls = "sla-h" if sla_v > 100 else "sla-m" if sla_v > 50 else "sla-ok"
            rows += f"""<tr>
              <td>{i+1}</td>
              <td class='mono'>{_esc(r.get('numero',''))}</td>
              <td>{_esc(r.get('elemento',''))}</td>
              <td>{_esc(r.get('etapa',''))}</td>
              <td>{_esc(r.get('solicitante',''))}</td>
              <td>{_esc(r.get('mes',''))}</td>
              <td class='{sla_cls}'>{sla_v:.0f} hrs</td>
              <td>{r.get('sla_tarea') and f"{r['sla_tarea']:.0f} hrs" or '—'}</td>
              <td>{r.get('sla_aprob') and f"{r['sla_aprob']:.0f} hrs" or '—'}</td>
              <td>{_esc(r.get('grupo',''))}</td>
              <td>{cuello_pill}</td>
            </tr>"""
        return rows

    rows_aa = tabla_rows(datos["top_cuellos_anio_actual"])
    rows_ap = tabla_rows(datos["top_cuellos_anio_anterior"])

    # Tarjetas por formulario
    def form_cards():
        cards = ""
        for form, anios in datos["por_form_anio"].items():
            info_aa = anios.get(aa, {})
            info_ap = anios.get(ap, {})
            vol  = info_aa.get("vol", 0)
            sla  = info_aa.get("sla")
            sla_p = info_ap.get("sla")
            delta = round(sla - sla_p, 1) if sla and sla_p else None
            delta_html = ""
            if delta is not None:
                cls = "delta-r" if delta > 0 else "delta-g"
                delta_html = f"<span class='{cls}'>{'+' if delta > 0 else ''}{delta} hrs vs {ap}</span>"

            top3 = info_aa.get("top3", [])
            bt_rows = ""
            for b in top3:
                c = b.get("cuello","")
                cp = "<span class='pill pill-r'>🔧 Tarea</span>" if c == "Tarea" else "<span class='pill pill-y'>⚠ Aprob.</span>" if c == "Aprobacion" else "—"
                sla_fmt = f"{b['sla']:.0f}" if b.get('sla') else '—'
                bt_rows += f"<tr><td class='mono'>{_esc(b.get('ritm',''))}</td><td>{sla_fmt} hrs</td><td>{_esc(b.get('grupo',''))}</td><td>{cp}</td></tr>"

            cards += f"""
            <div class='form-card'>
              <div class='form-head'>
                <div>
                  <div class='form-name'>{_esc(form)}</div>
                  <div class='form-sla'>SLA prom: <strong>{f"{sla:.1f} hrs" if sla else '—'}</strong> {delta_html}</div>
                </div>
                <div class='form-vol'>{vol}<div class='form-vol-lbl'>RITM {aa}</div></div>
              </div>
              <div class='form-body'>
                <div class='bt-title'>Cuellos de botella {aa}</div>
                <table class='bt-table'>
                  <thead><tr><th>RITM</th><th>SLA</th><th>Grupo</th><th>Cuello</th></tr></thead>
                  <tbody>{bt_rows if bt_rows else '<tr><td colspan=4 style="color:#9ca3af">Sin datos</td></tr>'}</tbody>
                </table>
              </div>
            </div>"""
        return cards

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Tickets Proyecto Workflow IT — Vista Comparativa</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Segoe UI',system-ui,sans-serif;background:#f0f2f5;color:#1a1a2e;font-size:14px}}
.hdr{{background:linear-gradient(135deg,#0c3c6e,#1a5fa8);color:#fff;padding:22px 32px}}
.hdr h1{{font-size:20px;font-weight:700}}
.hdr p{{font-size:12px;opacity:.75;margin-top:3px}}
.nav{{background:#fff;border-bottom:1px solid #e5e7eb;display:flex;overflow-x:auto;padding:0 24px}}
.tab-btn{{padding:14px 20px;font-size:13px;font-weight:500;color:#6b7280;cursor:pointer;border:none;background:none;border-bottom:3px solid transparent;white-space:nowrap}}
.tab-btn.active{{color:#0c3c6e;border-bottom-color:#0c3c6e}}
.tab-btn:hover{{color:#374151}}
.main{{padding:22px 32px;max-width:1280px;margin:0 auto}}
.tab-content{{display:none}}.tab-content.active{{display:block}}
.kpi-row{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:14px;margin-bottom:20px}}
.kpi{{background:#fff;border-radius:12px;padding:18px;border:1px solid #e5e7eb;position:relative;overflow:hidden}}
.kpi::before{{content:'';position:absolute;top:0;left:0;width:4px;height:100%;background:var(--acc,#0c3c6e)}}
.kpi .k-lbl{{font-size:11px;color:#9ca3af;font-weight:600;text-transform:uppercase;letter-spacing:.5px}}
.kpi .k-val{{font-size:26px;font-weight:700;color:#111;margin:5px 0 2px;line-height:1}}
.kpi .k-sub{{font-size:11px;color:#6b7280}}
.grid2{{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-bottom:18px}}
.grid3{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px;margin-bottom:18px}}
.card{{background:#fff;border-radius:12px;padding:20px;border:1px solid #e5e7eb;margin-bottom:18px}}
.card h3{{font-size:13px;font-weight:700;color:#111;margin-bottom:2px}}
.card .csub{{font-size:11px;color:#9ca3af;margin-bottom:14px}}
.interp{{background:#f0f7ff;border-radius:8px;padding:14px;font-size:13px;color:#374151;line-height:1.6;border-left:3px solid #0c3c6e;margin-top:12px}}
table{{width:100%;border-collapse:collapse;font-size:12px}}
th{{background:#f9fafb;text-align:left;padding:9px 10px;font-weight:600;color:#374151;border-bottom:1px solid #e5e7eb;font-size:11px;white-space:nowrap}}
td{{padding:8px 10px;border-bottom:1px solid #f3f4f6;color:#374151;vertical-align:middle}}
tr:hover td{{background:#f9fafb}}
.tw{{overflow-x:auto}}
.mono{{font-family:monospace;font-size:11px;color:#1e40af}}
.sla-h{{color:#dc2626;font-weight:700}}.sla-m{{color:#d97706;font-weight:600}}.sla-ok{{color:#059669}}
.pill{{display:inline-block;padding:2px 8px;border-radius:10px;font-size:10px;font-weight:600}}
.pill-r{{background:#fee2e2;color:#991b1b}}.pill-y{{background:#fef3c7;color:#92400e}}.pill-g{{background:#dcfce7;color:#166534}}
.ytabs{{display:flex;gap:8px;margin-bottom:12px}}
.ytab{{padding:5px 16px;border-radius:20px;font-size:12px;font-weight:600;cursor:pointer;border:1.5px solid #e5e7eb;color:#6b7280;background:#fff}}
.ytab.active{{background:#0c3c6e;color:#fff;border-color:#0c3c6e}}
.ytc{{display:none}}.ytc.active{{display:block}}
.stabs{{display:flex;gap:8px;margin-bottom:14px;flex-wrap:wrap}}
.stab{{padding:5px 14px;border-radius:16px;font-size:12px;cursor:pointer;border:1.5px solid #e5e7eb;color:#6b7280;background:#fff}}
.stab.active{{background:#1a5fa8;color:#fff;border-color:#1a5fa8}}
.stc{{display:none}}.stc.active{{display:block}}
.form-card{{background:#fff;border-radius:12px;border:1px solid #e5e7eb;overflow:hidden;margin-bottom:14px}}
.form-head{{padding:14px 18px;background:#f8fafc;border-bottom:1px solid #e5e7eb;display:flex;justify-content:space-between;align-items:center}}
.form-name{{font-size:13px;font-weight:700;color:#1e3a5f}}
.form-sla{{font-size:11px;color:#6b7280;margin-top:2px}}
.form-vol{{font-size:24px;font-weight:800;color:#0c3c6e;text-align:right}}
.form-vol-lbl{{font-size:10px;color:#9ca3af}}
.form-body{{padding:14px 18px}}
.bt-title{{font-size:10px;font-weight:700;text-transform:uppercase;color:#ef4444;letter-spacing:.5px;margin-bottom:8px}}
.bt-table{{font-size:11px}}
.delta-r{{color:#dc2626;font-size:10px;font-weight:600;margin-left:6px}}
.delta-g{{color:#059669;font-size:10px;font-weight:600;margin-left:6px}}
.big-kpi{{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:16px}}
.bk{{border-radius:12px;padding:16px;text-align:center}}
.bk-b{{background:#eef4ff;border:1px solid #bfdbfe}}
.bk-g{{background:#f0fdf4;border:1px solid #bbf7d0}}
.bk .bl{{font-size:10px;font-weight:600;text-transform:uppercase;color:#6b7280;margin-bottom:4px}}
.bk .bv{{font-size:28px;font-weight:700}}
.bk-b .bv{{color:#1d4ed8}}.bk-g .bv{{color:#15803d}}
.bk .bs{{font-size:11px;color:#6b7280;margin-top:2px}}
.imp-kpis{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:16px}}
.ik{{background:#fff;border-radius:10px;padding:14px;text-align:center;border:1px solid #e5e7eb}}
.ik .il{{font-size:10px;color:#9ca3af;text-transform:uppercase;font-weight:600}}
.ik .iv{{font-size:22px;font-weight:700;color:#0c3c6e;margin:4px 0}}
.ik .is{{font-size:11px;color:#6b7280}}
</style>
</head>
<body>

<div class="hdr">
  <h1>📋 Tickets Proyecto Workflow IT — Vista Comparativa</h1>
  <p>AFP Capital · ServiceNow · Datos al {datos['fecha_generacion']}</p>
</div>

<div class="nav">
  <button class="tab-btn active" onclick="showTab('t1',this)">📊 Resumen Ejecutivo</button>
  <button class="tab-btn" onclick="showTab('t2',this)">🗂 Vista por Formulario</button>
  <button class="tab-btn" onclick="showTab('t3',this)">📋 Detalles SLA</button>
  <button class="tab-btn" onclick="showTab('t4',this)">⏱ Análisis de Tiempos</button>
  <button class="tab-btn" onclick="showTab('t5',this)">🚀 Impacto y Mejoras</button>
</div>

<div class="main">

<!-- ═══ PESTAÑA 1: RESUMEN EJECUTIVO ═══ -->
<div id="t1" class="tab-content active">
  <div class="kpi-row">
    <div class="kpi" style="--acc:#0c3c6e"><div class="k-lbl">Total RITM {ap}</div><div class="k-val">{datos['ritm_por_anio'].get(ap,0):,}</div><div class="k-sub">Requerimientos {ap}</div></div>
    <div class="kpi" style="--acc:#10b981"><div class="k-lbl">Total RITM {aa}</div><div class="k-val">{datos['ritm_por_anio'].get(aa,0):,}</div><div class="k-sub">Ene–May {aa}</div></div>
    <div class="kpi" style="--acc:#f59e0b"><div class="k-lbl">SLA Prom {ap}</div><div class="k-val">{datos['sla_prom_por_anio'].get(ap) or '—'} <span style="font-size:14px">hrs</span></div><div class="k-sub">Horas hábiles</div></div>
    <div class="kpi" style="--acc:#8b5cf6"><div class="k-lbl">SLA Prom {aa}</div><div class="k-val">{datos['sla_prom_por_anio'].get(aa) or '—'} <span style="font-size:14px">hrs</span></div><div class="k-sub">Horas hábiles</div></div>
    <div class="kpi" style="--acc:#ec4899"><div class="k-lbl">SLA Tarea {aa}</div><div class="k-val">{datos['sla_tarea_prom_por_anio'].get(aa) or '—'} <span style="font-size:14px">hrs</span></div><div class="k-sub">Tiempo ejecución</div></div>
    <div class="kpi" style="--acc:#06b6d4"><div class="k-lbl">SLA Aprob {aa}</div><div class="k-val">{datos['sla_aprob_prom_por_anio'].get(aa) or '—'} <span style="font-size:14px">hrs</span></div><div class="k-sub">Tiempo aprobación</div></div>
  </div>

  <div class="grid2">
    <div class="card"><h3>Volumetría mensual — {ap} vs {aa}</h3><div class="csub">RITM por mes</div><canvas id="cVol" height="220"></canvas></div>
    <div class="card"><h3>SLA promedio mensual — {ap} vs {aa}</h3><div class="csub">Horas hábiles por mes (solo tickets cerrados)</div><canvas id="cSla" height="220"></canvas></div>
  </div>

  <div class="card">
    <h3>Tiempo de aprobación vs tiempo de tarea</h3>
    <div class="csub">Comparativa promedios anuales en horas hábiles</div>
    <div class="grid2" style="margin-bottom:14px">
      <div style="background:#f8fafc;border-radius:8px;padding:14px">
        <div style="font-size:12px;font-weight:700;color:#374151;margin-bottom:8px">{ap}</div>
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px">
          <div style="background:#eef4ff;border-radius:8px;padding:10px;text-align:center"><div style="font-size:10px;color:#1e40af;font-weight:600">SLA RITM</div><div style="font-size:20px;font-weight:700;color:#1d4ed8">{datos['sla_prom_por_anio'].get(ap) or '—'}</div></div>
          <div style="background:#f0fdf4;border-radius:8px;padding:10px;text-align:center"><div style="font-size:10px;color:#166534;font-weight:600">TAREA</div><div style="font-size:20px;font-weight:700;color:#15803d">{datos['sla_tarea_prom_por_anio'].get(ap) or '—'}</div></div>
          <div style="background:#fff7ed;border-radius:8px;padding:10px;text-align:center"><div style="font-size:10px;color:#9a3412;font-weight:600">APROB.</div><div style="font-size:20px;font-weight:700;color:#c2410c">{datos['sla_aprob_prom_por_anio'].get(ap) or '—'}</div></div>
        </div>
      </div>
      <div style="background:#f8fafc;border-radius:8px;padding:14px">
        <div style="font-size:12px;font-weight:700;color:#374151;margin-bottom:8px">{aa}</div>
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px">
          <div style="background:#eef4ff;border-radius:8px;padding:10px;text-align:center"><div style="font-size:10px;color:#1e40af;font-weight:600">SLA RITM</div><div style="font-size:20px;font-weight:700;color:#1d4ed8">{datos['sla_prom_por_anio'].get(aa) or '—'}</div></div>
          <div style="background:#f0fdf4;border-radius:8px;padding:10px;text-align:center"><div style="font-size:10px;color:#166534;font-weight:600">TAREA</div><div style="font-size:20px;font-weight:700;color:#15803d">{datos['sla_tarea_prom_por_anio'].get(aa) or '—'}</div></div>
          <div style="background:#fff7ed;border-radius:8px;padding:10px;text-align:center"><div style="font-size:10px;color:#9a3412;font-weight:600">APROB.</div><div style="font-size:20px;font-weight:700;color:#c2410c">{datos['sla_aprob_prom_por_anio'].get(aa) or '—'}</div></div>
        </div>
      </div>
    </div>
    <canvas id="cAprob" height="200"></canvas>
    <div class="interp">{textos.get('resumen_ejecutivo','')}</div>
  </div>
</div>

<!-- ═══ PESTAÑA 2: VISTA POR FORMULARIO ═══ -->
<div id="t2" class="tab-content">
  {form_cards()}
</div>

<!-- ═══ PESTAÑA 3: DETALLES SLA ═══ -->
<div id="t3" class="tab-content">
  <div class="card">
    <h3>Top 10 tickets por SLA — {aa}</h3>
    <div class="csub">Rojo &gt;200 hrs · naranja 100–200 hrs · verde &lt;100 hrs</div>
    <canvas id="cTop10" height="320"></canvas>
  </div>
  <div class="card">
    <h3>Detalle tickets</h3>
    <div class="ytabs">
      <div class="ytab active" onclick="showY('y{ap}',this)">{ap}</div>
      <div class="ytab" onclick="showY('y{aa}',this)">{aa}</div>
    </div>
    <div id="y{ap}" class="ytc active">
      <div class="tw"><table>
        <thead><tr><th>#</th><th>RITM</th><th>Formulario</th><th>Etapa</th><th>Solicitante</th><th>Mes</th><th>SLA Total</th><th>SLA Tarea</th><th>SLA Aprob</th><th>Grupo</th><th>Cuello</th></tr></thead>
        <tbody>{rows_ap}</tbody>
      </table></div>
    </div>
    <div id="y{aa}" class="ytc">
      <div class="tw"><table>
        <thead><tr><th>#</th><th>RITM</th><th>Formulario</th><th>Etapa</th><th>Solicitante</th><th>Mes</th><th>SLA Total</th><th>SLA Tarea</th><th>SLA Aprob</th><th>Grupo</th><th>Cuello</th></tr></thead>
        <tbody>{rows_aa}</tbody>
      </table></div>
    </div>
  </div>
</div>

<!-- ═══ PESTAÑA 4: ANÁLISIS DE TIEMPOS ═══ -->
<div id="t4" class="tab-content">
  <div class="stabs">
    <div class="stab active" onclick="showS('s4a',this)">Por Grupo Resolutor</div>
    <div class="stab" onclick="showS('s4b',this)">Por Formulario</div>
    <div class="stab" onclick="showS('s4c',this)">Cumplimiento SLA</div>
    <div class="stab" onclick="showS('s4d',this)">Aprobadores</div>
  </div>
  <div id="s4a" class="stc active">
    <div class="card"><h3>Tiempo promedio por grupo resolutor</h3><div class="csub">Horas hábiles promedio · solo tickets cerrados</div><canvas id="cGrupo" height="280"></canvas>
    <div class="tw" style="margin-top:14px"><table>
      <thead><tr><th>Grupo</th><th>Total</th><th>Cerrados</th><th>En curso</th><th>SLA prom (hrs)</th><th>SLA total (hrs)</th></tr></thead>
      <tbody>{''.join(f"<tr><td>{_esc(g['grupo'])}</td><td>{g['total']}</td><td>{g['cerrados']}</td><td>{g['en_curso']}</td><td>{g['sla_prom'] or '—'}</td><td>{g['sla_total'] or '—'}</td></tr>" for g in grupos)}</tbody>
    </table></div></div>
  </div>
  <div id="s4b" class="stc">
    <div class="card"><h3>% Tiempo aprobación vs post-aprobación por formulario</h3><div class="csub">Distribución del tiempo total del ticket</div><canvas id="cForm" height="260"></canvas>
    <div class="tw" style="margin-top:14px"><table>
      <thead><tr><th>Formulario</th><th>Total</th><th>SLA prom</th><th>Aprob prom</th><th>Post-aprob prom</th><th>% Aprob</th></tr></thead>
      <tbody>{''.join(f"<tr><td>{_esc(f['elemento'])}</td><td>{f['total']}</td><td>{f['sla_prom'] or '—'} hrs</td><td>{f['aprob_prom'] or '—'} hrs</td><td>{f['post_prom'] or '—'} hrs</td><td>{round((f['pct_aprob'] or 0)*100,1)}%</td></tr>" for f in formularios)}</tbody>
    </table></div></div>
  </div>
  <div id="s4c" class="stc">
    <div class="card"><h3>Cumplimiento SLA tareas por grupo</h3><div class="csub">% tareas completadas dentro del objetivo de horas</div>
    <div class="grid2"><canvas id="cCump" height="240"></canvas><canvas id="cCumpDona" height="240"></canvas></div>
    <div class="tw" style="margin-top:14px"><table>
      <thead><tr><th>Grupo</th><th>Total tareas</th><th>Dentro SLA</th><th>Fuera SLA</th><th>% Cumplimiento</th><th>SLA prom</th></tr></thead>
      <tbody>{''.join(f"<tr><td>{_esc(c['grupo'])}</td><td>{c['total']}</td><td>{c['dentro']}</td><td>{c['fuera']}</td><td>{round(c['pct']*100,1)}%</td><td>{c['sla_prom'] or '—'} hrs</td></tr>" for c in cump)}</tbody>
    </table></div></div>
  </div>
  <div id="s4d" class="stc">
    <div class="card"><h3>Tiempo promedio por aprobador</h3><div class="csub">Top 10 · horas hábiles promedio de aprobación</div><canvas id="cAprob2" height="280"></canvas>
    <div class="tw" style="margin-top:14px"><table>
      <thead><tr><th>Aprobador</th><th>Total</th><th>Completadas</th><th>SLA prom (hrs)</th><th>SLA total (hrs)</th></tr></thead>
      <tbody>{''.join(f"<tr><td>{_esc(a['aprobador'])}</td><td>{a['total']}</td><td>{a['completadas']}</td><td>{a['sla_prom'] or '—'}</td><td>{a['sla_total'] or '—'}</td></tr>" for a in aprobadores)}</tbody>
    </table></div></div>
  </div>
</div>

<!-- ═══ PESTAÑA 5: IMPACTO Y MEJORAS ═══ -->
<div id="t5" class="tab-content">
  <div class="big-kpi">
    <div class="bk bk-b"><div class="bl">Baseline {ap}</div><div class="bv">30.0 <span style="font-size:16px">hrs</span></div><div class="bs">Tiempo promedio base</div></div>
    <div class="bk bk-g"><div class="bl">Actual {aa}</div><div class="bv">{mt.get('actual_2026_hrs') or '—'} <span style="font-size:16px">hrs</span></div><div class="bs">{'↓ ' + str(mt.get('reduccion_hrs',0)) + ' hrs · ' + str(round((mt.get('pct_mejora',0))*100,1)) + '% mejora' if (mt.get('reduccion_hrs',0) or 0) > 0 else '↑ Sin mejora vs baseline'}</div></div>
  </div>
  <div class="imp-kpis">
    <div class="ik"><div class="il">RITM {aa}</div><div class="iv">{mt.get('total_ritm_2026',0):,}</div><div class="is">requerimientos</div></div>
    <div class="ik"><div class="il">HH ahorradas</div><div class="iv">{mt.get('hh_ahorradas_total',0):,.0f}</div><div class="is">horas hábiles</div></div>
    <div class="ik"><div class="il">Días-persona</div><div class="iv">{mt.get('dias_persona',0):.1f}</div><div class="is">días equivalentes</div></div>
    <div class="ik"><div class="il">Meses-persona</div><div class="iv">{mt.get('meses_persona',0):.1f}</div><div class="is">meses equivalentes</div></div>
    <div class="ik"><div class="il">FTE anual equiv.</div><div class="iv">{mt.get('fte_anual',0):.2f}</div><div class="is">personas equivalentes</div></div>
    <div class="ik"><div class="il">% Mejora SLA</div><div class="iv" style="color:{'#059669' if (mt.get('pct_mejora',0) or 0)>0 else '#dc2626'}">{round((mt.get('pct_mejora',0) or 0)*100,1)}%</div><div class="is">vs baseline 30 hrs</div></div>
  </div>
  <div class="grid2">
    <div class="card"><h3>SLA promedio {ap} vs {aa}</h3><div class="csub">Comparativa anual</div><canvas id="cMejora" height="200"></canvas></div>
    <div class="card"><h3>Automatización — Cuentas de Servicio Cloud</h3><div class="csub">Pre (Ene–Mar) vs Post (Abr–May) {aa}</div><canvas id="cAuto" height="200"></canvas>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:12px">
        <div style="background:#fff7ed;border-radius:8px;padding:12px;text-align:center"><div style="font-size:10px;color:#9a3412;font-weight:600">PRE-AUTO (Ene–Mar)</div><div style="font-size:22px;font-weight:700;color:#c2410c">{sla_pre:.1f} hrs</div><div style="font-size:11px;color:#6b7280">{at['pre']['total']} tickets</div></div>
        <div style="background:#f0fdf4;border-radius:8px;padding:12px;text-align:center"><div style="font-size:10px;color:#166534;font-weight:600">POST-AUTO (Abr–May)</div><div style="font-size:22px;font-weight:700;color:#15803d">{sla_post:.1f} hrs</div><div style="font-size:11px;color:#6b7280">{at['post']['total']} tickets</div></div>
      </div>
    </div>
  </div>
  <div class="card">
    <h3>Análisis de impacto</h3>
    <div class="interp" style="margin-bottom:10px">{textos.get('impacto_mejora','')}</div>
    <div class="interp" style="margin-bottom:10px">{textos.get('automatizacion','')}</div>
    <div class="interp">{textos.get('recomendacion','')}</div>
  </div>
</div>

</div><!-- /main -->

<script>{chartjs}</script>
<script>
// ── Navegación ────────────────────────────────────────────────────────────────
function showTab(id, btn) {{
  document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.getElementById(id).classList.add('active');
  btn.classList.add('active');
  setTimeout(renderCharts, 50);
}}
function showY(id, btn) {{
  var p = btn.closest('.card');
  p.querySelectorAll('.ytc').forEach(t => t.classList.remove('active'));
  p.querySelectorAll('.ytab').forEach(b => b.classList.remove('active'));
  document.getElementById(id).classList.add('active');
  btn.classList.add('active');
}}
function showS(id, btn) {{
  var p = btn.closest('.tab-content');
  p.querySelectorAll('.stc').forEach(t => t.classList.remove('active'));
  p.querySelectorAll('.stab').forEach(b => b.classList.remove('active'));
  document.getElementById(id).classList.add('active');
  btn.classList.add('active');
  setTimeout(renderCharts, 50);
}}

// ── Datos ─────────────────────────────────────────────────────────────────────
var LABELS = {json.dumps(labels_mes)};
var VOL_AP = {js_arr(vol_ap12)};
var VOL_AA = {js_arr(vol_aa12)};
var SLA_AP = {js_arr(sla_ap12)};
var SLA_AA = {js_arr(sla_aa12)};

var TOP10_LABELS = {json.dumps(top10_labels)};
var TOP10_DATA   = {json.dumps(top10_data)};
var TOP10_COLORS = [{','.join(top10_colors)}];

var GRUPO_LABELS = {json.dumps(grupo_labels)};
var GRUPO_DATA   = {json.dumps(grupo_data)};

var FORM_LABELS = {json.dumps(form_labels)};
var FORM_PCT_A  = {json.dumps(form_pct_a)};
var FORM_PCT_P  = {json.dumps(form_pct_p)};

var CUMP_LABELS = {json.dumps(cump_labels)};
var CUMP_DATA   = {json.dumps(cump_data)};

var APROB_LABELS = {json.dumps(aprob_labels)};
var APROB_DATA   = {json.dumps(aprob_data)};

var SLA_T_AP = {sla_t_ap}, SLA_T_AA = {sla_t_aa};
var SLA_A_AP = {sla_a_ap}, SLA_A_AA = {sla_a_aa};
var SLA_GLOBAL_AP = {datos['sla_prom_por_anio'].get(ap) or 0};
var SLA_GLOBAL_AA = {datos['sla_prom_por_anio'].get(aa) or 0};
var SLA_PRE = {sla_pre}, SLA_POST = {sla_post};

// ── Instancias de charts ──────────────────────────────────────────────────────
var charts = {{}};

function makeChart(id, config) {{
  var el = document.getElementById(id);
  if (!el) return;
  if (charts[id]) {{ charts[id].destroy(); }}
  charts[id] = new Chart(el, config);
}}

function renderCharts() {{
  // Volumetría
  makeChart('cVol', {{
    type: 'line',
    data: {{
      labels: LABELS,
      datasets: [
        {{label: '{ap}', data: VOL_AP, borderColor: '#3b82f6', backgroundColor: 'rgba(59,130,246,.08)', fill: true, tension: 0.4, pointRadius: 4, borderWidth: 2.5}},
        {{label: '{aa}', data: VOL_AA, borderColor: '#10b981', backgroundColor: 'rgba(16,185,129,.08)', fill: true, tension: 0.4, pointRadius: 4, borderWidth: 2.5}}
      ]
    }},
    options: {{responsive: true, maintainAspectRatio: false, plugins: {{legend: {{position: 'top'}}}}, scales: {{y: {{beginAtZero: true}}}}}}
  }});

  // SLA mensual
  makeChart('cSla', {{
    type: 'line',
    data: {{
      labels: LABELS,
      datasets: [
        {{label: '{ap}', data: SLA_AP, borderColor: '#f59e0b', backgroundColor: 'rgba(245,158,11,.08)', fill: true, tension: 0.4, pointRadius: 4, borderWidth: 2.5, spanGaps: false}},
        {{label: '{aa}', data: SLA_AA, borderColor: '#10b981', backgroundColor: 'rgba(16,185,129,.08)', fill: true, tension: 0.4, pointRadius: 4, borderWidth: 2.5, spanGaps: false}}
      ]
    }},
    options: {{responsive: true, maintainAspectRatio: false, plugins: {{legend: {{position: 'top'}}}}, scales: {{y: {{ticks: {{callback: v => v + ' hrs'}}}}}}}}
  }});

  // Aprobación vs Tarea
  makeChart('cAprob', {{
    type: 'bar',
    data: {{
      labels: ['SLA Tarea {ap}', 'SLA Tarea {aa}', 'SLA Aprob {ap}', 'SLA Aprob {aa}'],
      datasets: [{{
        data: [SLA_T_AP, SLA_T_AA, SLA_A_AP, SLA_A_AA],
        backgroundColor: ['rgba(59,130,246,.7)', 'rgba(16,185,129,.7)', 'rgba(245,158,11,.7)', 'rgba(6,182,212,.7)'],
        borderRadius: 4
      }}]
    }},
    options: {{responsive: true, maintainAspectRatio: false, plugins: {{legend: {{display: false}}}}, scales: {{y: {{ticks: {{callback: v => v + ' hrs'}}}}}}}}
  }});

  // Top 10
  makeChart('cTop10', {{
    type: 'bar',
    data: {{
      labels: TOP10_LABELS,
      datasets: [{{label: 'SLA (hrs)', data: TOP10_DATA, backgroundColor: TOP10_COLORS, borderRadius: 3}}]
    }},
    options: {{indexAxis: 'y', responsive: true, maintainAspectRatio: false, plugins: {{legend: {{display: false}}}}, scales: {{x: {{ticks: {{callback: v => v + 'h'}}}}}}}}
  }});

  // Grupo resolutor
  makeChart('cGrupo', {{
    type: 'bar',
    data: {{
      labels: GRUPO_LABELS,
      datasets: [{{label: 'SLA prom (hrs)', data: GRUPO_DATA, backgroundColor: 'rgba(59,130,246,.75)', borderRadius: 3}}]
    }},
    options: {{indexAxis: 'y', responsive: true, maintainAspectRatio: false, plugins: {{legend: {{display: false}}}}, scales: {{x: {{ticks: {{callback: v => v + 'h'}}}}}}}}
  }});

  // Por formulario
  makeChart('cForm', {{
    type: 'bar',
    data: {{
      labels: FORM_LABELS,
      datasets: [
        {{label: '% Aprobación', data: FORM_PCT_A, backgroundColor: 'rgba(245,158,11,.8)', borderRadius: 2}},
        {{label: '% Post-aprobación', data: FORM_PCT_P, backgroundColor: 'rgba(59,130,246,.8)', borderRadius: 2}}
      ]
    }},
    options: {{responsive: true, maintainAspectRatio: false, plugins: {{legend: {{position: 'bottom'}}}}, scales: {{x: {{stacked: true, ticks: {{maxRotation: 45}}}}, y: {{stacked: true, ticks: {{callback: v => v + '%'}}}}}}}}
  }});

  // Cumplimiento barras
  makeChart('cCump', {{
    type: 'bar',
    data: {{
      labels: CUMP_LABELS,
      datasets: [{{
        label: '% Cumplimiento',
        data: CUMP_DATA,
        backgroundColor: CUMP_DATA.map(v => v > 50 ? 'rgba(16,185,129,.8)' : v > 30 ? 'rgba(245,158,11,.8)' : 'rgba(220,38,38,.8)'),
        borderRadius: 3
      }}]
    }},
    options: {{responsive: true, maintainAspectRatio: false, plugins: {{legend: {{display: false}}}}, scales: {{y: {{max: 100, ticks: {{callback: v => v + '%'}}}}, x: {{ticks: {{maxRotation: 45}}}}}}}}
  }});

  // Cumplimiento dona
  var totalDentro = {sum(c['dentro'] for c in cump)};
  var totalFuera  = {sum(c['fuera'] for c in cump)};
  makeChart('cCumpDona', {{
    type: 'doughnut',
    data: {{
      labels: ['Dentro SLA', 'Fuera SLA'],
      datasets: [{{data: [totalDentro, totalFuera], backgroundColor: ['#10b981', '#ef4444'], borderWidth: 1, borderColor: '#fff'}}]
    }},
    options: {{responsive: true, maintainAspectRatio: false, cutout: '60%', plugins: {{legend: {{position: 'bottom'}}}}}}
  }});

  // Aprobadores
  makeChart('cAprob2', {{
    type: 'bar',
    data: {{
      labels: APROB_LABELS,
      datasets: [{{label: 'Tiempo prom (hrs)', data: APROB_DATA, backgroundColor: 'rgba(139,92,246,.75)', borderRadius: 3}}]
    }},
    options: {{indexAxis: 'y', responsive: true, maintainAspectRatio: false, plugins: {{legend: {{display: false}}}}, scales: {{x: {{ticks: {{callback: v => v + ' hrs'}}}}}}}}
  }});

  // Mejora
  makeChart('cMejora', {{
    type: 'bar',
    data: {{
      labels: ['{ap}', '{aa}'],
      datasets: [{{
        label: 'SLA prom (hrs)',
        data: [SLA_GLOBAL_AP, SLA_GLOBAL_AA],
        backgroundColor: ['rgba(245,158,11,.8)', 'rgba(16,185,129,.8)'],
        borderRadius: 4
      }}]
    }},
    options: {{responsive: true, maintainAspectRatio: false, plugins: {{legend: {{display: false}}}}, scales: {{y: {{ticks: {{callback: v => v + ' hrs'}}}}}}}}
  }});

  // Pre/Post automatización
  makeChart('cAuto', {{
    type: 'bar',
    data: {{
      labels: ['Pre-auto (Ene–Mar)', 'Post-auto (Abr–May)'],
      datasets: [{{
        label: 'SLA prom (hrs)',
        data: [SLA_PRE, SLA_POST],
        backgroundColor: ['rgba(245,158,11,.8)', 'rgba(16,185,129,.8)'],
        borderRadius: 4
      }}]
    }},
    options: {{responsive: true, maintainAspectRatio: false, plugins: {{legend: {{display: false}}}}, scales: {{y: {{ticks: {{callback: v => v + ' hrs'}}}}}}}}
  }});
}}

// Renderizar al cargar
document.addEventListener('DOMContentLoaded', function() {{
  setTimeout(renderCharts, 100);
}});
</script>
</body>
</html>"""

    print(f"📄 HTML generado en Python: {len(html):,} bytes")
    return html
