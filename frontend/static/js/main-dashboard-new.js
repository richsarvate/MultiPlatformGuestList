/**
 * Main Dashboard Application - Simplified and Modular
 */

class Dashboard {
    constructor() {
        this.dataManager = new window.DataManager(window.apiClient);
        this.uiManager = new window.UIManager();
    }

    init() {
        console.log('🚀 Initializing Show Analytics Dashboard');

        this.uiManager.setupEventListeners(this);
        this.loadMostRecentShow();
        this.startHealthMonitoring();
    }

    async onVenueChange() {
        const venue = document.getElementById('venue').value;

        if (venue) {
            await this.loadShows(venue);
        } else {
            this.uiManager.clearShows();
            this.uiManager.hideResults();
        }
    }

    async onShowDateChange() {
        const venue = document.getElementById('venue').value;
        const showDate = document.getElementById('show-date').value;

        if (venue && showDate) {
            await this.loadShowBreakdown(venue, showDate);
        } else {
            this.uiManager.hideResults();
        }
    }

    async loadMostRecentShow() {
        try {
            const recentData = await this.dataManager.loadMostRecentShow();

            if (recentData && recentData.recent_venue && recentData.recent_show) {
                await this.loadVenues();

                const venueSelect = document.getElementById('venue');
                if (venueSelect) {
                    venueSelect.value = recentData.recent_venue;
                    await this.loadShows(recentData.recent_venue, true);

                    const showDateSelect = document.getElementById('show-date');
                    if (showDateSelect) {
                        showDateSelect.value = recentData.recent_show;
                        await this.loadShowBreakdown(recentData.recent_venue, recentData.recent_show);
                    }
                }
            } else {
                await this.loadVenues();
            }

        } catch (error) {
            console.error('Error loading most recent show:', error);
            await this.loadVenues();
        }
    }

    async loadVenues() {
        try {
            const data = await this.dataManager.loadVenues();
            this.uiManager.populateVenues(data);
        } catch (error) {
            this.uiManager.showError(`Failed to load venues: ${error.message}`);
        }
    }

    async loadShows(venue, skipAutoSelect = false) {
        try {
            const result = await this.dataManager.loadShows(venue, skipAutoSelect);
            this.uiManager.populateShows(result.data, result.skipAutoSelect);
        } catch (error) {
            this.uiManager.showError(`Failed to load shows: ${error.message}`);
        }
    }

    async loadShowBreakdown(venue, showDate) {
        try {
            this.uiManager.showLoading();
            this.uiManager.hideError();

            const data = await this.dataManager.loadShowBreakdown(venue, showDate);
            this.uiManager.displayResults(data);
            this.uiManager.hideLoading();

        } catch (error) {
            this.uiManager.showError(`Failed to load show breakdown: ${error.message}`);
            this.uiManager.hideLoading();
        }
    }

    async startHealthMonitoring() {
        await this.checkHealth();
        setInterval(async () => {
            await this.checkHealth();
        }, 30000);
    }

    async checkHealth() {
        const health = await this.dataManager.checkHealth();
        this.uiManager.updateHealthStatus(health);
    }
}

// Global functions for modals
function showGuestDetails() {
    const venue = document.getElementById('venue')?.value;
    const showDate = document.getElementById('show-date')?.value;

    if (!venue || !showDate) {
        alert('Please select a venue and show date first');
        return;
    }

    const modalTitle = document.getElementById('guestDetailsModalLabel');
    if (modalTitle) {
        modalTitle.textContent = `Guest Details - ${venue} - ${showDate}`;
    }

    const modal = new bootstrap.Modal(document.getElementById('guestDetailsModal'));
    modal.show();

    loadGuestDetails(venue, showDate);
}

async function loadGuestDetails(venue, showDate) {
    const loadingDiv = document.getElementById('guest-loading');
    const contentDiv = document.getElementById('guest-details-content');
    const errorDiv = document.getElementById('guest-error');

    if (loadingDiv) loadingDiv.style.display = 'block';
    if (contentDiv) contentDiv.style.display = 'none';
    if (errorDiv) errorDiv.style.display = 'none';

    try {
        const data = await window.apiClient.getGuestDetails(venue, showDate);
        if (loadingDiv) loadingDiv.style.display = 'none';

        if (data.error) {
            throw new Error(data.error);
        }

        displayGuestDetails(data);

    } catch (error) {
        console.error('Error loading guest details:', error);
        if (loadingDiv) loadingDiv.style.display = 'none';
        if (errorDiv) {
            errorDiv.style.display = 'block';
            errorDiv.textContent = `Error loading guest details: ${error.message}`;
        }
    }
}

function displayGuestDetails(data) {
    const contentDiv = document.getElementById('guest-details-content');
    const showTitleEl = document.getElementById('guest-show-title');
    const summaryEl = document.getElementById('guest-summary');
    const tableBody = document.getElementById('guest-table-body');

    if (!contentDiv) return;

    const guests = data.contacts || data.guests || [];

    if (showTitleEl) {
        showTitleEl.textContent = `${data.venue} - ${data.show_date}`;
    }
    if (summaryEl) {
        summaryEl.textContent = `${guests.length} guests, ${data.total_tickets || 0} tickets`;
    }

    if (tableBody) {
        let html = '';
        guests.forEach(guest => {
            const name = guest.name || `${guest.first_name || ''} ${guest.last_name || ''}`.trim();
            html += `
                <tr>
                    <td>${name}</td>
                    <td>${guest.email || ''}</td>
                    <td>${guest.tickets || 1}</td>
                    <td><span class="badge bg-secondary">${guest.source || 'Unknown'}</span></td>
                    <td>$${guest.total_price ? guest.total_price.toFixed(2) : '0.00'}</td>
                    <td>${guest.discount_code || '-'}</td>
                </tr>
            `;
        });
        tableBody.innerHTML = html;
    }

    contentDiv.style.display = 'block';
}

function showRevenueBreakdown() {
    if (!window.dashboard || !window.dashboard.uiManager.currentRevenueBreakdown) {
        console.warn('No revenue breakdown data available');
        return;
    }

    const breakdown = window.dashboard.uiManager.currentRevenueBreakdown;
    const processingFees = window.dashboard.uiManager.currentProcessingFees;

    const grossEl = document.getElementById('breakdown-gross');
    const feesEl = document.getElementById('breakdown-fees');
    const totalEl = document.getElementById('breakdown-total');

    if (grossEl) grossEl.textContent = `$${breakdown.gross_revenue.toLocaleString()}`;
    if (feesEl) feesEl.textContent = `$${breakdown.processing_fees.toLocaleString()}`;
    if (totalEl) totalEl.textContent = `$${breakdown.net_revenue.toLocaleString()}`;

    const feesBreakdownEl = document.getElementById('fees-breakdown-details');
    if (feesBreakdownEl && processingFees) {
        let html = '';
        Object.entries(processingFees).forEach(([source, fee]) => {
            if (fee > 0) {
                html += `
                    <div class="row">
                        <div class="col-8">${source}:</div>
                        <div class="col-4 text-right">$${fee.toLocaleString()}</div>
                    </div>
                `;
            }
        });
        feesBreakdownEl.innerHTML = html;
    }

    const modal = new bootstrap.Modal(document.getElementById('revenueBreakdownModal'));
    modal.show();
}

// Initialize dashboard
document.addEventListener('DOMContentLoaded', function () {
    window.dashboard = new Dashboard();
    window.dashboard.init();
});
