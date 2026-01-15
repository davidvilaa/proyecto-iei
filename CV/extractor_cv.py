# -*- coding: utf-8 -*-
from __future__ import annotations

import re
import time
import unicodedata
import requests

import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_query import FieldFilter

# -------------------------
# Config
# -------------------------
CV_API_BASE = "http://127.0.0.1:8050"
CV_RECORDS_URL = f"{CV_API_BASE}/cv/records?limit=50"

CREDENTIALS_FILE = "iei-proyecto-firebase-adminsdk-fbsvc-04d774ba06.json"

CP_PREFIJOS_CV = {
    "Castellón": {"12"},
    "Valencia": {"46"},
    "Alicante": {"03"},
}

# -------------------------
# Utilidades (de tu script)
# -------------------------
def warn_if_empty(nombre_campo: str, valor, idx: int) -> None:
    if valor is None or str(valor).strip() == "":
        print(f"[WARN] Registro {idx}: campo '{nombre_campo}' vacío o ausente.")


def normalizar_provincia(nombre_raw: str, idx: int) -> str | None:
    """
    Normaliza provincia a Castellón / Valencia / Alicante ignorando tildes y mayúsculas.
    """
    if not nombre_raw or not nombre_raw.strip():
        print(f"[ERROR] Registro {idx}: provincia vacía.")
        return None

    original = nombre_raw.strip()
    s_norm = "".join(
        c for c in unicodedata.normalize("NFD", original)
        if unicodedata.category(c) != "Mn"
    ).lower()

    if s_norm == "castellon":
        if original != "Castellón":
            print(f"[INFO] Registro {idx}: provincia '{original}' normalizada a 'Castellón'.")
        return "Castellón"
    if s_norm == "valencia":
        if original != "Valencia":
            print(f"[INFO] Registro {idx}: provincia '{original}' normalizada a 'Valencia'.")
        return "Valencia"
    if s_norm == "alicante":
        if original != "Alicante":
            print(f"[INFO] Registro {idx}: provincia '{original}' normalizada a 'Alicante'.")
        return "Alicante"

    print(f"[ERROR] Registro {idx}: provincia '{nombre_raw}' no es Castellón, Valencia ni Alicante.")
    return None


def cp_coincide_con_provincia(cp: str, provincia_nombre: str, idx: int) -> None:
    if not cp or len(cp) < 2 or not provincia_nombre:
        return
    prefijo = cp[:2]
    permitidos = CP_PREFIJOS_CV.get(provincia_nombre, set())
    if permitidos and prefijo not in permitidos:
        print(
            f"[WARN] Registro {idx}: CP '{cp}' no parece corresponder a provincia "
            f"'{provincia_nombre}' (prefijos esperados: {', '.join(sorted(permitidos))})."
        )


def mapear_tipo(tipo_estacion_origen: str) -> str:
    if tipo_estacion_origen == "Estación Fija":
        return "Estación_fija"
    if tipo_estacion_origen == "Estación Móvil":
        return "Estación_movil"
    return "Otros"


def geocodificar(direccion: str, municipio: str, cod_postal: str) -> tuple[str, str]:
    """
    Geocodificación como en tu script:
    - 2 intentos (dirección completa, luego municipio+CP)
    - sleep ~1s para no saturar el servicio
    """
    query_full = f"{direccion}, {municipio}, {cod_postal}, Comunidad Valenciana, España"
    query_simple = f"{municipio}, {cod_postal}, España"

    url = "https://nominatim.openstreetmap.org/search"
    headers = {"User-Agent": "itv-cv-loader/1.0 (contacto@ejemplo.com)"}

    try:
        time.sleep(1.1)
        r = requests.get(url, params={"q": query_full, "format": "json", "limit": 1}, headers=headers, timeout=10)
        data = r.json()
        if data:
            return data[0]["lat"], data[0]["lon"]
    except Exception:
        pass

    try:
        time.sleep(1.1)
        r = requests.get(url, params={"q": query_simple, "format": "json", "limit": 1}, headers=headers, timeout=10)
        data = r.json()
        if data:
            print(f"[INFO] Usando coordenadas del municipio: {query_simple}")
            return data[0]["lat"], data[0]["lon"]
    except Exception:
        pass

    print(f"[WARN] No encontrado ni municipio ni dirección: {query_full}")
    return "0", "0"


