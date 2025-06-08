// Visualization module for Fire Fighting System Reliability App

// Function to initialize all charts when the page loads
function initializeCharts() {
    // Set up event listeners for trend period selector
    setupTrendSelector();
    
    // Load initial data
    loadLatestMetrics();
    loadTrendData('monthly'); // Default to monthly view
}

// Function to set up trend period selector
function setupTrendSelector() {
    const trendSelector = document.getElementById('trend-period');
    if (trendSelector) {
        trendSelector.addEventListener('change', function() {
            loadTrendData(this.value);
        });
    }
}

// Function to load latest metrics for KPI cards and distribution charts
function loadLatestMetrics() {
    fetch('/api/metrics/latest')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updateKPICards(data.data);
                createDistributionCharts(data.data);
            } else {
                console.error('Error loading metrics:', data.message);
                showErrorMessage('Failed to load latest metrics. Please try again later.');
            }
        })
        .catch(error => {
            console.error('Error fetching metrics:', error);
            showErrorMessage('Network error while loading metrics. Please check your connection.');
        });
}

// Function to update KPI cards with latest metrics
function updateKPICards(data) {
    // Update Testing Compliance KPI
    updateKPI('testing-compliance', data.testing_compliance, 90);
    
    // Update Inspection Compliance KPI
    updateKPI('inspection-compliance', data.inspection_compliance, 95);
    
    // Update Coverage Ratio KPI
    updateKPI('coverage-ratio', data.coverage_ratio, 85);
    
    // Update Effective Reliability KPI
    updateKPI('effective-reliability', data.effective_reliability, 80);
}

// Helper function to update a single KPI card
function updateKPI(id, value, target) {
    const valueElement = document.getElementById(`${id}-value`);
    const statusElement = document.getElementById(`${id}-status`);
    
    if (valueElement && statusElement) {
        valueElement.textContent = value.toFixed(2) + '%';
        
        // Update status text and apply color coding
        const achieved = value >= target;
        statusElement.textContent = achieved ? 'STATUS: ACHIEVED' : 'STATUS: IN PROGRESS';
        statusElement.style.color = achieved ? '#70AD47' : '#ED7D31';
    }
}

// Function to create distribution charts
function createDistributionCharts(data) {
    // Create Coverage Status Distribution Chart
    createPieChart(
        'coverage-chart',
        ['Fully Covered', 'Partially Covered', 'Not Covered'],
        [data.fully_covered, data.partially_covered, data.not_covered],
        ['#4472C4', '#70AD47', '#ED7D31']
    );
    
    // Create Inspection Status Distribution Chart
    createPieChart(
        'inspection-chart',
        ['Inspected', 'Not Inspected'],
        [data.inspected, data.not_inspected],
        ['#4472C4', '#ED7D31']
    );
    
    // Create Testing Status Distribution Chart
    createPieChart(
        'testing-chart',
        ['Tested', 'Not Tested'],
        [data.tested, data.not_tested],
        ['#4472C4', '#ED7D31']
    );
}

// Helper function to create a pie chart
function createPieChart(canvasId, labels, data, colors) {
    const canvas = document.getElementById(canvasId);
    
    // Clear any existing chart
    if (canvas._chart) {
        canvas._chart.destroy();
    }
    
    // Create new chart
    const ctx = canvas.getContext('2d');
    canvas._chart = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: colors,
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        font: {
                            size: 12
                        }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.raw || 0;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = Math.round((value / total) * 100);
                            return `${label}: ${value} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}

// Function to load trend data for charts
function loadTrendData(period) {
    fetch(`/api/metrics/trend/${period}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                createTrendChart(data.data, period);
                updateTrendTitle(period);
            } else {
                console.error('Error loading trend data:', data.message);
                showErrorMessage('Failed to load trend data. Please try again later.');
            }
        })
        .catch(error => {
            console.error('Error fetching trend data:', error);
            showErrorMessage('Network error while loading trend data. Please check your connection.');
        });
}

