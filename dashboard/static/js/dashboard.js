/**
 * Park&Ride Dashboard Application
 */

class DashboardApp {
    constructor() {
        this.charts = {};           // Chart.js instances by chart ID
        this.config = null;         // Dashboard configuration
        this.refreshTimer = null;   // Auto-refresh timer
        this.editingChartId = null; // Currently editing chart ID
        this.lastAutoTitle = '';    // Track last auto-generated title
        this.datePicker = null;     // Flatpickr instance
        this.customDateRange = null; // { start, end } for custom range

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
        this.initDatePicker();
        this.startAutoRefresh();
        this.updateLastUpdated();
        this.updateTimeRangeDropdown();
    }

    // --- API Methods ---

    async loadCarparks() {
        try {
            const response = await fetch('/api/carparks');
            const data = await response.json();
            this.carparks = data.carparks || [];
            this.populateCarparksList();
        } catch (error) {
            console.error('Failed to load carparks:', error);
            this.carparks = [];
        }
    }

    async loadConfig() {
        try {
            const response = await fetch('/api/config');
            this.config = await response.json();
            // Ensure settings has timeRange (migration from v1)
            if (!this.config.settings.timeRange) {
                this.config.settings.timeRange = 24;
            }
        } catch (error) {
            console.error('Failed to load config:', error);
            this.config = {
                version: 2,
                settings: { autoRefresh: true, refreshInterval: 60, timeRange: 24 },
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

    formatLocalISO(date) {
        // Format date in local time as ISO string (YYYY-MM-DDTHH:mm:ss)
        // This avoids timezone conversion that toISOString() does
        const pad = (n) => String(n).padStart(2, '0');
        return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
    }

    async fetchReadings(carparks, hours) {
        try {
            let url = `/api/readings?carpark=${encodeURIComponent(carparks.join(','))}`;
            if (this.customDateRange) {
                const start = this.formatLocalISO(this.customDateRange.start);
                const end = this.formatLocalISO(this.customDateRange.end);
                url += `&start=${start}&end=${end}`;
            } else {
                url += `&hours=${hours}`;
            }
            const response = await fetch(url);
            const data = await response.json();
            return data.readings || {};
        } catch (error) {
            console.error('Failed to fetch readings:', error);
            return {};
        }
    }

    // --- UI Methods ---

    populateCarparksList() {
        const listContainer = document.getElementById('carpark-list');
        listContainer.innerHTML = '';
        this.carparks.forEach(carpark => {
            const label = document.createElement('label');
            label.className = 'carpark-item';
            label.innerHTML = `
                <input type="checkbox" value="${carpark}">
                <span class="carpark-name">${carpark}</span>
            `;
            listContainer.appendChild(label);
        });
    }

    filterCarparksList(searchTerm) {
        const items = document.querySelectorAll('.carpark-item');
        const term = searchTerm.toLowerCase();
        items.forEach(item => {
            const name = item.querySelector('.carpark-name').textContent.toLowerCase();
            item.style.display = name.includes(term) ? '' : 'none';
        });
    }

    getSelectedCarparks() {
        const checkboxes = document.querySelectorAll('#carpark-list input[type="checkbox"]:checked');
        return Array.from(checkboxes).map(cb => cb.value);
    }

    setSelectedCarparks(carparks) {
        const checkboxes = document.querySelectorAll('#carpark-list input[type="checkbox"]');
        checkboxes.forEach(cb => {
            cb.checked = carparks.includes(cb.value);
        });
        this.updateSelectedCount();
    }

    updateSelectedCount() {
        const count = this.getSelectedCarparks().length;
        document.getElementById('selected-count').textContent = `${count} selected`;
    }

    generateAutoTitle() {
        const selected = this.getSelectedCarparks();
        return selected.join(', ');
    }

    updateAutoTitle() {
        const titleInput = document.getElementById('chart-title');
        const currentTitle = titleInput.value.trim();

        // Only auto-fill if title is empty or matches previous auto-generated value
        if (currentTitle === '' || currentTitle === this.lastAutoTitle) {
            const newTitle = this.generateAutoTitle();
            titleInput.value = newTitle;
            this.lastAutoTitle = newTitle;
        }
    }

    getTimeRangeLabel(hours) {
        if (this.customDateRange) {
            const options = { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' };
            const start = this.customDateRange.start.toLocaleString(undefined, options);
            const end = this.customDateRange.end.toLocaleString(undefined, options);
            return `${start} - ${end}`;
        }
        if (hours === 1) return 'Last 1 hour';
        if (hours === 6) return 'Last 6 hours';
        if (hours === 12) return 'Last 12 hours';
        if (hours === 24) return 'Last 24 hours';
        if (hours === 48) return 'Last 2 days';
        if (hours === 72) return 'Last 3 days';
        if (hours === 168) return 'Last 7 days';
        return `Last ${hours} hours`;
    }

    getTimeConfig(hours) {
        // Return adaptive time unit configuration based on range
        if (hours <= 1) {
            return {
                unit: 'minute',
                displayFormats: {
                    minute: 'HH:mm'
                },
                stepSize: 5
            };
        } else if (hours <= 6) {
            return {
                unit: 'hour',
                displayFormats: {
                    hour: 'HH:mm'
                },
                stepSize: 1
            };
        } else if (hours <= 48) {
            return {
                unit: 'hour',
                displayFormats: {
                    hour: 'MMM d, HH:mm'
                },
                stepSize: hours <= 24 ? 4 : 8
            };
        } else {
            return {
                unit: 'day',
                displayFormats: {
                    day: 'EEE MMM d'
                },
                stepSize: 1
            };
        }
    }

    updateTimeRangeDropdown() {
        const select = document.getElementById('time-range-select');
        const hours = this.config.settings.timeRange || 24;
        const customContainer = document.getElementById('custom-range-container');

        // Restore custom range from config if present
        if (this.config.settings.customRange && !this.customDateRange) {
            this.customDateRange = {
                start: new Date(this.config.settings.customRange.start),
                end: new Date(this.config.settings.customRange.end)
            };
            if (this.datePicker) {
                this.datePicker.setDate([this.customDateRange.start, this.customDateRange.end], false);
            }
        }

        if (this.customDateRange) {
            select.value = 'custom';
            customContainer.style.display = '';
        } else {
            select.value = hours;
            customContainer.style.display = 'none';
        }
    }

    initDatePicker() {
        this.datePicker = flatpickr('#date-range-picker', {
            mode: 'range',
            enableTime: true,
            time_24hr: true,
            enableSeconds: true,
            dateFormat: 'Y-m-d H:i:S',
            defaultDate: [new Date(), new Date()],
            maxDate: 'today',
            onChange: (selectedDates) => {
                if (selectedDates.length === 2) {
                    this.setCustomDateRange(selectedDates[0], selectedDates[1]);
                }
            }
        });

        // Restore picker dates if custom range is set
        if (this.customDateRange) {
            this.datePicker.setDate([this.customDateRange.start, this.customDateRange.end], false);
        }
    }

    setCustomDateRange(start, end) {
        this.customDateRange = { start, end };
        // Calculate hours from start to end
        const hours = Math.ceil((end - start) / (1000 * 60 * 60));
        this.config.settings.timeRange = hours;
        this.config.settings.customRange = { start: start.toISOString(), end: end.toISOString() };
        this.saveConfig();
        this.refreshAllCharts();
    }

    setGlobalTimeRange(hours) {
        this.customDateRange = null;
        delete this.config.settings.customRange;
        document.getElementById('custom-range-container').style.display = 'none';

        this.config.settings.timeRange = hours;
        this.saveConfig();
        this.updateTimeRangeDropdown();

        // Update all chart x-axis configurations and refresh
        Object.keys(this.charts).forEach(chartId => {
            const chart = this.charts[chartId];
            const timeConfig = this.getTimeConfig(hours);

            chart.options.scales.x.time.unit = timeConfig.unit;
            chart.options.scales.x.time.displayFormats = timeConfig.displayFormats;
            chart.options.scales.x.time.stepSize = timeConfig.stepSize;
            chart.options.scales.x.title.text = this.getTimeRangeLabel(hours);
        });

        this.refreshAllCharts();
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
        const hours = this.config.settings.timeRange || 24;
        const timeConfig = this.getTimeConfig(hours);

        const datasets = chartConfig.carparks.map((carpark, index) => ({
            label: carpark,
            data: [],
            borderColor: this.colors[index % this.colors.length],
            backgroundColor: this.colors[index % this.colors.length] + '20',
            fill: chartConfig.carparks.length === 1,
            tension: 0.3,
            pointRadius: 1,
            pointHoverRadius: 4,
            borderWidth: 2
        }));

        this.charts[chartConfig.id] = new Chart(ctx, {
            type: 'line',
            data: { datasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: {
                    duration: 300
                },
                interaction: {
                    mode: 'index',
                    intersect: false
                },
                scales: {
                    x: {
                        type: 'time',
                        time: {
                            unit: timeConfig.unit,
                            displayFormats: timeConfig.displayFormats,
                            stepSize: timeConfig.stepSize
                        },
                        title: {
                            display: true,
                            text: this.getTimeRangeLabel(hours),
                            color: '#666',
                            font: {
                                size: 11
                            }
                        },
                        grid: {
                            color: 'rgba(0, 0, 0, 0.05)'
                        },
                        ticks: {
                            maxRotation: 0,
                            autoSkip: true,
                            maxTicksLimit: 8
                        }
                    },
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Available Spots'
                        },
                        grid: {
                            color: 'rgba(0, 0, 0, 0.05)'
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
                        intersect: false,
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        titleFont: {
                            size: 13
                        },
                        bodyFont: {
                            size: 12
                        },
                        padding: 10,
                        callbacks: {
                            title: function(tooltipItems) {
                                if (tooltipItems.length > 0) {
                                    const date = new Date(tooltipItems[0].parsed.x);
                                    return date.toLocaleString();
                                }
                                return '';
                            },
                            label: function(context) {
                                const total = context.raw.total || '-';
                                return `${context.dataset.label}: ${context.parsed.y}/${total} spots`;
                            }
                        }
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

        const hours = this.config.settings.timeRange || 24;
        const readings = await this.fetchReadings(chartConfig.carparks, hours);

        chartConfig.carparks.forEach((carpark, index) => {
            const carparkReadings = readings[carpark] || [];
            chart.data.datasets[index].data = carparkReadings.map(r => ({
                x: new Date(r.timestamp),
                y: r.available,
                total: r.total_spots
            }));
        });

        chart.update();

        // Update chart info
        const card = document.querySelector(`[data-chart-id="${chartId}"]`);
        if (card) {
            const info = card.querySelector('.chart-info');
            const latestValues = chartConfig.carparks.map(carpark => {
                const data = readings[carpark] || [];
                if (data.length > 0) {
                    const latest = data[data.length - 1];
                    return `${carpark}: ${latest.available}/${latest.total_spots}`;
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
        this.lastAutoTitle = '';
        document.getElementById('modal-title').textContent = 'Add Chart';
        document.getElementById('chart-title').value = '';
        document.getElementById('carpark-search').value = '';
        this.filterCarparksList('');
        this.setSelectedCarparks([]);
        document.getElementById('chart-modal').classList.add('active');
    }

    openEditModal(chartId) {
        const chartConfig = this.config.charts.find(c => c.id === chartId);
        if (!chartConfig) return;

        this.editingChartId = chartId;
        this.lastAutoTitle = chartConfig.carparks.join(', ');
        document.getElementById('modal-title').textContent = 'Edit Chart';
        document.getElementById('chart-title').value = chartConfig.title;
        document.getElementById('carpark-search').value = '';
        this.filterCarparksList('');
        this.setSelectedCarparks(chartConfig.carparks);

        document.getElementById('chart-modal').classList.add('active');
    }

    closeModal() {
        document.getElementById('chart-modal').classList.remove('active');
        this.editingChartId = null;
        this.lastAutoTitle = '';
    }

    saveModal() {
        const title = document.getElementById('chart-title').value.trim();
        const selectedCarparks = this.getSelectedCarparks();

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
                carparks: selectedCarparks
            });
        } else {
            // Add new chart
            this.addChart({
                id: `chart-${Date.now()}`,
                title,
                carparks: selectedCarparks
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

        // Carpark search
        document.getElementById('carpark-search').addEventListener('input', (e) => {
            this.filterCarparksList(e.target.value);
        });

        // Clear search button
        document.getElementById('clear-search').addEventListener('click', () => {
            document.getElementById('carpark-search').value = '';
            this.filterCarparksList('');
        });

        // Carpark checkbox changes
        document.getElementById('carpark-list').addEventListener('change', (e) => {
            if (e.target.type === 'checkbox') {
                this.updateSelectedCount();
                this.updateAutoTitle();
            }
        });

        // Time range dropdown
        document.getElementById('time-range-select').addEventListener('change', (e) => {
            const value = e.target.value;
            if (value === 'custom') {
                document.getElementById('custom-range-container').style.display = '';
                this.datePicker.open();
            } else {
                this.setGlobalTimeRange(parseInt(value));
            }
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
