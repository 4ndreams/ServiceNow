import os
import json
import urllib.request
import anthropic


def _descargar_chartjs() -> str:
    """Lee Chart.js desde el archivo local del repositorio."""
    ruta = os.path.join(os.path.dirname(__file__), "chart.min.js")
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            codigo = f.read()
        print(f"✅ Chart.js cargado desde archivo local: {len(codigo):,} bytes")
        return codigo
    except Exception as e:
        print(f"WARNING: No se pudo leer chart.min.js: {e}")
        return ""


def generar_html(datos: dict) -> str:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    # Descargar Chart.js para embeber (así funciona sin internet al abrir el archivo)
    print("📦 Descargando Chart.js para embeber...")
    chartjs = _descargar_chartjs()

    aa = datos["anio_actual"]
    ap = datos["anio_anterior"]
    mt = datos["mejora_2025_2026"]
    at = datos["automatizacion"]
    rt = datos["resumen_tiempos"]

    resumen = {
        "fecha_generacion":    datos["fecha_generacion"],
        "anio_actual":         aa,
        "anio_anterior":       ap,
        "total_ritm":          datos["total_ritm"],
        "ritm_por_anio":       datos["ritm_por_anio"],
        "sla_prom_por_anio":   datos["sla_prom_por_anio"],
        "sla_tarea_por_anio":  datos["sla_tarea_prom_por_anio"],
        "sla_aprob_por_anio":  datos["sla_aprob_prom_por_anio"],
        "volumetria_mensual":  datos["resumen_mes"],
        "por_formulario": {
            form: {
                anio: {
                    "vol":  info["vol"],
                    "sla":  info["sla"],
                    "top3": [
                        {
                            "ritm":   r["numero"],
                            "sla":    r["sla"],
                            "slaT":   r["sla_tarea"],
                            "slaA":   r["sla_aprob"],
                            "grupo":  r["grupo"],
                            "estT":   r["estado_tarea"],
                            "estA":   r["estado_aprob"],
                            "cuello": r["cuello"],
                            "mes":    r["mes"],
                        }
                        for r in info["top3"]
                    ]
                }
                for anio, info in anios.items()
            }
            for form, anios in datos["por_form_anio"].items()
        },
        "top20_actual": [
            {
                "ritm":   r["numero"], "form": r["elemento"], "etapa": r["etapa"],
                "sol":    r["solicitante"], "mes": r["mes"],
                "sla":    r["sla"], "slaT": r["sla_tarea"], "slaA": r["sla_aprob"],
                "grupo":  r["grupo"], "estT": r["estado_tarea"],
                "estA":   r["estado_aprob"], "cuello": r["cuello"],
            }
            for r in datos["top_cuellos_anio_actual"]
        ],
        "top20_anterior": [
            {
                "ritm":   r["numero"], "form": r["elemento"], "etapa": r["etapa"],
                "sol":    r["solicitante"], "mes": r["mes"],
                "sla":    r["sla"], "slaT": r["sla_tarea"], "slaA": r["sla_aprob"],
                "grupo":  r["grupo"], "estT": r["estado_tarea"],
                "estA":   r["estado_aprob"], "cuello": r["cuello"],
            }
            for r in datos["top_cuellos_anio_anterior"]
        ],
        "analisis_tiempos": {
            "resumen_general":           rt,
            "por_grupo_resolutor":       datos["analisis_grupo"],
            "por_elemento":              datos["analisis_elemento"],
            "cumplimiento_sla_tareas":   datos["cumplimiento_grupo"],
            "por_aprobador":             datos["analisis_aprobadores"],
            "mejora_2025_2026":          mt,
            "automatizacion_cuentas_servicio": at,
        }
    }

    prompt = f"""Eres un asistente de reportería para AFP Capital, área Ingeniería TI.

Con los siguientes datos actualizados de ServiceNow, genera un reporte HTML completo, profesional y visualmente atractivo.

DATOS:
{json.dumps(resumen, ensure_ascii=False, indent=2)}

INSTRUCCIONES CRÍTICAS SOBRE CHART.JS:
- NO uses <script src="..."> para cargar Chart.js desde CDN externo. Está PROHIBIDO.
- Chart.js ya está embebido en el archivo. Usa EXACTAMENTE este placeholder donde iría el script de Chart.js:
  {{CHARTJS_PLACEHOLDER}}
- Pon ese placeholder UNA SOLA VEZ justo antes del cierre </body>
- Después del placeholder, agrega tu <script> con el código de los gráficos
- Así el archivo funciona completamente offline y sin restricciones de Chrome

INSTRUCCIONES GENERALES:
- Título: "Tickets Proyecto Workflow IT — Vista Comparativa"
- Subtítulo: "AFP Capital · Ingeniería TI · Datos al {datos['fecha_generacion']}"
- Header con gradiente azul oscuro (#0c3c6e a #1a5fa8)
- 5 pestañas navegables con iconos (usando onclick en JS puro, sin librerías)
- Todo CSS y JS inline en un solo archivo HTML
- Fondo #f0f2f5, cards border-radius 12px, fuente Segoe UI
- Colores: #0c3c6e azul, #10b981 verde, #f59e0b amarillo, #dc2626 rojo, #8b5cf6 púrpura

═══ PESTAÑA 1: "📊 Resumen Ejecutivo" ═══
- 4 KPIs: Total RITM {ap}, Total RITM {aa}, SLA Prom {ap}, SLA Prom {aa}
- Gráfico líneas: Volumetría mensual {ap} vs {aa} lado a lado
- Gráfico líneas: SLA promedio mensual {ap} vs {aa} lado a lado
- Sección comparativa Aprobación vs Tarea: tarjetas con promedios anuales + gráfico barras agrupadas por mes

═══ PESTAÑA 2: "🗂 Vista Operativa por Formulario" ═══
- Una tarjeta por cada formulario con: total RITM {aa} en grande, SLA promedio {aa}, delta vs {ap}
- Cuellos de botella {aa}: top 3 con RITM, SLA, grupo resolutor, estado tarea, cuello (Tarea/Aprobación)
- Tabla debajo con estado tarea, estado aprobación, SLA tarea, SLA aprobación

═══ PESTAÑA 3: "📋 Detalles SLA" ═══
- Gráfico barras horizontales top 10 tickets {aa}
- Dos tablas separadas con tabs: {ap} y {aa}
- Columnas: #, RITM, Formulario, Etapa, Solicitante, Mes, SLA Total, SLA Tarea, SLA Aprob, Grupo, Estado Tarea, Estado Aprob, Cuello

═══ PESTAÑA 4: "⏱ Análisis de Tiempos" ═══
4 sub-tabs:
TAB A — Gestión por Grupo Resolutor: tabla + gráfico barras horizontales tiempo promedio
TAB B — Gestión por Formulario: tabla + gráfico barras apiladas % aprobación vs % post-aprobación
TAB C — Cumplimiento SLA Tareas: tabla + gráfico dona cumplimiento general + barras por grupo
TAB D — Aprobadores: tabla + gráfico barras tiempo promedio por aprobador

═══ PESTAÑA 5: "🚀 Impacto y Mejoras" ═══
SECCIÓN A — Mejora 2025 vs 2026: KPIs (baseline, actual, reducción, % mejora, HH ahorradas, días-persona, FTE) + gráfico barras + texto interpretativo
SECCIÓN B — Automatización Cuentas Servicio Cloud: KPIs pre/post + gráfico barras comparativo + texto interpretativo

ESTILO:
- Pills coloreados para estados
- Cuello: Tarea=rojo claro, Aprobación=amarillo
- Tablas con hover y headers gris
- % mejora verde si positivo, rojo si negativo

Devuelve SOLO el HTML completo sin explicaciones ni bloques markdown. Empieza con <!DOCTYPE html>"""

    print("🤖 Llamando a Claude API...")
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8000,
        messages=[{"role": "user", "content": prompt}]
    )

    html = msg.content[0].text
    if html.startswith("```"):
        html = html.split("\n", 1)[1]
        if html.endswith("```"):
            html = html.rsplit("```", 1)[0]
    html = html.strip()

    # Reemplazar el placeholder con el código real de Chart.js
    if chartjs and "{CHARTJS_PLACEHOLDER}" in html:
        html = html.replace("{CHARTJS_PLACEHOLDER}", f"<script>{chartjs}</script>")
        print("✅ Chart.js embebido correctamente en el HTML")
    elif chartjs and "<script src=" in html and "chart" in html.lower():
        # Fallback: reemplazar cualquier tag de script que cargue Chart.js desde CDN
        import re
        html = re.sub(
            r'<script[^>]*cdnjs[^>]*chart[^>]*></script>',
            f"<script>{chartjs}</script>",
            html,
            flags=re.IGNORECASE
        )
        print("✅ Chart.js embebido via reemplazo de CDN")
    elif not chartjs:
        print("WARNING: Chart.js no disponible, los gráficos pueden no funcionar")

    print(f"📄 HTML generado: {len(html):,} bytes")
    return html
