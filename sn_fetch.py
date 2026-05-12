import os
import requests
from datetime import datetime, timedelta
from collections import defaultdict

SN_BASE = os.environ.get("SN_BASE_URL", "")
SN_USER = os.environ.get("SN_USERNAME", "")
SN_PASS = os.environ.get("SN_PASSWORD", "")

# 10 formularios del Excel
CAT_ITEMS = ",".join([
    "098c1d8333631610f9f4984a7e5c7b59",  # Gestión de Tablas
    "3ed9b2ce3bd26a10ee77c237f4e45ab0",  # Agendamiento de Componentes Nube
    "59b6c33b3b4eaa10ee77c237f4e45a23",  # Gestión de Consultas Programadas
    "6ba0d286338b1e10f9f4984a7e5c7b47",  # Cloud SQL
    "a43100c797cf92505529fa77f053afe2",  # Gestión de Buckets
    "a50483a73377ae10f9f4984a7e5c7b0b",  # Gestión de Maquinas Virtuales
    "b261e0e13b275250d034caea26e45a8d",  # Proyecto GCP
    "c919ef5b3bc4f610ee77c237f4e45a59",  # Creación de Proyecto PoC o Sandbox
    "ec519fef339fa610f9f4984a7e5c7b54",  # Gestión de Usuarios Cloud
    "f6c089e3339fa610f9f4984a7e5c7b19",  # Gestión de Cuentas de Servicio Cloud
])

AUTH    = (SN_USER, SN_PASS)
HEADERS = {"Accept": "application/json"}

FORMATOS_FECHA = [
    "%Y-%m-%d %H:%M:%S",
    "%d-%m-%Y %H:%M:%S",
    "%d/%m/%Y %H:%M:%S",
    "%m/%d/%Y %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%d-%m-%Y",
    "%Y-%m-%d",
]


def _parsear_fecha(fecha_str):
    if not fecha_str:
        return None
    fecha_str = fecha_str.strip()
    for fmt in FORMATOS_FECHA:
        try:
            return datetime.strptime(fecha_str, fmt)
        except ValueError:
            continue
    print(f"WARNING: No se pudo parsear: {repr(fecha_str)}")
    return None


def _parsear_mes(fecha_str):
    dt = _parsear_fecha(fecha_str)
    return dt.strftime("%Y-%m") if dt else ""


def _parsear_anio(fecha_str):
    dt = _parsear_fecha(fecha_str)
    return str(dt.year) if dt else ""


def _paginar(tabla, campos, query):
    resultados = []
    offset = 0
    while True:
        url = (
            f"{SN_BASE}/api/now/table/{tabla}"
            f"?sysparm_display_value=true"
            f"&sysparm_limit=1000"
            f"&sysparm_offset={offset}"
            f"&sysparm_fields={campos}"
            f"&sysparm_query={query}"
        )
        resp = requests.get(url, auth=AUTH, headers=HEADERS, timeout=60)
        resp.raise_for_status()
        data = resp.json().get("result", [])
        if not data:
            break
        resultados.extend(data)
        offset += 1000
        if len(data) < 1000:
            break
    return resultados


def _val(campo):
    if isinstance(campo, dict):
        return campo.get("display_value", "")
    return campo or ""