def get_starting_counter(db, collection_name: str) -> int:
    docs = db.collection(collection_name).stream()
    max_id = 0
    for doc in docs:
        try:
            num = int(doc.id)
            max_id = max(max_id, num)
        except ValueError:
            pass
    return max_id + 1


def get_first(registro: dict, keys: list[str], default=None):
    for k in keys:
        if k in registro and registro.get(k) is not None:
            return registro.get(k)
    return default


# -------------------------
# I/O: pedir raw al wrapper
# -------------------------
def obtener_registros_raw() -> list[dict]:
    resp = requests.get(CV_RECORDS_URL, timeout=(5, 120))
    resp.raise_for_status()
    return resp.json()


def init_firestore():
    if not firebase_admin._apps:
        cred = credentials.Certificate(CREDENTIALS_FILE)
        firebase_admin.initialize_app(cred)
    return firestore.client()


def main():
    print("[INFO] Extractor CV: pidiendo registros al wrapper...")
    data_cv = obtener_registros_raw()
    if not data_cv:
        print("[ERROR] No hay datos para procesar.")
        return

    db = init_firestore()
    print("[INFO] Conexión a Firebase exitosa.")

    batch = db.batch()
    registros_procesados = 0

    provincia_counter = get_starting_counter(db, "provincias")
    localidad_counter = get_starting_counter(db, "localidades")
    estacion_counter = get_starting_counter(db, "estaciones")

    provincia_ids = {}          # provincia_normalizada -> id
    localidad_ids = {}          # (municipio, provincia_id) -> id
    estacion_ids_vistas = {}    # Nº estación origen -> primer índice visto

    for i, registro in enumerate(data_cv, start=1):
        try:
            raw_provincia = (get_first(registro, ["PROVINCIA"], "") or "").strip()
            warn_if_empty("PROVINCIA", raw_provincia, i)

            cp_value = get_first(registro, ["C.POSTAL", "C. POSTAL", "CÓDIGO POSTAL", "CODIGO POSTAL"], None)
            warn_if_empty("C.POSTAL / C. POSTAL", cp_value, i)

            raw_municipio = (get_first(registro, ["MUNICIPIO"], "") or "").strip()
            warn_if_empty("MUNICIPIO", raw_municipio, i)

            raw_direccion = get_first(
                registro,
                ["DIRECCIÓN", "DIRECCION", "Dirección", "Direccion", "DIRECCI?N"],
                ""
            ) or ""
            warn_if_empty("DIRECCIÓN", raw_direccion, i)

            raw_horarios = get_first(registro, ["HORARIOS"], None)
            warn_if_empty("HORARIOS", raw_horarios, i)

            raw_correo = get_first(registro, ["CORREO", "EMAIL"], None)
            warn_if_empty("CORREO", raw_correo, i)

            raw_cod_estacion = str(
                get_first(registro, ["Nº ESTACIÓN", "Nº ESTACION", "N. ESTACIÓN", "N. ESTACION", "N? ESTACI?N"], "N/A")
            ).strip()
            warn_if_empty("Nº ESTACIÓN", raw_cod_estacion, i)

            # Duplicados por Nº estación
            if raw_cod_estacion and raw_cod_estacion != "N/A":
                if raw_cod_estacion in estacion_ids_vistas:
                    primero = estacion_ids_vistas[raw_cod_estacion]
                    print(f"[WARN] Registro {i}: duplicado Nº ESTACIÓN '{raw_cod_estacion}' (ya estaba en {primero}); se omite.")
                    continue
                estacion_ids_vistas[raw_cod_estacion] = i

            provincia_name = normalizar_provincia(raw_provincia, i)

            cp_str = str(cp_value).strip() if cp_value is not None and str(cp_value).strip() else ""
            cp_valido = True
            if cp_str and not re.fullmatch(r"\d{5}", cp_str):
                print(f"[WARN] Registro {i}: CP '{cp_str}' no tiene 5 dígitos; no se guardará.")
                cp_valido = False

            if provincia_name and cp_valido and re.fullmatch(r"\d{5}", cp_str or ""):
                cp_coincide_con_provincia(cp_str, provincia_name, i)
                prefijo = cp_str[:2]
                permitidos = CP_PREFIJOS_CV.get(provincia_name, set())
                if permitidos and prefijo not in permitidos:
                    cp_valido = False

            omitir_geocodificacion = not raw_municipio or not cp_str

            # PROVINCIA
            if provincia_name is not None:
                if provincia_name not in provincia_ids:
                    provincia_ids[provincia_name] = f"{provincia_counter:04d}"
                    provincia_counter += 1
                p_codigo = provincia_ids[provincia_name]

                batch.set(
                    db.collection("provincias").document(p_codigo),
                    {"codigo": p_codigo, "nombre": provincia_name},
                    merge=True,
                )
            else:
                p_codigo = ""

            # LOCALIDAD
            if raw_municipio:
                municipio_name = raw_municipio.strip().title()
                clave_localidad = (municipio_name, p_codigo)

                if clave_localidad in localidad_ids:
                    l_codigo = localidad_ids[clave_localidad]
                else:
                    query = db.collection("localidades").where(filter=FieldFilter("nombre", "==", municipio_name))
                    if p_codigo:
                        query = query.where(filter=FieldFilter("provincia_codigo", "==", p_codigo))

                    docs_exist = list(query.limit(1).stream())
                    if docs_exist:
                        l_codigo = docs_exist[0].id
                        localidad_ids[clave_localidad] = l_codigo
                    else:
                        l_codigo = f"{localidad_counter:04d}"
                        localidad_counter += 1
                        batch.set(
                            db.collection("localidades").document(l_codigo),
                            {"codigo": l_codigo, "nombre": municipio_name, "provincia_codigo": p_codigo},
                            merge=True,
                        )
                        localidad_ids[clave_localidad] = l_codigo

                tiene_municipio = True
            else:
                print(f"[ERROR] Registro {i}: MUNICIPIO vacío; no se crea localidad ni estación.")
                municipio_name = ""
                l_codigo = ""
                tiene_municipio = False

            # ESTACIÓN
            if raw_cod_estacion == "N/A" or not raw_cod_estacion:
                print(f"[WARN] Registro {i}: sin Nº ESTACIÓN válido; se omite.")
                continue

            if omitir_geocodificacion:
                latitud = ""
                longitud = ""
            else:
                latitud, longitud = geocodificar(raw_direccion, municipio_name, cp_str)

            tipo = mapear_tipo(get_first(registro, ["TIPO ESTACIÓN", "TIPO ESTACION", "TIPO ESTACI?N"], "") or "")

            if not provincia_name:
                print(f"[WARN] Registro {i}: Se omite por falta de PROVINCIA.")
                continue

            if not tiene_municipio:
                print(f"[WARN] Registro {i}: Se omite por falta de MUNICIPIO.")
                continue

            # cp_valido se calculó arriba en tu script
            if not cp_valido or not cp_str:
                print(f"[WARN] Registro {i}: Se omite por falta de CÓDIGO POSTAL válido.")
                continue

            tiene_coords = (latitud not in ["0", ""] and longitud not in ["0", ""])

            if tipo != "Estación_movil" and not tiene_coords:
                print(f"[WARN] Registro {i}: Se omite estación FIJA ({tipo}) sin coordenadas.")
                continue

            if not tiene_municipio:
                nombre_estacion = ""
                descripcion_estacion = ""
            else:
                nombre_estacion = f"Estación de {municipio_name}"
                descripcion_estacion = f"ITV en {municipio_name}. Revisión anual."

            cod_estacion = f"{estacion_counter:05d}"
            estacion_counter += 1

            batch.set(
                db.collection("estaciones").document(cod_estacion),
                {
                    "cod_estacion": cod_estacion,
                    "nombre": nombre_estacion,
                    "direccion": raw_direccion,
                    "codigo_postal": cp_str if cp_valido else "",
                    "longitud": longitud,
                    "latitud": latitud,
                    "tipo": tipo,
                    "descripcion": descripcion_estacion,
                    "horario": raw_horarios or "Consultar web",
                    "contacto": raw_correo or "N/A",
                    "URL": "Sitval.com",
                    "localidad_codigo": l_codigo,
                },
            )

            registros_procesados += 1
            if registros_procesados % 500 == 0:
                print(f"[INFO] Commit batch... {registros_procesados}")
                batch.commit()
                batch = db.batch()

        except Exception as e:
            print(f"[ERROR] Procesando registro {i}: {e}. Datos: {registro}")

    batch.commit()
    print(f"[INFO] Carga finalizada. Total {registros_procesados} estaciones.")


if __name__ == "__main__":
    main()
