# src/gal/extractor_gal.py
from __future__ import annotations

import re
import requests

import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_query import FieldFilter

# =========================
# Config del extractor
# =========================
GAL_API_BASE = "http://127.0.0.1:8001"  # donde levantes api_busqueda_gal.py
GAL_RECORDS_URL = f"{GAL_API_BASE}/gal/records"

CREDENTIALS_FILE = "iei-proyecto-firebase-adminsdk-fbsvc-04d774ba06.json"

# Prefijos de código postal válidos por provincia en Galicia
CP_PREFIJOS_GAL = {
    "A Coruña": {"15"},
    "Lugo": {"27"},
    "Ourense": {"32"},
    "Pontevedra": {"36"},
}





# =========================
# Funciones de tu lógica (reutilizadas)
# =========================
def generar_descripcion(nombre: str, concello: str | None, provincia: str | None) -> str:
    concello_str = concello or "[SIN_CONCELLO]"
    provincia_str = provincia or "[SIN_PROVINCIA]"
    return f"Estación de ITV {nombre} ubicada en {concello_str} ({provincia_str})."


def get_starting_counter(db, collection_name: str) -> int:
    """Devuelve el siguiente ID numérico libre en una colección."""
    docs = db.collection(collection_name).stream()
    max_id = 0
    for doc in docs:
        try:
            num = int(doc.id)
            if num > max_id:
                max_id = num
        except ValueError:
            pass
    return max_id + 1


def warn_if_empty(nombre_campo: str, valor: str, idx: int) -> None:
    if valor is None or str(valor).strip() == "":
        print(f"[WARN] Registro {idx}: campo '{nombre_campo}' vacío o ausente.")


def normalizar_provincia_gal(nombre_raw: str, idx: int) -> str | None:
    """
    Normaliza provincias gallegas a: A Coruña, Lugo, Ourense, Pontevedra.
    Si no coincide, devuelve None.
    """
    if not nombre_raw or not nombre_raw.strip():
        print(f"[ERROR] Registro {idx}: PROVINCIA vacía.")
        return None

    s_low = nombre_raw.strip().lower()

    if s_low in ("a coruña", "la coruña", "a coruna", "la coruna", "coruña", "coruna"):
        if s_low in ("coruña", "coruna"):
            print(f"[INFO] Registro {idx}: provincia '{nombre_raw}' normalizada a 'A Coruña'.")
        return "A Coruña"
    if s_low == "lugo":
        return "Lugo"
    if s_low in ("ourense", "orense"):
        return "Ourense"
    if s_low == "pontevedra":
        return "Pontevedra"

    print(f"[ERROR] Registro {idx}: provincia '{nombre_raw}' no es una provincia válida de Galicia.")
    return None


def cp_coincide_con_provincia(cp: str, provincia_nombre: str, idx: int) -> None:
    """Comprueba si el CP parece corresponder a la provincia (primeros 2 dígitos)."""
    if not cp or len(cp) < 2 or not provincia_nombre:
        return
    prefijo = cp[:2]
    permitidos = CP_PREFIJOS_GAL.get(provincia_nombre, set())
    if permitidos and prefijo not in permitidos:
        print(
            f"[WARN] Registro {idx}: CP '{cp}' no parece corresponder a provincia "
            f"'{provincia_nombre}' (prefijos esperados: {', '.join(sorted(permitidos))})."
        )


def parse_coord_gmaps(coord_str: str):
    """
    Convierte "43° 18.856', -8° 17.165'" en (lat, lon) decimales.
    (Tu dataset venía parecido; si cambia formato, se ajusta aquí.)
    """
    if not coord_str:
        return None, None

    try:
        partes = coord_str.split(",")
        if len(partes) != 2:
            return None, None

        lat_part = partes[0].strip()
        lon_part = partes[1].strip()

        def to_decimal(part: str):
            m = re.match(r"([+-]?\d+)[^\d]+([\d.]+)", part)
            if not m:
                return None
            deg = float(m.group(1))
            minutes = float(m.group(2))
            sign = 1 if deg >= 0 else -1
            return deg + sign * minutes / 60.0

        return to_decimal(lat_part), to_decimal(lon_part)

    except Exception:
        return None, None