def _horas_habiles(inicio_str, fin_str):
    if not inicio_str or not fin_str:
        return None
    try:
        inicio = _parsear_fecha(inicio_str)
        fin    = _parsear_fecha(fin_str)
        if not inicio or not fin:
            return None
        if inicio >= fin:
            return 0.0

        HORA_INI, HORA_FIN = 8, 19

        def clip_ini(dt):
            h = dt.hour + dt.minute / 60
            if h < HORA_INI:
                return dt.replace(hour=HORA_INI, minute=0, second=0)
            if h >= HORA_FIN:
                sig = dt.date() + timedelta(days=1)
                return datetime(sig.year, sig.month, sig.day, HORA_INI, 0, 0)
            return dt

        def clip_fin(dt):
            h = dt.hour + dt.minute / 60
            if h <= HORA_INI:
                prev = dt.date() - timedelta(days=1)
                return datetime(prev.year, prev.month, prev.day, HORA_FIN, 0, 0)
            if h > HORA_FIN:
                return dt.replace(hour=HORA_FIN, minute=0, second=0)
            return dt

        inicio = clip_ini(inicio)
        fin    = clip_fin(fin)
        total  = 0.0
        cur    = inicio

        while cur.date() <= fin.date():
            if cur.weekday() < 5:
                if cur.date() == inicio.date() == fin.date():
                    total += max(0, (fin.hour + fin.minute/60) - (cur.hour + cur.minute/60))
                    break
                elif cur.date() == inicio.date():
                    total += max(0, HORA_FIN - (cur.hour + cur.minute/60))
                elif cur.date() == fin.date():
                    total += max(0, (fin.hour + fin.minute/60) - HORA_INI)
                else:
                    total += HORA_FIN - HORA_INI
            cur = datetime(cur.year, cur.month, cur.day) + timedelta(days=1)

        return round(total, 2)
    except Exception as e:
        print(f"WARNING: Error horas habiles: {e}")
        return None


