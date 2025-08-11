/**
 * Main Dashboard Application - Clean and organized
 * No authentication, no Google Sheets integration
 */

class Dashboard {
    constructor() {
        this.currentRevenueBreakdown = null;
        this.currentProcessingFees = null;
        this.loadingStates = {
            venues: false,
            shows: false,
            breakdown: false
        };
    }

    init() {
        console.log('🚀 Initializing Show Analytics Dashboard');
        console.log('📊 MongoDB-only mode (no Google Sheets integration)');
        console.log('🔓 No authentication required (dev mode)');

        this.setupEventListeners();
        this.loadMostRecentShow();
        this.startHealthMonitoring();
    }

    setupEventListeners() {
        // Venue selection handler
        const venueSelect = document.getElementById('venue');
        if (venueSelect) {
            venueSelect.addEventListener('change', () => {
                this.onVenueChange();
            });
        }

        // Show date selection handler
        const showDateSelect = document.getElementById('show-date');
        if (showDateSelect) {
            showDateSelect.addEventListener('change', () => {
                this.onShowDateChange();
            });
        }
    }

    async onVenueChange() {
        const venue = document.getElementById('venue').value;

        if (venue) {
            await this.loadShows(venue);
        } else {
            this.clearShows();
            this.hideResults();
        }
    }

    async onShowDateChange() {
        const venue = document.getElementById('venue').value;
        const showDate = document.getElementById('show-date').value;

        if (venue && showDate) {
            await this.loadShowBreakdown(venue, showDate);
        } else {
            this.hideResults();
        }
    }

    async loadMostRecentShow() {
        try {
            const data = await window.apiClient.getRecentShow();

            if (data.error) {
                console.log('No recent show data available');
                return;
            }

            if (data.recent_venue && data.recent_show) {
                // Load venues first, then select the recent one
                await this.loadVenues();

                const venueSelect = document.getElementById('venue');
                if (venueSelect) {
                    venueSelect.value = data.recent_venue;
                    // Load shows but skip auto-selection
                    await this.loadShows(data.recent_venue, true);

                    const showDateSelect = document.getElementById('show-date');
                    if (showDateSelect) {
                        showDateSelect.value = data.recent_show;
                        // Manually trigger the show breakdown load
                        await this.loadShowBreakdown(data.recent_venue, data.recent_show);
                    }
                }
            } else {
                // No recent data, just load venues
                await this.loadVenues();
            }

        } catch (error) {
            console.error('Error loading most recent show:', error);
            // Don't show error to user, just load venues
            await this.loadVenues();
        }
    }

    async loadVenues() {
        if (this.loadingStates.venues) return;
        this.loadingStates.venues = true;

        try {
            const data = await window.apiClient.getVenues();

            if (data.error) {
                throw new Error(data.error);
            }

            const venueSelect = document.getElementById('venue');
            if (venueSelect) {
                venueSelect.innerHTML = '<option value="">Select a venue...</option>';

                data.venues.forEach(venue => {
                    const option = document.createElement('option');
                    option.value = venue;
                    option.textContent = venue;
                    venueSelect.appendChild(option);
                });

                venueSelect.disabled = false;
            }

            console.log(`Loaded ${data.venues.length} venues`);

        } catch (error) {
            console.error('Error loading venues:', error);
            this.showError(`Failed to load venues: ${error.message}`);
        } finally {
            this.loadingStates.venues = false;
        }
    }

