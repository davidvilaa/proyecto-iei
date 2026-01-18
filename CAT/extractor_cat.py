from __future__ import annotations

import re
import unicodedata
import requests
import os

import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_query import FieldFilter

# -------------------------
# Configuración
# -------------------------
CAT_API_BASE = "http://127.0.0.1:8040" 
CAT_RECORDS_URL = f"{CAT_API_BASE}/cat/records"

# Ruta de credenciales
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) 
PROJECT_ROOT = os.path.dirname(BASE_DIR)              
CREDENTIALS_FILE = os.path.join(PROJECT_ROOT, "iei-proyecto-firebase-adminsdk-fbsvc-04d774ba06.json")

# -------------------------
# Utilidades
# -------------------------
def normalizar_provincia_cat(nombre_raw: str) -> str | None:
    if not nombre_raw or not nombre_raw.strip():
        return None

    s = nombre_raw.strip()
    s_norm = "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    ).lower()

    if s_norm == "barcelona": return "Barcelona"
    if s_norm == "girona": return "Girona"
    if s_norm in ("lleida", "lerida"): return "Lleida"
    if s_norm == "tarragona": return "Tarragona"
    return None

def traducir_horario(horario_texto: str) -> str:
    if not horario_texto: return "Horario no especificado"
    return horario_texto.replace("dilluns", "Lunes").replace("divendres", "Viernes")

def ajustar_contacto(correo_origen: str) -> str:
    if not correo_origen: return "contacto@default.com"
    email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if re.fullmatch(email_regex, correo_origen.strip()):
        return correo_origen.strip()
    return f"INVALID_CONTACT_{correo_origen}"

def get_starting_counter(db, collection_name: str) -> int:
    docs = db.collection(collection_name).stream()
    max_id = 0
    for doc in docs:
        try:
            num = int(doc.id)
            max_id = max(max_id, num)
        except ValueError: pass
    return max_id + 1

def get_existing_names(db, collection_name: str) -> set[str]:
    """Devuelve un conjunto (set) con los nombres de las estaciones que ya existen en la BD."""
    existing = set()
    # Pedimos solo el campo 'nombre' para que sea más rápido y ligero
    docs = db.collection(collection_name).select(["nombre"]).stream()
    for doc in docs:
        data = doc.to_dict()
        if "nombre" in data:
            existing.add(data["nombre"])
    return existing

# --- FUNCIÓ CLAU PER ARREGLAR VILADECANS ---
def ajustar_coordenada(valor_float: float, es_latitud: bool) -> float:
    """
    Ajusta la magnitud del número (dividiendo o multiplicando por 10)
    hasta que encaje en las coordenadas lógicas de Catalunya.
    Esto arregla la mezcla de formatos de 6 y 8 cifras del XML.
    """
    if valor_float == 0: return 0.0
    
    # Rangos aproximados (seguridad) para Catalunya
    min_val = 39.0 if es_latitud else 0.0
    max_val = 44.0 if es_latitud else 4.0
    
    val = valor_float
    
    # 1. Si es demasiado grande (ej: 413028 -> 41.3)
    while abs(val) > max_val:
        val /= 10.0
        
    # 2. Si es demasiado pequeño por haber dividido demasiado antes (ej: 0.41 -> 41.0)
    # (Aunque con la lógica actual esto pasa menos, es por seguridad)
    while abs(val) < min_val and val != 0:
        val *= 10.0
        
    return val

# -------------------------
# Main
# -------------------------
def obtener_registros_raw() -> list[dict]:
    try:
        print(f"[INFO] Conectando a {CAT_RECORDS_URL}...")
        resp = requests.get(CAT_RECORDS_URL, timeout=60)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"[ERROR] Fallo al conectar con el Wrapper: {e}")
        return []

def init_firestore():
    if not firebase_admin._apps:
        cred = credentials.Certificate(CREDENTIALS_FILE)
        firebase_admin.initialize_app(cred)
    return firestore.client()

