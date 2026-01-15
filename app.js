// URLs APIs
const API_URLS = {
    search: 'http://localhost:5004/api/search',
    load: 'http://localhost:5005/api/load',
    wrapperCAT: 'http://localhost:5001/api/wrapper-cat',
    wrapperGAL: 'http://localhost:5002/api/wrapper-gal',
    wrapperCV: 'http://localhost:5003/api/wrapper-cv'
};

let map, markers = [], stationsData = [];

// INICIO
async function startApp() {
    await loadAllData();
    initMap();
    initSwagger();
}

// CARGA DATOS desde API Búsqueda
async function loadAllData() {
    try {
        const response = await fetch(API_URLS.search);
        
        if (!response.ok) {
            console.warn('API Búsqueda devolvió error HTTP:', response.status);
            stationsData = [];
            return;
        }
        
        const data = await response.json();
        
        if (data.status === 'success' && data.results) {
            stationsData = data.results.map(normalizeStation);
            console.log(`✅ ${stationsData.length} estaciones cargadas desde API`);
        } else {
            console.warn('API Búsqueda sin datos válidos:', data);
            stationsData = [];
        }
    } catch(e) {
        console.warn('API Búsqueda no disponible, cargando datos locales');
        stationsData = [];
    }
}

// NORMALIZAR estación (diferentes formatos regiones)
function normalizeStation(raw) {
    return {
        nombre: raw.estaci || raw['NOME DA ESTACIÓN'] || raw['N ESTACIN'] || 'N/D',
        tipo: raw.operador || raw['TIPO ESTACIÓN'] || 'Fija',
        direccion: raw.adrea || raw.ENDEREZO || raw.DIRECCIN || 'N/D',
        localidad: raw.municipi || raw.CONCELLO || raw.MUNICIPIO || 'N/D',
        cp: raw.cp || raw['CÓDIGO POSTAL'] || raw['C.POSTAL'] || 'N/D',
        provincia: raw.serveis_territorials || raw.PROVINCIA || 'N/D',
        descripcion: raw.horari_de_servei || raw.HORARIO || raw.HORARIOS || '',
        lat: parseCoord(raw.lat, raw.municipi || raw.CONCELLO || ''),
        lng: parseCoord(raw.long, raw.municipi || raw.CONCELLO || '')
    };
}

function parseCoord(val, municipio) {
    if (!val) return municipio.includes('Barcelona') ? 41.387 : 
                      municipio.includes('Valencia') ? 39.5 : 42.88;
    const num = parseFloat(val);
    return num > 1000 ? num / 1000000 : num;
}

// MAPA
function initMap() {
    map = L.map('mapaMashup').setView([41, 1.5], 6);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap'
    }).addTo(map);
    
    plotAllStations();
}

function plotAllStations() {
    markers = [];
    stationsData.forEach(station => {
        if (!isNaN(station.lat) && !isNaN(station.lng)) {
            const marker = L.circleMarker([station.lat, station.lng], {
                radius: 6,
                fillColor: '#007cba',
                color: '#fff',
                weight: 2,
                fillOpacity: 0.7
            }).addTo(map).bindPopup(`<b>${station.nombre}</b><br>${station.localidad}`);
            markers.push(marker);
        }
    });
}

// TABS
function showTab(tabName) {
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.getElementById(tabName).classList.add('active');
    event.target.classList.add('active');
}