    async loadShows(venue, skipAutoSelect = false) {
        if (this.loadingStates.shows) return;
        this.loadingStates.shows = true;

        try {
            const data = await window.apiClient.getShows(venue);

            if (data.error) {
                throw new Error(data.error);
            }

            const showSelect = document.getElementById('show-date');
            if (showSelect) {
                showSelect.innerHTML = '<option value="">Select a show date...</option>';

                let closestShow = null;
                let closestDiff = Infinity;
                const today = new Date();
                today.setHours(0, 0, 0, 0); // Set to start of day for comparison

                data.shows.forEach(show => {
                    const option = document.createElement('option');
                    option.value = show.show_date_original;  // Use original format for API calls
                    option.textContent = show.show_date_display;  // Use formatted date for display
                    showSelect.appendChild(option);

                    // Find show closest to today's date
                    const showDate = new Date(show.show_datetime);
                    showDate.setHours(0, 0, 0, 0); // Set to start of day for comparison
                    const diffDays = Math.abs(showDate - today) / (1000 * 60 * 60 * 24);

                    if (diffDays < closestDiff) {
                        closestDiff = diffDays;
                        closestShow = show;
                    }
                });

                // Auto-select the closest show date only if not skipping auto-select
                if (closestShow && !skipAutoSelect) {
                    showSelect.value = closestShow.show_date_original;
                    // Trigger the change event to load the breakdown
                    showSelect.dispatchEvent(new Event('change'));
                }

                showSelect.disabled = false;
            }

            console.log(`Loaded ${data.shows.length} shows for ${venue}`);

        } catch (error) {
            console.error('Error loading shows:', error);
            this.showError(`Failed to load shows: ${error.message}`);
        } finally {
            this.loadingStates.shows = false;
        }
    }

    async loadShowBreakdown(venue, showDate) {
        if (this.loadingStates.breakdown) return;
        this.loadingStates.breakdown = true;

        try {
            this.showLoading();
            this.hideError();

            const startTime = performance.now();
            const data = await window.apiClient.getShowBreakdown(venue, showDate);
            const loadTime = Math.round(performance.now() - startTime);

            if (data.error) {
                throw new Error(data.error);
            }

            console.log(`Loaded show breakdown for ${venue} - ${showDate} in ${loadTime}ms`);
            this.displayResults(data);
            this.hideLoading();

        } catch (error) {
            console.error('Error loading show breakdown:', error);
            this.showError(`Failed to load show breakdown: ${error.message}`);
            this.hideLoading();
        } finally {
            this.loadingStates.breakdown = false;
        }
    }

    displayResults(data) {
        // Update summary cards
        const totalRevenueEl = document.getElementById('total-revenue');
        const totalTicketsEl = document.getElementById('total-tickets');

        if (totalRevenueEl) {
            totalRevenueEl.textContent = `$${data.total_revenue.toLocaleString()}`;
        }
        if (totalTicketsEl) {
            totalTicketsEl.textContent = data.total_tickets.toLocaleString();
        }

        // Update venue cost card
        this.updateVenueCostDisplay(data.venue_cost);

        // Update comedian cost card
        this.updateComedianCostDisplay(data.comedian_cost);

        // Store revenue breakdown data for modal
        this.currentRevenueBreakdown = data.revenue_breakdown;
        this.currentProcessingFees = data.processing_fees_by_source;

        // Update net revenue card
        const netRevenueEl = document.getElementById('net-revenue');
        if (netRevenueEl) {
            netRevenueEl.textContent = `$${data.net_revenue.toLocaleString()}`;
        }

        // Update show details
        const showTitleEl = document.getElementById('show-title');
        const showSubtitleEl = document.getElementById('show-subtitle');

        if (showTitleEl) {
            showTitleEl.textContent = `${data.venue} - ${data.show_date}`;
        }
        if (showSubtitleEl) {
            showSubtitleEl.textContent =
                `${data.total_tickets} tickets sold • $${data.total_revenue.toLocaleString()} gross revenue • $${data.net_revenue.toLocaleString()} net`;
        }

        // Create charts
        if (data.source_breakdown && data.source_breakdown.by_revenue) {
            window.chartManager.createRevenueChart('revenue-chart', data.source_breakdown.by_revenue);
        }

        // Show results
        this.showResults();
    }