// Function to update trend chart title
function updateTrendTitle(period) {
    const titleElement = document.getElementById('trend-chart-title');
    if (titleElement) {
        const periodText = period.charAt(0).toUpperCase() + period.slice(1);
        titleElement.textContent = `${periodText} Compliance and Reliability Trends`;
    }
}

// Function to create trend chart
function createTrendChart(data, period) {
    const container = document.getElementById('trend-chart-container');
    
    // Clear existing chart
    container.innerHTML = '<canvas id="trend-chart"></canvas>';
    
    const ctx = document.getElementById('trend-chart').getContext('2d');
    
    // Format dates for display
    const formattedDates = formatDatesForPeriod(data.dates, period);
    
    // Create new chart
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: formattedDates,
            datasets: [
                createDataset('Testing Compliance', data.testing_compliance, '#5B9BD5', 'circle'),
                createDataset('Inspection Compliance', data.inspection_compliance, '#70AD47', 'triangle'),
                createDataset('Coverage Ratio', data.coverage_ratio, '#ED7D31', 'rect'),
                createDataset('Effective Reliability', data.effective_reliability, '#7030A0', 'diamond')
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false
            },
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        usePointStyle: true,
                        padding: 20,
                        font: {
                            size: 12
                        }
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(255, 255, 255, 0.9)',
                    titleColor: '#333',
                    bodyColor: '#333',
                    borderColor: '#ddd',
                    borderWidth: 1,
                    padding: 10,
                    usePointStyle: true,
                    callbacks: {
                        label: function(context) {
                            const label = context.dataset.label || '';
                            const value = context.raw || 0;
                            return `${label}: ${value.toFixed(2)}%`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: false,
                    min: getMinYScale(data),
                    max: 100,
                    title: {
                        display: true,
                        text: 'Percentage (%)',
                        font: {
                            weight: 'bold'
                        }
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.1)'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: periodToLabel(period),
                        font: {
                            weight: 'bold'
                        }
                    },
                    grid: {
                        display: false
                    }
                }
            }
        }
    });
}

// Helper function to create a dataset for the trend chart
function createDataset(label, data, color, pointStyle) {
    return {
        label: label,
        data: data,
        borderColor: color,
        backgroundColor: hexToRgba(color, 0.1),
        borderWidth: 2,
        tension: 0.3,
        pointStyle: pointStyle,
        pointRadius: 5,
        pointHoverRadius: 7,
        fill: true
    };
}

// Helper function to format dates based on period
function formatDatesForPeriod(dates, period) {
    return dates.map(dateStr => {
        const date = new Date(dateStr);
        
        if (period === 'weekly') {
            // Format as "Week DD/MM"
            return `Week ${date.getDate()}/${date.getMonth() + 1}`;
        } else if (period === 'monthly') {
            // Format as "MMM YYYY"
            const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
            return `${months[date.getMonth()]} ${date.getFullYear()}`;
        } else {
            // Format as "YYYY"
            return date.getFullYear().toString();
        }
    });
}

// Helper function to determine minimum Y scale value
function getMinYScale(data) {
    // Find the minimum value across all datasets
    const allValues = [
        ...data.testing_compliance,
        ...data.inspection_compliance,
        ...data.coverage_ratio,
        ...data.effective_reliability
    ];
    
    const min = Math.min(...allValues);
    
    // Round down to nearest 10 and subtract 10 for padding
    return Math.max(0, Math.floor(min / 10) * 10 - 10);
}

// Helper function to convert period to label
function periodToLabel(period) {
    switch (period) {
        case 'weekly':
            return 'Week';
        case 'monthly':
            return 'Month';
        case 'yearly':
            return 'Year';
        default:
            return 'Time Period';
    }
}

// Helper function to convert hex color to rgba
function hexToRgba(hex, alpha) {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

// Function to show error message
function showErrorMessage(message) {
    // Create alert element
    const alertDiv = document.createElement('div');
    alertDiv.className = 'alert alert-danger';
    alertDiv.textContent = message;
    
    // Add to page
    const container = document.querySelector('.container');
    container.insertBefore(alertDiv, container.firstChild);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
}

// Initialize charts when the page loads
document.addEventListener('DOMContentLoaded', initializeCharts);
