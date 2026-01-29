/**
 * Park&Ride Dashboard Application
 */

class DashboardApp {
    constructor() {
        this.charts = {};           // Chart.js instances by chart ID
        this.config = null;         // Dashboard configuration
        this.refreshTimer = null;   // Auto-refresh timer
        this.editingChartId = null; // Currently editing chart ID

        // Chart colors palette
        this.colors = [
            '#2196F3', '#4CAF50', '#FF9800', '#E91E63',
            '#9C27B0', '#00BCD4', '#FF5722', '#607D8B'
        ];
    }

    async init() {
        await this.loadCarparks();
        await this.loadConfig();
        this.renderCharts();
        this.setupEventListeners();
        this.startAutoRefresh();
        this.updateLastUpdated();
    }

    // --- API Methods ---

    async loadCarparks() {
        try {
            const response = await fetch('/api/carparks');
            const data = await response.json();
            this.carparks = data.carparks || [];
            this.populateCarparksSelect();
        } catch (error) {
            console.error('Failed to load carparks:', error);
            this.carparks = [];
        }
    }

    async loadConfig() {
        try {
            const response = await fetch('/api/config');
            this.config = await response.json();
        } catch (error) {
            console.error('Failed to load config:', error);
            this.config = {
                version: 1,
                settings: { autoRefresh: true, refreshInterval: 60 },
                charts: []
            };
        }
    }

