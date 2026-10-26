document.addEventListener("DOMContentLoaded", function () {


    /* =====================================================
       WORKSPACE TABS
       ===================================================== */

    const navItems =
        document.querySelectorAll(
            ".workspace-nav-item"
        );

    const tabContents =
        document.querySelectorAll(
            ".workspace-tab-content"
        );

    function switchWorkspaceTab(targetId) {
        if (!targetId) {
            console.warn("[OmniCare AI] Tab switch requested with empty target ID.");
            return false;
        }

        const targetPanel =
            document.getElementById(
                targetId
            );

        if (!targetPanel) {
            console.warn(
                "[OmniCare AI] Target tab panel not found for ID:",
                targetId
            );
            return false;
        }

        let foundNav = false;

        navItems.forEach(function (nav) {
            if (nav.getAttribute("data-tab") === targetId) {
                nav.classList.add("active");
                foundNav = true;
            } else {
                nav.classList.remove("active");
            }
        });

        tabContents.forEach(function (tab) {
            tab.classList.remove("active");
        });

        targetPanel.classList.add("active");

        if (targetId === "trend-analysis-tab") {
            if (typeof window.onTrendTabActivated === "function") {
                window.onTrendTabActivated();
            }
        }

        if (!foundNav) {
            console.warn(
                "[OmniCare AI] No navigation button matches data-tab:",
                targetId
            );
        }

        return true;
    }

    navItems.forEach(function (item) {
        item.addEventListener("click", function () {
            const targetId =
                item.getAttribute("data-tab");
            switchWorkspaceTab(targetId);
        });
    });

    // Initialize the active tab on page load
    const activeNav =
        document.querySelector(".workspace-nav-item.active") ||
        navItems[0];

    if (activeNav) {
        const initialTabId =
            activeNav.getAttribute("data-tab");
        switchWorkspaceTab(initialTabId);
    }
/* =====================================================
       TIMELINE FILTERS
       ===================================================== */

    const filterButtons =
        document.querySelectorAll(
            ".timeline-filter"
        );

    const timelineEvents =
        document.querySelectorAll(
            ".timeline-event"
        );


    filterButtons.forEach(
        function (button) {

            button.addEventListener(
                "click",
                function () {

                    const selectedFilter =
                        button.getAttribute(
                            "data-filter"
                        );


                    filterButtons.forEach(
                        function (btn) {

                            btn.classList.remove(
                                "active"
                            );

                        }
                    );


                    button.classList.add(
                        "active"
                    );


                    timelineEvents.forEach(
                        function (event) {

                            const eventType =
                                event.getAttribute(
                                    "data-event-type"
                                );


                            if (
                                selectedFilter === "all" ||
                                selectedFilter === eventType
                            ) {

                                event.classList.remove(
                                    "hidden-event"
                                );

                            } else {

                                event.classList.add(
                                    "hidden-event"
                                );

                            }

                        }
                    );

                }
            );

        }
    );



    /* =====================================================
       DOCTOR AI HEALTH ASSISTANT
       ===================================================== */

    const doctorAIQuestion =
        document.getElementById(
            "doctor-ai-question"
        );


    const doctorAISend =
        document.getElementById(
            "doctor-ai-send"
        );


    const doctorAIChat =
        document.getElementById(
            "doctor-ai-chat"
        );


    const doctorAILoading =
        document.getElementById(
            "doctor-ai-loading"
        );


    const quickQuestions =
        document.querySelectorAll(
            ".quick-question"
        );



    /* =====================================================
       PATIENT ID
       ===================================================== */

    const guestPatientId = window.GUEST_PATIENT_ID || "";
    const doctorAIPatientId = guestPatientId;



    /* =====================================================
       ESCAPE HTML
       ===================================================== */

    function escapeDoctorAIHTML(text) {

        const div =
            document.createElement(
                "div"
            );

        div.textContent =
            text;

        return div.innerHTML;

    }



    /* =====================================================
       FORMAT AI ANSWER
       ===================================================== */

function formatDoctorAIAnswer(text) {
    if (!text) return "";

    let safeText = escapeDoctorAIHTML(text);
    safeText = safeText.replace(/\r\n?/g, "\n");

    // Remove standalone Markdown separators and stray asterisks
    safeText = safeText.replace(/^\s*(?:\*{1,3}|_{3,}|-{3,})\s*$/gm, "");

    // Format headings and bold text
    safeText = safeText.replace(/^#{1,3}\s+(.+)$/gm, "<h4>$1</h4>");
    safeText = safeText.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");

    const lines = safeText.split("\n");
    const output = [];
    let listItems = [];

    function flushList() {
        if (listItems.length) {
            output.push(
                '<ul class="doctor-ai-list">' +
                listItems.map(item => `<li>${item}</li>`).join("") +
                "</ul>"
            );
            listItems = [];
        }
    }

    for (const rawLine of lines) {
        const line = rawLine.trim();

        if (!line) {
            flushList();
            continue;
        }

        // Handle bullet points, including a single stray asterisk
        const bulletMatch = line.match(/^[*+-]\s+(.+)$/);

        if (bulletMatch) {
            listItems.push(bulletMatch[1]);
        } else {
            flushList();
            output.push(`<p>${line}</p>`);
        }
    }

    flushList();
    return output.join("");
}


    /* =====================================================
       ADD DOCTOR MESSAGE
       ===================================================== */

    function addDoctorUserMessage(
        question
    ) {

        if (!doctorAIChat) {
            return;
        }


        const message =
            document.createElement(
                "div"
            );


        message.className =
            "doctor-user-message";


        message.innerHTML = `

            <div class="doctor-user-message-content">

                <strong>
                    You
                </strong>

                <p>
                    ${escapeDoctorAIHTML(question)}
                </p>

            </div>

            <div class="doctor-user-message-icon">
                👨‍⚕️
            </div>

        `;


        doctorAIChat.appendChild(
            message
        );


        doctorAIChat.scrollTop =
            doctorAIChat.scrollHeight;

    }



    /* =====================================================
       ADD AI MESSAGE
       ===================================================== */

    function addDoctorAIMessage(
        answer
    ) {

        if (!doctorAIChat) {
            return;
        }


        const message =
            document.createElement(
                "div"
            );


        message.className =
            "ai-message";


        message.innerHTML = `

            <div class="ai-message-icon">
                🤖
            </div>

            <div class="ai-message-content">

                <strong>
                    OmniCare AI
                </strong>

                <p>
                    ${formatDoctorAIAnswer(answer)}
                </p>

            </div>

        `;


        doctorAIChat.appendChild(
            message
        );


        doctorAIChat.scrollTop =
            doctorAIChat.scrollHeight;

    }


/* =====================================================
   ADD AI SOURCE RECORDS
   ===================================================== */

function addDoctorAISources(
    sources
) {

    if (
        !doctorAIChat ||
        !sources ||
        !sources.length
    ) {
        return;
    }


    const sourceContainer =
        document.createElement(
            "div"
        );


    sourceContainer.className =
        "doctor-ai-sources";


    let sourceHTML = `

        <div class="doctor-ai-sources-header">

            <strong>
                📚 Source Records
            </strong>

            <span>
                Verify the AI response against the original medical record.
            </span>

        </div>


        <div class="doctor-ai-source-list">

    `;


    sources.forEach(
        function (source) {

            sourceHTML += `

                <div class="doctor-ai-source-card">

                    <div class="doctor-ai-source-info">


                        <div class="doctor-ai-source-title">

                            📄

                            ${escapeDoctorAIHTML(
                                source.event_type ||
                                "Medical Record"
                            )}

                        </div>


                        ${
                            source.event_date
                            ? `

                                <div class="doctor-ai-source-detail">

                                    📅

                                    ${escapeDoctorAIHTML(
                                        source.event_date
                                    )}

                                </div>

                              `
                            : ""
                        }


                        ${
                            source.hospital_name
                            ? `

                                <div class="doctor-ai-source-detail">

                                    🏥

                                    ${escapeDoctorAIHTML(
                                        source.hospital_name
                                    )}

                                </div>

                              `
                            : ""
                        }


                        ${
                            source.provider_name
                            ? `

                                <div class="doctor-ai-source-detail">

                                    👨‍⚕️

                                    ${escapeDoctorAIHTML(
                                        source.provider_name
                                    )}

                                </div>

                              `
                            : ""
                        }


                    </div>


                    ${
                        source.view_url
                        ? `

                            <a
                                href="${source.view_url}"
                                target="_blank"
                                rel="noopener noreferrer"
                                class="doctor-ai-source-button"
                            >

                                📄 View Original

                            </a>

                          `
                        : ""
                    }


                </div>

            `;

        }
    );


    sourceHTML += `

        </div>

    `;


    sourceContainer.innerHTML =
        sourceHTML;


    doctorAIChat.appendChild(
        sourceContainer
    );


    doctorAIChat.scrollTop =
        doctorAIChat.scrollHeight;

}
    /* =====================================================
       ASK DOCTOR AI
       ===================================================== */

 /* =====================================================
   ASK DOCTOR AI
   ===================================================== */

async function askDoctorAI(
    question
) {

    question =
        question.trim();


    if (!question) {

        return;

    }


    /* -------------------------------------------------
       CHECK REQUIRED ELEMENTS
       ------------------------------------------------- */

    if (
        !doctorAIQuestion ||
        !doctorAISend ||
        !doctorAIChat
    ) {

        console.error(
            "Doctor AI elements not found."
        );

        return;

    }


    /* -------------------------------------------------
       SHOW DOCTOR QUESTION
       ------------------------------------------------- */

    addDoctorUserMessage(
        question
    );


    /* -------------------------------------------------
       CLEAR INPUT
       ------------------------------------------------- */

    doctorAIQuestion.value =
        "";


    /* -------------------------------------------------
       DISABLE INPUT
       ------------------------------------------------- */

    doctorAISend.disabled =
        true;

    doctorAIQuestion.disabled =
        true;


    /* -------------------------------------------------
       SHOW LOADING
       ------------------------------------------------- */

    if (doctorAILoading) {

        doctorAILoading.style.display =
            "flex";

    }


    try {

        /* ---------------------------------------------
           DEBUG
           --------------------------------------------- */

        console.log(
            "================================"
        );

        console.log(
            "OMNICARE AI REQUEST"
        );

        console.log(
            "Patient ID:",
            doctorAIPatientId
        );

        console.log(
            "Question:",
            question
        );

        console.log(
            "================================"
        );


        /* ---------------------------------------------
           SEND AI REQUEST TO FLASK
           --------------------------------------------- */

        const response =
            await fetch(
                `/doctor/guest-patient/${guestPatientId}/ai-assistant`,
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({
                        question:
                            question
                    })
                }
            );


        console.log(
            "AI HTTP Status:",
            response.status
        );


        /* ---------------------------------------------
           READ AI RESPONSE
           --------------------------------------------- */

        const data =
            await response.json();


        console.log(
            "AI Server Response:",
            data
        );


        /* ---------------------------------------------
           CHECK AI RESPONSE
           --------------------------------------------- */

        if (
            !response.ok ||
            !data.success
        ) {

            throw new Error(
                data.message ||
                "Unable to get AI response."
            );

        }


        /* ---------------------------------------------
           SHOW AI ANSWER
           --------------------------------------------- */

        addDoctorAIMessage(
            data.answer
        );


        /* =================================================
           LOAD SOURCE RECORDS
           ================================================= */

        console.log(
            "================================"
        );

        console.log(
            "LOADING AI SOURCE RECORDS"
        );

        console.log(
            "Patient ID:",
            doctorAIPatientId
        );

        console.log(
            "================================"
        );


        try {

            /* -----------------------------------------
               SOURCE API URL
               ----------------------------------------- */

            const sourceURL =
                `/doctor/guest-patient/${guestPatientId}/ai-sources`;


            console.log(
                "Source URL:",
                sourceURL
            );


            /* -----------------------------------------
               REQUEST SOURCE RECORDS
               ----------------------------------------- */

            const sourceResponse =
                await fetch(
                    sourceURL,
                    {
                        method: "GET",

                        headers: {
                            "Accept":
                                "application/json"
                        }
                    }
                );


            console.log(
                "Source HTTP Status:",
                sourceResponse.status
            );


            /* -----------------------------------------
               READ SOURCE RESPONSE
               ----------------------------------------- */

            const sourceData =
                await sourceResponse.json();


            console.log(
                "AI SOURCE RESPONSE:",
                sourceData
            );


            /* -----------------------------------------
               CHECK SOURCE RESPONSE
               ----------------------------------------- */

            if (
                !sourceResponse.ok
            ) {

                console.error(
                    "Source request failed."
                );

                console.error(
                    "HTTP Status:",
                    sourceResponse.status
                );

                console.error(
                    "Server Response:",
                    sourceData
                );

                return;

            }


            if (
                !sourceData.success
            ) {

                console.error(
                    "Source endpoint returned an error."
                );

                console.error(
                    "Message:",
                    sourceData.message
                );

                return;

            }


            /* -----------------------------------------
               CHECK SOURCE ARRAY
               ----------------------------------------- */

            const sources =
                sourceData.sources || [];


            console.log(
                "Number of source records:",
                sources.length
            );


            /* -----------------------------------------
               DISPLAY SOURCE RECORDS
               ----------------------------------------- */

            if (
                sources.length > 0
            ) {

                console.log(
                    "Displaying source records..."
                );

                addDoctorAISources(
                    sources
                );

            } else {

                console.warn(
                    "No source records were returned."
                );


                /* -------------------------------------
                   OPTIONAL EMPTY SOURCE MESSAGE
                   ------------------------------------- */

                if (doctorAIChat) {

                    const emptySource =
                        document.createElement(
                            "div"
                        );


                    emptySource.className =
                        "doctor-ai-sources";


                    emptySource.innerHTML = `
                        <div class="doctor-ai-sources-header">
                            <strong>
                                📚 Source Records
                            </strong>

                            <span>
                                No linked source records were found for this patient.
                            </span>
                        </div>
                    `;


                    doctorAIChat.appendChild(
                        emptySource
                    );


                    doctorAIChat.scrollTop =
                        doctorAIChat.scrollHeight;

                }

            }


        } catch (sourceError) {

            console.error(
                "================================"
            );

            console.error(
                "AI SOURCE FETCH ERROR"
            );

            console.error(
                sourceError
            );

            console.error(
                "================================"
            );


            /* -----------------------------------------
               DO NOT BREAK THE AI ANSWER
               ----------------------------------------- */

        }


    } catch (error) {

        /* ---------------------------------------------
           MAIN AI ERROR
           --------------------------------------------- */

        console.error(
            "================================"
        );

        console.error(
            "DOCTOR AI ERROR"
        );

        console.error(
            error
        );

        console.error(
            "================================"
        );


        addDoctorAIMessage(
            "I could not process your request right now. Please try again."
        );


    } finally {

        /* ---------------------------------------------
           HIDE LOADING
           --------------------------------------------- */

        if (doctorAILoading) {

            doctorAILoading.style.display =
                "none";

        }


        /* ---------------------------------------------
           ENABLE INPUT
           --------------------------------------------- */

        doctorAISend.disabled =
            false;

        doctorAIQuestion.disabled =
            false;


        doctorAIQuestion.focus();

    }

}
    /* =====================================================
       ASK AI BUTTON
       ===================================================== */

    if (doctorAISend) {

        doctorAISend.addEventListener(
            "click",
            function () {

                askDoctorAI(
                    doctorAIQuestion.value
                );

            }
        );

    }



    /* =====================================================
       ENTER TO SEND
       SHIFT + ENTER = NEW LINE
       ===================================================== */

    if (doctorAIQuestion) {

        doctorAIQuestion.addEventListener(
            "keydown",
            function (event) {

                if (
                    event.key === "Enter" &&
                    !event.shiftKey
                ) {

                    event.preventDefault();


                    askDoctorAI(
                        doctorAIQuestion.value
                    );

                }

            }
        );

    }



    /* =====================================================
       QUICK QUESTIONS
       ===================================================== */

    quickQuestions.forEach(
        function (button) {

            button.addEventListener(
                "click",
                function () {

                    const question =
                        button.getAttribute(
                            "data-question"
                        );


                    if (!question) {
                        return;
                    }


                    if (doctorAIQuestion) {

                        doctorAIQuestion.value =
                            question;

                    }


                    askDoctorAI(
                        question
                    );

                }
            );

        }
    );


    /* =====================================================
       TREND ANALYSIS CONTROLLER
       ===================================================== */

    const patientId = guestPatientId;
    let initialTrendData = window.INITIAL_TREND_DATA || {};
    let currentTrendData = initialTrendData;
    let chartInstances = {};

    // DOM Elements
    const trendDropdownToggle = document.getElementById("trend-dropdown-toggle");
    const trendDropdownMenu = document.getElementById("trend-dropdown-menu");
    const trendSelectedBadge = document.getElementById("trend-selected-badge");
    const trendSelectedLabelText = document.getElementById("trend-dropdown-label-text");
    const trendCheckboxes = document.querySelectorAll(".trend-param-checkbox");
    const trendPeriodBtns = document.querySelectorAll(".trend-period-btn");
    const trendApplyBtn = document.getElementById("trend-apply-filters-btn");
    const trendResetBtn = document.getElementById("trend-reset-filters-btn");
    const trendSelectTrendsBtn = document.getElementById("trend-select-trends-btn");
    const trendSelectAllBtn = document.getElementById("trend-select-all-btn");
    const trendClearAllBtn = document.getElementById("trend-clear-all-btn");

    const trendChartsGrid = document.getElementById("trend-charts-grid");
    const trendSummaryGrid = document.getElementById("trend-summary-grid");
    const trendAIList = document.getElementById("trend-ai-list");
    const trendTableBody = document.getElementById("trend-table-body");

    // 1. Dropdown Toggle & Outside Click
    if (trendDropdownToggle && trendDropdownMenu) {
        trendDropdownToggle.addEventListener("click", function (e) {
            e.stopPropagation();
            const isOpen = trendDropdownMenu.classList.contains("show");
            if (isOpen) {
                trendDropdownMenu.classList.remove("show");
                trendDropdownToggle.setAttribute("aria-expanded", "false");
            } else {
                trendDropdownMenu.classList.add("show");
                trendDropdownToggle.setAttribute("aria-expanded", "true");
            }
        });

        document.addEventListener("click", function (e) {
            if (!trendDropdownMenu.contains(e.target) && !trendDropdownToggle.contains(e.target)) {
                trendDropdownMenu.classList.remove("show");
                trendDropdownToggle.setAttribute("aria-expanded", "false");
            }
        });
    }

    // 2. Update Selected Count in Dropdown
    function updateDropdownSelectionCount() {
        const checked = document.querySelectorAll(".trend-param-checkbox:checked");
        const count = checked.length;
        if (trendSelectedBadge) {
            trendSelectedBadge.textContent = count;
        }
        if (trendSelectedLabelText) {
            trendSelectedLabelText.textContent = count > 0 ? `${count} Selected` : "Select Parameters";
        }
    }

    trendCheckboxes.forEach(function (cb) {
        cb.addEventListener("change", updateDropdownSelectionCount);
    });

    // 3. Quick Action Buttons
    if (trendSelectTrendsBtn) {
        trendSelectTrendsBtn.addEventListener("click", function (e) {
            e.preventDefault();
            const options = document.querySelectorAll(".trend-checkbox-option");
            options.forEach(function (opt) {
                const cb = opt.querySelector(".trend-param-checkbox");
                if (cb) {
                    cb.checked = opt.getAttribute("data-sufficient") === "true";
                }
            });
            updateDropdownSelectionCount();
        });
    }

    if (trendSelectAllBtn) {
        trendSelectAllBtn.addEventListener("click", function (e) {
            e.preventDefault();
            trendCheckboxes.forEach(function (cb) { cb.checked = true; });
            updateDropdownSelectionCount();
        });
    }

    if (trendClearAllBtn) {
        trendClearAllBtn.addEventListener("click", function (e) {
            e.preventDefault();
            trendCheckboxes.forEach(function (cb) { cb.checked = false; });
            updateDropdownSelectionCount();
        });
    }

    // 4. Period Buttons
    trendPeriodBtns.forEach(function (btn) {
        btn.addEventListener("click", function () {
            trendPeriodBtns.forEach(function (b) { b.classList.remove("active"); });
            btn.classList.add("active");
        });
    });

    function getSelectedPeriod() {
        const activeBtn = document.querySelector(".trend-period-btn.active");
        return activeBtn ? activeBtn.getAttribute("data-period") : "all";
    }

    function getSelectedParameterKeys() {
        const checked = document.querySelectorAll(".trend-param-checkbox:checked");
        return Array.from(checked).map(function (cb) { return cb.value; });
    }

    // 5. Chart.js Line Chart Rendering
    function destroyAllCharts() {
        Object.keys(chartInstances).forEach(function (key) {
            if (chartInstances[key]) {
                try {
                    chartInstances[key].destroy();
                } catch (e) {
                    console.warn("Chart destroy error:", e);
                }
            }
        });
        chartInstances = {};
    }

    function renderTrendCharts(chartsData) {
        if (!chartsData || typeof Chart === "undefined") {
            return;
        }

        Object.keys(chartsData).forEach(function (key) {
            const chartData = chartsData[key];
            if (!chartData || !chartData.has_sufficient_data) {
                return;
            }

            const canvas = document.getElementById("canvas-" + key);
            if (!canvas) {
                return;
            }

            // Destroy previous instance if any
            if (chartInstances[key]) {
                try {
                    chartInstances[key].destroy();
                } catch (e) {}
            }

            const ctx = canvas.getContext("2d");
            const isDual = chartData.datasets && chartData.datasets.length > 1;

            chartInstances[key] = new Chart(ctx, {
                type: "line",
                data: {
                    labels: chartData.labels,
                    datasets: chartData.datasets
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: {
                        mode: "index",
                        intersect: false
                    },
                    plugins: {
                        legend: {
                            display: isDual,
                            position: "top",
                            labels: {
                                boxWidth: 12,
                                font: {
                                    weight: "bold",
                                    size: 11
                                }
                            }
                        },
                        tooltip: {
                            backgroundColor: "rgba(18, 63, 99, 0.95)",
                            titleFont: { size: 12, weight: "bold" },
                            bodyFont: { size: 12 },
                            padding: 10,
                            cornerRadius: 8,
                            callbacks: {
                                label: function (context) {
                                    const ds = context.dataset;
                                    const val = context.parsed.y;
                                    const unit = chartData.unit || "";
                                    return " " + (ds.label || "") + ": " + val + " " + unit;
                                },
                                afterLabel: function (context) {
                                    const idx = context.dataIndex;
                                    const meta = chartData.meta && chartData.meta[idx];
                                    if (meta) {
                                        let lines = [];
                                        if (meta.danger_label) {
                                            lines.push("Status: [" + meta.danger_label + "]");
                                        }
                                        if (meta.danger_reason) {
                                            lines.push("Note: " + meta.danger_reason);
                                        }
                                        return lines;
                                    }
                                    return "";
                                }
                            }
                        }
                    },
                    scales: {
                        x: {
                            grid: {
                                color: "#f1f5f9"
                            },
                            ticks: {
                                font: {
                                    size: 11,
                                    weight: "600"
                                },
                                color: "#64748b"
                            }
                        },
                        y: {
                            grid: {
                                color: "#e2e8f0"
                            },
                            ticks: {
                                font: {
                                    size: 11,
                                    weight: "600"
                                },
                                color: "#64748b"
                            },
                            title: {
                                display: true,
                                text: chartData.unit,
                                color: "#64748b",
                                font: { size: 11, weight: "bold" }
                            }
                        }
                    }
                }
            });
        });
    }

    // 6. Tab Activation Hook
    window.onTrendTabActivated = function () {
        setTimeout(function () {
            if (currentTrendData && currentTrendData.charts) {
                renderTrendCharts(currentTrendData.charts);
            }
        }, 80);
    };

    // Initial render if trend tab is active
    const currentActiveNav = document.querySelector(".workspace-nav-item.active");
    if (currentActiveNav && currentActiveNav.getAttribute("data-tab") === "trend-analysis-tab") {
        window.onTrendTabActivated();
    }

    // 7. Dynamic DOM Rendering Helpers
    function renderSummariesHTML(summaries) {
        if (!trendSummaryGrid) return;
        if (!summaries || summaries.length === 0) {
            trendSummaryGrid.innerHTML = `
                <div class="trend-empty-state" style="grid-column: 1 / -1;">
                    <div class="trend-empty-icon">📂</div>
                    <h3>No Parameter Summaries</h3>
                    <p>No measurements match the currently selected parameters or date range.</p>
                </div>
            `;
            return;
        }

        let html = "";
        summaries.forEach(function (s) {
            const arrow = s.change_direction === "up" ? "↗" : (s.change_direction === "down" ? "↘" : "→");
            const changeHtml = s.has_sufficient_data && s.change_text ?
                '<span class="trend-change-badge ' + s.change_direction + '">' + arrow + ' ' + escapeHtml(s.change_text) + (s.pct_change ? ' (' + escapeHtml(s.pct_change) + ')' : '') + '</span>' :
                '<span style="color: #94a3b8; font-weight: 600;">Single reading</span>';

            html += `
                <div class="trend-summary-card">
                    <div class="trend-summary-top">
                        <div>
                            <h4 class="trend-summary-name">${escapeHtml(s.param_name)}</h4>
                            <span class="trend-summary-category">${escapeHtml(s.category)}</span>
                        </div>
                        <span class="trend-status-badge ${escapeHtml(s.danger_level)}">
                            ${escapeHtml(s.danger_label)}
                        </span>
                    </div>
                    <div class="trend-summary-value-area">
                        <span class="trend-summary-number">${s.latest_value}</span>
                        <span class="trend-summary-unit">${escapeHtml(s.unit)}</span>
                    </div>
                    <div class="trend-summary-bottom">
                        <div>${changeHtml}</div>
                        <span class="trend-summary-date">${escapeHtml(s.latest_date_formatted)}</span>
                    </div>
                </div>
            `;
        });
        trendSummaryGrid.innerHTML = html;
    }

    function renderChartsHTML(charts) {
        if (!trendChartsGrid) return;
        destroyAllCharts();

        const keys = Object.keys(charts || {});
        if (keys.length === 0) {
            trendChartsGrid.innerHTML = `
                <div class="trend-empty-state" style="grid-column: 1 / -1;">
                    <div class="trend-empty-icon">📈</div>
                    <h3>No Trend Charts Available</h3>
                    <p>Select at least one health parameter above to display its trend chart.</p>
                </div>
            `;
            return;
        }

        let html = "";
        keys.forEach(function (key) {
            const chart = charts[key];
            if (chart.has_sufficient_data) {
                const dangerBadge = chart.latest_danger_level ?
                    '<span class="trend-status-badge ' + escapeHtml(chart.latest_danger_level) + '">' + escapeHtml(chart.latest_danger_label) + ': ' + chart.latest_value + ' ' + escapeHtml(chart.unit) + '</span>' : "";

                html += `
                    <div class="trend-chart-card" data-card-key="${key}">
                        <div class="trend-chart-header">
                            <div>
                                <h4 class="trend-chart-title">${escapeHtml(chart.param_name)}</h4>
                                <p class="trend-chart-ref-range">Reference: ${escapeHtml(chart.reference_range)}</p>
                            </div>
                            ${dangerBadge}
                        </div>
                        <div class="trend-chart-canvas-wrapper">
                            <canvas id="canvas-${key}" data-key="${key}"></canvas>
                        </div>
                        <div class="trend-chart-footer">
                            <div class="trend-chart-clinical-note">
                                <span>ℹ️</span>
                                <span>${escapeHtml(chart.latest_danger_reason || "Plotted from authorized records.")}</span>
                            </div>
                        </div>
                    </div>
                `;
            } else {
                const singleMeta = chart.meta && chart.meta[0];
                const recordLink = singleMeta && singleMeta.record_id ?
                    '<a href="/doctor/guest-record/' + singleMeta.record_id + '/view" target="_blank" rel="noopener noreferrer" class="trend-chart-source-link">📄 View Source Report</a>' : "";

                html += `
                    <div class="trend-chart-card" data-card-key="${key}">
                        <div class="trend-chart-header">
                            <div>
                                <h4 class="trend-chart-title">${escapeHtml(chart.param_name)}</h4>
                                <p class="trend-chart-ref-range">Reference: ${escapeHtml(chart.reference_range)}</p>
                            </div>
                            <span class="trend-status-badge gray">Single Observation</span>
                        </div>
                        <div class="trend-single-measurement-box">
                            <div class="trend-single-value">
                                ${chart.latest_value !== undefined ? chart.latest_value : (singleMeta ? singleMeta.value : "N/A")}
                                <span style="font-size: 16px; color: #64748b;">${escapeHtml(chart.unit)}</span>
                            </div>
                            <div class="trend-single-meta">
                                Recorded on ${chart.labels && chart.labels[0] ? escapeHtml(chart.labels[0]) : "N/A"}
                                ${singleMeta && singleMeta.danger_label ? ' &bull; <strong style="color: #123f63;">' + escapeHtml(singleMeta.danger_label) + '</strong>' : ""}
                            </div>
                            <div class="trend-insufficient-banner">
                                <span>⚠️</span>
                                <span>Insufficient historical data for trend analysis. At least two chronological measurements are required to establish a trajectory.</span>
                            </div>
                        </div>
                        <div class="trend-chart-footer">
                            <div class="trend-chart-clinical-note">
                                <span>ℹ️</span>
                                <span>${escapeHtml(singleMeta && singleMeta.danger_reason ? singleMeta.danger_reason : "Awaiting follow-up laboratory measurements.")}</span>
                            </div>
                            ${recordLink}
                        </div>
                    </div>
                `;
            }
        });

        trendChartsGrid.innerHTML = html;
        setTimeout(function () {
            renderTrendCharts(charts);
        }, 50);
    }

    function renderAIObservationsHTML(ai_observations) {
        if (!trendAIList) return;
        if (!ai_observations || ai_observations.length === 0) {
            trendAIList.innerHTML = `<div style="padding: 14px; color: #64748b; font-size: 13px;">No observations available for the active selection.</div>`;
            return;
        }

        let html = "";
        ai_observations.forEach(function (obs) {
            const icon = obs.type === "alert" ? "⚠️" : (obs.type === "warning" ? "🔶" : (obs.type === "positive" ? "🟢" : "ℹ️"));
            html += `
                <div class="trend-ai-item ${escapeHtml(obs.type)}">
                    <div class="trend-ai-icon">${icon}</div>
                    <div class="trend-ai-content">
                        <h4>${escapeHtml(obs.title)}</h4>
                        <p>${escapeHtml(obs.text)}</p>
                    </div>
                </div>
            `;
        });
        trendAIList.innerHTML = html;
    }

    function renderHistoricalTableHTML(rows) {
        if (!trendTableBody) return;
        if (!rows || rows.length === 0) {
            trendTableBody.innerHTML = `
                <tr>
                    <td colspan="7" style="text-align: center; padding: 28px; color: #64748b;">
                        No historical measurements match the active parameters and date filter.
                    </td>
                </tr>
            `;
            return;
        }

        let html = "";
        rows.forEach(function (row) {
            const actionLink = row.record_id ?
                '<a href="/doctor/guest-record/' + row.record_id + '/view" target="_blank" rel="noopener noreferrer" class="trend-table-action-btn">📄 View Original</a>' :
                '<span style="color: #94a3b8; font-size: 11px;">Unavailable</span>';

            html += `
                <tr>
                    <td class="trend-table-date">${escapeHtml(row.formatted_date)}</td>
                    <td class="trend-table-param">${escapeHtml(row.param_name)}</td>
                    <td class="trend-table-value">${row.value} <span style="font-size: 11px; color: #64748b; font-weight: 600;">${escapeHtml(row.unit)}</span></td>
                    <td style="color: #475569; font-size: 12px;">${escapeHtml(row.reference_range)}</td>
                    <td>
                        <span class="trend-status-badge ${escapeHtml(row.danger_level)}">
                            ${escapeHtml(row.danger_label)}
                        </span>
                    </td>
                    <td class="trend-table-record" title="${escapeHtml(row.record_title)}">
                        <strong>${escapeHtml(row.record_title)}</strong>
                        <div style="font-size: 11px; color: #64748b;">${escapeHtml(row.record_type)}</div>
                    </td>
                    <td>${actionLink}</td>
                </tr>
            `;
        });
        trendTableBody.innerHTML = html;
    }

    function escapeHtml(text) {
        if (!text) return "";
        return String(text)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    // 8. Apply Filters Logic
    async function applyTrendFilters() {
        const selectedParams = getSelectedParameterKeys();
        const selectedPeriod = getSelectedPeriod();

        if (selectedParams.length === 0) {
            alert("Please select at least one health parameter to display.");
            return;
        }

        if (trendApplyBtn) {
            trendApplyBtn.disabled = true;
            trendApplyBtn.innerHTML = `<span>⏳</span><span>Updating...</span>`;
        }

        try {
            const response = await fetch(`/doctor/guest-patient/${guestPatientId}/trend-data`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    parameters: selectedParams,
                    time_period: selectedPeriod
                })
            });

            const result = await response.json();
            if (result.success && result.trend_data) {
                currentTrendData = result.trend_data;
                renderSummariesHTML(currentTrendData.summaries);
                renderChartsHTML(currentTrendData.charts);
                renderAIObservationsHTML(currentTrendData.ai_observations);
                renderHistoricalTableHTML(currentTrendData.historical_table);
            } else {
                alert(result.message || "Failed to update trend analysis data.");
            }
        } catch (error) {
            console.error("Trend data filter error:", error);
            alert("A network error occurred while updating health trends. Please try again.");
        } finally {
            if (trendApplyBtn) {
                trendApplyBtn.disabled = false;
                trendApplyBtn.innerHTML = `<span>⚡</span><span>Apply Filters</span>`;
            }
        }
    }

    if (trendApplyBtn) {
        trendApplyBtn.addEventListener("click", applyTrendFilters);
    }

    // 9. Reset Filters Logic
    function resetTrendFilters() {
        // Reset period to 'all'
        trendPeriodBtns.forEach(function (btn) {
            if (btn.getAttribute("data-period") === "all") {
                btn.classList.add("active");
            } else {
                btn.classList.remove("active");
            }
        });

        // Reset parameter checkboxes to defaults
        const defaultKeys = (initialTrendData && initialTrendData.default_selected_keys) || [];
        trendCheckboxes.forEach(function (cb) {
            cb.checked = defaultKeys.includes(cb.value);
        });

        updateDropdownSelectionCount();
        applyTrendFilters();
    }

    if (trendResetBtn) {
        trendResetBtn.addEventListener("click", resetTrendFilters);
    }


    /* =====================================================
       GUEST RECORD FILE PICKER ENHANCEMENT
       ===================================================== */
    const medicalFileInput = document.getElementById("upload-medical-file");
    const fileChosenText = document.getElementById("file-chosen-text");
    if (medicalFileInput && fileChosenText) {
        medicalFileInput.addEventListener("change", function () {
            if (this.files && this.files.length > 0) {
                const file = this.files[0];
                const sizeMB = (file.size / (1024 * 1024)).toFixed(2);
                fileChosenText.textContent = `${file.name} (${sizeMB} MB)`;
            } else {
                fileChosenText.textContent = "Choose PDF, PNG, JPG, or WEBP report";
            }
        });
    }

});
