document.addEventListener("DOMContentLoaded", function() {
    // Helper function to create charts
    function createLineChart(ctx, labels, datasets, title) {
        new Chart(ctx, {
            type: "line",
            data: {
                labels: labels,
                datasets: datasets
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: "top",
                    },
                    title: {
                        display: true,
                        text: title
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: "Percentage (%)"
                        }
                    }
                }
            }
        });
    }

    // Weekly Chart
    var weeklyLabels = weeklyMetrics.map(m => m.date);
    var weeklyDatasets = [
        {
            label: "Reliability Score",
            data: weeklyMetrics.map(m => m.reliability_score),
            borderColor: "#007bff",
            fill: false
        },
        {
            label: "Testing Compliance",
            data: weeklyMetrics.map(m => m.testing_compliance),
            borderColor: "#28a745",
            fill: false
        },
        {
            label: "Inspection Compliance",
            data: weeklyMetrics.map(m => m.inspection_compliance),
            borderColor: "#ffc107",
            fill: false
        },
        {
            label: "Coverage Ratio",
            data: weeklyMetrics.map(m => m.coverage_ratio),
            borderColor: "#17a2b8",
            fill: false
        },
        {
            label: "Effective Reliability",
            data: weeklyMetrics.map(m => m.effective_reliability),
            borderColor: "#dc3545",
            fill: false
        }
    ];
    var weeklyCtx = document.getElementById("weeklyChart").getContext("2d");
    createLineChart(weeklyCtx, weeklyLabels, weeklyDatasets, "Weekly Reliability Trends");

    // Monthly Chart
    var monthlyLabels = monthlyMetrics.map(m => m.month);
    var monthlyDatasets = [
        {
            label: "Reliability Score",
            data: monthlyMetrics.map(m => m.avg_reliability),
            borderColor: "#007bff",
            fill: false
        },
        {
            label: "Testing Compliance",
            data: monthlyMetrics.map(m => m.avg_testing_compliance),
            borderColor: "#28a745",
            fill: false
        },
        {
            label: "Inspection Compliance",
            data: monthlyMetrics.map(m => m.avg_inspection_compliance),
            borderColor: "#ffc107",
            fill: false
        },
        {
            label: "Coverage Ratio",
            data: monthlyMetrics.map(m => m.avg_coverage_ratio),
            borderColor: "#17a2b8",
            fill: false
        },
        {
            label: "Effective Reliability",
            data: monthlyMetrics.map(m => m.avg_effective_reliability),
            borderColor: "#dc3545",
            fill: false
        }
    ];
    var monthlyCtx = document.getElementById("monthlyChart").getContext("2d");
    createLineChart(monthlyCtx, monthlyLabels, monthlyDatasets, "Monthly Reliability Trends");

    // Yearly Chart
    var yearlyLabels = yearlyMetrics.map(m => m.year);
    var yearlyDatasets = [
        {
            label: "Reliability Score",
            data: yearlyMetrics.map(m => m.avg_reliability),
            borderColor: "#007bff",
            fill: false
        },
        {
            label: "Testing Compliance",
            data: yearlyMetrics.map(m => m.avg_testing_compliance),
            borderColor: "#28a745",
            fill: false
        },
        {
            label: "Inspection Compliance",
            data: yearlyMetrics.map(m => m.avg_inspection_compliance),
            borderColor: "#ffc107",
            fill: false
        },
        {
            label: "Coverage Ratio",
            data: yearlyMetrics.map(m => m.avg_coverage_ratio),
            borderColor: "#17a2b8",
            fill: false
        },
        {
            label: "Effective Reliability",
            data: yearlyMetrics.map(m => m.avg_effective_reliability),
            borderColor: "#dc3545",
            fill: false
        }
    ];
    var yearlyCtx = document.getElementById("yearlyChart").getContext("2d");
    createLineChart(yearlyCtx, yearlyLabels, yearlyDatasets, "Yearly Reliability Trends");
});

