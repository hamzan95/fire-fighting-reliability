document.addEventListener("DOMContentLoaded", function() {
    // Helper function to create enhanced line charts
    function createLineChart(ctx, labels, datasets, title, options = {}) {
        return new Chart(ctx, {
            type: "line",
            data: {
                labels: labels,
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false,
                },
                plugins: {
                    legend: {
                        position: "top",
                        labels: {
                            usePointStyle: true,
                            padding: 20
                        }
                    },
                    title: {
                        display: true,
                        text: title,
                        font: {
                            size: 16,
                            weight: 'bold'
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(0,0,0,0.8)',
                        titleColor: 'white',
                        bodyColor: 'white',
                        borderColor: 'rgba(255,255,255,0.2)',
                        borderWidth: 1,
                        callbacks: {
                            label: function(context) {
                                return context.dataset.label + ': ' + context.parsed.y.toFixed(1) + '%';
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        display: true,
                        title: {
                            display: true,
                            text: options.xAxisTitle || 'Time Period',
                            font: {
                                weight: 'bold'
                            }
                        },
                        grid: {
                            color: 'rgba(0,0,0,0.1)'
                        }
                    },
                    y: {
                        beginAtZero: true,
                        max: 100,
                        title: {
                            display: true,
                            text: "Percentage (%)",
                            font: {
                                weight: 'bold'
                            }
                        },
                        grid: {
                            color: 'rgba(0,0,0,0.1)'
                        },
                        ticks: {
                            callback: function(value) {
                                return value + '%';
                            }
                        }
                    }
                },
                elements: {
                    line: {
                        tension: 0.2
                    },
                    point: {
                        radius: 4,
                        hoverRadius: 6
                    }
                },
                ...options
            }
        });
    }

    // Enhanced color scheme
    const colors = {
        reliability: {
            border: '#007bff',
            background: 'rgba(0, 123, 255, 0.1)'
        },
        testing: {
            border: '#28a745',
            background: 'rgba(40, 167, 69, 0.1)'
        },
        inspection: {
            border: '#ffc107',
            background: 'rgba(255, 193, 7, 0.1)'
        },
        coverage: {
            border: '#17a2b8',
            background: 'rgba(23, 162, 184, 0.1)'
        },
        effective: {
            border: '#dc3545',
            background: 'rgba(220, 53, 69, 0.1)'
        }
    };

    // Daily Chart (formerly Weekly)
    if (weeklyMetrics && weeklyMetrics.length > 0) {
        var dailyLabels = weeklyMetrics.map(m => {
            const date = new Date(m.date);
            return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        });
        var dailyDatasets = [
            {
                label: "Effective Reliability",
                data: weeklyMetrics.map(m => m.effective_reliability),
                borderColor: colors.effective.border,
                backgroundColor: colors.effective.background,
                fill: true,
                borderWidth: 3
            },
            {
                label: "Testing Compliance",
                data: weeklyMetrics.map(m => m.testing_compliance),
                borderColor: colors.testing.border,
                backgroundColor: colors.testing.background,
                fill: false,
                borderWidth: 2
            },
            {
                label: "Inspection Compliance",
                data: weeklyMetrics.map(m => m.inspection_compliance),
                borderColor: colors.inspection.border,
                backgroundColor: colors.inspection.background,
                fill: false,
                borderWidth: 2
            },
            {
                label: "Coverage Ratio",
                data: weeklyMetrics.map(m => m.coverage_ratio),
                borderColor: colors.coverage.border,
                backgroundColor: colors.coverage.background,
                fill: false,
                borderWidth: 2
            }
        ];
        var dailyCtx = document.getElementById("dailyChart").getContext("2d");
        createLineChart(dailyCtx, dailyLabels, dailyDatasets, "Daily Reliability Trends", {
            xAxisTitle: 'Date'
        });
    }

    // Monthly Chart
    if (monthlyMetrics && monthlyMetrics.length > 0) {
        var monthlyLabels = monthlyMetrics.map(m => {
            const [year, month] = m.month.split('-');
            const date = new Date(year, month - 1);
            return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short' });
        });
        var monthlyDatasets = [
            {
                label: "Effective Reliability",
                data: monthlyMetrics.map(m => m.avg_effective_reliability),
                borderColor: colors.effective.border,
                backgroundColor: colors.effective.background,
                fill: true,
                borderWidth: 3
            },
            {
                label: "Testing Compliance",
                data: monthlyMetrics.map(m => m.avg_testing_compliance),
                borderColor: colors.testing.border,
                backgroundColor: colors.testing.background,
                fill: false,
                borderWidth: 2
            },
            {
                label: "Inspection Compliance",
                data: monthlyMetrics.map(m => m.avg_inspection_compliance),
                borderColor: colors.inspection.border,
                backgroundColor: colors.inspection.background,
                fill: false,
                borderWidth: 2
            },
            {
                label: "Coverage Ratio",
                data: monthlyMetrics.map(m => m.avg_coverage_ratio),
                borderColor: colors.coverage.border,
                backgroundColor: colors.coverage.background,
                fill: false,
                borderWidth: 2
            }
        ];
        var monthlyCtx = document.getElementById("monthlyChart").getContext("2d");
        createLineChart(monthlyCtx, monthlyLabels, monthlyDatasets, "Monthly Reliability Trends", {
            xAxisTitle: 'Month'
        });
    }

    // Yearly Chart
    if (yearlyMetrics && yearlyMetrics.length > 0) {
        var yearlyLabels = yearlyMetrics.map(m => m.year);
        var yearlyDatasets = [
            {
                label: "Effective Reliability",
                data: yearlyMetrics.map(m => m.avg_effective_reliability),
                borderColor: colors.effective.border,
                backgroundColor: colors.effective.background,
                fill: true,
                borderWidth: 4
            },
            {
                label: "Testing Compliance",
                data: yearlyMetrics.map(m => m.avg_testing_compliance),
                borderColor: colors.testing.border,
                backgroundColor: colors.testing.background,
                fill: false,
                borderWidth: 3
            },
            {
                label: "Inspection Compliance",
                data: yearlyMetrics.map(m => m.avg_inspection_compliance),
                borderColor: colors.inspection.border,
                backgroundColor: colors.inspection.background,
                fill: false,
                borderWidth: 3
            },
            {
                label: "Coverage Ratio",
                data: yearlyMetrics.map(m => m.avg_coverage_ratio),
                borderColor: colors.coverage.border,
                backgroundColor: colors.coverage.background,
                fill: false,
                borderWidth: 3
            }
        ];
        var yearlyCtx = document.getElementById("yearlyChart").getContext("2d");
        createLineChart(yearlyCtx, yearlyLabels, yearlyDatasets, "Yearly Reliability Trends", {
            xAxisTitle: 'Year'
        });
    }

    // Add animation and loading states
    function showLoadingState(chartId) {
        const canvas = document.getElementById(chartId);
        const ctx = canvas.getContext('2d');
        ctx.fillStyle = '#f8f9fa';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = '#6c757d';
        ctx.font = '16px Arial';
        ctx.textAlign = 'center';
        ctx.fillText('Loading chart data...', canvas.width / 2, canvas.height / 2);
    }

    // Enhanced tab switching with chart refresh
    document.querySelectorAll('[data-bs-toggle="tab"]').forEach(tab => {
        tab.addEventListener('shown.bs.tab', function (e) {
            // Small delay to ensure tab content is visible
            setTimeout(() => {
                Chart.helpers.each(Chart.instances, function(instance) {
                    instance.resize();
                });
            }, 100);
        });
    });

    // Add smooth scrolling for better UX
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
});

// Global functions for admin controls
function refreshChart(chartType) {
    // This function can be called to refresh specific charts
    console.log(`Refreshing ${chartType} chart...`);
    // Implementation would depend on your specific needs
}

function exportChartData(chartType) {
    // Function to export chart data as CSV
    console.log(`Exporting ${chartType} data...`);
    // Implementation for data export
}

