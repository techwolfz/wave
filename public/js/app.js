// Generate a unique ID for this device
const deviceId = 'device-' + Math.random().toString(36).substr(2, 9);
document.getElementById('device-id').textContent = deviceId;

// Initialize Map
const map = L.map('map').setView([0, 0], 2); // Default to world view initially

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
}).addTo(map);

// Store markers for all devices
const markers = {};

// Custom Icon factory
function createCustomIcon(color) {
    return L.divIcon({
        className: 'device-marker',
        html: `
            <div class="marker-pin" style="background-color: ${color};"></div>
            <div class="marker-label">Device</div>
        `,
        iconSize: [24, 24],
        iconAnchor: [12, 24]
    });
}

const myIcon = createCustomIcon('var(--success-color)');
const otherIcon = createCustomIcon('var(--accent-color)');

// WebSocket Connection
let ws;
const statusBadge = document.getElementById('connection-status');

function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;
    
    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        statusBadge.textContent = 'Connected';
        statusBadge.className = 'badge connected';
    };

    ws.onclose = () => {
        statusBadge.textContent = 'Disconnected';
        statusBadge.className = 'badge disconnected';
        // Try to reconnect after 3 seconds
        setTimeout(connectWebSocket, 3000);
    };

    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        ws.close();
    };

    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            if (data.id && data.lat && data.lng) {
                updateOtherDeviceLocation(data);
            }
        } catch (e) {
            console.error('Failed to parse message:', e);
        }
    };
}

connectWebSocket();

function sendLocationUpdate(lat, lng, accuracy) {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
            id: deviceId,
            lat: lat,
            lng: lng,
            accuracy: accuracy,
            timestamp: new Date().toISOString()
        }));
    }
}

function updateOtherDeviceLocation(data) {
    const { id, lat, lng } = data;
    
    if (id === deviceId) return; // Ignore our own echoed messages if any
    
    if (!markers[id]) {
        // Create new marker
        markers[id] = L.marker([lat, lng], { icon: otherIcon }).addTo(map);
        markers[id].bindPopup(`Device: ${id}`);
    } else {
        // Update existing marker
        markers[id].setLatLng([lat, lng]);
    }
}

// Geolocation
let watchId;
let myMarker = null;
let isFirstLocation = true;

const latEl = document.getElementById('lat-val');
const lngEl = document.getElementById('lng-val');
const accEl = document.getElementById('acc-val');
const locateBtn = document.getElementById('locate-me-btn');

function startTracking() {
    if ('geolocation' in navigator) {
        watchId = navigator.geolocation.watchPosition(
            (position) => {
                const lat = position.coords.latitude;
                const lng = position.coords.longitude;
                const accuracy = position.coords.accuracy;

                // Update UI
                latEl.textContent = lat.toFixed(5);
                lngEl.textContent = lng.toFixed(5);
                accEl.textContent = `${Math.round(accuracy)}m`;

                // Update My Marker
                if (!myMarker) {
                    myMarker = L.marker([lat, lng], { icon: myIcon, zIndexOffset: 1000 }).addTo(map);
                    myMarker.bindPopup('You are here').openPopup();
                } else {
                    myMarker.setLatLng([lat, lng]);
                }

                // Center map on first location
                if (isFirstLocation) {
                    map.setView([lat, lng], 15);
                    isFirstLocation = false;
                }

                // Send to server
                sendLocationUpdate(lat, lng, accuracy);
            },
            (error) => {
                console.error('Geolocation error:', error.message);
                alert(`Error getting location: ${error.message}`);
            },
            {
                enableHighAccuracy: true,
                maximumAge: 0,
                timeout: 5000
            }
        );
    } else {
        alert('Geolocation is not supported by your browser');
    }
}

locateBtn.addEventListener('click', () => {
    if (myMarker) {
        map.setView(myMarker.getLatLng(), 15);
    }
});

// Start tracking immediately
startTracking();
