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
        this.draggedChartId = null; // Currently dragged chart ID
        this.resizing = null;       // Resize state { chartId, startX, startWidth }
        this.gridColumnWidth = 0;   // Calculated column width in pixels
        this.insightsOffset = 0;    // Pagination offset for insights history
        this.insightsLimit = 10;    // Page size for insights history

        // Chart colors palette
        this.colors = [
            '#2196F3', '#4CAF50', '#FF9800', '#E91E63',
            '#9C27B0', '#00BCD4', '#FF5722', '#607D8B'
        ];

        // Chart type configurations
        this.chartTypes = {
            available_spots: {
                yAxisTitle: 'Available Spots',
                getValue: (r) => r.available,
                formatTooltip: (value, total) => `${value}/${total} spots`,
                formatInfo: (latest) => `${latest.available}/${latest.total_spots}`,
                yAxisConfig: { beginAtZero: true }
            },
            vacancy_rate: {
                yAxisTitle: 'Vacancy Rate (%)',
                getValue: (r) => r.total_spots > 0 ? (r.available / r.total_spots) * 100 : 0,
                formatTooltip: (value) => `${value.toFixed(1)}%`,
                formatInfo: (latest) => {
                    const rate = latest.total_spots > 0
                        ? ((latest.available / latest.total_spots) * 100).toFixed(1) : 0;
                    return `${rate}%`;
                },
                yAxisConfig: { beginAtZero: true, max: 100 }
            }
        };
    }

    async init() {
        await this.loadCarparks();
        await this.loadConfig();
        this.renderCharts();
        this.setupEventListeners();
        this.setupInsightsEventListeners();
        this.initDatePicker();
        this.startAutoRefresh();
        this.updateLastUpdated();
        this.updateTimeRangeDropdown();
        this.loadLatestInsight();
    }

    // --- API Methods ---

    async loadCarparks() {
        try {
            const response = await fetch('/api/carparks');
            const data = await response.json();
            this.carparks = data.carparks || [];
            this.populateCarparksList();
            this.populateInsightsCarparkDropdown();
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
            // Migrate charts to include layout if missing
            this.migrateChartLayouts();
        } catch (error) {
            console.error('Failed to load config:', error);
            this.config = {
                version: 2,
                settings: { autoRefresh: true, refreshInterval: 60, timeRange: 24 },
                charts: []
            };
        }
    }

    migrateChartLayouts() {
        // Assign layout to charts that don't have one
        let row = 0;
        let col = 0;
        this.config.charts.forEach(chart => {
            if (!chart.layout) {
                chart.layout = { row, col: 0, width: 12 };
                row++;
            }
        });
        // Normalize to ensure no overlaps
        this.normalizeLayout();
    }

    normalizeLayout() {
        // Sort charts by row then column
        const charts = this.config.charts.slice();
        charts.sort((a, b) => {
            const aLayout = a.layout || { row: 0, col: 0, width: 12 };
            const bLayout = b.layout || { row: 0, col: 0, width: 12 };
            if (aLayout.row !== bLayout.row) return aLayout.row - bLayout.row;
            return aLayout.col - bLayout.col;
        });

        // Reflow charts to remove gaps and prevent overlaps
        let currentRow = 0;
        let currentCol = 0;

        charts.forEach(chart => {
            const layout = chart.layout || { row: 0, col: 0, width: 12 };
            const width = layout.width || 12;

            // If chart doesn't fit on current row, move to next
            if (currentCol + width > 12) {
                currentRow++;
                currentCol = 0;
            }

            layout.row = currentRow;
            layout.col = currentCol;
            chart.layout = layout;

            currentCol += width;
            // If row is full, move to next
            if (currentCol >= 12) {
                currentRow++;
                currentCol = 0;
            }
        });

        // Update config with sorted charts
        this.config.charts = charts;
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

    populateCarparksList(selectedCarparks = []) {
        const listContainer = document.getElementById('carpark-list');
        listContainer.innerHTML = '';

        const selectedSet = new Set(selectedCarparks);
        const sortedCarparks = [...this.carparks].sort((a, b) => {
            const aSelected = selectedSet.has(a);
            const bSelected = selectedSet.has(b);
            if (aSelected && !bSelected) return -1;
            if (!aSelected && bSelected) return 1;
            return a.localeCompare(b);
        });

        sortedCarparks.forEach(carpark => {
            const label = document.createElement('label');
            label.className = 'carpark-item';
            label.innerHTML = `
                <input type="checkbox" value="${carpark}" ${selectedSet.has(carpark) ? 'checked' : ''}>
                <span class="carpark-name">${carpark}</span>
            `;
            listContainer.appendChild(label);
        });
        this.updateSelectedCount();
    }

    populateInsightsCarparkDropdown() {
        const select = document.getElementById('insight-carpark-select');
        if (!select) return;

        // Keep "All Carparks" as first option
        select.innerHTML = '<option value="">All Carparks</option>';

        // Add each carpark as an option
        this.carparks.forEach(carpark => {
            const option = document.createElement('option');
            option.value = carpark;
            option.textContent = carpark;
            select.appendChild(option);
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

        // Calculate grid column width for resize calculations
        this.calculateGridColumnWidth();

        if (this.config.charts.length === 0) {
            const template = document.getElementById('empty-state-template');
            container.appendChild(template.content.cloneNode(true));
            return;
        }

        this.config.charts.forEach(chartConfig => {
            this.createChartCard(chartConfig);
        });
    }

    calculateGridColumnWidth() {
        const container = document.getElementById('charts-container');
        if (container) {
            const containerWidth = container.clientWidth - 48; // 1.5rem * 2 padding
            const gap = 24; // 1.5rem gap
            this.gridColumnWidth = (containerWidth - (11 * gap)) / 12;
        }
    }

    createChartCard(chartConfig) {
        const container = document.getElementById('charts-container');
        const template = document.getElementById('chart-card-template');
        const card = template.content.cloneNode(true);

        const cardElement = card.querySelector('.chart-card');
        cardElement.dataset.chartId = chartConfig.id;
        cardElement.setAttribute('draggable', 'true');

        // Apply layout
        const layout = chartConfig.layout || { row: 0, col: 0, width: 12 };
        cardElement.dataset.width = layout.width;
        cardElement.style.gridRow = layout.row + 1;
        cardElement.style.gridColumn = `${layout.col + 1} / span ${layout.width}`;

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

        // Add resize handle
        const resizeHandle = document.createElement('div');
        resizeHandle.className = 'resize-handle';
        resizeHandle.addEventListener('mousedown', (e) => this.startResize(e, chartConfig.id));
        cardElement.appendChild(resizeHandle);

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
        const chartType = chartConfig.chartType || 'available_spots';
        const typeConfig = this.chartTypes[chartType];

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

        // Build y-axis config
        const yAxisConfig = {
            beginAtZero: typeConfig.yAxisConfig.beginAtZero,
            title: {
                display: true,
                text: typeConfig.yAxisTitle
            },
            grid: {
                color: 'rgba(0, 0, 0, 0.05)'
            }
        };
        if (typeConfig.yAxisConfig.max !== undefined) {
            yAxisConfig.max = typeConfig.yAxisConfig.max;
            yAxisConfig.ticks = {
                callback: (v) => v + '%'
            };
        }

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
                    y: yAxisConfig
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
                            label: (context) => {
                                const value = context.parsed.y;
                                const total = context.raw.total || '-';
                                return `${context.dataset.label}: ${typeConfig.formatTooltip(value, total)}`;
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
        const chartType = chartConfig.chartType || 'available_spots';
        const typeConfig = this.chartTypes[chartType];

        chartConfig.carparks.forEach((carpark, index) => {
            const carparkReadings = readings[carpark] || [];
            chart.data.datasets[index].data = carparkReadings.map(r => ({
                x: new Date(r.timestamp),
                y: typeConfig.getValue(r),
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
                    return `${carpark}: ${typeConfig.formatInfo(latest)}`;
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
        document.getElementById('chart-type').value = 'available_spots';
        document.getElementById('chart-width').value = '12';
        document.getElementById('carpark-search').value = '';
        this.populateCarparksList([]);
        this.filterCarparksList('');
        document.getElementById('chart-modal').classList.add('active');
    }

    openEditModal(chartId) {
        const chartConfig = this.config.charts.find(c => c.id === chartId);
        if (!chartConfig) return;

        this.editingChartId = chartId;
        this.lastAutoTitle = chartConfig.carparks.join(', ');
        document.getElementById('modal-title').textContent = 'Edit Chart';
        document.getElementById('chart-title').value = chartConfig.title;
        document.getElementById('chart-type').value = chartConfig.chartType || 'available_spots';
        document.getElementById('chart-width').value = chartConfig.layout?.width?.toString() || '12';
        document.getElementById('carpark-search').value = '';
        this.populateCarparksList(chartConfig.carparks);
        this.filterCarparksList('');
        document.getElementById('chart-modal').classList.add('active');
    }

    closeModal() {
        document.getElementById('chart-modal').classList.remove('active');
        this.editingChartId = null;
        this.lastAutoTitle = '';
    }

    saveModal() {
        const title = document.getElementById('chart-title').value.trim();
        const chartType = document.getElementById('chart-type').value;
        const chartWidth = parseInt(document.getElementById('chart-width').value);
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
            const chartConfig = this.config.charts.find(c => c.id === this.editingChartId);
            const currentLayout = chartConfig?.layout || { row: 0, col: 0, width: 12 };
            this.updateChart(this.editingChartId, {
                title,
                chartType,
                carparks: selectedCarparks,
                layout: { ...currentLayout, width: chartWidth }
            });
        } else {
            // Add new chart - place at end with full width
            const lastChart = this.config.charts[this.config.charts.length - 1];
            const newRow = lastChart ? (lastChart.layout?.row || 0) + 1 : 0;
            this.addChart({
                id: `chart-${Date.now()}`,
                title,
                chartType,
                carparks: selectedCarparks,
                layout: { row: newRow, col: 0, width: chartWidth }
            });
        }

        this.closeModal();
    }

    // --- Chart Management ---

    addChart(chartConfig) {
        this.config.charts.push(chartConfig);
        this.normalizeLayout();
        this.saveConfig();
        this.renderCharts();
    }

    updateChart(chartId, updates) {
        const chartConfig = this.config.charts.find(c => c.id === chartId);
        if (!chartConfig) return;

        Object.assign(chartConfig, updates);
        this.normalizeLayout();
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

    // --- Insights Methods ---

    async loadLatestInsight() {
        try {
            const response = await fetch('/api/insights/latest');
            const data = await response.json();
            if (data.insight) {
                this.renderLatestInsight(data.insight);
            }
        } catch (error) {
            console.error('Failed to load latest insight:', error);
        }
    }

    async generateInsight() {
        this.setGeneratingState(true);
        try {
            const hours = this.config.settings.timeRange || 24;
            const selectedCarpark = document.getElementById('insight-carpark-select').value;
            const response = await fetch('/api/insights/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    type: 'daily_summary',
                    hours,
                    carpark: selectedCarpark || null
                })
            });
            const data = await response.json();
            if (data.error) {
                this.renderInsightError(data.error);
            } else if (data.insight) {
                this.renderLatestInsight(data.insight);
            }
        } catch (error) {
            console.error('Failed to generate insight:', error);
            this.renderInsightError('Failed to connect to the server. Please try again.');
        } finally {
            this.setGeneratingState(false);
        }
    }

    renderLatestInsight(insight) {
        const container = document.getElementById('latest-insight');
        const createdAt = insight.created_at ? new Date(insight.created_at).toLocaleString() : 'Just now';
        const rangeStart = insight.data_range_start ? new Date(insight.data_range_start).toLocaleString() : '-';
        const rangeEnd = insight.data_range_end ? new Date(insight.data_range_end).toLocaleString() : '-';

        // Convert content paragraphs
        const contentHtml = insight.content
            .split('\n\n')
            .filter(p => p.trim())
            .map(p => `<p>${this.escapeHtml(p)}</p>`)
            .join('');

        container.innerHTML = `
            <div class="insight-content">
                <span class="insight-type">${this.escapeHtml(insight.insight_type.replace('_', ' '))}</span>
                <h3 class="insight-title">${this.escapeHtml(insight.title)}</h3>
                <div class="insight-text">${contentHtml}</div>
                <div class="insight-meta">
                    <span>Generated: ${createdAt}</span>
                    <span>Data range: ${rangeStart} - ${rangeEnd}</span>
                </div>
            </div>
        `;
    }

    renderInsightError(message) {
        const container = document.getElementById('latest-insight');
        container.innerHTML = `
            <div class="insight-error">
                <p><strong>Error:</strong> ${this.escapeHtml(message)}</p>
            </div>
        `;
    }

    setGeneratingState(isGenerating) {
        const btn = document.getElementById('generate-insight-btn');
        const textSpan = btn.querySelector('.btn-label');
        const loadingSpan = btn.querySelector('.btn-loading');
        btn.disabled = isGenerating;
        textSpan.style.display = isGenerating ? 'none' : 'inline';
        loadingSpan.style.display = isGenerating ? 'inline-flex' : 'none';
    }

    async loadInsightsHistory(reset = false) {
        if (reset) {
            this.insightsOffset = 0;
        }

        try {
            const response = await fetch(
                `/api/insights?limit=${this.insightsLimit}&offset=${this.insightsOffset}`
            );
            const data = await response.json();

            const listContainer = document.getElementById('insights-history-list');
            const emptyState = document.getElementById('insights-history-empty');
            const loadMoreBtn = document.getElementById('load-more-insights');

            if (reset) {
                listContainer.innerHTML = '';
            }

            if (data.insights.length === 0 && this.insightsOffset === 0) {
                listContainer.style.display = 'none';
                emptyState.style.display = 'block';
                loadMoreBtn.style.display = 'none';
                return;
            }

            listContainer.style.display = 'block';
            emptyState.style.display = 'none';

            data.insights.forEach(insight => {
                const item = document.createElement('div');
                item.className = 'insights-history-item';
                item.innerHTML = `
                    <span class="insight-type">${this.escapeHtml(insight.insight_type.replace('_', ' '))}</span>
                    <h4 class="insight-title">${this.escapeHtml(insight.title)}</h4>
                    <p class="insight-preview">${this.escapeHtml(insight.content.substring(0, 150))}...</p>
                    <span class="insight-date">${new Date(insight.created_at).toLocaleString()}</span>
                `;
                item.addEventListener('click', () => {
                    this.renderLatestInsight(insight);
                    this.closeInsightsHistoryModal();
                });
                listContainer.appendChild(item);
            });

            this.insightsOffset += data.insights.length;
            loadMoreBtn.style.display = data.hasMore ? 'block' : 'none';
        } catch (error) {
            console.error('Failed to load insights history:', error);
        }
    }

    openInsightsHistoryModal() {
        this.loadInsightsHistory(true);
        document.getElementById('insights-history-modal').classList.add('active');
    }

    closeInsightsHistoryModal() {
        document.getElementById('insights-history-modal').classList.remove('active');
    }

    toggleInsightsSection() {
        const section = document.getElementById('insights-section');
        section.classList.toggle('collapsed');
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    setupInsightsEventListeners() {
        // Toggle insights section collapse
        document.getElementById('insights-toggle').addEventListener('click', (e) => {
            // Don't toggle if clicking on buttons
            if (e.target.closest('.insights-actions')) return;
            this.toggleInsightsSection();
        });

        // Generate insight button
        document.getElementById('generate-insight-btn').addEventListener('click', (e) => {
            e.stopPropagation();
            this.generateInsight();
        });

        // View history button
        document.getElementById('toggle-insights-history').addEventListener('click', () => {
            this.openInsightsHistoryModal();
        });

        // History modal close buttons
        document.getElementById('insights-history-close').addEventListener('click', () => {
            this.closeInsightsHistoryModal();
        });

        document.getElementById('insights-history-close-btn').addEventListener('click', () => {
            this.closeInsightsHistoryModal();
        });

        // Load more button
        document.getElementById('load-more-insights').addEventListener('click', () => {
            this.loadInsightsHistory(false);
        });

        // Close modal on backdrop click
        document.getElementById('insights-history-modal').addEventListener('click', (e) => {
            if (e.target.classList.contains('modal')) {
                this.closeInsightsHistoryModal();
            }
        });
    }

    // --- Drag and Drop ---

    handleDragStart(e) {
        const card = e.target.closest('.chart-card');
        if (!card) return;

        this.draggedChartId = card.dataset.chartId;
        card.classList.add('dragging');
        e.dataTransfer.effectAllowed = 'move';
    }

    handleDragEnd(e) {
        const card = e.target.closest('.chart-card');
        if (card) {
            card.classList.remove('dragging');
        }
        this.draggedChartId = null;

        // Remove drag-over class from all cards
        document.querySelectorAll('.chart-card.drag-over').forEach(c => {
            c.classList.remove('drag-over');
        });
    }

    handleDragOver(e) {
        e.preventDefault();
        const card = e.target.closest('.chart-card');
        if (card && card.dataset.chartId !== this.draggedChartId) {
            card.classList.add('drag-over');
        }
    }

    handleDragLeave(e) {
        const card = e.target.closest('.chart-card');
        if (card) {
            card.classList.remove('drag-over');
        }
    }

    handleDrop(e) {
        e.preventDefault();
        const targetCard = e.target.closest('.chart-card');
        if (!targetCard || !this.draggedChartId) return;

        const targetId = targetCard.dataset.chartId;
        if (targetId !== this.draggedChartId) {
            this.reorderCharts(this.draggedChartId, targetId);
        }

        targetCard.classList.remove('drag-over');
    }

    reorderCharts(draggedId, targetId) {
        const charts = this.config.charts;
        const draggedIndex = charts.findIndex(c => c.id === draggedId);
        const targetIndex = charts.findIndex(c => c.id === targetId);

        if (draggedIndex === -1 || targetIndex === -1) return;

        // Remove dragged chart and insert at target position
        const [draggedChart] = charts.splice(draggedIndex, 1);
        charts.splice(targetIndex, 0, draggedChart);

        // Normalize layout after reorder
        this.normalizeLayout();
        this.saveConfig();

        // Destroy all chart instances before re-rendering
        Object.keys(this.charts).forEach(chartId => {
            if (this.charts[chartId]) {
                this.charts[chartId].destroy();
                delete this.charts[chartId];
            }
        });

        this.renderCharts();
    }

    // --- Resize Functionality ---

    startResize(e, chartId) {
        e.preventDefault();
        e.stopPropagation();

        this.calculateGridColumnWidth();

        const chartConfig = this.config.charts.find(c => c.id === chartId);
        if (!chartConfig) return;

        const layout = chartConfig.layout || { row: 0, col: 0, width: 12 };

        this.resizing = {
            chartId,
            startX: e.clientX,
            startWidth: layout.width,
            currentWidth: layout.width,
            minWidth: 3,
            maxWidth: 12 - layout.col
        };

        const handle = e.target;
        handle.classList.add('resizing');

        document.addEventListener('mousemove', this.handleResize);
        document.addEventListener('mouseup', this.endResize);
    }

    handleResize = (e) => {
        if (!this.resizing) return;

        const deltaX = e.clientX - this.resizing.startX;
        const columnWidth = this.gridColumnWidth + 24; // Include gap
        const deltaColumns = Math.round(deltaX / columnWidth);

        let newWidth = this.resizing.startWidth + deltaColumns;
        newWidth = Math.max(this.resizing.minWidth, Math.min(this.resizing.maxWidth, newWidth));

        // Only update if width changed
        if (newWidth !== this.resizing.currentWidth) {
            this.resizing.currentWidth = newWidth;

            // Update visual width
            const card = document.querySelector(`[data-chart-id="${this.resizing.chartId}"]`);
            if (card) {
                card.dataset.width = newWidth;
                const chartConfig = this.config.charts.find(c => c.id === this.resizing.chartId);
                if (chartConfig) {
                    const layout = chartConfig.layout || { row: 0, col: 0, width: 12 };
                    card.style.gridColumn = `${layout.col + 1} / span ${newWidth}`;
                }

                // Resize the Chart.js instance smoothly
                if (this.charts[this.resizing.chartId]) {
                    this.charts[this.resizing.chartId].resize();
                }
            }
        }
    }

    endResize = (e) => {
        if (!this.resizing) return;

        const newWidth = this.resizing.currentWidth || this.resizing.startWidth;

        // Update config
        const chartConfig = this.config.charts.find(c => c.id === this.resizing.chartId);
        if (chartConfig && chartConfig.layout) {
            chartConfig.layout.width = newWidth;
            this.saveConfig();
        }

        // Remove resizing class
        document.querySelectorAll('.resize-handle.resizing').forEach(h => {
            h.classList.remove('resizing');
        });

        const resizingChartId = this.resizing.chartId;
        this.resizing = null;
        document.removeEventListener('mousemove', this.handleResize);
        document.removeEventListener('mouseup', this.endResize);

        // Final resize to ensure chart fits properly
        if (this.charts[resizingChartId]) {
            this.charts[resizingChartId].resize();
        }
    }

    // --- Event Listeners ---

    setupEventListeners() {
        // Drag and drop for chart reordering
        const chartsContainer = document.getElementById('charts-container');
        chartsContainer.addEventListener('dragstart', (e) => this.handleDragStart(e));
        chartsContainer.addEventListener('dragend', (e) => this.handleDragEnd(e));
        chartsContainer.addEventListener('dragover', (e) => this.handleDragOver(e));
        chartsContainer.addEventListener('dragleave', (e) => this.handleDragLeave(e));
        chartsContainer.addEventListener('drop', (e) => this.handleDrop(e));

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

        // Recalculate grid column width on window resize
        window.addEventListener('resize', () => {
            this.calculateGridColumnWidth();
        });
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.app = new DashboardApp();
    window.app.init();
});