# =========================
# 1) Obtener datos raw desde la API del wrapper
# =========================
def obtener_registros_raw() -> list[dict]:
    resp = requests.get(GAL_RECORDS_URL, timeout=60)
    resp.raise_for_status()
    return resp.json()


# =========================
# 2) Cargar a Firestore (temporal)
# =========================
def init_firestore():
    """
    Inicializa Firestore.
    Nota: firebase_admin.initialize_app() solo debe llamarse una vez por proceso.
    """
    if not firebase_admin._apps:
        cred = credentials.Certificate(CREDENTIALS_FILE)
        firebase_admin.initialize_app(cred)
    return firestore.client()


def main():
    print("[INFO] Extractor GAL: pidiendo registros al wrapper...")
    data_gal = obtener_registros_raw()

    if not data_gal:
        print("[ERROR] No hay datos para procesar.")
        return

    print("[INFO] Conectando a Firestore...")
    db = init_firestore()
    print("[INFO] Conexión a Firebase exitosa.")

    batch = db.batch()
    registros_procesados = 0

    provincia_ids = {}
    localidad_ids = {}
    estaciones_por_concello = {}
    nombre_est_vistos = {}

    provincia_counter = get_starting_counter(db, "provincias")
    localidad_counter = get_starting_counter(db, "localidades")
    estacion_counter = get_starting_counter(db, "estaciones")

    print(f"[INFO] Procesando {len(data_gal)} registros raw...")

    for i, registro in enumerate(data_gal, start=1):
        try:
            # ===== Lectura y normalización básica =====
            raw_provincia = (registro.get("PROVINCIA") or "").strip()
            warn_if_empty("PROVINCIA", raw_provincia, i)
            provincia_nombre = normalizar_provincia_gal(raw_provincia, i)

            raw_concello = (registro.get("CONCELLO") or "").strip()
            warn_if_empty("CONCELLO", raw_concello, i)
            concello_norm = raw_concello.strip().title()

            raw_nombre_est = (registro.get("NOME DA ESTACIÓN") or registro.get("NOME DA ESTACI\u00d3N") or "").strip()
            warn_if_empty("NOME DA ESTACIÓN", raw_nombre_est, i)

            raw_enderezo = (registro.get("ENDEREZO") or "").strip()
            warn_if_empty("ENDEREZO", raw_enderezo, i)

            raw_cp = (registro.get("CÓDIGO POSTAL") or registro.get("C\u00d3DIGO POSTAL") or "").strip()
            warn_if_empty("CÓDIGO POSTAL", raw_cp, i)

            cp_valido = True
            if raw_cp and not re.fullmatch(r"\d{5}", raw_cp):
                print(f"[WARN] Registro {i}: CP '{raw_cp}' no tiene 5 dígitos; no se guardará.")
                cp_valido = False

            raw_horario = (registro.get("HORARIO") or "").strip()
            warn_if_empty("HORARIO", raw_horario, i)

            raw_correo = (registro.get("CORREO ELECTRÓNICO") or registro.get("CORREO ELECTR\u00d3NICO") or "").strip()
            warn_if_empty("CORREO ELECTRÓNICO", raw_correo, i)

            raw_url = (registro.get("SOLICITUDE DE CITA PREVIA") or "").strip()
            warn_if_empty("SOLICITUDE DE CITA PREVIA", raw_url, i)

            raw_coords = (registro.get("COORDENADAS GMAPS") or "").strip()

            # ===== Duplicados por nombre de estación (raw) =====
            if raw_nombre_est:
                if raw_nombre_est in nombre_est_vistos:
                    primero = nombre_est_vistos[raw_nombre_est]
                    print(f"[WARN] Registro {i}: duplicado '{raw_nombre_est}' (ya estaba en {primero}); se omite.")
                    continue
                nombre_est_vistos[raw_nombre_est] = i

            # ===== Provincia: creación / reutilización =====
            if provincia_nombre is not None:
                if provincia_nombre in provincia_ids:
                    p_codigo = provincia_ids[provincia_nombre]
                else:
                    docs_prov = list(
                        db.collection("provincias")
                        .where(filter=FieldFilter("nombre", "==", provincia_nombre))
                        .limit(1)
                        .stream()
                    )
                    if docs_prov:
                        p_codigo = docs_prov[0].id
                        provincia_ids[provincia_nombre] = p_codigo
                    else:
                        p_codigo = f"{provincia_counter:04d}"
                        provincia_counter += 1
                        batch.set(
                            db.collection("provincias").document(p_codigo),
                            {"codigo": p_codigo, "nombre": provincia_nombre},
                            merge=True,
                        )
                        provincia_ids[provincia_nombre] = p_codigo
            else:
                p_codigo = ""

            # Validación CP–provincia solo si el CP es válido
            if provincia_nombre and cp_valido and re.fullmatch(r"\d{5}", raw_cp or ""):
                cp_coincide_con_provincia(raw_cp, provincia_nombre, i)
                prefijo = raw_cp[:2]
                permitidos = CP_PREFIJOS_GAL.get(provincia_nombre, set())
                if permitidos and prefijo not in permitidos:
                    cp_valido = False  # lo invalidamos (como ya hacías)

            # ===== Localidad (concello) =====
            if concello_norm:
                if concello_norm in localidad_ids:
                    l_codigo = localidad_ids[concello_norm]
                else:
                    docs_loc = list(
                        db.collection("localidades")
                        .where(filter=FieldFilter("nombre", "==", concello_norm))
                        .limit(1)
                        .stream()
                    )
                    if docs_loc:
                        l_codigo = docs_loc[0].id
                        localidad_ids[concello_norm] = l_codigo
                    else:
                        l_codigo = f"{localidad_counter:04d}"
                        localidad_counter += 1
                        batch.set(
                            db.collection("localidades").document(l_codigo),
                            {"codigo": l_codigo, "nombre": concello_norm, "provincia_codigo": p_codigo},
                            merge=True,
                        )
                        localidad_ids[concello_norm] = l_codigo
                tiene_concello = True
            else:
                print(f"[ERROR] Registro {i}: CONCELLO vacío; no se crea localidad ni estación.")
                l_codigo = ""
                tiene_concello = False

            # ===== Estación =====
            if not tiene_concello:
                nombre_estacion = ""
                descripcion = ""
            else:
                count_prev = estaciones_por_concello.get(concello_norm, 0)
                nuevo_indice = count_prev + 1
                estaciones_por_concello[concello_norm] = nuevo_indice

                nombre_estacion = (
                    f"Estación de {concello_norm}" if nuevo_indice == 1 else f"Estación de {concello_norm} {nuevo_indice}"
                )
                descripcion = generar_descripcion(nombre_estacion, concello_norm, provincia_nombre or "")

            # Coordenadas + validación rango
            latitud, longitud = parse_coord_gmaps(raw_coords)
            if latitud is None or longitud is None:
                latitud, longitud = "", ""
            else:
                if not (-90.0 <= latitud <= 90.0) or not (-180.0 <= longitud <= 180.0):
                    latitud, longitud = "", ""

            cod_estacion = f"{estacion_counter:05d}"
            estacion_counter += 1

            estacion_data = {
                "nombre": nombre_estacion,
                "cod_estacion": cod_estacion,
                "direccion": raw_enderezo,
                "codigo_postal": raw_cp if cp_valido else "",
                "longitud": longitud,
                "latitud": latitud,
                "tipo": "Estación_fija",
                "descripcion": descripcion,
                "horario": raw_horario or "Consultar web",
                "contacto": raw_correo or "N/A",
                "URL": raw_url,
                "localidad_codigo": l_codigo,
            }

            batch.set(db.collection("estaciones").document(cod_estacion), estacion_data)

            registros_procesados += 1
            if registros_procesados % 500 == 0:
                print(f"[INFO] Commit batch... {registros_procesados} registros")
                batch.commit()
                batch = db.batch()

        except Exception as e:
            print(f"[ERROR] Registro {i}: {e}. Datos: {registro}")

    batch.commit()
    print(f"[INFO] Carga finalizada. Total: {registros_procesados} estaciones.")


if __name__ == "__main__":
    main()





