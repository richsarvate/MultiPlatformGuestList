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
        // Get the text content of the selected option for better display
        const venueSelect = document.getElementById('venue');
        const showDateSelect = document.getElementById('show-date');
        const venueName = venueSelect?.selectedOptions[0]?.textContent || venue;
        const showDateName = showDateSelect?.selectedOptions[0]?.textContent || showDate;
        modalTitle.textContent = `Guest Details - ${venueName} - ${showDateName}`;
    }

    const modal = new bootstrap.Modal(document.getElementById('guestDetailsModal'));
    modal.show();

    loadGuestDetails(venue, showDate);
}

function showComedianManager() {
    const venue = document.getElementById('venue')?.value;
    const showDate = document.getElementById('show-date')?.value;

    if (!venue || !showDate) {
        alert('Please select a venue and show date first');
        return;
    }

    const modalTitle = document.getElementById('comedianModalLabel');
    if (modalTitle) {
        // Get the text content of the selected option for better display
        const venueSelect = document.getElementById('venue');
        const showDateSelect = document.getElementById('show-date');
        const venueName = venueSelect?.selectedOptions[0]?.textContent || venue;
        const showDateName = showDateSelect?.selectedOptions[0]?.textContent || showDate;
        modalTitle.innerHTML = `<i class="fas fa-microphone me-2"></i>
                        Manage Comedians & Payments - ${venueName} - ${showDateName}
                        <span id="save-status" class="ms-3" style="font-size: 0.8em; display: none;">
                            <i class="fas fa-spinner fa-spin"></i> Saving...
                        </span>`;
    }

    const modal = new bootstrap.Modal(document.getElementById('comedianModal'));
    modal.show();

    // Load comedian data for the selected show
    if (window.comedianManager) {
        window.comedianManager.loadComedianData(venue, showDate);
    }
}

function addComedianRow() {
    if (window.comedianManager) {
        window.comedianManager.addComedianRow();
    }
}

// Helper function to get consistent source colors
function getSourceColor(source) {
    const colorMap = {
        'Squarespace': '#1a1a1a',  // Keep the same (dark gray/black)
        'Eventbrite': '#FF6B35',   // ORANGE
        'Bucketlist': '#007BFF',   // BLUE
        'Fever': '#8A2BE2',        // PURPLE  
        'DoMORE': '#39FF14',       // NEON GREEN
        'Manual': '#8c8c8c'
    };
    return colorMap[source] || '#95a5a6';
}

// Helper function to create colored source badge
function createSourceBadge(source) {
    const color = getSourceColor(source);
    const textColor = (source === 'Squarespace' || source === 'Manual') ? '#fff' : '#000';
    return `<span class="badge" style="background-color: ${color}; color: ${textColor};">${source || 'Unknown'}</span>`;
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

    // Get venue and show date from the form since API doesn't return them
    const venue = document.getElementById('venue')?.value || 'Unknown Venue';
    const showDate = document.getElementById('show-date')?.value || 'Unknown Date';

    if (showTitleEl) {
        showTitleEl.textContent = `${venue} - ${showDate}`;
    }

    // Calculate total tickets from guests
    const totalTickets = guests.reduce((sum, guest) => sum + (parseInt(guest.tickets) || 1), 0);

    if (summaryEl) {
        summaryEl.textContent = `${totalTickets} tickets`;
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
                    <td>${createSourceBadge(guest.source)}</td>
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
    const processingFees = window.dashboard.uiManager.currentProcessingFees || {};

    // Calculate totals
    let totalGrossRevenue = 0;
    let totalProcessingFees = 0;
    let totalNetRevenue = 0;

    // Get source data - use by_source if available, otherwise fallback to source_breakdown
    const sourceData = breakdown.by_source || {};
    const revenueBySource = breakdown.source_breakdown?.by_revenue || breakdown.source_breakdown || {};

    // Build detailed source breakdown HTML
    let sourceBreakdownHtml = '';
    Object.entries(revenueBySource).forEach(([source, grossRevenue]) => {
        const processingFee = processingFees[source] 
            ? (typeof processingFees[source] === 'object' ? processingFees[source].total : processingFees[source])
            : 0;
        const netRevenue = grossRevenue - processingFee;
        
        // Get ticket count from by_source structure
        const ticketCount = sourceData[source]?.tickets || 'Unknown';
        
        // Calculate fee percentage for display
        let feeDescription = '';
        if (source === 'Squarespace') {
            feeDescription = '(2.9% + $0.30 per transaction)';
        } else if (source === 'Bucketlist' || source === 'Fever') {
            feeDescription = '(25% platform fee)';
        } else if (source === 'Eventbrite') {
            feeDescription = '(3.7% + $1.79 per transaction)';
        } else if (processingFee === 0) {
            feeDescription = '(Free)';
        }

        totalGrossRevenue += grossRevenue;
        totalProcessingFees += processingFee;
        totalNetRevenue += netRevenue;

        sourceBreakdownHtml += `
            <div class="mb-3 p-3" style="background: rgba(255,255,255,0.05); border-radius: 10px; border: 1px solid rgba(255,255,255,0.1);">
                <div class="mb-2">
                    <strong style="color: #e9ecef; font-size: 1.05rem;">${source}: ${ticketCount} tickets</strong>
                </div>
                <div class="ps-3">
                    <div class="d-flex justify-content-between py-1" style="color: #e9ecef;">
                        <span>Gross Revenue:</span>
                        <span style="font-weight: 600;">$${grossRevenue.toFixed(2)}</span>
                    </div>
                    <div class="d-flex justify-content-between py-1" style="color: #fd7e83;">
                        <span>Processing Fees: ${feeDescription}</span>
                        <span style="font-weight: 600;">-$${processingFee.toFixed(2)}</span>
                    </div>
                    <div class="d-flex justify-content-between py-1 mt-2 pt-2" style="color: #51cf66; border-top: 1px solid rgba(255,255,255,0.1);">
                        <span style="font-weight: 600;">Net Revenue:</span>
                        <span style="font-weight: 700;">$${netRevenue.toFixed(2)}</span>
                    </div>
                </div>
            </div>
        `;
    });

    // Calculate venue share and final net
    const venueShareRate = breakdown.venue_cost?.rate || 30;
    const venueShare = (totalNetRevenue * venueShareRate) / 100;
    const finalNetRevenue = totalNetRevenue - venueShare;

    // Populate modal elements
    document.getElementById('total-gross-revenue').textContent = `$${totalGrossRevenue.toFixed(2)}`;
    document.getElementById('source-breakdown-details').innerHTML = sourceBreakdownHtml;
    
    // Summary section
    document.getElementById('summary-gross-revenue').textContent = `$${totalGrossRevenue.toFixed(2)}`;
    document.getElementById('summary-processing-fees').textContent = `-$${totalProcessingFees.toFixed(2)}`;
    document.getElementById('summary-net-revenue').textContent = `$${totalNetRevenue.toFixed(2)}`;
    document.getElementById('summary-venue-share').textContent = `-$${venueShare.toFixed(2)}`;
    document.getElementById('summary-final-net').textContent = `$${finalNetRevenue.toFixed(2)}`;

    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('revenueBreakdownModal'));
    modal.show();
}

// Initialize dashboard
document.addEventListener('DOMContentLoaded', function () {
    window.dashboard = new Dashboard();
    window.dashboard.init();
});
