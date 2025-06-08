// Dashboard JavaScript for Fire Fighting System Reliability App

document.addEventListener('DOMContentLoaded', function() {
    // Load latest metrics for KPI cards
    loadLatestMetrics();
    
    // Load trend data for charts
    loadTrendData('weekly');
    
    // Set up trend period selector
    const trendSelector = document.getElementById('trend-period');
    if (trendSelector) {
        trendSelector.addEventListener('change', function() {
            loadTrendData(this.value);
        });
    }
});

// Function to load latest metrics for KPI cards
function loadLatestMetrics() {
    fetch('/api/metrics/latest')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updateKPICards(data.data);
                updateDistributionCharts(data.data);
            } else {
                console.error('Error loading metrics:', data.message);
            }
        })
        .catch(error => {
            console.error('Error fetching metrics:', error);
        });
}

// Function to update KPI cards with latest data
function updateKPICards(data) {
    // Update Testing Compliance KPI
    document.getElementById('testing-compliance-value').textContent = data.testing_compliance.toFixed(2) + '%';
    document.getElementById('testing-compliance-status').textContent = 
        data.testing_compliance >= 90 ? 'STATUS: ACHIEVED' : 'STATUS: IN PROGRESS';
    
    // Update Inspection Compliance KPI
    document.getElementById('inspection-compliance-value').textContent = data.inspection_compliance.toFixed(2) + '%';
    document.getElementById('inspection-compliance-status').textContent = 
        data.inspection_compliance >= 95 ? 'STATUS: ACHIEVED' : 'STATUS: IN PROGRESS';
    
    // Update Coverage Ratio KPI
    document.getElementById('coverage-ratio-value').textContent = data.coverage_ratio.toFixed(2) + '%';
    document.getElementById('coverage-ratio-status').textContent = 
        data.coverage_ratio >= 85 ? 'STATUS: ACHIEVED' : 'STATUS: IN PROGRESS';
    
    // Update Effective Reliability KPI
    document.getElementById('effective-reliability-value').textContent = data.effective_reliability.toFixed(2) + '%';
    document.getElementById('effective-reliability-status').textContent = 
        data.effective_reliability >= 80 ? 'STATUS: ACHIEVED' : 'STATUS: IN PROGRESS';
}

// Function to update distribution charts
function updateDistributionCharts(data) {
    // Coverage Status Distribution Chart
    const coverageCtx = document.getElementById('coverage-chart').getContext('2d');
    new Chart(coverageCtx, {
        type: 'pie',
        data: {
            labels: ['Fully Covered', 'Partially Covered', 'Not Covered'],
            datasets: [{
                data: [data.fully_covered, data.partially_covered, data.not_covered],
                backgroundColor: ['#4472C4', '#70AD47', '#ED7D31'],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'bottom'
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
    
    // Inspection Status Distribution Chart
    const inspectionCtx = document.getElementById('inspection-chart').getContext('2d');
    new Chart(inspectionCtx, {
        type: 'pie',
        data: {
            labels: ['Inspected', 'Not Inspected'],
            datasets: [{
                data: [data.inspected, data.not_inspected],
                backgroundColor: ['#4472C4', '#ED7D31'],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'bottom'
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
    
    // Testing Status Distribution Chart
    const testingCtx = document.getElementById('testing-chart').getContext('2d');
    new Chart(testingCtx, {
        type: 'pie',
        data: {
            labels: ['Tested', 'Not Tested'],
            datasets: [{
                data: [data.tested, data.not_tested],
                backgroundColor: ['#4472C4', '#ED7D31'],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'bottom'
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
                updateTrendChart(data.data, period);
            } else {
                console.error('Error loading trend data:', data.message);
            }
        })
        .catch(error => {
            console.error('Error fetching trend data:', error);
        });
}

// Function to update trend chart
function updateTrendChart(data, period) {
    // Clear previous chart if exists
    const chartContainer = document.getElementById('trend-chart-container');
    chartContainer.innerHTML = '<canvas id="trend-chart"></canvas>';
    
    const ctx = document.getElementById('trend-chart').getContext('2d');
    
    // Format dates for display
    const formattedDates = data.dates.map(date => {
        const d = new Date(date);
        if (period === 'weekly') {
            return `Week ${d.getDate()}/${d.getMonth()+1}`;
        } else if (period === 'monthly') {
            const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
            return `${months[d.getMonth()]} ${d.getFullYear()}`;
        } else {
            return d.getFullYear().toString();
        }
    });
    
    // Create chart
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: formattedDates,
            datasets: [
                {
                    label: 'Testing Compliance',
                    data: data.testing_compliance,
                    borderColor: '#5B9BD5',
                    backgroundColor: 'rgba(91, 155, 213, 0.1)',
                    borderWidth: 2,
                    tension: 0.3,
                    pointRadius: 4
                },
                {
                    label: 'Inspection Compliance',
                    data: data.inspection_compliance,
                    borderColor: '#70AD47',
                    backgroundColor: 'rgba(112, 173, 71, 0.1)',
                    borderWidth: 2,
                    tension: 0.3,
                    pointRadius: 4
                },
                {
                    label: 'Coverage Ratio',
                    data: data.coverage_ratio,
                    borderColor: '#ED7D31',
                    backgroundColor: 'rgba(237, 125, 49, 0.1)',
                    borderWidth: 2,
                    tension: 0.3,
                    pointRadius: 4
                },
                {
                    label: 'Effective Reliability',
                    data: data.effective_reliability,
                    borderColor: '#7030A0',
                    backgroundColor: 'rgba(112, 48, 160, 0.1)',
                    borderWidth: 2,
                    tension: 0.3,
                    pointRadius: 4
                }
            ]
        },
        options: {
            responsive: true,
            plugins: {
                title: {
                    display: true,
                    text: `${period.charAt(0).toUpperCase() + period.slice(1)} Compliance and Reliability Trends`,
                    font: {
                        size: 16,
                        weight: 'bold'
                    }
                },
                legend: {
                    position: 'bottom'
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            },
            scales: {
                y: {
                    beginAtZero: false,
                    min: 40,
                    max: 100,
                    title: {
                        display: true,
                        text: 'Percentage (%)'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: period.charAt(0).toUpperCase() + period.slice(1)
                    }
                }
            }
        }
    });
    
    // Update chart title
    document.getElementById('trend-chart-title').textContent = 
        `${period.charAt(0).toUpperCase() + period.slice(1)} Compliance and Reliability Trends`;
}
