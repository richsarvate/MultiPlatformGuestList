/**
 * Comedian Manager - Handle all comedian-related UI operations
 * No Google Sheets integration - MongoDB only
 */

class ComedianManager {
    constructor() {
        this.currentComedianData = [];
        this.autoSaveTimeout = null;
        this.isSaving = false;
    }

    async loadComedianData(venue, showDate) {
        try {
            const data = await window.apiClient.getComedians(venue, showDate);
            
            if (data.error) {
                throw new Error(data.error);
            }
            
            // Store current data - always from MongoDB now
            this.currentComedianData = data.comedians || [];
            
            // Populate table
            this.populateComedianTable(this.currentComedianData);
            this.updateComedianTotal();
            
            console.log(`Loaded ${this.currentComedianData.length} comedians from MongoDB`);
            
        } catch (error) {
            console.error('Error loading comedian data:', error);
            throw error;
        }
    }

    populateComedianTable(comedians) {
        const tableBody = document.getElementById('comedian-table-body');
        if (!tableBody) return;
        
        tableBody.innerHTML = '';
        
        comedians.forEach((comedian, index) => {
            this.addComedianRowToTable(comedian, index);
        });
    }

    addComedianRowToTable(comedian, index) {
        const tableBody = document.getElementById('comedian-table-body');
        if (!tableBody) return;
        
        const row = document.createElement('tr');
        row.setAttribute('data-index', index);
        
        row.innerHTML = `
            <td>
                <input type="text" class="form-control" value="${comedian.name || ''}" 
                       oninput="window.comedianManager.updateComedianNameField(${index}, this.value)"
                       style="background: #1a1a1a; border: 1px solid #404040; color: #ecf0f1;">
            </td>
            <td>
                <input type="number" class="form-control" value="${comedian.amount || 0}" step="0.01" min="0"
                       oninput="window.comedianManager.updateComedianField(${index}, 'amount', parseFloat(this.value) || 0)"
                       style="background: #1a1a1a; border: 1px solid #404040; color: #ecf0f1;">
            </td>
            <td>
                <div class="input-group" style="position: relative;">
                    <input type="text" class="form-control" value="${comedian.venmo_handle || ''}" 
                           id="venmo-handle-${index}"
                           placeholder="@username"
                           oninput="window.comedianManager.updateVenmoHandle(${index}, this.value)"
                           style="background: #1a1a1a; border: 1px solid #404040; color: #ecf0f1; font-size: 0.9em;">
                    ${comedian.venmo_handle ? `
                        <button type="button" class="btn btn-sm venmo-pay-btn" 
                                onclick="window.venmoManager.openVenmoPayment('${comedian.venmo_handle}', ${comedian.amount || 0})"
                                style="background: #3d95ce; border: none; color: white; font-size: 0.8em; padding: 4px 8px; margin-left: 4px;"
                                title="Pay with Venmo">
                            💳 Pay
                        </button>
                    ` : ''}
                </div>
            </td>
            <td>
                <div class="form-check">
                    <input type="checkbox" class="form-check-input" ${comedian.paid ? 'checked' : ''}
                           onchange="window.comedianManager.updateComedianField(${index}, 'paid', this.checked)"
                           style="transform: scale(1.4); cursor: pointer; margin-right: 8px;">
                    <label class="form-check-label" style="color: #ecf0f1; margin-left: 12px; font-size: 1em; font-weight: 500; cursor: pointer; padding: 6px 10px; border-radius: 4px; background: rgba(255,255,255,0.08);">
                        ${comedian.paid ? 'Paid' : 'Unpaid'}
                    </label>
                </div>
            </td>
            <td>
                <button type="button" class="btn btn-sm" 
                        style="background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%); border: none; color: white;"
                        onclick="window.comedianManager.removeComedian(${index})">
                    <i class="fas fa-trash"></i>
                </button>
            </td>
        `;
        
        tableBody.appendChild(row);
    }

    addComedianRow() {
        const newComedian = {
            id: '',
            name: '',
            amount: 50,
            venmo_handle: '',
            paid: false,
            payment_date: null,
            notes: ''
        };
        
        this.currentComedianData = this.currentComedianData || [];
        this.currentComedianData.push(newComedian);
        
        const index = this.currentComedianData.length - 1;
        this.addComedianRowToTable(newComedian, index);
        this.updateComedianTotal();
        
        // Trigger auto-save when adding new comedian
        this.triggerAutoSave(true);
    }

