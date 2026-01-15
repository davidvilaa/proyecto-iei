# src/cat/extractor_cat.py
from __future__ import annotations

import re
import unicodedata
import requests

import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_query import FieldFilter

# -------------------------
# Config
# -------------------------
CAT_API_BASE = "http://127.0.0.1:8002"
CAT_RECORDS_URL = f"{CAT_API_BASE}/cat/records"

CREDENTIALS_FILE = "iei-proyecto-firebase-adminsdk-fbsvc-04d774ba06.json"

CP_PREFIJOS_CAT = {
    "Barcelona": {"08"},
    "Girona": {"17"},
    "Lleida": {"25"},
    "Tarragona": {"43"},
}




# -------------------------
# Utilidades (de tu script)
# -------------------------
def warn_if_empty(nombre_campo: str, valor, idx: int) -> None:
    if valor is None or str(valor).strip() == "":
        print(f"[WARN] Registro {idx}: campo '{nombre_campo}' vacío o ausente.")


def normalizar_provincia_cat(nombre_raw: str, idx: int) -> str | None:
    """
    Normaliza provincia a Barcelona / Girona / Lleida / Tarragona (ignorando tildes y mayúsculas).
    """
    if not nombre_raw or not nombre_raw.strip():
        print(f"[ERROR] Registro {idx}: provincia vacía.")
        return None

    s = nombre_raw.strip()
    s_norm = "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    ).lower()

    if s_norm == "barcelona":
        return "Barcelona"
    if s_norm == "girona":
        return "Girona"
    if s_norm in ("lleida", "lerida"):
        return "Lleida"
    if s_norm == "tarragona":
        return "Tarragona"

    print(f"[ERROR] Registro {idx}: provincia '{nombre_raw}' no es una provincia válida de Catalunya.")
    return None


def cp_coincide_con_provincia(cp: str, provincia_nombre: str, idx: int) -> None:
    if not cp or len(cp) < 2 or not provincia_nombre:
        return
    prefijo = cp[:2]
    permitidos = CP_PREFIJOS_CAT.get(provincia_nombre, set())
    if permitidos and prefijo not in permitidos:
        print(
            f"[WARN] Registro {idx}: CP '{cp}' no coincide con provincia '{provincia_nombre}' "
            f"(prefijos esperados: {', '.join(sorted(permitidos))})."
        )


def traducir_horario(horario_texto: str) -> str:
    """
    En tu script era muy simple; aquí lo dejamos igual.
    Si queréis, podéis ampliar traducciones catalán->castellano.
    """
    if not horario_texto:
        return "Horario no especificado"
    return horario_texto.replace("dilluns", "Lunes")


def ajustar_contacto(correo_origen: str) -> str:
    if not correo_origen:
        return "contacto@default.com"

    email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"
    if re.fullmatch(email_regex, correo_origen.strip()):
        return correo_origen.strip()

    print(f"[WARN] El contacto '{correo_origen}' no es un email válido. Usando placeholder.")
    return f"INVALID_CONTACT_{correo_origen}"


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


# -------------------------
# I/O: pedir raw al wrapper
# -------------------------
def obtener_registros_raw() -> list[dict]:
    resp = requests.get(CAT_RECORDS_URL, timeout=60)
    resp.raise_for_status()
    return resp.json()


def init_firestore():
    # Importante: initialize_app solo una vez por proceso
    if not firebase_admin._apps:
        cred = credentials.Certificate(CREDENTIALS_FILE)
        firebase_admin.initialize_app(cred)
    return firestore.client()


