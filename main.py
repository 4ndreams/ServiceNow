import os
from sn_fetch import fetch_all_data
from claude_report import generar_html
from send_email import enviar_correo


def validar_datos(datos):
    """Verifica que los datos llegaron bien antes de generar el HTML."""
    errores = []

    # Verificar que hay años correctos
    anios = list(datos["ritm_por_anio"].keys())
    aa = datos["anio_actual"]
    ap = datos["anio_anterior"]

    if aa not in anios and ap not in anios:
        errores.append(f"ERROR CRÍTICO: No se detectaron años {aa} ni {ap}. Años encontrados: {anios}")

    # Verificar que hay RITM
    total = datos["total_ritm"]
    if total == 0:
        errores.append("ERROR: No se descargaron RITM de ServiceNow")

    # Verificar que hay SLA calculado
    sla_prom = datos["sla_prom_por_anio"]
    todos_none = all(v is None for v in sla_prom.values())
    if todos_none:
        errores.append("ERROR CRÍTICO: Todos los SLA son None — el parseo de fechas falló")

    # Verificar meses
    meses = list(datos["resumen_mes"].keys())
    meses_validos = [m for m in meses if len(m) == 7 and "-" in m]
    if len(meses_validos) < len(meses) * 0.5:
        errores.append(f"ERROR: Formato de meses incorrecto. Ejemplos: {meses[:3]}")

    # Verificar formularios
    forms = list(datos["por_form_anio"].keys())
    if len(forms) == 0:
        errores.append("ERROR: No se encontraron formularios")

    return errores


def main():
    print("🚀 Iniciando reporte semanal...")

    # 1. Descargar datos
    print("📡 Conectando a ServiceNow...")
    datos = fetch_all_data()
    print(f"✅ Descargados: {datos['total_ritm']} RITM, {datos['total_tasks']} tareas, {datos['total_approvals']} aprobaciones")

    # 2. Mostrar DEBUG completo
    print("\n=== DEBUG DATOS ===")
    print(f"Años disponibles:  {list(datos['ritm_por_anio'].keys())}")
    print(f"RITM por año:      {datos['ritm_por_anio']}")
    print(f"SLA prom por año:  {datos['sla_prom_por_anio']}")
    print(f"SLA tarea por año: {datos['sla_tarea_prom_por_anio']}")
    print(f"SLA aprob por año: {datos['sla_aprob_prom_por_anio']}")
    print(f"Meses (primeros 6): {list(datos['resumen_mes'].keys())[:6]}")
    print(f"Formularios ({len(datos['por_form_anio'])}): {list(datos['por_form_anio'].keys())}")
    print(f"Top cuellos actual: {len(datos['top_cuellos_anio_actual'])}")
    print(f"Análisis grupos:   {len(datos['analisis_grupo'])} grupos")
    print(f"Resumen tiempos:   {datos['resumen_tiempos']}")
    print(f"Mejora 2025-2026:  {datos['mejora_2025_2026']}")
    print(f"Automatización:    pre={datos['automatizacion']['pre']['total']} post={datos['automatizacion']['post']['total']}")
    print("=== FIN DEBUG ===\n")

    # 3. Validar que los datos llegaron bien
    errores = validar_datos(datos)
    if errores:
        print("\n⚠️  PROBLEMAS DETECTADOS EN LOS DATOS:")
        for e in errores:
            print(f"   {e}")
        if any("CRÍTICO" in e for e in errores):
            raise Exception(f"Datos inválidos, no se genera el reporte: {errores}")
        else:
            print("   (Advertencias no críticas, continuando...)\n")
    else:
        print("✅ Validación de datos OK — todos los campos están correctos\n")

    # 4. Generar HTML
    print("🤖 Generando reporte con Claude...")
    html = generar_html(datos)
    print("✅ HTML generado")

    # Guardar localmente como artefacto
    with open("reporte_semanal.html", "w", encoding="utf-8") as f:
        f.write(html)

    # 5. Enviar correo
    print("📧 Enviando correo...")
    destinatarios = os.environ["EMAIL_RECIPIENTS"].split(",")
    enviar_correo(
        destinatarios=[d.strip() for d in destinatarios],
        asunto="Reporte Semanal — Tickets Proyecto Workflow IT",
        html=html
    )
    print("🎉 Reporte completado y enviado")


if __name__ == "__main__":
    main()
