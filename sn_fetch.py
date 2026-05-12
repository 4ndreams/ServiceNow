import os
import requests
from datetime import datetime
from collections import defaultdict

SN_BASE  = os.environ.get("SN_BASE_URL", "")
SN_USER  = os.environ.get("SN_USERNAME", "")
SN_PASS  = os.environ.get("SN_PASSWORD", "")

CAT_ITEMS = ",".join([
    "098c1d8333631610f9f4984a7e5c7b59",
    "3ed9b2ce3bd26a10ee77c237f4e45ab0",
    "59b6c33b3b4eaa10ee77c237f4e45a23",
    "6ba0d286338b1e10f9f4984a7e5c7b47",
    "a43100c797cf92505529fa77f053afe2",
    "a50483a73377ae10f9f4984a7e5c7b0b",
    "b261e0e13b275250d034caea26e45a8d",
    "c919ef5b3bc4f610ee77c237f4e45a59",
])

AUTH    = (SN_USER, SN_PASS)
HEADERS = {"Accept": "application/json"}


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
        from datetime import timedelta
        fmt = "%Y-%m-%d %H:%M:%S"
        inicio = datetime.strptime(inicio_str, fmt)
        fin    = datetime.strptime(fin_str, fmt)
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
    except Exception:
        return None


def fetch_all_data():
    anio_actual  = datetime.now().year
    fecha_desde  = f"{anio_actual - 1}-01-01"

    # RITM
    raw_ritm = _paginar(
        "sc_req_item",
        "number,cat_item,stage,opened_by,sys_created_on,closed_at",
        f"opened_at>={fecha_desde}^cat_itemIN{CAT_ITEMS}"
    )

    ritm_list = []
    for r in raw_ritm:
        creado  = _val(r.get("sys_created_on", ""))
        cerrado = _val(r.get("closed_at", ""))
        ritm_list.append({
            "numero":      _val(r.get("number", "")),
            "elemento":    _val(r.get("cat_item", "")),
            "etapa":       _val(r.get("stage", "")),
            "solicitante": _val(r.get("opened_by", "")),
            "creado":      creado,
            "cerrado":     cerrado,
            "mes":         creado[:7] if creado else "",
            "anio":        creado[:4] if creado else "",
            "sla":         _horas_habiles(creado, cerrado),
        })

    # Tareas
    raw_tasks = _paginar(
        "sc_task",
        "number,request_item,state,assignment_group,opened_at,closed_at",
        f"opened_at>={fecha_desde}^stateIN-5,3,1^cat_itemIN{CAT_ITEMS}"
    )

    task_sla   = defaultdict(list)
    task_grupo = defaultdict(list)
    task_estado= defaultdict(list)
    for t in raw_tasks:
        ritm = _val(t.get("request_item", ""))
        ini  = _val(t.get("opened_at", ""))
        fin  = _val(t.get("closed_at", ""))
        sla  = _horas_habiles(ini, fin)
        if sla is not None:
            task_sla[ritm].append(sla)
        g = _val(t.get("assignment_group", ""))
        if g:
            task_grupo[ritm].append(g)
        e = _val(t.get("state", ""))
        if e:
            task_estado[ritm].append(e)

    # Aprobaciones
    numeros = {r["numero"] for r in ritm_list}
    raw_aprob = _paginar(
        "sysapproval_approver",
        "state,sysapproval,approver,sys_created_on,sys_updated_on",
        f"sys_created_on>={fecha_desde}"
    )

    aprob_sla   = defaultdict(list)
    aprob_estado= defaultdict(list)
    for a in raw_aprob:
        ritm = _val(a.get("sysapproval", ""))
        if ritm not in numeros:
            continue
        cre = _val(a.get("sys_created_on", ""))
        act = _val(a.get("sys_updated_on", ""))
        sla = _horas_habiles(cre, act)
        if sla is not None:
            aprob_sla[ritm].append(sla)
        e = _val(a.get("state", ""))
        if e:
            aprob_estado[ritm].append(e)

    # Enriquecer RITM
    def prom(lst):
        v = [x for x in lst if x is not None]
        return round(sum(v)/len(v), 1) if v else None

    for r in ritm_list:
        n = r["numero"]
        st = task_sla.get(n)
        sa = aprob_sla.get(n)
        r["sla_tarea"]    = round(sum(st)/len(st), 2) if st else None
        r["sla_aprob"]    = round(max(sa), 2) if sa else None
        r["grupo"]        = ", ".join(set(task_grupo.get(n, [])))
        r["estado_tarea"] = ", ".join(set(task_estado.get(n, [])))
        r["estado_aprob"] = ", ".join(set(aprob_estado.get(n, [])))
        if r["sla_aprob"] and r["sla_tarea"]:
            r["cuello"] = "Aprobación" if r["sla_aprob"] > r["sla_tarea"] else "Tarea"
        elif r["sla_tarea"]:
            r["cuello"] = "Tarea"
        elif r["sla_aprob"]:
            r["cuello"] = "Aprobación"
        else:
            r["cuello"] = "Sin datos"

    # Agrupar
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
                    "vol":  len(rs),
                    "sla":  prom([r["sla"] for r in rs]),
                    "top3": top_n(rs, 3),
                }
                for anio, rs in anios.items()
            }
            for form, anios in por_form.items()
        },
        "top_cuellos_anio_actual":   top_n(por_anio.get(aa, []), 20),
        "top_cuellos_anio_anterior": top_n(por_anio.get(ap, []), 20),
    }
