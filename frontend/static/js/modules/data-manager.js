/**
 * Dashboard Data Manager
 * Handles data loading and state management
 */

class DataManager {
    constructor(apiClient) {
        this.apiClient = apiClient;
        this.loadingStates = {
            venues: false,
            shows: false,
            breakdown: false
        };
    }

    async loadMostRecentShow() {
        try {
            const data = await this.apiClient.getRecentShow();

            if (data.error) {
                console.log('No recent show data available');
                return null;
            }

            return data;
        } catch (error) {
            console.error('Error loading recent show:', error);
            return null;
        }
    }

    async loadVenues() {
        if (this.loadingStates.venues) return null;
        this.loadingStates.venues = true;

        try {
            const data = await this.apiClient.getVenues();

            if (data.error) {
                throw new Error(data.error);
            }

            console.log(`Loaded ${data.venues.length} venues`);
            return data;

        } catch (error) {
            console.error('Error loading venues:', error);
            throw error;
        } finally {
            this.loadingStates.venues = false;
        }
    }

    async loadShows(venue, skipAutoSelect = false) {
        if (this.loadingStates.shows) return null;
        this.loadingStates.shows = true;

        try {
            const data = await this.apiClient.getShows(venue);

            if (data.error) {
                throw new Error(data.error);
            }

            console.log(`Loaded ${data.shows.length} shows for ${venue}`);
            return { data, skipAutoSelect };

        } catch (error) {
            console.error('Error loading shows:', error);
            throw error;
        } finally {
            this.loadingStates.shows = false;
        }
    }

    async loadShowBreakdown(venue, showDate) {
        if (this.loadingStates.breakdown) return null;
        this.loadingStates.breakdown = true;

        try {
            const startTime = performance.now();
            const data = await this.apiClient.getShowBreakdown(venue, showDate);
            const loadTime = Math.round(performance.now() - startTime);

            if (data.error) {
                throw new Error(data.error);
            }

            console.log(`Loaded breakdown for ${venue} - ${showDate} in ${loadTime}ms`);
            return data;

        } catch (error) {
            console.error('Error loading show breakdown:', error);
            throw error;
        } finally {
            this.loadingStates.breakdown = false;
        }
    }

    async checkHealth() {
        try {
            const health = await this.apiClient.getHealth();
            console.log(`Health check: ${health.status} - ${health.total_records || 0} records`);
            return health;
        } catch (error) {
            console.warn('Health check failed:', error);
            return { status: 'unhealthy', error: error.message };
        }
    }
}

window.DataManager = DataManager;
