// static/js/admin_charts.js
document.addEventListener('DOMContentLoaded', function () {
    // Chart.js global defaults for consistent styling
    Chart.defaults.font.family = "'Poppins', sans-serif";
    Chart.defaults.font.size = 14;
    Chart.defaults.color = '#2d3748'; // Match CSS --text-dark
    Chart.defaults.plugins.tooltip.backgroundColor = '#1a202c'; // Match CSS --dark-bg
    Chart.defaults.plugins.tooltip.borderColor = '#27ae60'; // Match CSS --primary-green
    Chart.defaults.plugins.tooltip.borderWidth = 1;

    // Function to create gradient background
    function createGradient(ctx, chartArea) {
        const gradient = ctx.createLinearGradient(
            chartArea.left,
            chartArea.bottom,
            chartArea.right,
            chartArea.top
        );
        gradient.addColorStop(0, '#e74c3c'); // CSS --primary-red
        gradient.addColorStop(1, '#27ae60'); // CSS --primary-green
        return gradient;
    }

    // Function to fetch data and render chart
    async function renderChart(canvasId, apiUrl, defaultChartType, title) {
        try {
            const response = await fetch(apiUrl);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const data = await response.json();

            const ctx = document.getElementById(canvasId).getContext('2d');
            const chartContainer = ctx.canvas.parentElement;
            let chartInstance = null;

            // Chart configuration
            const chartConfig = {
                type: defaultChartType,
                data: {
                    labels: data.labels || [],
                    datasets: [{
                        label: data.title || title,
                        data: data.data || [],
                        backgroundColor: defaultChartType === 'line' ? 'rgba(39, 174, 96, 0.2)' : createGradient(ctx, {
                            left: 0,
                            bottom: ctx.canvas.height,
                            right: ctx.canvas.width,
                            top: 0
                        }),
                        borderColor: defaultChartType === 'line' ? '#27ae60' : '#e74c3c',
                        borderWidth: 2,
                        fill: defaultChartType === 'line',
                        tension: defaultChartType === 'line' ? 0.4 : 0,
                        pointBackgroundColor: '#fff',
                        pointBorderColor: '#e74c3c',
                        pointHoverBackgroundColor: '#27ae60',
                        pointHoverBorderColor: '#fff',
                        pointRadius: 4,
                        pointHoverRadius: 6
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    layout: {
                        padding: 15
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: {
                                color: 'rgba(0, 0, 0, 0.1)',
                                borderColor: '#e2e8f0' // Match CSS --accent-bg
                            },
                            ticks: {
                                color: '#2d3748',
                                font: { size: 12 }
                            }
                        },
                        x: {
                            grid: {
                                display: defaultChartType === 'pie' || defaultChartType === 'doughnut' ? false : true,
                                color: 'rgba(0, 0, 0, 0.1)'
                            },
                            ticks: {
                                color: '#2d3748',
                                font: { size: 12 }
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            display: defaultChartType === 'pie' || defaultChartType === 'doughnut',
                            position: 'top',
                            labels: {
                                font: { size: 14 },
                                color: '#2d3748'
                            }
                        },
                        title: {
                            display: true,
                            text: data.title || title,
                            font: { size: 16, weight: '600' },
                            color: '#2d3748',
                            padding: { top: 10, bottom: 20 }
                        },
                        tooltip: {
                            enabled: true,
                            padding: 10,
                            cornerRadius: 8,
                            titleFont: { size: 14 },
                            bodyFont: { size: 12 },
                            callbacks: {
                                label: function (context) {
                                    return `${context.dataset.label}: ${context.parsed.y || context.parsed}`;
                                }
                            }
                        }
                    }
                }
            };

            // Render chart
            chartInstance = new Chart(ctx, chartConfig);

            // Add chart type toggle (bar, line, doughnut)
            const toggleContainer = document.createElement('div');
            toggleContainer.className = 'chart-toggle';
            toggleContainer.innerHTML = `
                <select class="chart-type-select">
                    <option value="bar" ${defaultChartType === 'bar' ? 'selected' : ''}>Bar</option>
                    <option value="line" ${defaultChartType === 'line' ? 'selected' : ''}>Line</option>
                    <option value="doughnut" ${defaultChartType === 'doughnut' ? 'selected' : ''}>Doughnut</option>
                </select>
            `;
            chartContainer.insertBefore(toggleContainer, ctx.canvas);

            // Handle chart type change
            toggleContainer.querySelector('.chart-type-select').addEventListener('change', function () {
                const newType = this.value;
                chartConfig.type = newType;
                chartConfig.data.datasets[0].backgroundColor = newType === 'line' ? 'rgba(39, 174, 96, 0.2)' : createGradient(ctx, {
                    left: 0,
                    bottom: ctx.canvas.height,
                    right: ctx.canvas.width,
                    top: 0
                });
                chartConfig.data.datasets[0].borderColor = newType === 'line' ? '#27ae60' : '#e74c3c';
                chartConfig.data.datasets[0].fill = newType === 'line';
                chartConfig.options.scales.x.grid.display = newType === 'pie' || newType === 'doughnut' ? false : true;
                chartConfig.options.plugins.legend.display = newType === 'pie' || newType === 'doughnut';
                chartInstance.destroy();
                chartInstance = new Chart(ctx, chartConfig);
            });

        } catch (error) {
            console.error(`Error fetching data for ${canvasId}:`, error);
            const chartContainer = document.getElementById(canvasId).parentElement;
            chartContainer.innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-triangle"></i> Could not load chart: ${title}.
                </div>`;
        }
    }

    // Render charts on admin dashboard
    const charts = [
        { id: 'videoViewsChart', url: '/admin/api/video_views', type: 'bar', title: 'Video Views' },
        { id: 'enrollmentTrendsChart', url: '/admin/api/enrollment_trends', type: 'line', title: 'Enrollment Trends' },
        { id: 'likesDistributionChart', url: '/admin/api/likes_distribution', type: 'doughnut', title: 'Likes Distribution' },
        { id: 'userActivityChart', url: '/admin/api/user_activity', type: 'bar', title: 'User Activity' }
    ];

    charts.forEach(chart => {
        if (document.getElementById(chart.id)) {
            renderChart(chart.id, chart.url, chart.type, chart.title);
        }
    });

    // Responsive chart adjustments
    function adjustChartFontSize() {
        const isMobile = window.innerWidth <= 768;
        Chart.defaults.font.size = isMobile ? 12 : 14;
        Chart.defaults.plugins.title.font.size = isMobile ? 14 : 16;
        Chart.defaults.plugins.tooltip.titleFont.size = isMobile ? 12 : 14;
        Chart.defaults.plugins.tooltip.bodyFont.size = isMobile ? 10 : 12;
        document.querySelectorAll('.chart-container canvas').forEach(canvas => {
            const chart = Chart.getChart(canvas);
            if (chart) {
                chart.options.scales.y.ticks.font.size = isMobile ? 10 : 12;
                chart.options.scales.x.ticks.font.size = isMobile ? 10 : 12;
                chart.options.plugins.legend.labels.font.size = isMobile ? 12 : 14;
                chart.update();
            }
        });
    }

    // Run on load and resize
    adjustChartFontSize();
    window.addEventListener('resize', adjustChartFontSize);
});