    updateComedianField(index, field, value) {
        if (this.currentComedianData && this.currentComedianData[index]) {
            this.currentComedianData[index][field] = value;
            
            // Update the paid label and checkbox if it's the paid field
            if (field === 'paid') {
                const row = document.querySelector(`tr[data-index="${index}"]`);
                if (row) {
                    const label = row.querySelector('.form-check-label');
                    const checkbox = row.querySelector('.form-check-input');
                    if (label) {
                        label.textContent = value ? 'Paid' : 'Unpaid';
                    }
                    if (checkbox) {
                        checkbox.checked = value;
                    }
                }
                // Immediate save for payment status changes
                this.triggerAutoSave(true);
            } else {
                // Debounced save for text/number fields
                this.triggerAutoSave(false);
            }
            
            this.updateComedianTotal();
        }
    }

    async updateComedianNameField(index, value) {
        // Simply update the name field
        this.updateComedianField(index, 'name', value);
    }

    removeComedian(index) {
        if (this.currentComedianData && index >= 0 && index < this.currentComedianData.length) {
            // Remove the comedian from the data
            this.currentComedianData.splice(index, 1);
            
            // Rebuild the table to ensure proper indexing
            this.populateComedianTable(this.currentComedianData);
            this.updateComedianTotal();
            
            // Immediate save when removing comedians
            this.triggerAutoSave(true);
        }
    }

    async updateVenmoHandle(index, value) {
        // Clean the handle (remove @ if present, trim whitespace)
        const cleanHandle = value.replace('@', '').trim();
        
        if (this.currentComedianData && this.currentComedianData[index]) {
            // Update the field
            this.updateComedianField(index, 'venmo_handle', cleanHandle);
            
            // Update pay button based on whether we have a handle
            this.updatePayButtonInRow(index, cleanHandle);
            
            console.log(`Updated Venmo handle for ${this.currentComedianData[index].name}: ${cleanHandle ? '@' + cleanHandle : '(cleared)'}`);
        }
    }

    updatePayButtonInRow(index, venmoHandle) {
        const row = document.querySelector(`tr[data-index="${index}"]`);
        if (!row) return;
        
        const venmoCell = row.children[2]; // Venmo handle column
        const inputGroup = venmoCell.querySelector('.input-group');
        
        if (venmoHandle && venmoHandle.trim()) {
            // Check if pay button already exists
            let payButton = inputGroup.querySelector('.venmo-pay-btn');
            
            if (!payButton) {
                // Create and add pay button
                payButton = document.createElement('button');
                payButton.type = 'button';
                payButton.className = 'btn btn-sm venmo-pay-btn';
                payButton.style.cssText = 'background: #3d95ce; border: none; color: white; font-size: 0.8em; padding: 4px 8px; margin-left: 4px;';
                payButton.title = 'Pay with Venmo';
                payButton.innerHTML = '💳 Pay';
                
                const comedian = this.currentComedianData[index];
                payButton.onclick = () => window.venmoManager.openVenmoPayment(venmoHandle, comedian.amount || 0);
                
                inputGroup.appendChild(payButton);
            } else {
                // Update existing button
                const comedian = this.currentComedianData[index];
                payButton.onclick = () => window.venmoManager.openVenmoPayment(venmoHandle, comedian.amount || 0);
            }
        } else {
            // Remove pay button if handle is empty
            const payButton = inputGroup.querySelector('.venmo-pay-btn');
            if (payButton) {
                payButton.remove();
            }
        }
    }

    updateComedianTotal() {
        if (!this.currentComedianData) return;
        
        const total = this.currentComedianData.reduce((sum, comedian) => {
            return sum + (parseFloat(comedian.amount) || 0);
        }, 0);
        
        const totalElement = document.getElementById('total-comedian-cost');
        if (totalElement) {
            totalElement.textContent = total.toLocaleString();
        }
        
        this.updateComedianPreview();
    }

