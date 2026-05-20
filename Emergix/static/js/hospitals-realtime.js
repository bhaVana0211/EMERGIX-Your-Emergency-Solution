/**
 * EMERGIX — Hospitals Realtime JavaScript
 * Listens for live bed count updates and updates the UI.
 */

document.addEventListener('alpine:init', () => {
    Alpine.data('hospitalsRealtime', () => ({
        socket: null,
        isConnected: false,
        
        init() {
            if (typeof io === 'undefined') return;

            this.socket = io({
                reconnection: true,
                reconnectionDelay: 1000
            });

            this.socket.on('connect', () => {
                this.isConnected = true;
                // Patients don't need a specific room to receive broadcast bed updates,
                // but they need it to receive alert acknowledgements.
                this.socket.emit('join_user', {});
            });

            this.socket.on('disconnect', () => {
                this.isConnected = false;
            });

            // Listen for global bed updates
            this.socket.on('bed_updated', (data) => {
                // Dispatch event so the discovery component can update its list
                window.dispatchEvent(new CustomEvent('live-bed-update', { 
                    detail: data 
                }));
            });

            // Listen for specific alert acknowledgements sent to this user
            this.socket.on('alert_acknowledged', (data) => {
                window.dispatchEvent(new CustomEvent('alert-acknowledged', {
                    detail: data
                }));
                
                // Show a toast or alert
                alert(`Hospital ${data.hospital_name} has acknowledged your alert! Please proceed safely.`);
            });
        }
    }));
});
