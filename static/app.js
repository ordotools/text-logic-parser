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
        document.getElementById("spacy-concepts-card").classList.add("hidden");
        document.querySelector(".app-container").classList.remove("layout-quadrants");
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
        document.getElementById("spacy-concepts-card").classList.add("hidden");
        document.querySelector(".app-container").classList.remove("layout-quadrants");

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
                const errorMsg = errorData.detail || errorData.message || errorData.error || "Failed to analyze essay.";
                throw new Error(errorMsg);
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

        // 1. Render spaCy Semantic Concepts
        const concepts = data.concepts || {};
        const nounChunksContainer = document.getElementById("concepts-noun-chunks");
        const entitiesContainer = document.getElementById("concepts-entities");
        const keyTermsContainer = document.getElementById("concepts-key-terms");

        // Fill Noun Chunks
        nounChunksContainer.innerHTML = "";
        if (concepts.noun_chunks && concepts.noun_chunks.length > 0) {
            concepts.noun_chunks.forEach(chunk => {
                const tag = document.createElement("span");
                tag.className = "concept-tag tag-blue";
                tag.textContent = chunk;
                nounChunksContainer.appendChild(tag);
            });
        } else {
            nounChunksContainer.innerHTML = '<span class="concept-tag tag-empty">None detected</span>';
        }

        // Fill Entities
        entitiesContainer.innerHTML = "";
        if (concepts.entities && concepts.entities.length > 0) {
            concepts.entities.forEach(ent => {
                const tag = document.createElement("span");
                tag.className = "concept-tag tag-pink";
                tag.textContent = `${ent.text} [${ent.label}]`;
                entitiesContainer.appendChild(tag);
            });
        } else {
            entitiesContainer.innerHTML = '<span class="concept-tag tag-empty">None detected</span>';
        }

        // Fill Key Terms
        keyTermsContainer.innerHTML = "";
        if (concepts.key_terms && concepts.key_terms.length > 0) {
            concepts.key_terms.forEach(term => {
                const tag = document.createElement("span");
                tag.className = "concept-tag tag-gold";
                tag.textContent = term;
                keyTermsContainer.appendChild(tag);
            });
        } else {
            keyTermsContainer.innerHTML = '<span class="concept-tag tag-empty">None detected</span>';
        }

        // 2. Render spaCy Raw Parsed Arguments
        const rawArgsContainer = document.getElementById("raw-spacy-arguments");
        rawArgsContainer.innerHTML = "";
        const rawSpacyArgs = data.raw_spacy_arguments || [];

        if (rawSpacyArgs.length === 0) {
            rawArgsContainer.innerHTML = '<div class="raw-arg-empty">No explicit arguments parsed directly by spaCy. Sending full text to the AI Agent for deep reconstruction.</div>';
        } else {
            rawSpacyArgs.forEach((arg, index) => {
                const item = document.createElement("div");
                item.className = "raw-arg-item animate-slide-up";
                
                let premisesHtml = "";
                arg.raw_premises.forEach((p, idx) => {
                    premisesHtml += `
                        <div class="raw-arg-prop-row">
                            <span class="label">Premise ${idx+1}:</span>
                            <span class="val">${p}</span>
                        </div>
                    `;
                });
                
                item.innerHTML = `
                    <div class="raw-arg-title">Argument candidate #${index + 1}</div>
                    <div class="raw-arg-props">
                        ${premisesHtml}
                        <div class="raw-arg-prop-row">
                            <span class="label">Conclusion:</span>
                            <span class="val">${arg.raw_conclusion}</span>
                        </div>
                    </div>
                `;
                rawArgsContainer.appendChild(item);
            });
        }

        // Show the concepts card
        document.getElementById("spacy-concepts-card").classList.remove("hidden");

        if (!data.success || !data.arguments || data.arguments.length === 0) {
            resultsCountBadge.textContent = "0 Arguments Extracted";
            statValid.textContent = "0";
            statInvalid.textContent = "0";
            statWarnings.textContent = "0";
            alert("No logical arguments could be identified in the text. Ensure your text contains logical claims, assertions, or assumptions.");
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
            cardInstance.querySelector(".rationale-text").textContent = arg.rationale || "Reconstructed from text context.";

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
            const svgContent = drawEulerDiagram(arg.minor_term, arg.major_term, arg.middle_term, status, premises, conclusion, index);
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

        // Activate quadrant layout
        const appContainer = document.querySelector(".app-container");
        appContainer.classList.add("layout-quadrants");

        // Only scroll to results on mobile/tablets where it flows vertically
        if (!window.matchMedia("(min-width: 1024px)").matches) {
            resultsSection.scrollIntoView({ behavior: "smooth" });
        }
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

    function drawEulerDiagram(minor, major, middle, status, premises, conclusion, index) {
        // Safe string truncated for labels
        const S = truncate(minor, 12);
        const P = truncate(major, 12);
        const M = truncate(middle, 12);

        // Generate a unique suffix for this diagram's IDs to prevent collisions in the DOM
        const suffix = index !== undefined ? index : Math.floor(Math.random() * 1000000);

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

        let shadingSvg = "";
        let xSvg = "";

        if (minor && major && middle && premises && premises.length > 0) {
            const shadedRegions = Array(8).fill(false);
            const xPositions = [];

            // Helper to get role of a term
            const getTermRole = (termText, minT, majT, midT) => {
                const norm = (t) => {
                    if (!t) return "";
                    let s = t.trim().toLowerCase();
                    s = s.replace(/^(a|an|the)\s+/, "");
                    if (s.endsWith("es")) s = s.slice(0, -2);
                    else if (s.endsWith("s")) s = s.slice(0, -1);
                    return s.trim();
                };

                const termNorm = norm(termText);
                const sNorm = norm(minT);
                const pNorm = norm(majT);
                const mNorm = norm(midT);

                if (termNorm === sNorm) return "S";
                if (termNorm === pNorm) return "P";
                if (termNorm === mNorm) return "M";

                if (sNorm.includes(termNorm) || termNorm.includes(sNorm)) return "S";
                if (pNorm.includes(termNorm) || termNorm.includes(pNorm)) return "P";
                if (mNorm.includes(termNorm) || termNorm.includes(mNorm)) return "M";

                return null;
            };

            const regionCenters = {
                1: { x: 65, y: 145 },   // S only
                2: { x: 215, y: 145 },  // P only
                3: { x: 140, y: 55 },   // M only
                4: { x: 110, y: 105 },  // S & M only
                5: { x: 170, y: 105 },  // P & M only
                6: { x: 140, y: 142 },  // S & P only
                7: { x: 140, y: 125 }   // S & P & M
            };

            const borderPoints = {
                "4-7": { x: 139, y: 120 },
                "5-7": { x: 141, y: 120 },
                "6-7": { x: 140, y: 133 }
            };

            const getRelationRegions = (subjRole, predRole, typeCode) => {
                let shade = [];
                let x = [];
                const key = `${subjRole}-${predRole}`;

                if (key === "S-M") {
                    if (typeCode === "A") shade = [1, 6];
                    else if (typeCode === "E") shade = [4, 7];
                    else if (typeCode === "I" || typeCode === "Singular Affirmative") x = [4, 7];
                    else if (typeCode === "O" || typeCode === "Singular Negative") x = [1, 6];
                } else if (key === "M-S") {
                    if (typeCode === "A") shade = [3, 5];
                    else if (typeCode === "E") shade = [4, 7];
                    else if (typeCode === "I" || typeCode === "Singular Affirmative") x = [4, 7];
                    else if (typeCode === "O" || typeCode === "Singular Negative") x = [3, 5];
                } else if (key === "P-M") {
                    if (typeCode === "A") shade = [2, 6];
                    else if (typeCode === "E") shade = [5, 7];
                    else if (typeCode === "I" || typeCode === "Singular Affirmative") x = [5, 7];
                    else if (typeCode === "O" || typeCode === "Singular Negative") x = [2, 6];
                } else if (key === "M-P") {
                    if (typeCode === "A") shade = [3, 4];
                    else if (typeCode === "E") shade = [5, 7];
                    else if (typeCode === "I" || typeCode === "Singular Affirmative") x = [5, 7];
                    else if (typeCode === "O" || typeCode === "Singular Negative") x = [3, 4];
                } else if (key === "S-P") {
                    if (typeCode === "A") shade = [1, 4];
                    else if (typeCode === "E") shade = [6, 7];
                    else if (typeCode === "I" || typeCode === "Singular Affirmative") x = [6, 7];
                    else if (typeCode === "O" || typeCode === "Singular Negative") x = [1, 4];
                } else if (key === "P-S") {
                    if (typeCode === "A") shade = [2, 5];
                    else if (typeCode === "E") shade = [6, 7];
                    else if (typeCode === "I" || typeCode === "Singular Affirmative") x = [6, 7];
                    else if (typeCode === "O" || typeCode === "Singular Negative") x = [2, 5];
                }
                return { shade, x };
            };

            // First pass: Process universal premises to shade regions
            premises.forEach(p => {
                const sRole = getTermRole(p.subject, minor, major, middle);
                const pRole = getTermRole(p.predicate, minor, major, middle);
                if (sRole && pRole) {
                    const rel = getRelationRegions(sRole, pRole, p.type_code);
                    rel.shade.forEach(r => {
                        shadedRegions[r] = true;
                    });
                }
            });

            // Second pass: Process particular / singular premises to place 'X'
            premises.forEach(p => {
                const sRole = getTermRole(p.subject, minor, major, middle);
                const pRole = getTermRole(p.predicate, minor, major, middle);
                if (sRole && pRole) {
                    const rel = getRelationRegions(sRole, pRole, p.type_code);
                    if (rel.x && rel.x.length > 0) {
                        // Find unshaded candidates
                        const unshaded = rel.x.filter(r => !shadedRegions[r]);
                        if (unshaded.length === 1) {
                            xPositions.push(regionCenters[unshaded[0]]);
                        } else if (unshaded.length === 2) {
                            const key = `${unshaded[0]}-${unshaded[1]}`;
                            const revKey = `${unshaded[1]}-${unshaded[0]}`;
                            const pt = borderPoints[key] || borderPoints[revKey] || regionCenters[unshaded[0]];
                            xPositions.push(pt);
                        } else {
                            // Contradictory/fallback: place in first candidate anyway
                            xPositions.push(regionCenters[rel.x[0]]);
                        }
                    }
                }
            });

            // Generate Shading SVG elements
            for (let r = 1; r <= 7; r++) {
                if (shadedRegions[r]) {
                    let mask1, mask2, mask3;
                    switch (r) {
                        case 1: mask1 = `mask-S-${suffix}`; mask2 = `mask-not-P-${suffix}`; mask3 = `mask-not-M-${suffix}`; break;
                        case 2: mask1 = `mask-not-S-${suffix}`; mask2 = `mask-P-${suffix}`; mask3 = `mask-not-M-${suffix}`; break;
                        case 3: mask1 = `mask-not-S-${suffix}`; mask2 = `mask-not-P-${suffix}`; mask3 = `mask-M-${suffix}`; break;
                        case 4: mask1 = `mask-S-${suffix}`; mask2 = `mask-not-P-${suffix}`; mask3 = `mask-M-${suffix}`; break;
                        case 5: mask1 = `mask-not-S-${suffix}`; mask2 = `mask-P-${suffix}`; mask3 = `mask-M-${suffix}`; break;
                        case 6: mask1 = `mask-S-${suffix}`; mask2 = `mask-P-${suffix}`; mask3 = `mask-not-M-${suffix}`; break;
                        case 7: mask1 = `mask-S-${suffix}`; mask2 = `mask-P-${suffix}`; mask3 = `mask-M-${suffix}`; break;
                    }
                    shadingSvg += `
                    <g mask="url(#${mask1})">
                        <g mask="url(#${mask2})">
                            <g mask="url(#${mask3})">
                                <rect x="0" y="0" width="280" height="220" fill="rgba(15, 23, 42, 0.65)" />
                                <rect x="0" y="0" width="280" height="220" fill="url(#diagonalHatch-${suffix})" />
                            </g>
                        </g>
                    </g>
                    `;
                }
            }

            // Generate X SVG elements
            xPositions.forEach(pt => {
                xSvg += `
                <g class="venn-x" stroke="#dfa837" stroke-width="2.5" stroke-linecap="round" opacity="0.95">
                    <line x1="${pt.x - 6}" y1="${pt.y - 6}" x2="${pt.x + 6}" y2="${pt.y + 6}" />
                    <line x1="${pt.x + 6}" y1="${pt.y - 6}" x2="${pt.x - 6}" y2="${pt.y + 6}" />
                    <circle cx="${pt.x}" cy="${pt.y}" r="6" fill="rgba(223, 168, 55, 0.3)" fill-opacity="0.3" filter="blur(1px)" />
                </g>
                `;
            });
        }

        // SVG string rendering three overlapping circles beautifully
        return `
        <svg viewBox="0 0 280 220" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg" ${filterShadow}>
            <!-- Definitions for styling -->
            <defs>
                <linearGradient id="goldGlow-${suffix}" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stop-color="#dfa837" stop-opacity="0.2"/>
                    <stop offset="100%" stop-color="#b47e1b" stop-opacity="0.05"/>
                </linearGradient>
                <pattern id="diagonalHatch-${suffix}" width="8" height="8" patternTransform="rotate(45 0 0)" patternUnits="userSpaceOnUse">
                    <line x1="0" y1="0" x2="0" y2="8" stroke="rgba(148, 163, 184, 0.35)" stroke-width="1.5" />
                </pattern>
                
                <!-- Masks for each circle -->
                <mask id="mask-S-${suffix}">
                    <rect width="280" height="220" fill="black" />
                    <circle cx="95" cy="135" r="48" fill="white" />
                </mask>
                <mask id="mask-not-S-${suffix}">
                    <rect width="280" height="220" fill="white" />
                    <circle cx="95" cy="135" r="48" fill="black" />
                </mask>
                
                <mask id="mask-P-${suffix}">
                    <rect width="280" height="220" fill="black" />
                    <circle cx="185" cy="135" r="48" fill="white" />
                </mask>
                <mask id="mask-not-P-${suffix}">
                    <rect width="280" height="220" fill="white" />
                    <circle cx="185" cy="135" r="48" fill="black" />
                </mask>
                
                <mask id="mask-M-${suffix}">
                    <rect width="280" height="220" fill="black" />
                    <circle cx="140" cy="85" r="48" fill="white" />
                </mask>
                <mask id="mask-not-M-${suffix}">
                    <rect width="280" height="220" fill="white" />
                    <circle cx="140" cy="85" r="48" fill="black" />
                </mask>
            </defs>

            <!-- Base shaded regions -->
            ${shadingSvg}

            <!-- Subject Circle (Left) S -->
            <circle cx="95" cy="135" r="48" fill="rgba(59, 130, 246, 0.04)" stroke="#3b82f6" stroke-width="2" stroke-dasharray="4 2" />
            
            <!-- Predicate Circle (Right) P -->
            <circle cx="185" cy="135" r="48" fill="rgba(236, 72, 153, 0.04)" stroke="#ec4899" stroke-width="2" stroke-dasharray="4 2" />
            
            <!-- Middle Circle (Top) M -->
            <circle cx="140" cy="85" r="48" fill="url(#goldGlow-${suffix})" stroke="#dfa837" stroke-width="2" />
            
            <!-- Dynamic X Existential Badges -->
            ${xSvg}
            
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
