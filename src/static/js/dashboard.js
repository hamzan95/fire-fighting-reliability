document.addEventListener("DOMContentLoaded", function() {
    // Coverage Chart
    var coverageCtx = document.getElementById("coverageChart").getContext("2d");
    new Chart(coverageCtx, {
        type: "pie",
        data: {
            labels: Object.keys(coverageData),
            datasets: [{
                data: Object.values(coverageData),
                backgroundColor: ["#007bff", "#ffc107", "#dc3545"]
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: "top",
                },
                title: {
                    display: true,
                    text: "Substation Coverage Status"
                }
            }
        }
    });

    // Inspection Chart
    var inspectionCtx = document.getElementById("inspectionChart").getContext("2d");
    new Chart(inspectionCtx, {
        type: "pie",
        data: {
            labels: Object.keys(inspectionData),
            datasets: [{
                data: Object.values(inspectionData),
                backgroundColor: ["#28a745", "#dc3545"]
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: "top",
                },
                title: {
                    display: true,
                    text: "Substation Inspection Status"
                }
            }
        }
    });

    // Testing Chart
    var testingCtx = document.getElementById("testingChart").getContext("2d");
    new Chart(testingCtx, {
        type: "pie",
        data: {
            labels: Object.keys(testingData),
            datasets: [{
                data: Object.values(testingData),
                backgroundColor: ["#17a2b8", "#dc3545"]
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: "top",
                },
                title: {
                    display: true,
                    text: "Substation Testing Status"
                }
            }
        }
    });
});

