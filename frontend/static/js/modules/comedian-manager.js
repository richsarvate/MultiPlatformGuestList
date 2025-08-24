/**
 * Simple Comedian Manager - Basic comedian modal functionality
 */

class ComedianManager {
    constructor() {
        this.comedians = [];
        this.modal = null;
        this.currentVenue = null;
        this.currentShowDate = null;
        console.log('🎭 ComedianManager created');
    }

    /**
     * Initialize the comedian manager
     */
    init() {
        console.log('🎭 Initializing Simple Comedian Manager');
        this.modal = document.getElementById('comedianModal');
        this.setupEventListeners();
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Save and close button
        const saveButton = document.getElementById('saveComedians');
        if (saveButton) {
            saveButton.addEventListener('click', () => this.saveAndClose());
        }

        // Add comedian button
        const addButton = document.getElementById('addComedian');
        if (addButton) {
            addButton.addEventListener('click', () => this.addComedianRow());
        }
    }

    /**
     * Open the comedian modal for a specific show
     */
    async openModal(venue, showDate) {
        this.currentVenue = venue;
        this.currentShowDate = showDate;

        console.log(`Opening comedian modal for ${venue} - ${showDate}`);

        // Update modal title
        const modalTitle = document.getElementById('comedianModalTitle');
        if (modalTitle) {
            modalTitle.textContent = `Manage Comedians - ${venue} - ${showDate}`;
        }

        // Load existing comedians
        await this.loadComedians();

        // Show the modal
        if (this.modal) {
            const bsModal = new bootstrap.Modal(this.modal);
            bsModal.show();
        }
    }

    /**
     * Load comedians from the server
     */
    async loadComedians() {
        try {
            const response = await fetch(`/api/comedians/?venue=${encodeURIComponent(this.currentVenue)}&show_date=${encodeURIComponent(this.currentShowDate)}`);
            const data = await response.json();
            
            this.comedians = data.comedians || [];
            this.renderComedians();
            this.updateTotal();
            
            // Also update the main dashboard display immediately
            this.updateCostDisplay(this.comedians);
            
            console.log(`Loaded ${this.comedians.length} comedians`);
        } catch (error) {
            console.error('Error loading comedians:', error);
            this.comedians = [];
            this.renderComedians();
            this.updateTotal();
            
            // Also update the main dashboard display with empty list
            this.updateCostDisplay(this.comedians);
        }
    }

    /**
     * Render the comedians table
     */
    renderComedians() {
        const tbody = document.getElementById('comedianTableBody');
        if (!tbody) return;

        tbody.innerHTML = '';

        // Render existing comedians only
        this.comedians.forEach((comedian, index) => {
            const row = this.createComedianRow(comedian, index);
            tbody.appendChild(row);
        });
    }

    /**
     * Create a single comedian row
     */
    createComedianRow(comedian, index, isNew = false) {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>
                <input type="text" class="form-control" value="${comedian.name || ''}" 
                       onchange="window.comedianManager.updateComedian(${index}, 'name', this.value)">
            </td>
            <td>
                <input type="number" class="form-control" value="${comedian.payment || ''}" 
                       oninput="window.comedianManager.updateComedian(${index}, 'payment', this.value)"
                       onchange="window.comedianManager.updateComedian(${index}, 'payment', this.value)">
            </td>
            <td>
                <input type="text" class="form-control" value="${comedian.handle || ''}" 
                       onchange="window.comedianManager.updateComedian(${index}, 'handle', this.value)">
            </td>
            <td>
                <input type="checkbox" class="form-check-input" ${comedian.paid ? 'checked' : ''}
                       onchange="window.comedianManager.updateComedian(${index}, 'paid', this.checked)">
            </td>
            <td>
                ${!isNew ? 
                    `<button type="button" class="btn btn-sm btn-danger" onclick="window.comedianManager.removeComedian(${index})">Remove</button>` : 
                    ``
                }
            </td>
        `;
        return row;
    }

    /**
     * Update a comedian's data
     */
    updateComedian(index, field, value) {
        // Only update existing comedians, don't auto-add new ones
        if (index < this.comedians.length) {
            // Update the field
            if (field === 'payment') {
                this.comedians[index][field] = parseFloat(value) || 0;
            } else if (field === 'paid') {
                this.comedians[index][field] = value;
            } else {
                this.comedians[index][field] = value;
            }
            // Update the total whenever payment changes
            if (field === 'payment') {
                this.updateTotal();
            }
        }
    }

    /**
     * Calculate and update the total cost display
     */
    updateTotal() {
        const total = this.comedians.reduce((sum, comedian) => {
            return sum + (parseFloat(comedian.payment) || 0);
        }, 0);
        
        const totalElement = document.getElementById('totalComedianCost');
        if (totalElement) {
            totalElement.textContent = total.toFixed(0);
        }
        
        // Also update the main dashboard comedian cost display
        this.updateCostDisplay(this.comedians);
    }

    /**
     * Add a new comedian row
     */
    addComedianRow() {
        this.comedians.push({
            name: '',
            payment: '',
            handle: '',
            paid: false
        });
        this.renderComedians();
        this.updateTotal();
    }

    /**
     * Remove a comedian
     */
    removeComedian(index) {
        this.comedians.splice(index, 1);
        this.renderComedians();
        this.updateTotal();
    }

    /**
     * Save comedians and close modal
     */
    async saveAndClose() {
        try {
            // Filter out empty comedians
            const validComedians = this.comedians.filter(c => c.name && c.name.trim() !== '');

            console.log('Saving comedians:', validComedians);

            const response = await fetch('/api/comedians/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    venue: this.currentVenue,
                    show_date: this.currentShowDate,
                    comedians: validComedians
                })
            });

            if (response.ok) {
                console.log('Comedians saved successfully');
                
                // Update the comedian cost display
                this.updateCostDisplay(validComedians);
                
                // Close the modal
                const bsModal = bootstrap.Modal.getInstance(this.modal);
                if (bsModal) {
                    bsModal.hide();
                }
            } else {
                console.error('Error saving comedians');
                alert('Error saving comedians. Please try again.');
            }
        } catch (error) {
            console.error('Error saving comedians:', error);
            alert('Error saving comedians. Please try again.');
        }
    }

    /**
     * Update the cost display on the main dashboard
     */
    updateCostDisplay(comedians) {
        const totalCost = comedians.reduce((sum, c) => sum + (parseFloat(c.payment) || 0), 0);
        const costElement = document.getElementById('comedian-cost');
        if (costElement) {
            costElement.textContent = `$${totalCost}`;
        }
        
        // Trigger update of total profit calculation
        if (window.dashboard && window.dashboard.uiManager && window.dashboard.uiManager.currentFullData) {
            window.dashboard.uiManager.updateSummaryCards(window.dashboard.uiManager.currentFullData);
        }
    }
}

// Global function to open the comedian modal
function showComedianManager() {
    console.log('showComedianManager called');
    const venue = document.getElementById('venue')?.value;
    const showDate = document.getElementById('show-date')?.value;

    if (!venue || !showDate) {
        alert('Please select a venue and show date first');
        return;
    }

    if (window.comedianManager) {
        window.comedianManager.openModal(venue, showDate);
    } else {
        console.error('comedianManager not initialized');
    }
}

// Initialize comedian manager when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('Initializing comedian manager');
    window.comedianManager = new ComedianManager();
    window.comedianManager.init();
    
    // Also expose the global function
    window.showComedianManager = showComedianManager;
});