def fetch_all_data():
    anio_actual = datetime.now().year
    fecha_desde = f"{anio_actual - 1}-01-01"
    now_str     = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ── RITM ──────────────────────────────────────────────────────────────────
    raw_ritm = _paginar(
        "sc_req_item",
        "number,cat_item,stage,opened_by,sys_created_on,closed_at,sys_updated_on",
        f"opened_at>={fecha_desde}^cat_itemIN{CAT_ITEMS}"
    )

    if raw_ritm:
        ej = _val(raw_ritm[0].get("sys_created_on", ""))
        print(f"DEBUG fecha cruda: {repr(ej)} → parseada: {_parsear_fecha(ej)}")

    ritm_list = []
    for r in raw_ritm:
        creado  = _val(r.get("sys_created_on", ""))
        cerrado = _val(r.get("closed_at", ""))
        # Para tickets abiertos calcular hasta ahora
        fin_sla = cerrado if cerrado else now_str
        ritm_list.append({
            "numero":      _val(r.get("number", "")),
            "elemento":    _val(r.get("cat_item", "")),
            "etapa":       _val(r.get("stage", "")),
            "solicitante": _val(r.get("opened_by", "")),
            "creado":      creado,
            "cerrado":     cerrado,
            "mes":         _parsear_mes(creado),
            "anio":        _parsear_anio(creado),
            "sla":         _horas_habiles(creado, fin_sla),
            "cerrado_real": bool(cerrado),
        })

    # ── Tareas ─────────────────────────────────────────────────────────────────
    raw_tasks = _paginar(
        "sc_task",
        "number,request_item,state,assignment_group,assigned_to,opened_at,closed_at,due_date",
        f"opened_at>={fecha_desde}^cat_itemIN{CAT_ITEMS}"
    )

    task_sla        = defaultdict(list)
    task_grupo      = defaultdict(list)
    task_estado     = defaultdict(list)
    task_dentro_sla = defaultdict(list)

    # SLA targets por grupo (en horas hábiles)
    SLA_TARGETS = {
        "Kyndryl_Accesos Cloud": 12,
        "Kyndryl_Ingeniería":    8,
        "Ingenieria SURA":       8,
        "INGENIERIA SURA":       8,
        "Seguridad SURA":        8,
    }

    for t in raw_tasks:
        ritm   = _val(t.get("request_item", ""))
        ini    = _val(t.get("opened_at", ""))
        fin    = _val(t.get("closed_at", ""))
        grupo  = _val(t.get("assignment_group", ""))
        estado = _val(t.get("state", ""))
        fin_t  = fin if fin else now_str
        sla    = _horas_habiles(ini, fin_t)

        if sla is not None:
            task_sla[ritm].append(sla)
            # Verificar cumplimiento SLA
            target = SLA_TARGETS.get(grupo, 12)
            task_dentro_sla[ritm].append(sla <= target)

        if grupo:
            task_grupo[ritm].append(grupo)
        if estado:
            task_estado[ritm].append(estado)

    # ── Aprobaciones ───────────────────────────────────────────────────────────
    numeros   = {r["numero"] for r in ritm_list}
    raw_aprob = _paginar(
        "sysapproval_approver",
        "state,sysapproval,approver,sys_created_on,sys_updated_on",
        f"sys_created_on>={fecha_desde}"
    )

    aprob_sla     = defaultdict(list)
    aprob_estado  = defaultdict(list)
    aprob_aprobador = defaultdict(list)

    for a in raw_aprob:
        ritm = _val(a.get("sysapproval", ""))
        if ritm not in numeros:
            continue
        cre    = _val(a.get("sys_created_on", ""))
        act    = _val(a.get("sys_updated_on", ""))
        estado = _val(a.get("state", ""))
        apro   = _val(a.get("approver", ""))
        sla    = _horas_habiles(cre, act if act else now_str)
        if sla is not None:
            aprob_sla[ritm].append(sla)
        if estado:
            aprob_estado[ritm].append(estado)
        if apro:
            aprob_aprobador[ritm].append(apro)

    # ── Enriquecer RITM ────────────────────────────────────────────────────────
    def prom(lst):
        v = [x for x in lst if x is not None]
        return round(sum(v) / len(v), 1) if v else None

    for r in ritm_list:
        n  = r["numero"]
        st = task_sla.get(n)
        sa = aprob_sla.get(n)
        r["sla_tarea"]      = round(sum(st) / len(st), 2) if st else None
        r["sla_aprob"]      = round(sum(sa), 2) if sa else None
        r["grupo"]          = ", ".join(set(task_grupo.get(n, [])))
        r["estado_tarea"]   = ", ".join(set(task_estado.get(n, [])))
        r["estado_aprob"]   = ", ".join(set(aprob_estado.get(n, [])))
        r["aprobadores"]    = ", ".join(set(aprob_aprobador.get(n, [])))
        r["dentro_sla"]     = all(task_dentro_sla.get(n, [False]))
        r["sla_post_aprob"] = round(r["sla"] - r["sla_aprob"], 2) if r["sla"] and r["sla_aprob"] else None

        if r["sla_aprob"] and r["sla_tarea"]:
            r["cuello"] = "Aprobacion" if r["sla_aprob"] > r["sla_tarea"] else "Tarea"
        elif r["sla_tarea"]:
            r["cuello"] = "Tarea"
        elif r["sla_aprob"]:
            r["cuello"] = "Aprobacion"
        else:
            r["cuello"] = "Sin datos"

    # ── Agrupar por año y mes ──────────────────────────────────────────────────
    por_anio = defaultdict(list)
    for r in ritm_list:
        if r["anio"]:
            por_anio[r["anio"]].append(r)

    vol_mes = defaultdict(int)
    sla_mes = defaultdict(list)
    for r in ritm_list:
        if r["mes"]:
            vol_mes[r["mes"]] += 1
            if r["sla"] is not None:
                sla_mes[r["mes"]].append(r["sla"])

    resumen_mes = {}
    for mes in sorted(set(list(vol_mes.keys()) + list(sla_mes.keys()))):
        resumen_mes[mes] = {
            "vol": vol_mes.get(mes, 0),
            "sla": prom(sla_mes.get(mes, [])),
        }

    por_form = defaultdict(lambda: defaultdict(list))
    for r in ritm_list:
        por_form[r["elemento"]][r["anio"]].append(r)

    def top_n(lista, n=20):
        return sorted(
            [r for r in lista if r["sla"] is not None],
            key=lambda x: x["sla"], reverse=True
        )[:n]

    aa = str(anio_actual)
    ap = str(anio_actual - 1)

    # ── Análisis de tiempos (sección 1: por grupo resolutor) ──────────────────
    grupo_stats = defaultdict(lambda: {"total": 0, "cerrados": 0, "en_curso": 0, "sla_hrs": []})
    for r in ritm_list:
        grupo = r["grupo"] or "Sin grupo"
        for g in grupo.split(", "):
            g = g.strip()
            if not g:
                continue
            grupo_stats[g]["total"] += 1
            if r["cerrado_real"]:
                grupo_stats[g]["cerrados"] += 1
            else:
                grupo_stats[g]["en_curso"] += 1
            if r["sla"] is not None:
                grupo_stats[g]["sla_hrs"].append(r["sla"])

    analisis_grupo = []
    for g, s in sorted(grupo_stats.items()):
        analisis_grupo.append({
            "grupo":    g,
            "total":    s["total"],
            "cerrados": s["cerrados"],
            "en_curso": s["en_curso"],
            "sla_prom": prom(s["sla_hrs"]),
            "sla_total": round(sum(s["sla_hrs"]), 2) if s["sla_hrs"] else None,
        })

    # ── Análisis de tiempos (sección 1B: por elemento/formulario) ─────────────
    elem_stats = defaultdict(lambda: {"total": 0, "cerrados": 0, "en_curso": 0, "sla_hrs": [], "aprob_hrs": [], "post_hrs": []})
    for r in ritm_list:
        e = r["elemento"] or "Sin elemento"
        elem_stats[e]["total"] += 1
        if r["cerrado_real"]:
            elem_stats[e]["cerrados"] += 1
        else:
            elem_stats[e]["en_curso"] += 1
        if r["sla"] is not None:
            elem_stats[e]["sla_hrs"].append(r["sla"])
        if r["sla_aprob"] is not None:
            elem_stats[e]["aprob_hrs"].append(r["sla_aprob"])
        if r["sla_post_aprob"] is not None:
            elem_stats[e]["post_hrs"].append(r["sla_post_aprob"])

    analisis_elemento = []
    for e, s in sorted(elem_stats.items()):
        sla_p  = prom(s["sla_hrs"])
        apr_p  = prom(s["aprob_hrs"])
        post_p = prom(s["post_hrs"])
        analisis_elemento.append({
            "elemento":      e,
            "total":         s["total"],
            "cerrados":      s["cerrados"],
            "en_curso":      s["en_curso"],
            "sla_prom":      sla_p,
            "sla_total":     round(sum(s["sla_hrs"]), 2) if s["sla_hrs"] else None,
            "aprob_prom":    apr_p,
            "post_prom":     post_p,
            "pct_aprob":     round(apr_p / sla_p, 4) if sla_p and apr_p else None,
            "pct_post":      round(post_p / sla_p, 4) if sla_p and post_p else None,
        })

    # ── Análisis cumplimiento SLA tareas por grupo ─────────────────────────────
    tarea_grupo_stats = defaultdict(lambda: {"total": 0, "dentro": 0, "fuera": 0, "sla_hrs": []})
    for t in raw_tasks:
        grupo  = _val(t.get("assignment_group", ""))
        ini    = _val(t.get("opened_at", ""))
        fin    = _val(t.get("closed_at", ""))
        fin_t  = fin if fin else now_str
        sla    = _horas_habiles(ini, fin_t)
        if not grupo:
            continue
        tarea_grupo_stats[grupo]["total"] += 1
        if sla is not None:
            tarea_grupo_stats[grupo]["sla_hrs"].append(sla)
            target = SLA_TARGETS.get(grupo, 12)
            if sla <= target:
                tarea_grupo_stats[grupo]["dentro"] += 1
            else:
                tarea_grupo_stats[grupo]["fuera"] += 1

    cumplimiento_grupo = []
    for g, s in sorted(tarea_grupo_stats.items()):
        total = s["total"]
        pct   = round(s["dentro"] / total, 4) if total > 0 else 0
        cumplimiento_grupo.append({
            "grupo":    g,
            "total":    total,
            "dentro":   s["dentro"],
            "fuera":    total - s["dentro"],
            "pct":      pct,
            "sla_prom": prom(s["sla_hrs"]),
        })

    # ── Análisis aprobadores ───────────────────────────────────────────────────
    aprobador_stats = defaultdict(lambda: {"total": 0, "completadas": 0, "sla_hrs": []})
    for a in raw_aprob:
        ritm = _val(a.get("sysapproval", ""))
        if ritm not in numeros:
            continue
        apro   = _val(a.get("approver", ""))
        estado = _val(a.get("state", ""))
        cre    = _val(a.get("sys_created_on", ""))
        act    = _val(a.get("sys_updated_on", ""))
        if not apro:
            continue
        aprobador_stats[apro]["total"] += 1
        if estado.lower() in ["approved", "aprobado"]:
            aprobador_stats[apro]["completadas"] += 1
        sla = _horas_habiles(cre, act if act else now_str)
        if sla is not None:
            aprobador_stats[apro]["sla_hrs"].append(sla)

    analisis_aprobadores = []
    for ap_name, s in sorted(aprobador_stats.items()):
        analisis_aprobadores.append({
            "aprobador":   ap_name,
            "total":       s["total"],
            "completadas": s["completadas"],
            "sla_prom":    prom(s["sla_hrs"]),
            "sla_total":   round(sum(s["sla_hrs"]), 2) if s["sla_hrs"] else None,
        })

    # ── Resumen general aprobación vs gestión ─────────────────────────────────
    todos_sla     = [r["sla"] for r in ritm_list if r["sla"] is not None]
    todos_aprob   = [r["sla_aprob"] for r in ritm_list if r["sla_aprob"] is not None]
    todos_post    = [r["sla_post_aprob"] for r in ritm_list if r["sla_post_aprob"] is not None]
    total_sla     = round(sum(todos_sla), 2) if todos_sla else 0
    total_aprob   = round(sum(todos_aprob), 2) if todos_aprob else 0
    total_post    = round(sum(todos_post), 2) if todos_post else 0

    resumen_tiempos = {
        "sla_prom":        prom(todos_sla),
        "sla_total":       total_sla,
        "aprob_prom":      prom(todos_aprob),
        "aprob_total":     total_aprob,
        "post_prom":       prom(todos_post),
        "post_total":      total_post,
        "pct_aprob":       round(total_aprob / total_sla, 4) if total_sla else None,
        "pct_post":        round(total_post / total_sla, 4) if total_sla else None,
    }

    # ── Análisis pre/post automatización (Gestión Cuentas Servicio Cloud) ──────
    cuentas = [r for r in ritm_list if "Cuentas de Servicio" in r["elemento"]]
    pre     = [r for r in cuentas if r["mes"] in ["2026-01","2026-02","2026-03"]]
    post    = [r for r in cuentas if r["mes"] in ["2026-04","2026-05"]]

    automatizacion = {
        "pre": {
            "total":    len(pre),
            "cerrados": sum(1 for r in pre if r["cerrado_real"]),
            "sla_prom": prom([r["sla"] for r in pre if r["sla"]]),
            "sla_total": round(sum(r["sla"] for r in pre if r["sla"]), 2),
        },
        "post": {
            "total":    len(post),
            "cerrados": sum(1 for r in post if r["cerrado_real"]),
            "sla_prom": prom([r["sla"] for r in post if r["sla"]]),
            "sla_total": round(sum(r["sla"] for r in post if r["sla"]), 2),
        }
    }
    sla_pre  = automatizacion["pre"]["sla_prom"] or 0
    sla_post_val = automatizacion["post"]["sla_prom"] or 0
    automatizacion["reduccion_hrs"]  = round(sla_pre - sla_post_val, 2)
    automatizacion["pct_mejora"]     = round((sla_pre - sla_post_val) / sla_pre, 4) if sla_pre else 0
    automatizacion["hh_ahorradas"]   = round(automatizacion["post"]["total"] * sla_pre - automatizacion["post"]["sla_total"], 2)

    # ── Mejora 2025 vs 2026 ───────────────────────────────────────────────────
    sla_2025 = prom([r["sla"] for r in por_anio.get(ap, []) if r["sla"]])
    sla_2026 = prom([r["sla"] for r in por_anio.get(aa, []) if r["sla"]])
    BASELINE_2025 = 30.0  # hrs hábiles baseline 2025
    mejora_2025_2026 = {
        "baseline_2025_hrs":  BASELINE_2025,
        "actual_2026_hrs":    sla_2026,
        "reduccion_hrs":      round(BASELINE_2025 - (sla_2026 or 0), 2),
        "pct_mejora":         round((BASELINE_2025 - (sla_2026 or 0)) / BASELINE_2025, 4) if sla_2026 else None,
        "total_ritm_2026":    len(por_anio.get(aa, [])),
        "hh_ahorradas_total": round(len(por_anio.get(aa, [])) * (BASELINE_2025 - (sla_2026 or 0)), 2),
        "dias_persona":       round(len(por_anio.get(aa, [])) * (BASELINE_2025 - (sla_2026 or 0)) / 10, 2),
        "meses_persona":      round(len(por_anio.get(aa, [])) * (BASELINE_2025 - (sla_2026 or 0)) / 10 / 22, 2),
        "fte_anual":          round(len(por_anio.get(aa, [])) * (BASELINE_2025 - (sla_2026 or 0)) / 10 / 22 / 12, 2),
    }

    # Debug
    print(f"DEBUG años: {sorted(por_anio.keys())}")
    print(f"DEBUG RITM: { {a: len(v) for a, v in por_anio.items()} }")
    con_sla = sum(1 for r in ritm_list if r["sla"] is not None)
    print(f"DEBUG con SLA: {con_sla}/{len(ritm_list)}")
    print(f"DEBUG formularios: {list(elem_stats.keys())}")

    return {
        "fecha_generacion":          datetime.now().strftime("%d %b %Y %H:%M"),
        "total_ritm":                len(ritm_list),
        "total_tasks":               len(raw_tasks),
        "total_approvals":           len(raw_aprob),
        "anio_actual":               aa,
        "anio_anterior":             ap,
        "ritm_por_anio":             {a: len(v) for a, v in por_anio.items()},
        "sla_prom_por_anio":         {a: prom([r["sla"] for r in v]) for a, v in por_anio.items()},
        "sla_tarea_prom_por_anio":   {a: prom([r["sla_tarea"] for r in v]) for a, v in por_anio.items()},
        "sla_aprob_prom_por_anio":   {a: prom([r["sla_aprob"] for r in v]) for a, v in por_anio.items()},
        "resumen_mes":               resumen_mes,
        "por_form_anio": {
            form: {
                anio: {
                    "vol":    len(rs),
                    "sla":    prom([r["sla"] for r in rs]),
                    "top3":   top_n(rs, 3),
                }
                for anio, rs in anios.items()
            }
            for form, anios in por_form.items()
        },
        "top_cuellos_anio_actual":   top_n(por_anio.get(aa, []), 20),
        "top_cuellos_anio_anterior": top_n(por_anio.get(ap, []), 20),
        # Análisis de tiempos
        "analisis_grupo":            analisis_grupo,
        "analisis_elemento":         analisis_elemento,
        "cumplimiento_grupo":        cumplimiento_grupo,
        "analisis_aprobadores":      analisis_aprobadores,
        "resumen_tiempos":           resumen_tiempos,
        "automatizacion":            automatizacion,
        "mejora_2025_2026":          mejora_2025_2026,
    }