    async saveConfig() {
        try {
            await fetch('/api/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(this.config)
            });
        } catch (error) {
            console.error('Failed to save config:', error);
        }
    }

    async fetchReadings(carparks, hours) {
        try {
            const response = await fetch(
                `/api/readings?carpark=${encodeURIComponent(carparks.join(','))}&hours=${hours}`
            );
            const data = await response.json();
            return data.readings || {};
        } catch (error) {
            console.error('Failed to fetch readings:', error);
            return {};
        }
    }

    // --- UI Methods ---

    populateCarparksSelect() {
        const select = document.getElementById('carpark-select');
        select.innerHTML = '';
        this.carparks.forEach(carpark => {
            const option = document.createElement('option');
            option.value = carpark;
            option.textContent = carpark;
            select.appendChild(option);
        });
    }

    renderCharts() {
        const container = document.getElementById('charts-container');
        container.innerHTML = '';

        if (this.config.charts.length === 0) {
            const template = document.getElementById('empty-state-template');
            container.appendChild(template.content.cloneNode(true));
            return;
        }

        this.config.charts.forEach(chartConfig => {
            this.createChartCard(chartConfig);
        });
    }

    createChartCard(chartConfig) {
        const container = document.getElementById('charts-container');
        const template = document.getElementById('chart-card-template');
        const card = template.content.cloneNode(true);

        const cardElement = card.querySelector('.chart-card');
        cardElement.dataset.chartId = chartConfig.id;

        card.querySelector('.chart-title').textContent = chartConfig.title;

        const canvas = card.querySelector('canvas');
        canvas.id = `canvas-${chartConfig.id}`;

        // Event listeners
        card.querySelector('.edit-btn').addEventListener('click', () => {
            this.openEditModal(chartConfig.id);
        });

        card.querySelector('.remove-btn').addEventListener('click', () => {
            this.removeChart(chartConfig.id);
        });

        container.appendChild(card);

        // Create Chart.js instance
        this.createChart(chartConfig);
    }

    createChart(chartConfig) {
        const canvas = document.getElementById(`canvas-${chartConfig.id}`);
        if (!canvas) return;

        const ctx = canvas.getContext('2d');

        const datasets = chartConfig.carparks.map((carpark, index) => ({
            label: carpark,
            data: [],
            borderColor: this.colors[index % this.colors.length],
            backgroundColor: this.colors[index % this.colors.length] + '20',
            fill: chartConfig.carparks.length === 1,
            tension: 0.1,
            pointRadius: 2
        }));

        this.charts[chartConfig.id] = new Chart(ctx, {
            type: 'line',
            data: { datasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false
                },
                scales: {
                    x: {
                        type: 'time',
                        time: {
                            unit: chartConfig.hours <= 6 ? 'hour' : 'day',
                            displayFormats: {
                                hour: 'HH:mm',
                                day: 'MMM d HH:mm'
                            }
                        },
                        title: {
                            display: false
                        }
                    },
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Available Spots'
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: chartConfig.carparks.length > 1,
                        position: 'top'
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false
                    }
                }
            }
        });

        // Load initial data
        this.refreshChart(chartConfig.id);
    }

    async refreshChart(chartId) {
        const chartConfig = this.config.charts.find(c => c.id === chartId);
        const chart = this.charts[chartId];
        if (!chartConfig || !chart) return;

        const readings = await this.fetchReadings(chartConfig.carparks, chartConfig.hours);

        chartConfig.carparks.forEach((carpark, index) => {
            const carparkReadings = readings[carpark] || [];
            chart.data.datasets[index].data = carparkReadings.map(r => ({
                x: new Date(r.timestamp),
                y: r.available
            }));
        });

        chart.update('none');

        // Update chart info
        const card = document.querySelector(`[data-chart-id="${chartId}"]`);
        if (card) {
            const info = card.querySelector('.chart-info');
            const latestValues = chartConfig.carparks.map(carpark => {
                const data = readings[carpark] || [];
                if (data.length > 0) {
                    return `${carpark}: ${data[data.length - 1].available}`;
                }
                return `${carpark}: -`;
            });
            info.textContent = latestValues.join(' | ');
        }
    }

    async refreshAllCharts() {
        for (const chartConfig of this.config.charts) {
            await this.refreshChart(chartConfig.id);
        }
        this.updateLastUpdated();
    }

    updateLastUpdated() {
        const element = document.getElementById('last-updated');
        element.textContent = new Date().toLocaleTimeString();
    }

    // --- Modal Methods ---

    openAddModal() {
        this.editingChartId = null;
        document.getElementById('modal-title').textContent = 'Add Chart';
        document.getElementById('chart-title').value = '';
        document.getElementById('carpark-select').selectedIndex = -1;
        document.getElementById('time-range').value = '24';
        document.getElementById('chart-modal').classList.add('active');
    }

    openEditModal(chartId) {
        const chartConfig = this.config.charts.find(c => c.id === chartId);
        if (!chartConfig) return;

        this.editingChartId = chartId;
        document.getElementById('modal-title').textContent = 'Edit Chart';
        document.getElementById('chart-title').value = chartConfig.title;
        document.getElementById('time-range').value = chartConfig.hours.toString();

        // Select carparks
        const select = document.getElementById('carpark-select');
        Array.from(select.options).forEach(option => {
            option.selected = chartConfig.carparks.includes(option.value);
        });

        document.getElementById('chart-modal').classList.add('active');
    }

    closeModal() {
        document.getElementById('chart-modal').classList.remove('active');
        this.editingChartId = null;
    }

    saveModal() {
        const title = document.getElementById('chart-title').value.trim();
        const select = document.getElementById('carpark-select');
        const selectedCarparks = Array.from(select.selectedOptions).map(o => o.value);
        const hours = parseInt(document.getElementById('time-range').value);

        if (!title) {
            alert('Please enter a chart title');
            return;
        }

        if (selectedCarparks.length === 0) {
            alert('Please select at least one carpark');
            return;
        }

        if (this.editingChartId) {
            // Update existing chart
            this.updateChart(this.editingChartId, {
                title,
                carparks: selectedCarparks,
                hours
            });
        } else {
            // Add new chart
            this.addChart({
                id: `chart-${Date.now()}`,
                title,
                carparks: selectedCarparks,
                hours
            });
        }

        this.closeModal();
    }

    // --- Chart Management ---

    addChart(chartConfig) {
        this.config.charts.push(chartConfig);
        this.saveConfig();
        this.renderCharts();
    }

    updateChart(chartId, updates) {
        const chartConfig = this.config.charts.find(c => c.id === chartId);
        if (!chartConfig) return;

        Object.assign(chartConfig, updates);
        this.saveConfig();

        // Destroy and recreate chart
        if (this.charts[chartId]) {
            this.charts[chartId].destroy();
            delete this.charts[chartId];
        }

        this.renderCharts();
    }

    removeChart(chartId) {
        if (!confirm('Remove this chart?')) return;

        // Destroy chart instance
        if (this.charts[chartId]) {
            this.charts[chartId].destroy();
            delete this.charts[chartId];
        }

        // Remove from config
        this.config.charts = this.config.charts.filter(c => c.id !== chartId);
        this.saveConfig();
        this.renderCharts();
    }

    // --- Auto Refresh ---

    startAutoRefresh() {
        const enabled = this.config.settings?.autoRefresh !== false;
        const interval = (this.config.settings?.refreshInterval || 60) * 1000;

        document.getElementById('auto-refresh-toggle').checked = enabled;
        document.getElementById('refresh-interval').textContent =
            `(${this.config.settings?.refreshInterval || 60}s)`;

        if (this.refreshTimer) {
            clearInterval(this.refreshTimer);
        }

        if (enabled) {
            this.refreshTimer = setInterval(() => {
                this.refreshAllCharts();
            }, interval);
        }
    }

    toggleAutoRefresh() {
        const enabled = document.getElementById('auto-refresh-toggle').checked;
        this.config.settings.autoRefresh = enabled;
        this.saveConfig();
        this.startAutoRefresh();
    }

    // --- Event Listeners ---

    setupEventListeners() {
        // Add chart button
        document.getElementById('add-chart-btn').addEventListener('click', () => {
            this.openAddModal();
        });

        // Modal controls
        document.getElementById('modal-close').addEventListener('click', () => {
            this.closeModal();
        });

        document.getElementById('modal-cancel').addEventListener('click', () => {
            this.closeModal();
        });

        document.getElementById('modal-save').addEventListener('click', () => {
            this.saveModal();
        });

        // Close modal on backdrop click
        document.getElementById('chart-modal').addEventListener('click', (e) => {
            if (e.target.classList.contains('modal')) {
                this.closeModal();
            }
        });

        // Auto-refresh toggle
        document.getElementById('auto-refresh-toggle').addEventListener('change', () => {
            this.toggleAutoRefresh();
        });

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeModal();
            }
        });
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.app = new DashboardApp();
    window.app.init();
});
