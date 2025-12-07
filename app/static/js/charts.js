class ChartManager {
    constructor() {
        this.charts = new Map();
        this.defaultOptions = {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                }
            },
            elements: {
                line: {
                    tension: 0.4
                }
            }
        };
    }
    
    createLineChart(canvasId, data, options = {}) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return null;
        
        const config = {
            type: 'line',
            data: data,
            options: {...this.defaultOptions, ...options}
        };
        
        const chart = new Chart(ctx, config);
        this.charts.set(canvasId, chart);
        return chart;
    }
    
    createBarChart(canvasId, data, options = {}) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return null;
        
        const config = {
            type: 'bar',
            data: data,
            options: {...this.defaultOptions, ...options}
        };
        
        const chart = new Chart(ctx, config);
        this.charts.set(canvasId, chart);
        return chart;
    }
    
    createPieChart(canvasId, data, options = {}) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return null;
        
        const config = {
            type: 'pie',
            data: data,
            options: {...this.defaultOptions, ...options}
        };
        
        const chart = new Chart(ctx, config);
        this.charts.set(canvasId, chart);
        return chart;
    }
    
    createGauge(canvasId, value, max = 100, options = {}) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return null;
        
        const config = {
            type: 'doughnut',
            data: {
                datasets: [{
                    data: [value, max - value],
                    backgroundColor: [
                        value > max * 0.8 ? '#EF4444' : value > max * 0.6 ? '#F59E0B' : '#10B981',
                        '#E5E7EB'
                    ],
                    borderWidth: 0
                }]
            },
            options: {
                ...this.defaultOptions,
                cutout: '70%',
                rotation: -90,
                circumference: 180,
                ...options
            }
        };
        
        const chart = new Chart(ctx, config);
        this.charts.set(canvasId, chart);
        return chart;
    }
    
    updateChart(canvasId, newData) {
        const chart = this.charts.get(canvasId);
        if (!chart) return;
        
        chart.data = newData;
        chart.update();
    }
    
    destroyChart(canvasId) {
        const chart = this.charts.get(canvasId);
        if (chart) {
            chart.destroy();
            this.charts.delete(canvasId);
        }
    }
    
    destroyAll() {
        this.charts.forEach((chart, id) => {
            chart.destroy();
        });
        this.charts.clear();
    }
}

const chartManager = new ChartManager();