def main():
    print("[INFO] Extractor CAT: pidiendo registros al wrapper...")
    data_cat = obtener_registros_raw()
    if not data_cat:
        print("[ERROR] No hay datos para procesar.")
        return

    db = init_firestore()
    print("[INFO] Conexión a Firebase exitosa.")

    batch = db.batch()
    registros_procesados = 0

    provincia_counter = get_starting_counter(db, "provincias")
    localidad_counter = get_starting_counter(db, "localidades")
    estacion_counter = get_starting_counter(db, "estaciones")

    provincia_ids = {}              # provincia_normalizada -> id
    localidad_ids = {}              # municipio -> id (como lo tenías)
    estaci_vistas = {}              # estaci -> primer índice (para duplicados)
    estaciones_por_municipio = {}   # municipio -> contador

    for i, registro in enumerate(data_cat, start=1):
        try:
            # ===== Lectura campos raw (del wrapper) =====
            raw_provincia = (registro.get("serveis_territorials") or "").strip()
            warn_if_empty("serveis_territorials (provincia)", raw_provincia, i)

            municipio_raw = (registro.get("municipi") or "").strip()
            warn_if_empty("municipi", municipio_raw, i)
            municipio_norm = municipio_raw.title()

            raw_direccion = registro.get("adre_a", "")
            warn_if_empty("adre_a (dirección)", raw_direccion, i)

            raw_cp = (registro.get("cp") or "").strip()
            warn_if_empty("cp", raw_cp, i)

            cp_valido = True
            if raw_cp and not re.fullmatch(r"\\d{5}", raw_cp):
                print(f"[WARN] Registro {i}: CP '{raw_cp}' no tiene 5 dígitos; no se guardará.")
                cp_valido = False

            raw_horario = registro.get("horari_de_servei", "")
            warn_if_empty("horari_de_servei", raw_horario, i)

            raw_correo = registro.get("correu_electr_nic", "")
            warn_if_empty("correu_electr_nic", raw_correo, i)

            raw_tel = (registro.get("tel_atenc_public") or "").strip()
            warn_if_empty("tel_atenc_public", raw_tel, i)

            raw_estaci = (registro.get("estaci") or "").strip()
            warn_if_empty("estaci", raw_estaci, i)

            # ===== Duplicados por 'estaci' =====
            if raw_estaci:
                if raw_estaci in estaci_vistas:
                    primero = estaci_vistas[raw_estaci]
                    print(f"[WARN] Registro {i}: duplicado estaci '{raw_estaci}' (ya estaba en {primero}); se omite.")
                    continue
                estaci_vistas[raw_estaci] = i

            # ===== Provincia =====
            provincia_nombre = normalizar_provincia_cat(raw_provincia, i)
            if provincia_nombre is not None:
                if provincia_nombre in provincia_ids:
                    p_codigo = provincia_ids[provincia_nombre]
                else:
                    # Reutilización si ya existe en BD
                    docs_prov = list(
                        db.collection("provincias")
                        .where(filter=FieldFilter("nombre", "==", provincia_nombre))
                        .limit(1)
                        .stream()
                    )
                    if docs_prov:
                        p_codigo = docs_prov[0].id
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

            # Coherencia CP-provincia
            if provincia_nombre and cp_valido and re.fullmatch(r"\\d{5}", raw_cp or ""):
                cp_coincide_con_provincia(raw_cp, provincia_nombre, i)
                prefijo = raw_cp[:2]
                permitidos = CP_PREFIJOS_CAT.get(provincia_nombre, set())
                if permitidos and prefijo not in permitidos:
                    cp_valido = False

            # ===== Localidad =====
            if municipio_raw:
                if municipio_norm in localidad_ids:
                    l_codigo = localidad_ids[municipio_norm]
                else:
                    docs_loc = list(
                        db.collection("localidades")
                        .where(filter=FieldFilter("nombre", "==", municipio_norm))
                        .limit(1)
                        .stream()
                    )
                    if docs_loc:
                        l_codigo = docs_loc[0].id
                    else:
                        l_codigo = f"{localidad_counter:04d}"
                        localidad_counter += 1
                        batch.set(
                            db.collection("localidades").document(l_codigo),
                            {"codigo": l_codigo, "nombre": municipio_norm, "provincia_codigo": p_codigo},
                            merge=True,
                        )
                    localidad_ids[municipio_norm] = l_codigo
                tiene_municipio = True
            else:
                print(f"[ERROR] Registro {i}: municipio vacío; se omite nombre/descripcion.")
                l_codigo = ""
                tiene_municipio = False

            # ===== Coordenadas (en tu XML venían en micro-unidades) =====
            long_raw = float(registro.get("long", 0) or 0)
            lat_raw = float(registro.get("lat", 0) or 0)
            longitud = str(long_raw / 1_000_000.0)
            latitud = str(lat_raw / 1_000_000.0)

            # ===== Estación =====
            if tiene_municipio:
                count_prev = estaciones_por_municipio.get(municipio_norm, 0)
                nuevo_indice = count_prev + 1
                estaciones_por_municipio[municipio_norm] = nuevo_indice
                nombre_estacion = (
                    f"Estación de {municipio_norm}"
                    if nuevo_indice == 1
                    else f"Estación de {municipio_norm} {nuevo_indice}"
                )
                descripcion = f"ITV en {municipio_norm}. Revisión anual."
            else:
                nombre_estacion = ""
                descripcion = ""

            contacto_final = raw_tel if raw_tel else ajustar_contacto(raw_correo)

            cod_estacion = f"{estacion_counter:05d}"
            estacion_counter += 1

            batch.set(
                db.collection("estaciones").document(cod_estacion),
                {
                    "nombre": nombre_estacion,
                    "cod_estacion": cod_estacion,
                    "direccion": raw_direccion,
                    "codigo_postal": raw_cp if cp_valido else "",
                    "longitud": longitud,
                    "latitud": latitud,
                    "tipo": "Estación_fija",
                    "descripcion": descripcion,
                    "horario": traducir_horario(raw_horario),
                    "contacto": contacto_final,
                    "URL": registro.get("web", ""),
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





