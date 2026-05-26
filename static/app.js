// Lyceum Logic Analyzer - Frontend Application Script

document.addEventListener("DOMContentLoaded", () => {
    // DOM Elements
    const essayInput = document.getElementById("essay-input");
    const analyzeBtn = document.getElementById("analyze-btn");
    const loadSampleBtn = document.getElementById("load-sample-btn");
    const clearBtn = document.getElementById("clear-btn");
    const loadingState = document.getElementById("loading-state");
    const resultsSection = document.getElementById("results-section");
    const argumentsList = document.getElementById("arguments-list");
    const resultsCountBadge = document.getElementById("results-count-badge");
    
    // Overview Stats
    const statValid = document.getElementById("stat-valid");
    const statInvalid = document.getElementById("stat-invalid");
    const statWarnings = document.getElementById("stat-warnings");

    // Template
    const cardTemplate = document.getElementById("argument-card-template");

    // Sample Essay Content
    const SAMPLE_ESSAY = `Many scholars have debated the nature of mortality and truth. First of all, we know that all men are mortal, and we also know that Socrates is a man. Consequently, Socrates is mortal. This has been a foundational truth for centuries.

Furthermore, some politicians are corrupt, and since all politicians are public figures, it must be that some public figures are not corrupt.

Additionally, since all humans are mortal, and all Greeks are humans, some Greeks are mortal. 

However, others claim that all cats are animals and all dogs are animals, which proves that all cats are dogs. But this is clearly absurd.`;

    // Event Listeners
    loadSampleBtn.addEventListener("click", () => {
        essayInput.value = SAMPLE_ESSAY;
        essayInput.focus();
    });

    clearBtn.addEventListener("click", () => {
        essayInput.value = "";
        resultsSection.classList.add("hidden");
    });

    analyzeBtn.addEventListener("click", async () => {
        const text = essayInput.value.trim();
        if (!text) {
            alert("Please paste an essay or load a sample first.");
            return;
        }

        // Show loading state
        setLoading(true);
        resultsSection.classList.add("hidden");

        try {
            const response = await fetch("/api/analyze", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ text })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || "Failed to analyze essay.");
            }

            const data = await response.json();
            renderResults(data);
        } catch (error) {
            alert(`Error: ${error.message}`);
            console.error("Analysis failed:", error);
        } finally {
            setLoading(false);
        }
    });

    function setLoading(isLoading) {
        if (isLoading) {
            analyzeBtn.disabled = true;
            analyzeBtn.querySelector(".btn-text").classList.add("hidden");
            analyzeBtn.querySelector(".btn-loading-spinner").classList.remove("hidden");
            loadingState.classList.remove("hidden");
        } else {
            analyzeBtn.disabled = false;
            analyzeBtn.querySelector(".btn-text").classList.remove("hidden");
            analyzeBtn.querySelector(".btn-loading-spinner").classList.add("hidden");
            loadingState.classList.add("hidden");
        }
    }

    function renderResults(data) {
        // Clear previous arguments
        argumentsList.innerHTML = "";

        if (!data.success || !data.arguments || data.arguments.length === 0) {
            resultsCountBadge.textContent = "0 Arguments Extracted";
            statValid.textContent = "0";
            statInvalid.textContent = "0";
            statWarnings.textContent = "0";
            alert("No logical arguments could be identified in the text. Make sure your sentences make claims using logical indicators like 'therefore', 'so', or 'consequently'.");
            return;
        }

        const args = data.arguments;
        resultsCountBadge.textContent = `${args.length} Argument${args.length > 1 ? 's' : ''} Extracted`;

        let validCount = 0;
        let invalidCount = 0;
        let warningCount = 0;

        args.forEach((arg, index) => {
            // Count logic
            let status = "invalid";
            if (arg.is_valid) {
                // Check if there are warning-only violations
                const hasWarnings = arg.violations && arg.violations.some(v => v.is_warning);
                if (hasWarnings) {
                    status = "warning";
                    warningCount++;
                } else {
                    status = "valid";
                    validCount++;
                }
            } else {
                invalidCount++;
            }

            // Create Card from Template
            const cardInstance = cardTemplate.content.cloneNode(true);
            
            // Set indexes & titles
            cardInstance.querySelector(".arg-index").textContent = `Argument #${index + 1}`;
            cardInstance.querySelector(".excerpt-text").textContent = `"${arg.original_text}"`;
            
            // Set status badges
            const badge = cardInstance.querySelector(".status-badge");
            badge.setAttribute("data-status", status);
            
            const badgeIcon = badge.querySelector("i");
            const badgeText = badge.querySelector(".status-text");
            
            if (status === "valid") {
                badgeIcon.className = "fa-solid fa-circle-check";
                badgeText.textContent = "Valid";
            } else if (status === "warning") {
                badgeIcon.className = "fa-solid fa-circle-info";
                badgeText.textContent = "Valid (Caveat)";
            } else {
                badgeIcon.className = "fa-solid fa-triangle-exclamation";
                badgeText.textContent = "Fallacious";
            }

            // Map Premises & Conclusion in UI
            const premises = arg.reconstructed_syllogism.premises;
            const conclusion = arg.reconstructed_syllogism.conclusion;

            // Render Premise 1
            const p1Row = cardInstance.querySelector(".prop-row.premise-1");
            fillPropRow(p1Row, premises[0]);

            // Render Premise 2
            const p2Row = cardInstance.querySelector(".prop-row.premise-2");
            if (premises.length > 1) {
                fillPropRow(p2Row, premises[1]);
            } else {
                p2Row.classList.add("hidden");
            }

            // Render Conclusion
            const concRow = cardInstance.querySelector(".prop-row.conclusion-prop");
            fillPropRow(concRow, conclusion);

            // Draw Euler/Venn Diagram
            const diagramWrapper = cardInstance.querySelector(".svg-diagram-wrapper");
            const svgContent = drawEulerDiagram(arg.minor_term, arg.major_term, arg.middle_term, status);
            diagramWrapper.innerHTML = svgContent;

            // Fill Legend
            cardInstance.querySelector(".term-minor-val").textContent = arg.minor_term || "[None]";
            cardInstance.querySelector(".term-major-val").textContent = arg.major_term || "[None]";
            cardInstance.querySelector(".term-middle-val").textContent = arg.middle_term || "[None]";

            // Handle Fallacies/Violations section
            const fallaciesSection = cardInstance.querySelector(".arg-fallacies-section");
            const fallaciesList = cardInstance.querySelector(".fallacies-list");

            if (arg.violations && arg.violations.length > 0) {
                fallaciesSection.classList.remove("hidden");
                arg.violations.forEach(v => {
                    const fallCard = document.createElement("div");
                    fallCard.className = "fallacy-violation-card";
                    fallCard.setAttribute("data-warning", v.is_warning ? "true" : "false");

                    fallCard.innerHTML = `
                        <div class="fallacy-title-row">
                            <i class="${v.is_warning ? 'fa-solid fa-circle-info' : 'fa-solid fa-circle-xmark'}"></i>
                            <h5>${v.title}</h5>
                        </div>
                        <p class="fallacy-desc">${v.description}</p>
                        <p class="fallacy-details">${v.details}</p>
                    `;
                    fallaciesList.appendChild(fallCard);
                });
            }

            // Append argument card to list
            argumentsList.appendChild(cardInstance);
        });

        // Set top dashboard counters
        statValid.textContent = validCount;
        statInvalid.textContent = invalidCount;
        statWarnings.textContent = warningCount;

        // Display results block
        resultsSection.classList.remove("hidden");
        resultsSection.scrollIntoView({ behavior: "smooth" });
    }

    function fillPropRow(rowElement, propData) {
        if (!propData) return;
        
        // Quantifier formatting
        const qElement = rowElement.querySelector(".quantifier");
        qElement.textContent = propData.quantifier ? capitalize(propData.quantifier) + " " : "";

        // Terms
        rowElement.querySelector(".subject").textContent = propData.subject;
        rowElement.querySelector(".copula").textContent = " " + propData.copula + " ";
        rowElement.querySelector(".predicate").textContent = propData.predicate;

        // Type Code and Implicit badge
        rowElement.querySelector(".prop-badge.type-code").textContent = propData.type_code;
        
        const implicitBadge = rowElement.querySelector(".prop-badge.implicit-badge");
        if (implicitBadge) {
            if (propData.is_implicit) {
                implicitBadge.classList.remove("hidden");
            } else {
                implicitBadge.classList.add("hidden");
            }
        }

        // Distribution details
        const sDist = rowElement.querySelector(".dist-tag.subject-dist");
        const pDist = rowElement.querySelector(".dist-tag.predicate-dist");
        
        sDist.setAttribute("data-dist", propData.is_subject_distributed ? "true" : "false");
        sDist.textContent = `Subject: ${propData.is_subject_distributed ? 'Distributed' : 'Undistributed'}`;

        pDist.setAttribute("data-dist", propData.is_predicate_distributed ? "true" : "false");
        pDist.textContent = `Predicate: ${propData.is_predicate_distributed ? 'Distributed' : 'Undistributed'}`;
    }

    function drawEulerDiagram(minor, major, middle, status) {
        // Safe string truncated for labels
        const S = truncate(minor, 12);
        const P = truncate(major, 12);
        const M = truncate(middle, 12);

        let iconOverlay = "";
        let filterShadow = "";

        if (status === "valid") {
            // Glowing green validation circle in center
            iconOverlay = `
                <circle cx="140" cy="115" r="22" fill="#065f46" stroke="#10b981" stroke-width="2" opacity="0.9" />
                <path d="M133 115 l5 5 l9 -9" stroke="#ffffff" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" fill="none" />
            `;
            filterShadow = `style="filter: drop-shadow(0 0 10px rgba(16, 185, 129, 0.25))"`;
        } else if (status === "warning") {
            // Warning amber circle
            iconOverlay = `
                <circle cx="140" cy="115" r="22" fill="#78350f" stroke="#f59e0b" stroke-width="2" opacity="0.9" />
                <path d="M140 105 v12 M140 123 h.01" stroke="#ffffff" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" fill="none" />
            `;
            filterShadow = `style="filter: drop-shadow(0 0 10px rgba(245, 158, 11, 0.25))"`;
        } else {
            // Fallacy cross red circle
            iconOverlay = `
                <circle cx="140" cy="115" r="22" fill="#991b1b" stroke="#f43f5e" stroke-width="2" opacity="0.9" />
                <path d="M133 108 l14 14 M147 108 l-14 14" stroke="#ffffff" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" fill="none" />
            `;
            filterShadow = `style="filter: drop-shadow(0 0 10px rgba(244, 63, 94, 0.25))"`;
        }

        // SVG string rendering three overlapping circles beautifully
        return `
        <svg viewBox="0 0 280 220" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg" ${filterShadow}>
            <!-- Definitions for styling -->
            <defs>
                <linearGradient id="goldGlow" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stop-color="#dfa837" stop-opacity="0.2"/>
                    <stop offset="100%" stop-color="#b47e1b" stop-opacity="0.05"/>
                </linearGradient>
            </defs>

            <!-- Subject Circle (Left) S -->
            <circle cx="95" cy="135" r="48" fill="rgba(59, 130, 246, 0.08)" stroke="#3b82f6" stroke-width="2" stroke-dasharray="4 2" />
            
            <!-- Predicate Circle (Right) P -->
            <circle cx="185" cy="135" r="48" fill="rgba(236, 72, 153, 0.08)" stroke="#ec4899" stroke-width="2" stroke-dasharray="4 2" />
            
            <!-- Middle Circle (Top) M -->
            <circle cx="140" cy="85" r="48" fill="url(#goldGlow)" stroke="#dfa837" stroke-width="2" />
            
            <!-- Floating Text Labels -->
            <!-- M label -->
            <rect x="90" y="24" width="100" height="18" rx="4" fill="rgba(10, 13, 22, 0.85)" stroke="rgba(223, 168, 55, 0.3)" stroke-width="1" />
            <text x="140" y="37" font-family="Outfit, sans-serif" font-size="10" font-weight="600" fill="#dfa837" text-anchor="middle">M: ${M}</text>

            <!-- S label -->
            <rect x="15" y="186" width="100" height="18" rx="4" fill="rgba(10, 13, 22, 0.85)" stroke="rgba(59, 130, 246, 0.3)" stroke-width="1" />
            <text x="65" y="199" font-family="Outfit, sans-serif" font-size="10" font-weight="600" fill="#3b82f6" text-anchor="middle">S: ${S}</text>

            <!-- P label -->
            <rect x="165" y="186" width="100" height="18" rx="4" fill="rgba(10, 13, 22, 0.85)" stroke="rgba(236, 72, 153, 0.3)" stroke-width="1" />
            <text x="215" y="199" font-family="Outfit, sans-serif" font-size="10" font-weight="600" fill="#ec4899" text-anchor="middle">P: ${P}</text>

            <!-- Center logic status overlay icon -->
            ${iconOverlay}
        </svg>
        `;
    }

    function capitalize(str) {
        if (!str) return "";
        return str.charAt(0).toUpperCase() + str.slice(1);
    }

    function truncate(str, length) {
        if (!str) return "[none]";
        if (str.length <= length) return str;
        return str.substring(0, length - 2) + "..";
    }
});
