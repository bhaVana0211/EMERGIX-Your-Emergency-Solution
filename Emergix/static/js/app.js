/**
 * EMERGIX — Main App JavaScript
 * Handles geolocation, fetching nearby hospitals, filtering, and UI interactions.
 */

document.addEventListener('alpine:init', () => {
    Alpine.data('hospitalDiscovery', () => ({
        isLoading: true,
        locationStatus: 'Detecting your location...',
        locationError: null,
        hospitals: [],
        filteredHospitals: [],
        
        // Search & Filters
        userLat: null,
        userLng: null,
        userAddress: '',
        radius: 10,
        selectedType: 'all',
        availableOnly: true,
        selectedBedTypes: [],
        searchQuery: '',
        
        // Bed types array for chips
        bedTypes: [
            { id: 'general', label: 'General' },
            { id: 'icu', label: 'ICU' },
            { id: 'oxygen', label: 'Oxygen' },
            { id: 'ventilator', label: 'Ventilator' },
            { id: 'opd', label: 'OPD' },
            { id: 'emergency', label: 'Emergency' },
            { id: 'pediatric', label: 'Pediatric' },
            { id: 'maternity', label: 'Maternity' }
        ],

        init() {
            this.requestLocation();
            
            // Listen for filter changes to refetch or re-filter
            this.$watch('radius', () => this.fetchHospitals());
            this.$watch('selectedType', () => this.fetchHospitals());
            this.$watch('availableOnly', () => this.fetchHospitals());
            this.$watch('selectedBedTypes', () => this.fetchHospitals());
        },

        toggleBedType(typeId) {
            if (this.selectedBedTypes.includes(typeId)) {
                this.selectedBedTypes = this.selectedBedTypes.filter(t => t !== typeId);
            } else {
                this.selectedBedTypes.push(typeId);
            }
        },

        requestLocation() {
            this.isLoading = true;
            this.locationError = null;

            if (!navigator.geolocation) {
                this.locationError = 'Geolocation is not supported by your browser.';
                this.isLoading = false;
                return;
            }

            navigator.geolocation.getCurrentPosition(
                (position) => {
                    this.userLat = position.coords.latitude;
                    this.userLng = position.coords.longitude;
                    this.reverseGeocode(this.userLat, this.userLng);
                    this.fetchHospitals();
                },
                (error) => {
                    console.warn('Geolocation error:', error);
                    this.locationError = 'Could not get your location. Please enter your area manually.';
                    this.isLoading = false;
                },
                { timeout: 10000, maximumAge: 60000, enableHighAccuracy: true }
            );
        },

        async reverseGeocode(lat, lng) {
            try {
                // Use OpenStreetMap Nominatim for free reverse geocoding
                const res = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}&zoom=14`);
                const data = await res.json();
                
                let area = '';
                if (data.address) {
                    area = data.address.suburb || data.address.neighbourhood || data.address.city_district || data.address.city || data.address.town;
                    const city = data.address.city || data.address.town || data.address.county;
                    if (area && city && area !== city) {
                        this.userAddress = `${area}, ${city}`;
                    } else if (city) {
                        this.userAddress = city;
                    } else {
                        this.userAddress = data.display_name.split(',').slice(0,2).join(',');
                    }
                }
            } catch (err) {
                console.error('Reverse geocode failed', err);
                this.userAddress = 'Current Location';
            }
        },

        async manualSearch() {
            if (!this.searchQuery.trim()) return;
            
            this.isLoading = true;
            this.locationError = null;
            this.locationStatus = 'Finding location...';

            try {
                // Forward geocoding
                const res = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(this.searchQuery + ', Odisha, India')}&limit=1`);
                const data = await res.json();

                if (data && data.length > 0) {
                    this.userLat = parseFloat(data[0].lat);
                    this.userLng = parseFloat(data[0].lon);
                    this.userAddress = data[0].display_name.split(',').slice(0, 2).join(',');
                    this.fetchHospitals();
                } else {
                    this.locationError = 'Location not found. Try a different area name.';
                    this.isLoading = false;
                }
            } catch (err) {
                console.error('Search failed', err);
                this.locationError = 'Search failed. Please try again.';
                this.isLoading = false;
            }
        },

        async fetchHospitals() {
            if (!this.userLat || !this.userLng) return;
            
            this.isLoading = true;
            this.locationStatus = 'Loading hospitals...';

            let url = `/api/hospitals/nearby?lat=${this.userLat}&lng=${this.userLng}&radius=${this.radius}&hospital_type=${this.selectedType}&available_only=${this.availableOnly}`;
            
            if (this.selectedBedTypes.length > 0) {
                url += `&bed_type=${this.selectedBedTypes.join(',')}`;
            }

            try {
                const res = await fetch(url);
                const data = await res.json();
                
                if (data.success) {
                    this.hospitals = data.data.hospitals;
                    this.filteredHospitals = this.hospitals; // UI filtering if needed
                }
            } catch (err) {
                console.error('Failed to fetch hospitals', err);
            } finally {
                this.isLoading = false;
            }
        },

        getNavUrl(hospital) {
            return `https://www.google.com/maps/dir/?api=1&origin=${this.userLat},${this.userLng}&destination=${hospital.latitude},${hospital.longitude}&travelmode=driving`;
        },

        getOccupancyClass(pct) {
            if (pct >= 100) return 'progress-danger';
            if (pct >= 80) return 'progress-warning';
            return 'progress-safe';
        }
    }));
});