    updateComedianPreview() {
        const previewContainer = document.getElementById('comedian-preview-content');
        if (!previewContainer) return;
        
        if (!this.currentComedianData || this.currentComedianData.length === 0) {
            previewContainer.innerHTML = `
                <div style="color: #888; text-align: center; font-style: italic; padding: 10px;">
                    No comedians added yet
                </div>
            `;
            return;
        }
        
        // Sort comedians by amount (highest first) and take top 5 for preview
        const sortedComedians = [...this.currentComedianData]
            .filter(c => c.name && c.name.trim())
            .sort((a, b) => (parseFloat(b.amount) || 0) - (parseFloat(a.amount) || 0))
            .slice(0, 5);
        
        let previewHtml = '';
        let totalAmount = 0;
        
        sortedComedians.forEach(comedian => {
            const amount = parseFloat(comedian.amount) || 0;
            totalAmount += amount;
            const paidStatus = comedian.paid ? '✅' : '';
            
            previewHtml += `
                <div style="display: flex; justify-content: space-between; align-items: center; padding: 3px 6px; border-bottom: 1px solid rgba(255,255,255,0.1); min-height: 24px;">
                    <div style="flex: 1; overflow: hidden; margin-right: 8px;">
                        <span style="font-weight: 500; word-wrap: break-word; line-height: 1.2;">${comedian.name}</span>
                        ${paidStatus ? `<span style="margin-left: 6px; font-size: 0.9em;">${paidStatus}</span>` : ''}
                    </div>
                    <div style="color: #2ecc71; font-weight: 600; white-space: nowrap;">$${amount.toLocaleString()}</div>
                </div>
            `;
        });
        
        // Add summary if there are more comedians
        const remainingCount = this.currentComedianData.filter(c => c.name && c.name.trim()).length - sortedComedians.length;
        if (remainingCount > 0) {
            const remainingTotal = this.currentComedianData
                .filter(c => c.name && c.name.trim())
                .slice(5)
                .reduce((sum, c) => sum + (parseFloat(c.amount) || 0), 0);
            
            previewHtml += `
                <div style="padding: 6px; text-align: center; color: #888; font-style: italic; border-top: 1px solid rgba(255,255,255,0.2);">
                    +${remainingCount} more ($${remainingTotal.toLocaleString()})
                </div>
            `;
        }
        
        previewContainer.innerHTML = previewHtml;
    }

    triggerAutoSave(immediate = false) {
        if (this.isSaving) return;
        
        clearTimeout(this.autoSaveTimeout);
        
        if (immediate) {
            this.autoSaveComedians();
        } else {
            // Debounced save - wait 1.5 seconds after last change
            this.autoSaveTimeout = setTimeout(() => this.autoSaveComedians(), 1500);
        }
    }

    async autoSaveComedians() {
        const venue = document.getElementById('venue')?.value;
        const showDate = document.getElementById('show-date')?.value;
        
        if (!venue || !showDate || !this.currentComedianData) {
            return;
        }

        if (this.isSaving) return;
        this.isSaving = true;
        
        try {
            this.showSaveStatus('saving');
            
            const data = await window.apiClient.saveComedians(venue, showDate, this.currentComedianData);
            
            if (data.error) {
                throw new Error(data.error);
            }
            
            // Update the stored data with any server-generated IDs
            this.currentComedianData = data.comedians;
            
            this.showSaveStatus('saved');
            console.log(`Auto-saved ${this.currentComedianData.length} comedians to MongoDB`);
            
        } catch (error) {
            console.error('Error auto-saving comedian data:', error);
            this.showSaveStatus('error');
        } finally {
            this.isSaving = false;
        }
    }

    showSaveStatus(status) {
        const saveStatus = document.getElementById('save-status');
        if (!saveStatus) return;
        
        if (status === 'saving') {
            saveStatus.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';
            saveStatus.style.color = '#ff6b35';
            saveStatus.style.display = 'inline';
        } else if (status === 'saved') {
            saveStatus.innerHTML = '<i class="fas fa-check"></i> Saved';
            saveStatus.style.color = '#27ae60';
            saveStatus.style.display = 'inline';
            // Hide after 2 seconds
            setTimeout(() => {
                saveStatus.style.display = 'none';
            }, 2000);
        } else if (status === 'error') {
            saveStatus.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Error saving';
            saveStatus.style.color = '#e74c3c';
            saveStatus.style.display = 'inline';
            setTimeout(() => {
                saveStatus.style.display = 'none';
            }, 3000);
        } else {
            saveStatus.style.display = 'none';
        }
    }
}

// Create global comedian manager instance
window.comedianManager = new ComedianManager();