def main():
    print("[INFO] Extractor CAT: Iniciando proceso...")
    data_cat = obtener_registros_raw()
    
    if not data_cat:
        print(f"[ERROR] No hay datos. Revisa puerto 8040.")
        return

    try:
        db = init_firestore()
        print("[INFO] Conexión a Firebase exitosa.")
    except Exception as e:
        print(f"[ERROR] Error conectando a Firebase: {e}")
        return

    batch = db.batch()
    registros_insertados = 0

    provincia_counter = get_starting_counter(db, "provincias")
    localidad_counter = get_starting_counter(db, "localidades")
    estacion_counter = get_starting_counter(db, "estaciones")

    nombres_existentes = get_existing_names(db, "estaciones")

    provincia_ids = {}
    localidad_ids = {}
    estaci_vistas = {}
    estaciones_por_municipio = {}

    print(f"[INFO] Procesando {len(data_cat)} registros...")

    for i, registro in enumerate(data_cat, start=1):
        try:
            # 1. Identificador básico
            raw_estaci = (registro.get("estaci") or "").strip()
            
            # --- CONTROL DUPLICADOS ---
            if raw_estaci:
                if raw_estaci in estaci_vistas:
                    continue
                estaci_vistas[raw_estaci] = i

            # --- PROVINCIA ---
            raw_provincia = (registro.get("serveis_territorials") or "").strip()
            provincia_nombre = normalizar_provincia_cat(raw_provincia)
            if not provincia_nombre:
                print(f"[WARN] Registro {i}: Provincia inexistente. NO SE GUARDA EN BD")
                continue

            # --- MUNICIPIO ---
            municipio_raw = (registro.get("municipi") or "").strip()
            if not municipio_raw:
                print(f"[WARN] Registro {i}: Municipio inexistente. NO SE GUARDA EN BD")
                continue
            municipio_norm = municipio_raw.title()

            # Nombre estación
            count_prev = estaciones_por_municipio.get(municipio_norm, 0)
            nuevo_indice = count_prev + 1
            sufijo = f" {nuevo_indice}" if nuevo_indice > 1 else ""
            nombre_estacion = f"Estación de {municipio_norm}{sufijo}"

            if nombre_estacion in nombres_existentes:
                print(f"[SKIP] Datos repetidos (ya en BD): {nombre_estacion}")
                continue

            # --- CÓDIGO POSTAL ---
            raw_cp = (registro.get("cp") or "").strip()
            if raw_cp and raw_cp.isdigit() and len(raw_cp) < 5:
                raw_cp = raw_cp.zfill(5)
            
            cp_valido = bool(raw_cp and re.fullmatch(r"\d{5}", raw_cp))
            if not cp_valido:
                print(f"[WARN] Registro {i} ({nombre_estacion}): Codigo postal inexistente. NO SE GUARDA EN BD")
                continue

            # --- GEOLOCALIZACIÓN INTELIGENTE ---
            # Detección de móvil
            denominacion = (registro.get("denominaci", "") or "").lower()
            es_movil = "mòbil" in denominacion or "móvil" in denominacion or "mòbil" in nombre_estacion.lower()
            tipo_estacion = "Estación_movil" if es_movil else "Estación_fija"

            # Extracción desde geocoded_column POINT(LON LAT)
            geocoded = registro.get("geocoded_column", "")
            match_geo = re.search(r"POINT\s*\(\s*([-\d]+)\s+([-\d]+)\s*\)", geocoded)
            
            lat_val = 0.0
            lon_val = 0.0

            if match_geo:
                # Obtenemos los enteros crudos (ej: 413028 o 41357138)
                raw_lon = float(match_geo.group(1))
                raw_lat = float(match_geo.group(2))
                
                # Ajustamos magnitud automáticamente para que sean coordenadas GPS válidas
                lon_val = ajustar_coordenada(raw_lon, es_latitud=False)
                lat_val = ajustar_coordenada(raw_lat, es_latitud=True)
            else:
                # Intentamos fallback a campos lat/long individuales
                try:
                    raw_lon = float(registro.get("long", 0) or 0)
                    raw_lat = float(registro.get("lat", 0) or 0)
                    lon_val = ajustar_coordenada(raw_lon, es_latitud=False)
                    lat_val = ajustar_coordenada(raw_lat, es_latitud=True)
                except:
                    pass

            # FILTRO GEOGRÁFICO
            dentro_cat = (40.0 <= lat_val <= 44.0) and (0.0 <= lon_val <= 4.0)

            if not es_movil and not dentro_cat:
                if lat_val != 0 or lon_val != 0:
                    print(f"[WARN] Registro {i} ({nombre_estacion}): Coordenadas fuera de Cataluña ({lat_val}, {lon_val}). NO SE GUARDA EN BD")
                else:
                    print(f"[WARN] Registro {i} ({nombre_estacion}): Coordenadas vacías (0,0). NO SE GUARDA EN BD")
                continue

            longitud = str(lon_val)
            latitud = str(lat_val)

            # -------------------------------------------------------------------
            # GUARDADO
            # -------------------------------------------------------------------
            
            # Actualizar contadores
            estaciones_por_municipio[municipio_norm] = nuevo_indice

            # Provincia
            if provincia_nombre in provincia_ids:
                p_codigo = provincia_ids[provincia_nombre]
            else:
                docs_prov = list(db.collection("provincias").where(filter=FieldFilter("nombre", "==", provincia_nombre)).limit(1).stream())
                if docs_prov:
                    p_codigo = docs_prov[0].id
                else:
                    p_codigo = f"{provincia_counter:04d}"
                    provincia_counter += 1
                    batch.set(db.collection("provincias").document(p_codigo), {"codigo": p_codigo, "nombre": provincia_nombre}, merge=True)
                provincia_ids[provincia_nombre] = p_codigo

            # Localidad
            if municipio_norm in localidad_ids:
                l_codigo = localidad_ids[municipio_norm]
            else:
                docs_loc = list(db.collection("localidades").where(filter=FieldFilter("nombre", "==", municipio_norm)).limit(1).stream())
                if docs_loc:
                    l_codigo = docs_loc[0].id
                else:
                    l_codigo = f"{localidad_counter:04d}"
                    localidad_counter += 1
                    batch.set(db.collection("localidades").document(l_codigo), {"codigo": l_codigo, "nombre": municipio_norm, "provincia_codigo": p_codigo}, merge=True)
                localidad_ids[municipio_norm] = l_codigo

            # Estación
            raw_direccion = registro.get("adre_a", "")
            raw_horario = registro.get("horari_de_servei", "")
            raw_correo = registro.get("correu_electr_nic", "")
            raw_tel = (registro.get("tel_atenc_public") or "").strip()
            contacto_final = raw_tel if raw_tel else ajustar_contacto(raw_correo)

            cod_estacion = f"{estacion_counter:05d}"
            estacion_counter += 1

            batch.set(
                db.collection("estaciones").document(cod_estacion),
                {
                    "nombre": nombre_estacion,
                    "cod_estacion": cod_estacion,
                    "direccion": raw_direccion,
                    "codigo_postal": raw_cp, 
                    "longitud": longitud,
                    "latitud": latitud,
                    "tipo": tipo_estacion,
                    "descripcion": f"ITV en {municipio_norm}. Revisión anual.",
                    "horario": traducir_horario(raw_horario),
                    "contacto": contacto_final,
                    "URL": str(registro.get("web", "")),
                    "localidad_codigo": l_codigo,
                },
            )

            registros_insertados += 1
            if registros_insertados % 500 == 0:
                print(f"[INFO] Insertados {registros_insertados}...")
                batch.commit()
                batch = db.batch()

        except Exception as e:
            print(f"[ERROR] Excepción registro {i}: {e}")

    batch.commit()
    print(f"[INFO] Carga finalizada. {registros_insertados} estaciones insertadas.")

if __name__ == "__main__":
    main()