    updateVenueCostDisplay(venueCost) {
        const venueCostContainer = document.getElementById('venue-cost-container');
        const venueCostEl = document.getElementById('venue-cost');
        const venueCostLabelEl = document.getElementById('venue-cost-label');

        if (venueCost && venueCost.amount > 0) {
            if (venueCostContainer) venueCostContainer.style.display = 'block';
            if (venueCostEl) venueCostEl.textContent = `$${venueCost.amount.toLocaleString()}`;
            if (venueCostLabelEl) venueCostLabelEl.textContent = venueCost.description;

            // Show/hide door split payment button
            const doorSplitSection = document.getElementById('door-split-pay-section');
            if (doorSplitSection) {
                doorSplitSection.style.display = venueCost.description.includes('door split') ? 'block' : 'none';
            }
        } else {
            if (venueCostContainer) venueCostContainer.style.display = 'none';
        }
    }

    updateComedianCostDisplay(comedianCost) {
        const comedianCostEl = document.getElementById('comedian-cost');

        if (comedianCost) {
            if (comedianCostEl) {
                comedianCostEl.textContent = `$${comedianCost.amount.toLocaleString()}`;
            }
            // Store comedian data for the modal - always from MongoDB now
            window.comedianManager.currentComedianData = comedianCost.comedians || [];
            window.comedianManager.updateComedianPreview();
        } else {
            if (comedianCostEl) {
                comedianCostEl.textContent = '$0';
            }
            window.comedianManager.currentComedianData = [];
            window.comedianManager.updateComedianPreview();
        }
    }

    addYearToShowDate(showDate) {
        try {
            if (!showDate) return showDate;

            // If date already has year, return as is
            if (/\b\d{4}\b/.test(showDate)) {
                return showDate;
            }

            // Add current year to the end
            const currentYear = new Date().getFullYear();
            return `${showDate} ${currentYear}`;
        } catch (error) {
            console.error('Error adding year to show date:', error);
            return showDate;
        }
    }

    clearShows() {
        const showSelect = document.getElementById('show-date');
        if (showSelect) {
            showSelect.innerHTML = '<option value="">Select a show date...</option>';
            showSelect.disabled = true;
        }
    }

    showLoading() {
        const loadingEl = document.getElementById('loading');
        if (loadingEl) loadingEl.style.display = 'block';
    }

    hideLoading() {
        const loadingEl = document.getElementById('loading');
        if (loadingEl) loadingEl.style.display = 'none';
    }

    showError(message) {
        const errorEl = document.getElementById('error');
        if (errorEl) {
            errorEl.textContent = message;
            errorEl.style.display = 'block';
        }
    }

    hideError() {
        const errorEl = document.getElementById('error');
        if (errorEl) errorEl.style.display = 'none';
    }

    showResults() {
        const resultsEl = document.getElementById('results');
        if (resultsEl) resultsEl.style.display = 'block';
    }

    hideResults() {
        const resultsEl = document.getElementById('results');
        if (resultsEl) resultsEl.style.display = 'none';
    }

    async startHealthMonitoring() {
        // Initial health check
        await this.checkHealth();

        // Check health every 30 seconds
        setInterval(async () => {
            await this.checkHealth();
        }, 30000);
    }

    async checkHealth() {
        try {
            const health = await window.apiClient.getHealth();
            console.log(`Health check: ${health.status} - ${health.total_records || 0} records`);

            // Update the UI
            const healthStatusEl = document.getElementById('health-status');
            if (healthStatusEl) {
                if (health.status === 'healthy') {
                    healthStatusEl.textContent = `✅ Connected - ${health.total_records || 0} records`;
                    healthStatusEl.className = 'text-success';
                } else {
                    healthStatusEl.textContent = `⚠️ ${health.status}`;
                    healthStatusEl.className = 'text-warning';
                }
            }
        } catch (error) {
            console.warn('Health check failed:', error);

            // Update UI to show error
            const healthStatusEl = document.getElementById('health-status');
            if (healthStatusEl) {
                healthStatusEl.textContent = '❌ Connection Error';
                healthStatusEl.className = 'text-danger';
            }
        }
    }
}

