/**
 * Chart Manager - Handle all data visualization
 * Clean chart creation and management
 */

class ChartManager {
    constructor() {
        this.charts = {};
        this.colorSchemes = {
            primary: ['#1a1a1a', '#2d2d2d', '#404040', '#595959', '#737373', '#8c8c8c', '#a6a6a6', '#bfbfbf'],
            revenue: ['#ff6b35', '#c0392b', '#2c3e50', '#34495e']
        };
    }

    getSourceColor(source) {
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

    createRevenueChart(elementId, sourceData) {
        this.destroyChart(elementId);

        const ctx = document.getElementById(elementId).getContext('2d');

        // Extract revenue values from the nested structure
        const labels = Object.keys(sourceData);
        const values = labels.map(source => sourceData[source].revenue || 0);

        // Create colors array that matches the source order
        const colors = labels.map(label => this.getSourceColor(label));

        this.charts[elementId] = new Chart(ctx, {
            type: 'pie',
            data: {
                labels: labels,
                datasets: [{
                    data: values,
                    backgroundColor: colors,
                    borderWidth: 1,
                    borderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 10,
                            usePointStyle: true,
                            font: { size: 11 }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                const value = context.parsed;
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = ((value / total) * 100).toFixed(1);
                                return `${context.label}: $${value.toLocaleString()} (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
    }

    destroyChart(chartId) {
        if (this.charts[chartId]) {
            this.charts[chartId].destroy();
            delete this.charts[chartId];
        }
    }

    destroyAllCharts() {
        Object.keys(this.charts).forEach(chartId => {
            this.destroyChart(chartId);
        });
    }
}

// Create global chart manager instance
window.chartManager = new ChartManager();
