import os
from sn_fetch import fetch_all_data
from claude_report import generar_html
from send_email import enviar_correo


def validar_datos(datos):
    errores = []
    anios = list(datos["ritm_por_anio"].keys())
    aa = datos["anio_actual"]
    ap = datos["anio_anterior"]
    if aa not in anios and ap not in anios:
        errores.append(f"ERROR CRÍTICO: No se detectaron años {aa} ni {ap}. Encontrados: {anios}")
    if datos["total_ritm"] == 0:
        errores.append("ERROR: No se descargaron RITM")
    sla_prom = datos["sla_prom_por_anio"]
    if all(v is None for v in sla_prom.values()):
        errores.append("ERROR CRÍTICO: Todos los SLA son None")
    meses = list(datos["resumen_mes"].keys())
    meses_validos = [m for m in meses if len(m) == 7 and "-" in m]
    if len(meses_validos) < len(meses) * 0.5:
        errores.append(f"ERROR: Formato de meses incorrecto: {meses[:3]}")
    return errores


def main():
    print("🚀 Iniciando reporte semanal...")

    print("📡 Conectando a ServiceNow...")
    datos = fetch_all_data()
    print(f"✅ Descargados: {datos['total_ritm']} RITM, {datos['total_tasks']} tareas")

    print("\n=== DEBUG DATOS ===")
    print(f"Años:      {list(datos['ritm_por_anio'].keys())}")
    print(f"RITM:      {datos['ritm_por_anio']}")
    print(f"SLA prom:  {datos['sla_prom_por_anio']}")
    print(f"Meses:     {list(datos['resumen_mes'].keys())[:6]}")
    print(f"Forms:     {list(datos['por_form_anio'].keys())}")
    print(f"Mejora:    {datos['mejora_2025_2026']}")
    print(f"Automatización: pre={datos['automatizacion']['pre']['total']} post={datos['automatizacion']['post']['total']}")
    print("=== FIN DEBUG ===\n")

    errores = validar_datos(datos)
    if errores:
        print("⚠️  PROBLEMAS DETECTADOS:")
        for e in errores:
            print(f"   {e}")
        if any("CRÍTICO" in e for e in errores):
            raise Exception(f"Datos inválidos: {errores}")
    else:
        print("✅ Validación de datos OK\n")

    print("🤖 Generando reporte con Claude...")
    html = generar_html(datos)
    print("✅ HTML generado")

    with open("reporte_semanal.html", "w", encoding="utf-8") as f:
        f.write(html)

    # URL de GitHub Pages donde quedará publicado el reporte
    repo = os.environ.get("GITHUB_REPO", "4ndreams/ServiceNow")
    usuario = repo.split("/")[0]
    repo_nombre = repo.split("/")[1]
    url_reporte = f"https://{usuario}.github.io/{repo_nombre}/"

    print("📧 Enviando correo con link...")
    destinatarios = os.environ["EMAIL_RECIPIENTS"].split(",")
    enviar_correo(
        destinatarios=[d.strip() for d in destinatarios],
        asunto="Reporte Semanal — Tickets Proyecto Workflow IT",
        html=html,
        url_reporte=url_reporte,
        fecha=datos["fecha_generacion"]
    )
    print(f"🎉 Reporte publicado en: {url_reporte}")
    print("🎉 Reporte completado y enviado")


if __name__ == "__main__":
    main()