// BÚSQUEDA
document.getElementById('searchForm').addEventListener('submit', async e => {
    e.preventDefault();
    const formData = new FormData(e.target);
    
    const params = new URLSearchParams({
        localidad: formData.get('localidad') || '',
        cp: formData.get('cp') || '',
        provincia: formData.get('provincia') || '',
        tipo: formData.get('tipo') || ''
    });
    
    try {
        const response = await fetch(`${API_URLS.search}?${params}`);
        const data = await response.json();
        
        if (data.status === 'success' && data.results) {
            const results = data.results.map(normalizeStation);
            displayResults(results);
            updateMapMarkers(results);
        } else if (data.status === 'ok') {
            alert('API funcionando pero sin datos. Verifica archivos JSON.');
            displayResults([]);
        } else {
            alert('Error: ' + (data.message || 'Sin resultados'));
            displayResults([]);
        }
    } catch(e) {
        console.error('Error búsqueda:', e);
        alert('No se pudo conectar con API de búsqueda (puerto 5004)');
    }
});

function displayResults(stations) {
    const tbody = document.querySelector('#resultadosBusqueda tbody');
    tbody.innerHTML = stations.slice(0, 50).map(s => 
        `<tr>
            <td>${s.nombre}</td>
            <td>${s.tipo}</td>
            <td>${s.direccion}</td>
            <td>${s.localidad}</td>
            <td>${s.cp}</td>
            <td>${s.provincia}</td>
            <td>${s.descripcion}</td>
        </tr>`
    ).join('');
}

function updateMapMarkers(stations) {
    markers.forEach(m => map.removeLayer(m));
    markers = [];
    
    stations.slice(0, 50).forEach(s => {
        if (!isNaN(s.lat) && !isNaN(s.lng)) {
            const marker = L.marker([s.lat, s.lng])
                .addTo(map)
                .bindPopup(`<b>${s.nombre}</b><br>${s.localidad} (${s.cp})`);
            markers.push(marker);
        }
    });
    
    if (markers.length) {
        map.fitBounds(markers.map(m => m.getLatLng()));
    }
}

