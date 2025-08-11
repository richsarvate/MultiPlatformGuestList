/**
 * API Module - Handle all API calls to the backend
 * Clean separation of API logic from UI logic
 */

class ApiClient {
    constructor(baseUrl = '') {
        this.baseUrl = baseUrl;
    }

    async get(endpoint) {
        const response = await fetch(`${this.baseUrl}${endpoint}`);
        return await response.json();
    }

    async post(endpoint, data) {
        const response = await fetch(`${this.baseUrl}${endpoint}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });
        return await response.json();
    }

    async put(endpoint, data) {
        const response = await fetch(`${this.baseUrl}${endpoint}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });
        return await response.json();
    }

    // Health and basic info
    async getHealth() {
        return await this.get('/api/health');
    }

    async getRecentShow() {
        return await this.get('/api/recent');
    }

    // Venue operations
    async getVenues() {
        return await this.get('/api/venues/');
    }

    async getVenuePaymentInfo(venue) {
        return await this.get(`/api/venues//${encodeURIComponent(venue)}/payment-info`);
    }

    async updateVenuePayment(venue, showDate, paid) {
        return await this.put(`/api/venues//${encodeURIComponent(venue)}/payment`, {
            show_date: showDate,
            paid: paid
        });
    }

    // Show operations
    async getShows(venue) {
        return await this.get(`/api/shows/?venue=${encodeURIComponent(venue)}`);
    }

    async getShowBreakdown(venue, showDate) {
        return await this.get(`/api/shows/breakdown?venue=${encodeURIComponent(venue)}&show_date=${encodeURIComponent(showDate)}`);
    }

    async getGuestDetails(venue, showDate) {
        return await this.get(`/api/shows/guests?venue=${encodeURIComponent(venue)}&show_date=${encodeURIComponent(showDate)}`);
    }

    // Comedian operations - MongoDB only, no Google Sheets
    async getComedians(venue, showDate) {
        return await this.get(`/api/comedians//?venue=${encodeURIComponent(venue)}&show_date=${encodeURIComponent(showDate)}`);
    }

    async saveComedians(venue, showDate, comedians) {
        return await this.post('/api/comedians//', {
            venue: venue,
            show_date: showDate,
            comedians: comedians
        });
    }

    async updateComedianPayment(comedianId, paymentData) {
        return await this.put(`/api/comedians//${comedianId}/payment`, {
            payment_data: paymentData
        });
    }
}

// Create global API client instance
window.apiClient = new ApiClient();
