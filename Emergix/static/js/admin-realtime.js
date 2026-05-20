/**
 * EMERGIX — Admin Realtime JavaScript
 * Handles Socket.IO connection for hospital admin dashboard to receive live alerts.
 */

document.addEventListener('alpine:init', () => {
    Alpine.data('adminRealtime', (hospitalId) => ({
        socket: null,
        isConnected: false,
        reconnectAttempts: 0,
        
        init() {
            if (typeof io === 'undefined') {
                console.error('Socket.IO script not loaded');
                return;
            }

            // Connect to WebSocket server
            this.socket = io({
                reconnection: true,
                reconnectionDelay: 1000,
                reconnectionDelayMax: 5000,
                reconnectionAttempts: Infinity
            });

            this.setupSocketListeners();
        },

        setupSocketListeners() {
            this.socket.on('connect', () => {
                this.isConnected = true;
                this.reconnectAttempts = 0;
                console.log('Connected to real-time server');
                // The server automatically joins the room based on session, 
                // but we can explicitly request if needed
                this.socket.emit('join_hospital', { hospital_id: hospitalId });
            });

            this.socket.on('disconnect', () => {
                this.isConnected = false;
                console.warn('Disconnected from real-time server');
            });

            this.socket.on('new_alert', (alertData) => {
                console.log('New alert received:', alertData);
                
                // Dispatch custom event that Alpine components can listen to
                window.dispatchEvent(new CustomEvent('new-alert-received', { 
                    detail: alertData 
                }));

                // Optional: HTML5 Notification if permission granted
                this.showBrowserNotification(alertData);
            });
        },

        showBrowserNotification(alertData) {
            if (!("Notification" in window)) return;

            const title = `New Alert: ${alertData.bed_type_needed.toUpperCase()} needed`;
            const options = {
                body: `${alertData.patient_name} arriving in ~${alertData.est_arrival_min} mins.\nTap to view details.`,
                icon: '/static/images/logo.png', // Fallback gracefully if not exists
                tag: alertData.booking_ref
            };

            if (Notification.permission === "granted") {
                new Notification(title, options);
            } else if (Notification.permission !== "denied") {
                Notification.requestPermission().then(permission => {
                    if (permission === "granted") {
                        new Notification(title, options);
                    }
                });
            }
        },

        async updateAlertStatus(alertId, status) {
            try {
                const res = await fetch(`/api/admin/alerts/${alertId}/status`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ status })
                });
                const data = await res.json();
                return data.success;
            } catch (err) {
                console.error('Failed to update status', err);
                return false;
            }
        }
    }));
});
