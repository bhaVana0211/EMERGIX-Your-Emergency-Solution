/**
 * EMERGIX — Alert Modal JavaScript
 * Alpine.js component for handling the pre-arrival alert form.
 */

document.addEventListener('alpine:init', () => {
    Alpine.data('alertModal', () => ({
        isOpen: false,
        isSubmitting: false,
        isSuccess: false,
        hospital: null,
        bookingRef: '',
        error: null,

        // Form fields
        formData: {
            patient_name: '',
            patient_age: '',
            patient_gender: 'male',
            bed_type_needed: 'general',
            contact_phone: '',
            notes: '',
            est_arrival_min: 30,
            user_lat: null,
            user_lng: null
        },

        openModal(hospitalData, preselectedBedType = 'general', uLat = null, uLng = null) {
            this.hospital = hospitalData;
            this.formData.bed_type_needed = preselectedBedType;
            this.formData.user_lat = uLat;
            this.formData.user_lng = uLng;
            
            // Try to pre-fill from global window object if rendered in template
            if (window.currentUser) {
                this.formData.patient_name = window.currentUser.name || '';
                this.formData.contact_phone = window.currentUser.phone || '';
            }

            this.isSuccess = false;
            this.error = null;
            this.isOpen = true;
            document.body.style.overflow = 'hidden'; // prevent background scrolling
        },

        closeModal() {
            this.isOpen = false;
            document.body.style.overflow = '';
            // Reset form after animation
            setTimeout(() => {
                this.isSuccess = false;
                this.hospital = null;
                this.error = null;
            }, 300);
        },

        async submitAlert() {
            this.isSubmitting = true;
            this.error = null;

            const payload = {
                hospital_id: this.hospital.id,
                ...this.formData
            };

            // Ensure types
            if (payload.patient_age) payload.patient_age = parseInt(payload.patient_age);
            payload.est_arrival_min = parseInt(payload.est_arrival_min);

            try {
                const res = await fetch('/api/alerts/create', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(payload)
                });

                const data = await res.json();

                if (res.ok && data.success) {
                    this.bookingRef = data.data.booking_ref;
                    this.isSuccess = true;
                } else {
                    this.error = data.error || 'Failed to send alert. Please try again.';
                }
            } catch (err) {
                console.error('Alert submission error:', err);
                this.error = 'Network error. Please check your connection and try again.';
            } finally {
                this.isSubmitting = false;
            }
        }
    }));
});
