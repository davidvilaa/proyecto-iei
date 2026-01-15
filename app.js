// URLs APIs ACTUALIZADAS (Puertos y rutas nuevos)
const API_URLS = {
    search: 'http://localhost:5004/api/search',
    load: 'http://localhost:5005/api/load',
    // Actualizamos a los puertos 5020, 5030, 5010 y rutas /records
    wrapperCAT: 'http://localhost:5020/cat/records',
    wrapperGAL: 'http://localhost:5030/gal/records',
    wrapperCV: 'http://localhost:5010/cv/records'
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
        nombre: raw.estaci || raw['NOME DA ESTACIÓN'] || raw['N ESTACIN'] || raw.nombre || 'N/D',
        tipo: raw.operador || raw['TIPO ESTACIÓN'] || raw.tipo || 'Fija',
        direccion: raw.adrea || raw.ENDEREZO || raw.DIRECCIN || raw.direccion || 'N/D',
        localidad: raw.municipi || raw.CONCELLO || raw.MUNICIPIO || raw.localidad || 'N/D',
        cp: raw.cp || raw['CÓDIGO POSTAL'] || raw['C.POSTAL'] || raw.cp || 'N/D',
        provincia: raw.serveis_territorials || raw.PROVINCIA || raw.provincia || 'N/D',
        descripcion: raw.horari_de_servei || raw.HORARIO || raw.HORARIOS || raw.descripcion || '',
        lat: parseCoord(raw.lat, raw.municipi || raw.CONCELLO || raw.localidad || ''),
        lng: parseCoord(raw.long, raw.municipi || raw.CONCELLO || raw.localidad || '')
    };
}

function parseCoord(val, municipio) {
    // Si ya es número válido, devolverlo tal cual (para las nuevas APIs)
    if (typeof val === 'number') return val;
    
    if (!val) return municipio.includes('Barcelona') ? 41.387 : 
                      municipio.includes('Valencia') ? 39.5 : 42.88;
    const num = parseFloat(val);
    // Ajuste para formatos antiguos
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

// SWAGGER ACTUALIZADO
function initSwagger() {
    SwaggerUIBundle({
        spec: {
            openapi: "3.0.0",
            info: { 
                title: "ITV API (Microservicios)", 
                version: "2.0", 
                description: "Arquitectura distribuida: 3 Servicios Regionales + 1 Orquestador + 1 Carga"
            },
            servers: [
                {url: "http://localhost:5020", description: "Microservicio CAT"},
                {url: "http://localhost:5030", description: "Microservicio GAL"},
                {url: "http://localhost:5010", description: "Microservicio CV"},
                {url: "http://localhost:5004", description: "Orquestador Búsqueda"},
                {url: "http://localhost:5005", description: "API Carga"}
            ],
            paths: {
                // Endpoints de Datos Raw (Extractores)
                "/cat/records": {
                    get: {
                        summary: "CAT: Datos Raw (XML)",
                        description: "Devuelve datos crudos del XML. Selecciona servidor CAT (5020).",
                        tags: ["Datos Raw"],
                        responses: { "200": { description: "Lista de registros XML" } }
                    }
                },
                "/gal/records": {
                    get: {
                        summary: "GAL: Datos Raw (CSV)",
                        description: "Devuelve datos crudos del CSV. Selecciona servidor GAL (5030).",
                        tags: ["Datos Raw"],
                        responses: { "200": { description: "Lista de registros CSV" } }
                    }
                },
                "/cv/records": {
                    get: {
                        summary: "CV: Datos Raw (JSON)",
                        description: "Devuelve datos crudos del JSON. Selecciona servidor CV (5010).",
                        tags: ["Datos Raw"],
                        responses: { "200": { description: "Lista de registros JSON" } }
                    }
                },
                // Endpoints de Búsqueda Regionales (NUEVOS)
                "/api/search/cat": {
                    get: {
                        summary: "CAT: Búsqueda Local",
                        description: "Busca solo en Cataluña. Selecciona servidor CAT (5020).",
                        tags: ["Búsqueda Regional"],
                        parameters: [
                            { name: "localidad", in: "query", schema: {type: "string"} },
                            { name: "tipo", in: "query", schema: {type: "string"} }
                        ],
                        responses: { "200": { description: "Resultados normalizados JSON" } }
                    }
                },
                "/api/search/gal": {
                    get: {
                        summary: "GAL: Búsqueda Local",
                        description: "Busca solo en Galicia. Selecciona servidor GAL (5030).",
                        tags: ["Búsqueda Regional"],
                        parameters: [
                            { name: "localidad", in: "query", schema: {type: "string"} },
                            { name: "tipo", in: "query", schema: {type: "string"} }
                        ],
                        responses: { "200": { description: "Resultados normalizados JSON" } }
                    }
                },
                "/api/search/cv": {
                    get: {
                        summary: "CV: Búsqueda Local",
                        description: "Busca solo en Valencia. Selecciona servidor CV (5010).",
                        tags: ["Búsqueda Regional"],
                        parameters: [
                            { name: "localidad", in: "query", schema: {type: "string"} },
                            { name: "tipo", in: "query", schema: {type: "string"} }
                        ],
                        responses: { "200": { description: "Resultados normalizados JSON" } }
                    }
                },
                // Orquestador Global
                "/api/search": {
                    get: {
                        summary: "Orquestador: Búsqueda Global",
                        description: "Consulta a las 3 APIs regionales. Selecciona servidor Orquestador (5004).",
                        tags: ["Orquestador"],
                        parameters: [
                            { name: "localidad", in: "query", schema: {type: "string"} },
                            { name: "tipo", in: "query", schema: {type: "string"} }
                        ],
                        responses: { "200": { description: "Resultados combinados" } }
                    }
                },
                // API Carga
                "/api/load": {
                    post: {
                        summary: "API Carga",
                        description: "Sube archivos. Selecciona servidor Carga (5005).",
                        tags: ["Carga"],
                        requestBody: {
                            content: {
                                "multipart/form-data": {
                                    schema: {
                                        type: "object",
                                        properties: {
                                            archivo: { type: "string", format: "binary" },
                                            fuente: { type: "string", enum: ["CAT XML", "GAL CSV", "CV JSON"] }
                                        }
                                    }
                                }
                            }
                        },
                        responses: { "200": { description: "Resultado carga" } }
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