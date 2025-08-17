/**
 * UI Manager
 * Handles DOM manipulation and UI updates
 */

class UIManager {
    constructor() {
        this.currentRevenueBreakdown = null;
        this.currentProcessingFees = null;
    }

    setupEventListeners(dashboard) {
        const venueSelect = document.getElementById('venue');
        if (venueSelect) {
            venueSelect.addEventListener('change', () => dashboard.onVenueChange());
        }

        const showDateSelect = document.getElementById('show-date');
        if (showDateSelect) {
            showDateSelect.addEventListener('change', () => dashboard.onShowDateChange());
        }
    }

    populateVenues(venuesData) {
        const venueSelect = document.getElementById('venue');
        if (!venueSelect) return;

        venueSelect.innerHTML = '<option value="">Select a venue...</option>';

        venuesData.venues.forEach(venue => {
            const option = document.createElement('option');
            option.value = venue;
            option.textContent = venue;
            venueSelect.appendChild(option);
        });

        venueSelect.disabled = false;
    }

    populateShows(showsData, skipAutoSelect = false) {
        const showSelect = document.getElementById('show-date');
        if (!showSelect) return null;

        showSelect.innerHTML = '<option value="">Select a show date...</option>';

        let closestShow = null;
        let closestDiff = Infinity;
        const today = new Date();
        today.setHours(0, 0, 0, 0);

        showsData.shows.forEach(show => {
            const option = document.createElement('option');
            option.value = show.show_datetime;
            option.textContent = show.show_date;
            showSelect.appendChild(option);

            const showDate = new Date(show.show_datetime);
            showDate.setHours(0, 0, 0, 0);
            const diffDays = Math.abs(showDate - today) / (1000 * 60 * 60 * 24);

            if (diffDays < closestDiff) {
                closestDiff = diffDays;
                closestShow = show;
            }
        });

        if (closestShow && !skipAutoSelect) {
            showSelect.value = closestShow.show_datetime;
            showSelect.dispatchEvent(new Event('change'));
        }

        showSelect.disabled = false;
        return closestShow;
    }

    displayResults(data) {
        this.updateSummaryCards(data);
        this.updateVenueCostDisplay(data.venue_cost);
        this.updateComedianCostDisplay(data.comedian_cost);
        this.updateShowDetails(data);
        this.storeRevenueData(data);

        if (data.by_source) {
            window.chartManager.createRevenueChart('revenue-chart', data.by_source);
        }

        this.showResults();
    }

    updateSummaryCards(data) {
        const totalRevenueEl = document.getElementById('total-revenue');
        const totalTicketsEl = document.getElementById('total-tickets');
        const netRevenueEl = document.getElementById('net-revenue');

        if (totalRevenueEl) totalRevenueEl.textContent = `$${data.total_revenue.toLocaleString()}`;
        if (totalTicketsEl) totalTicketsEl.textContent = data.total_tickets.toLocaleString();
        if (netRevenueEl) netRevenueEl.textContent = `$${data.net_revenue.toLocaleString()}`;
    }

    updateVenueCostDisplay(venueCost) {
        const venueCostContainer = document.getElementById('venue-cost-container');
        const venueCostEl = document.getElementById('venue-cost');
        const venueCostLabelEl = document.getElementById('venue-cost-label');

        if (venueCost && venueCost.amount > 0) {
            if (venueCostContainer) venueCostContainer.style.display = 'block';
            if (venueCostEl) venueCostEl.textContent = `$${venueCost.amount.toLocaleString()}`;
            if (venueCostLabelEl) venueCostLabelEl.textContent = venueCost.description;

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
            window.comedianManager.currentComedianData = comedianCost.comedians || [];
            window.comedianManager.updateComedianPreview();
        } else {
            if (comedianCostEl) comedianCostEl.textContent = '$0';
            window.comedianManager.currentComedianData = [];
            window.comedianManager.updateComedianPreview();
        }
    }

    updateShowDetails(data) {
        const showTitleEl = document.getElementById('show-title');
        const showSubtitleEl = document.getElementById('show-subtitle');

        if (showTitleEl) {
            showTitleEl.textContent = `${data.venue} - ${data.show_date}`;
        }
        if (showSubtitleEl) {
            showSubtitleEl.textContent =
                `${data.total_tickets} tickets sold • $${data.total_revenue.toLocaleString()} gross revenue • $${data.net_revenue.toLocaleString()} net`;
        }
    }

    storeRevenueData(data) {
        // Create a complete breakdown object with all required fields
        this.currentRevenueBreakdown = {
            gross_revenue: data.revenue_breakdown?.gross_revenue || data.total_revenue || 0,
            processing_fees: data.revenue_breakdown?.processing_fees || 0,
            net_revenue: data.net_revenue || 0,
            source_breakdown: data.revenue_breakdown?.source_breakdown || {},
            by_source: data.by_source || {}
        };
        this.currentProcessingFees = data.processing_fees?.fees_by_source || {};
    }

    updateHealthStatus(health) {
        const healthStatusEl = document.getElementById('health-status');
        if (!healthStatusEl) return;

        if (health.status === 'healthy') {
            healthStatusEl.textContent = `✅ Connected - ${health.total_records || 0} records`;
            healthStatusEl.className = 'text-success';
        } else if (health.status === 'unhealthy') {
            healthStatusEl.textContent = '❌ Connection Error';
            healthStatusEl.className = 'text-danger';
        } else {
            healthStatusEl.textContent = `⚠️ ${health.status}`;
            healthStatusEl.className = 'text-warning';
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
}

window.UIManager = UIManager;
