import os
import json
import re
import anthropic


def _leer_chartjs() -> str:
    """Lee Chart.js desde el archivo local del repositorio."""
    ruta = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chart.min.js")
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            codigo = f.read()
        print(f"✅ Chart.js cargado: {len(codigo):,} bytes")
        return codigo
    except Exception as e:
        print(f"WARNING: No se pudo leer chart.min.js: {e}")
        return ""


def _fix_charts_en_pestanas(html: str) -> str:
    """
    Fix crítico: Chart.js no puede renderizar en elementos con display:none.
    Este fix:
    1. Reemplaza la inicialización directa de charts por funciones nombradas
    2. Llama a esas funciones dentro de DOMContentLoaded
    3. Vuelve a llamarlas cuando se hace click en cada pestaña
    """

    # Encontrar todos los bloques new Chart(...)
    patron = re.compile(r'(new Chart\(document\.getElementById\([\'"](\w+)[\'"]\),[^;]+\);)', re.DOTALL)
    matches = list(patron.finditer(html))

    if not matches:
        print("WARNING: No se encontraron bloques new Chart() para parchear")
        return html

    print(f"✅ Parcheando {len(matches)} gráficos para funcionar en pestañas ocultas")

    # Construir funciones init para cada chart
    chart_funcs = []
    chart_ids = []
    replaced_html = html

    for match in matches:
        chart_code = match.group(1)
        canvas_id = match.group(2)
        func_name = f"initChart_{canvas_id}"
        chart_ids.append(canvas_id)

        # Crear función que destruye el chart anterior si existe y lo recrea
        func = f"""
function {func_name}() {{
  var el = document.getElementById('{canvas_id}');
  if (!el) return;
  if (el._chartInstance) {{ el._chartInstance.destroy(); }}
  var instance = {chart_code.rstrip(';')}
  el._chartInstance = instance;
}}"""
        chart_funcs.append(func)
        # Reemplazar el new Chart directo por llamada a función
        replaced_html = replaced_html.replace(chart_code, f"{func_name}();", 1)

    # Insertar las funciones y el DOMContentLoaded antes del </body>
    all_funcs = "\n".join(chart_funcs)
    all_calls = "\n  ".join([f"initChart_{cid}();" for cid in chart_ids])

    patch_script = f"""
<script>
{all_funcs}

// Inicializar todos los charts cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', function() {{
  // Pequeño delay para asegurar que los elementos estén visibles
  setTimeout(function() {{
    {all_calls}
  }}, 100);
}});

// Re-renderizar charts cuando se cambia de pestaña
(function() {{
  var originalShowTab = window.showTab;
  window.showTab = function(id, btn) {{
    if (originalShowTab) originalShowTab(id, btn);
    setTimeout(function() {{
      {all_calls}
    }}, 50);
  }};
}})();
</script>
"""

    # Insertar antes de </body>
    if "</body>" in replaced_html:
        replaced_html = replaced_html.replace("</body>", patch_script + "\n</body>")
    else:
        replaced_html += patch_script

    return replaced_html


def generar_html(datos: dict) -> str:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    print("📦 Cargando Chart.js...")
    chartjs = _leer_chartjs()

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

    prompt = f"""Eres un asistente de reportería para AFP Capital, equipo ServiceNow.

Con los siguientes datos actualizados de ServiceNow, genera un reporte HTML completo, profesional y visualmente atractivo.

DATOS:
{json.dumps(resumen, ensure_ascii=False, indent=2)}

INSTRUCCIONES CRÍTICAS SOBRE CHART.JS:
- NO uses <script src="..."> para cargar Chart.js desde CDN externo. Está PROHIBIDO.
- Chart.js ya está embebido en el archivo. Usa EXACTAMENTE este placeholder donde iría el tag de Chart.js:
  {{CHARTJS_PLACEHOLDER}}
- Pon ese placeholder UNA SOLA VEZ justo antes del cierre </body>
- Después del placeholder agrega tu <script> con TODOS los new Chart(...)
- USA document.getElementById() directamente en cada new Chart(), NO uses variables intermedias para el canvas
- Cada new Chart() debe terminar en punto y coma (;)
- NO uses DOMContentLoaded ni window.onload — el sistema lo maneja automáticamente

INSTRUCCIONES GENERALES:
- Título: "Tickets Proyecto Workflow IT — Vista Comparativa"
- Subtítulo: "AFP Capital · ServiceNow · Datos al {datos['fecha_generacion']}"
- Header con gradiente azul oscuro (#0c3c6e a #1a5fa8)
- 5 pestañas navegables con iconos usando onclick en JS puro
- Todo CSS y JS inline en un solo archivo HTML
- Fondo #f0f2f5, cards border-radius 12px, fuente Segoe UI
- Primera pestaña visible por defecto con clase "active"

═══ PESTAÑA 1: "📊 Resumen Ejecutivo" ═══
- 4 KPIs: Total RITM {ap}, Total RITM {aa}, SLA Prom {ap}, SLA Prom {aa}
- Gráfico líneas: Volumetría mensual {ap} vs {aa}
- Gráfico líneas: SLA promedio mensual {ap} vs {aa}
- Sección comparativa Aprobación vs Tarea: tarjetas + gráfico barras agrupadas

═══ PESTAÑA 2: "🗂 Vista por Formulario" ═══
- Una tarjeta por formulario: total RITM {aa}, SLA promedio, delta vs {ap}
- Top 3 cuellos de botella con RITM, SLA, grupo, estado tarea, cuello
- Tabla con estado tarea, aprobación, SLA tarea, SLA aprobación

═══ PESTAÑA 3: "📋 Detalles SLA" ═══
- Gráfico barras horizontales top 10 tickets {aa}
- Tablas separadas con tabs: {ap} y {aa}
- Columnas: #, RITM, Formulario, Etapa, Solicitante, Mes, SLA Total, SLA Tarea, SLA Aprob, Grupo, Cuello

═══ PESTAÑA 4: "⏱ Análisis de Tiempos" ═══
4 sub-tabs: Grupo Resolutor | Por Formulario | Cumplimiento SLA | Aprobadores
Cada uno con tabla + gráfico

═══ PESTAÑA 5: "🚀 Impacto y Mejoras" ═══
2 secciones: Mejora 2025 vs 2026 | Automatización Cuentas Servicio Cloud
KPIs + gráficos + texto interpretativo

ESTILO:
- Pills para estados y cuellos de botella
- Tablas con hover effect
- % mejora verde si positivo, rojo si negativo

Devuelve SOLO el HTML completo sin explicaciones. Empieza con <!DOCTYPE html>"""

    print("🤖 Llamando a Claude API...")
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=16000,
        messages=[{"role": "user", "content": prompt}]
    )

    html = msg.content[0].text
    if html.startswith("```"):
        html = html.split("\n", 1)[1]
        if html.endswith("```"):
            html = html.rsplit("```", 1)[0]
    html = html.strip()

    # Embeber Chart.js
    if chartjs and "{CHARTJS_PLACEHOLDER}" in html:
        html = html.replace("{CHARTJS_PLACEHOLDER}", f"<script>{chartjs}</script>")
        print("✅ Chart.js embebido correctamente")
    elif chartjs:
        # Fallback: insertar Chart.js antes del último </script>
        html = html.replace("</body>", f"<script>{chartjs}</script>\n</body>", 1)
        print("✅ Chart.js embebido via fallback")

    # Aplicar el fix para pestañas ocultas
    html = _fix_charts_en_pestanas(html)

    print(f"📄 HTML final: {len(html):,} bytes")
    return html