// CARGA
document.getElementById('loadForm').addEventListener('submit', async e => {
    e.preventDefault();
    const formData = new FormData(e.target);
    
    const file = formData.get('archivo');
    if (!file || file.size === 0) {
        alert('Selecciona un archivo válido');
        return;
    }
    
    try {
        const response = await fetch(API_URLS.load, {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            document.getElementById('okCount').textContent = data.registros_ok;
            
            const repBody = document.querySelector('#reparados tbody');
            if (data.detalles_reparados && data.detalles_reparados.length > 0) {
                repBody.innerHTML = data.detalles_reparados.map(d => 
                    `<tr><td colspan="5">${d}</td></tr>`
                ).join('');
            } else {
                repBody.innerHTML = '<tr><td colspan="5" style="text-align:center">No hay errores reparados</td></tr>';
            }
            
            const rejBody = document.querySelector('#rechazados tbody');
            if (data.detalles_rechazados && data.detalles_rechazados.length > 0) {
                rejBody.innerHTML = data.detalles_rechazados.map(d => 
                    `<tr><td colspan="4">${d}</td></tr>`
                ).join('');
            } else {
                rejBody.innerHTML = '<tr><td colspan="4" style="text-align:center">No hay errores rechazados</td></tr>';
            }
            
            alert(`Carga exitosa: ${data.registros_ok} registros cargados`);
        } else {
            alert('Error en carga: ' + data.message);
        }
    } catch(e) {
        console.error('Error carga:', e);
        alert('No se pudo conectar con API de carga (puerto 5005)');
    }
});

// SWAGGER
function initSwagger() {
    SwaggerUIBundle({
        spec: {
            openapi: "3.0.0",
            info: { 
                title: "ITV API", 
                version: "1.0", 
                description: "5 APIs REST independientes para gestión de estaciones ITV"
            },
            servers: [
                {url: "http://localhost:5001", description: "API Wrapper CAT"},
                {url: "http://localhost:5002", description: "API Wrapper GAL"},
                {url: "http://localhost:5003", description: "API Wrapper CV"},
                {url: "http://localhost:5004", description: "API Búsqueda"},
                {url: "http://localhost:5005", description: "API Carga"}
            ],
            paths: {
                "/api/wrapper-cat": {
                    get: {
                        summary: "Wrapper CAT (extractor_cat.py)",
                        description: "Ejecuta extractor de Catalunya (XML) y devuelve datos normalizados",
                        tags: ["Wrappers"],
                        responses: {
                            "200": {
                                description: "Datos Catalunya",
                                content: {
                                    "application/json": {
                                        schema: {
                                            type: "object",
                                            properties: {
                                                status: {type: "string"},
                                                region: {type: "string"},
                                                total_records: {type: "integer"},
                                                data: {type: "array"}
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                },
                "/api/wrapper-gal": {
                    get: {
                        summary: "Wrapper GAL (extractor_gal.py)",
                        description: "Ejecuta extractor de Galicia (CSV) y devuelve datos normalizados",
                        tags: ["Wrappers"],
                        responses: {
                            "200": {description: "Datos Galicia"}
                        }
                    }
                },
                "/api/wrapper-cv": {
                    get: {
                        summary: "Wrapper CV (extractor_cv.py)",
                        description: "Ejecuta extractor de Comunidad Valenciana (JSON) y devuelve datos normalizados",
                        tags: ["Wrappers"],
                        responses: {
                            "200": {description: "Datos Comunidad Valenciana"}
                        }
                    }
                },
                "/api/search": {
                    get: {
                        summary: "API Búsqueda (consume 3 wrappers)",
                        description: "Busca estaciones ITV en las 3 regiones mediante consultas a los wrappers",
                        tags: ["Búsqueda"],
                        parameters: [
                            {
                                name: "localidad",
                                in: "query",
                                description: "Nombre de la localidad",
                                schema: {type: "string"}
                            },
                            {
                                name: "tipo",
                                in: "query",
                                description: "Tipo de estación",
                                schema: {
                                    type: "string",
                                    enum: ["fija", "movil", "otros"]
                                }
                            },
                            {
                                name: "cp",
                                in: "query",
                                description: "Código postal",
                                schema: {type: "string"}
                            },
                            {
                                name: "provincia",
                                in: "query",
                                description: "Nombre de la provincia",
                                schema: {type: "string"}
                            }
                        ],
                        responses: {
                            "200": {
                                description: "Resultados búsqueda",
                                content: {
                                    "application/json": {
                                        schema: {
                                            type: "object",
                                            properties: {
                                                status: {type: "string"},
                                                total_results: {type: "integer"},
                                                results: {type: "array"}
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                },
                "/api/load": {
                    post: {
                        summary: "API Carga (ejecuta extractores)",
                        description: "Recibe archivo (XML/CSV/JSON) y ejecuta el extractor correspondiente según la fuente",
                        tags: ["Carga"],
                        requestBody: {
                            required: true,
                            content: {
                                "multipart/form-data": {
                                    schema: {
                                        type: "object",
                                        properties: {
                                            archivo: {
                                                type: "string",
                                                format: "binary",
                                                description: "Archivo fuente (ITV-CAT.xml, Estacions_ITV.csv, estaciones.json)"
                                            },
                                            fuente: {
                                                type: "string",
                                                enum: ["CAT XML", "GAL CSV", "CV JSON"],
                                                description: "Tipo de fuente de datos"
                                            }
                                        },
                                        required: ["archivo", "fuente"]
                                    }
                                }
                            }
                        },
                        responses: {
                            "200": {
                                description: "Resultado carga",
                                content: {
                                    "application/json": {
                                        schema: {
                                            type: "object",
                                            properties: {
                                                status: {type: "string"},
                                                registros_ok: {type: "integer"},
                                                registros_reparados: {type: "integer"},
                                                registros_rechazados: {type: "integer"},
                                                detalles_reparados: {type: "array"},
                                                detalles_rechazados: {type: "array"}
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        dom_id: '#swagger-container',
        presets: [SwaggerUIBundle.presets.apis, SwaggerUIStandalonePreset]
    });
}

// INICIAR APP
startApp();
