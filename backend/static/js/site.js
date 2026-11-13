(function () {
    "use strict";

    /* Page scripts (for example the analytics dashboard) read colours through these helpers. */
    window.ssToken = ssToken;
    window.ssWithAlpha = withAlpha;

    runWhenReady(function () {
        initOptionBuilders();
        initSystemReportChart();
    });

    function runWhenReady(callback) {
        if (document.readyState === "loading") {
            document.addEventListener("DOMContentLoaded", callback);
            return;
        }

        callback();
    }

    function initOptionBuilders() {
        document.querySelectorAll("[data-option-builder]").forEach(function (builder) {
            var list = builder.querySelector("[data-option-list]");
            var addButton = builder.querySelector("[data-option-add]");
            var sourceWrap = builder.querySelector("[data-option-source-wrap]");

            if (!list || !addButton || !sourceWrap) {
                return;
            }

            var source = sourceWrap.querySelector("textarea, input[type='text'], input:not([type])");
            if (!source) {
                return;
            }

            sourceWrap.classList.add("is-enhanced");
            source.setAttribute("aria-hidden", "true");
            source.tabIndex = -1;

            var initialValues = source.value
                .split(/\r?\n/)
                .map(function (value) {
                    return value.trim();
                })
                .filter(Boolean);

            if (initialValues.length === 0) {
                addOptionRow(list, "", syncOptions);
            } else {
                initialValues.forEach(function (value) {
                    addOptionRow(list, value, syncOptions);
                });
            }

            addButton.addEventListener("click", function () {
                var input = addOptionRow(list, "", syncOptions);
                input.focus();
                syncOptions();
            });

            var form = builder.closest("form");
            if (form) {
                form.addEventListener("submit", syncOptions);
            }

            syncOptions();

            function syncOptions() {
                source.value = Array.from(
                    list.querySelectorAll("[data-option-input]")
                )
                    .map(function (input) {
                        return input.value.trim();
                    })
                    .filter(Boolean)
                    .join("\n");
            }
        });
    }

    function addOptionRow(list, value, syncOptions) {
        var row = document.createElement("div");
        row.className = "option-builder-row";

        var input = document.createElement("input");
        input.type = "text";
        input.className = "form-control";
        input.placeholder = "Option text";
        input.value = value;
        input.setAttribute("data-option-input", "");

        var removeButton = document.createElement("button");
        removeButton.type = "button";
        removeButton.className = "btn btn-outline-danger";
        removeButton.innerHTML = '<i class="bi bi-x-lg me-1"></i>Remove';

        input.addEventListener("input", syncOptions);
        removeButton.addEventListener("click", function () {
            row.remove();
            if (!list.querySelector("[data-option-input]")) {
                addOptionRow(list, "", syncOptions);
            }
            syncOptions();
        });

        row.appendChild(input);
        row.appendChild(removeButton);
        list.appendChild(row);

        return input;
    }

    function initSystemReportChart() {
        var root = document.querySelector("[data-system-report]");
        if (!root) {
            return;
        }

        if (typeof Chart === "undefined") {
            window.setTimeout(function () {
                if (typeof Chart === "undefined") {
                    warnReport("Chart.js is not available.");
                    showUnavailableCharts(root);
                    return;
                }

                initSystemReportChart();
            }, 150);
            return;
        }

        renderCategoryChart({
            canvasId: "usersByTypeChart",
            jsonId: "users-by-type-data",
            type: "doughnut",
            label: "Users",
            keys: ["SERVICE_PROVIDER", "RESPONDENT", "ADMIN"],
            labels: ["Service providers", "Respondents", "Admins"],
            colors: [ssToken("--ss-chart-1"), ssToken("--ss-chart-2"), ssToken("--ss-chart-3")],
            emptyMessage: "No user data is available.",
        });

        renderCategoryChart({
            canvasId: "surveysByStatusChart",
            jsonId: "surveys-by-status-data",
            type: "bar",
            label: "Surveys",
            keys: ["DRAFT", "PUBLISHED", "CLOSED"],
            labels: ["Draft", "Published", "Closed"],
            colors: [ssToken("--ss-chart-other"), ssToken("--ss-chart-1"), ssToken("--ss-chart-5")],
            emptyMessage: "No survey data is available.",
        });

        renderTimeSeriesChart(
            "responsesOverTimeChart",
            "responses-over-time-data",
            "Responses",
            ssToken("--ss-chart-1"),
            "No responses were submitted in the selected range."
        );
        renderTimeSeriesChart(
            "userGrowthChart",
            "user-growth-data",
            "New users",
            ssToken("--ss-chart-3"),
            "No new users were created in the selected range."
        );
        renderMostActiveSurveysChart();
    }

    function renderCategoryChart(config) {
        var canvas = document.getElementById(config.canvasId);
        if (!canvas) {
            warnReport("Missing canvas #" + config.canvasId + ".");
            return;
        }

        var source = readJsonScript(config.jsonId, {});
        var values = config.keys.map(function (key) {
            return readNumber(source[key]);
        });

        if (!hasPositiveValue(values)) {
            replaceCanvasWithEmpty(canvas, config.emptyMessage);
            return;
        }

        var options = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: config.type === "doughnut" ? "bottom" : "top",
                },
            },
        };

        if (config.type !== "doughnut") {
            options.scales = verticalCountScales();
            options.plugins.legend.display = false;
        }

        new Chart(canvas.getContext("2d"), {
            type: config.type,
            data: {
                labels: config.labels,
                datasets: [
                    {
                        label: config.label,
                        data: values,
                        backgroundColor: config.colors,
                        borderColor: config.colors,
                        borderWidth: 1,
                        borderRadius: config.type === "bar" ? 8 : 0,
                    },
                ],
            },
            options: options,
        });
    }

    function renderTimeSeriesChart(canvasId, jsonId, label, color, emptyMessage) {
        var canvas = document.getElementById(canvasId);
        if (!canvas) {
            warnReport("Missing canvas #" + canvasId + ".");
            return;
        }

        var rows = readJsonScript(jsonId, []);
        if (!Array.isArray(rows) || rows.length === 0) {
            replaceCanvasWithEmpty(canvas, emptyMessage);
            return;
        }

        var values = rows.map(function (row) {
            return readNumber(row.count);
        });
        if (!hasPositiveValue(values)) {
            replaceCanvasWithEmpty(canvas, emptyMessage);
            return;
        }

        new Chart(canvas.getContext("2d"), {
            type: "line",
            data: {
                labels: rows.map(function (row) {
                    return row.date;
                }),
                datasets: [
                    {
                        label: label,
                        data: values,
                        borderColor: color,
                        backgroundColor: withAlpha(color, 0.14),
                        borderWidth: 2,
                        fill: true,
                        tension: 0.3,
                        pointRadius: 3,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: verticalCountScales(),
                plugins: {
                    legend: {
                        display: false,
                    },
                },
            },
        });
    }

    function renderMostActiveSurveysChart() {
        var canvas = document.getElementById("mostActiveSurveysChart");
        if (!canvas) {
            warnReport("Missing canvas #mostActiveSurveysChart.");
            return;
        }

        var rows = readJsonScript("most-active-surveys-data", []);
        if (!Array.isArray(rows) || rows.length === 0) {
            replaceCanvasWithEmpty(
                canvas,
                "No survey activity is available for the selected range."
            );
            return;
        }

        var values = rows.map(function (row) {
            return readNumber(row.response_count);
        });
        if (!hasPositiveValue(values)) {
            replaceCanvasWithEmpty(
                canvas,
                "No survey activity is available for the selected range."
            );
            return;
        }

        new Chart(canvas.getContext("2d"), {
            type: "bar",
            data: {
                labels: rows.map(function (row) {
                    return row.title || "Survey " + row.survey_id;
                }),
                datasets: [
                    {
                        label: "Responses",
                        data: values,
                        backgroundColor: ssToken("--ss-chart-1"),
                        borderColor: ssToken("--ss-brand-deep"),
                        borderWidth: 1,
                        borderRadius: 8,
                    },
                ],
            },
            options: {
                indexAxis: "y",
                responsive: true,
                maintainAspectRatio: false,
                scales: horizontalCountScales(),
                plugins: {
                    legend: {
                        display: false,
                    },
                },
            },
        });
    }

    function readJsonScript(id, fallback) {
        var script = document.getElementById(id);
        if (!script) {
            warnReport("Missing data script #" + id + ".");
            return fallback;
        }

        try {
            return JSON.parse(script.textContent || "null") || fallback;
        } catch (error) {
            warnReport("Invalid JSON in #" + id + ".");
            return fallback;
        }
    }

    function showUnavailableCharts(root) {
        root.querySelectorAll(".report-chart-wrap").forEach(function (panel) {
            panel.innerHTML = emptyStateMarkup("Charts are unavailable right now.");
        });
    }

    function replaceCanvasWithEmpty(canvas, message) {
        var panel = canvas.closest(".report-chart-wrap");
        if (!panel) {
            return;
        }

        panel.innerHTML = emptyStateMarkup(message);
    }

    function emptyStateMarkup(message) {
        return (
            '<div class="empty-state report-empty-state">' +
            escapeHtml(message) +
            "</div>"
        );
    }

    function warnReport(message) {
        if (window.console && typeof window.console.warn === "function") {
            window.console.warn("System reports: " + message);
        }
    }

    function escapeHtml(value) {
        return String(value)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function verticalCountScales() {
        return {
            y: {
                beginAtZero: true,
                ticks: {
                    precision: 0,
                },
            },
            x: {
                grid: {
                    display: false,
                },
            },
        };
    }

    function horizontalCountScales() {
        return {
            x: {
                beginAtZero: true,
                ticks: {
                    precision: 0,
                },
            },
            y: {
                grid: {
                    display: false,
                },
            },
        };
    }

    function hasPositiveValue(values) {
        return values.some(function (value) {
            return value > 0;
        });
    }

    /* Read a design token from tokens.css; the only place colours are defined. */
    function ssToken(name) {
        return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    }

    /* Add an alpha channel to a 6-digit hex token value, returned as 8-digit hex. */
    function withAlpha(hex, alpha) {
        var channel = Math.round(alpha * 255).toString(16).padStart(2, "0");
        return hex + channel;
    }

    function readNumber(value) {
        var number = Number.parseInt(value || "0", 10);
        return Number.isFinite(number) ? number : 0;
    }
})();