// Global function to show guest details modal
function showGuestDetails() {
    const venue = document.getElementById('venue')?.value;
    const showDate = document.getElementById('show-date')?.value;

    if (!venue || !showDate) {
        alert('Please select a venue and show date first');
        return;
    }

    // Update modal title
    const modalTitle = document.getElementById('guestDetailsModalLabel');
    if (modalTitle) {
        modalTitle.textContent = `Guest Details - ${venue} - ${showDate}`;
    }

    // Show the modal
    const modal = new bootstrap.Modal(document.getElementById('guestDetailsModal'));
    modal.show();

    // Load guest details
    loadGuestDetails(venue, showDate);
}

// Function to load and display guest details
async function loadGuestDetails(venue, showDate) {
    const loadingDiv = document.getElementById('guest-loading');
    const contentDiv = document.getElementById('guest-details-content');
    const errorDiv = document.getElementById('guest-error');

    // Show loading state
    if (loadingDiv) loadingDiv.style.display = 'block';
    if (contentDiv) contentDiv.style.display = 'none';
    if (errorDiv) errorDiv.style.display = 'none';

    try {
        // Fetch guest details from API using the API client
        const data = await window.apiClient.getGuestDetails(venue, showDate);

        if (loadingDiv) loadingDiv.style.display = 'none';

        if (data.error) {
            throw new Error(data.error);
        }

        // Display guest details
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

// Function to display guest details in the modal
function displayGuestDetails(data) {
    console.log('displayGuestDetails called with data:', data);

    const contentDiv = document.getElementById('guest-details-content');
    const showTitleEl = document.getElementById('guest-show-title');
    const summaryEl = document.getElementById('guest-summary');
    const tableBody = document.getElementById('guest-table-body');

    if (!contentDiv) return;

    const guests = data.contacts || data.guests || [];
    console.log('guests array:', guests);
    console.log('guests.length:', guests.length);
    console.log('total_tickets:', data.total_tickets);

    // Update show title and summary
    if (showTitleEl) {
        showTitleEl.textContent = `${data.venue} - ${data.show_date}`;
    }
    if (summaryEl) {
        summaryEl.textContent = `${guests.length} guests, ${data.total_tickets || 0} tickets`;
        console.log('Updated summary text:', summaryEl.textContent);
    }

    // Populate table body
    if (tableBody) {
        let html = '';
        guests.forEach(guest => {
            // Handle both contacts and guests data structures
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
        console.log('Table body HTML updated with', guests.length, 'rows');
    }

    contentDiv.style.display = 'block';
}

// Global function to show revenue breakdown modal
function showRevenueBreakdown() {
    if (!window.dashboard || !window.dashboard.currentRevenueBreakdown) {
        console.warn('No revenue breakdown data available');
        return;
    }

    const breakdown = window.dashboard.currentRevenueBreakdown;
    const processingFees = window.dashboard.currentProcessingFees;

    // Populate modal with breakdown data
    const grossEl = document.getElementById('breakdown-gross');
    const feesEl = document.getElementById('breakdown-fees');
    const totalEl = document.getElementById('breakdown-total');

    if (grossEl) grossEl.textContent = `$${breakdown.gross_revenue.toLocaleString()}`;
    if (feesEl) feesEl.textContent = `$${breakdown.processing_fees.toLocaleString()}`;
    if (totalEl) totalEl.textContent = `$${breakdown.net_revenue.toLocaleString()}`;

    // Populate processing fees breakdown by source
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

    // Show the modal
    const modal = new bootstrap.Modal(document.getElementById('revenueBreakdownModal'));
    modal.show();
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', function () {
    window.dashboard = new Dashboard();
    window.dashboard.init();
});
