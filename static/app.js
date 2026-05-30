// Lyceum Logic Analyzer - Frontend Application Script

document.addEventListener("DOMContentLoaded", () => {
    // DOM Elements
    const essayInput = document.getElementById("essay-input");
    const analyzeBtn = document.getElementById("analyze-btn");
    const loadSampleBtn = document.getElementById("load-sample-btn");
    const clearBtn = document.getElementById("clear-btn");
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
        document.querySelector(".app-container").classList.remove("layout-three-columns");

        // Reset integrated progress header state
        setLoading(false);
        document.getElementById("header-progress-status").classList.add("hidden");
    });

    analyzeBtn.addEventListener("click", async () => {
        const text = essayInput.value.trim();
        if (!text) {
            alert("Please paste an essay or load a sample first.");
            return;
        }

        // Show loading state and active layout
        setLoading(true);

        // Clear dashboard stats
        statValid.textContent = "0";
        statInvalid.textContent = "0";
        statWarnings.textContent = "0";
        resultsCountBadge.textContent = "0 Arguments Extracted";

        const startTime = performance.now();
        const argumentsArray = [];
        const seenArguments = new Set();
        let globalConcepts = null;
        let globalRawArguments = null;
        let processedChunksCount = 0;
        let totalChunksCount = 0;

        let validCount = 0;
        let invalidCount = 0;
        let warningCount = 0;

        argumentsList.innerHTML = "";

        const versionSelect = document.getElementById("version-select");
        const version = versionSelect ? versionSelect.value : "v1";

        try {
            const response = await fetch("/api/analyze/stream", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ text, version })
            });

            if (!response.ok) {
                let errorMsg = "Failed to start streaming analysis.";
                try {
                    const errorData = await response.json();
                    errorMsg = errorData.detail || errorData.message || errorData.error || errorMsg;
                } catch (e) { }
                throw new Error(errorMsg);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder("utf-8");
            let buffer = "";

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split("\n");

                // Save the last incomplete line back to the buffer
                buffer = lines.pop();

                // Process complete SSE event packets
                for (let i = 0; i < lines.length; i++) {
                    const line = lines[i].trim();
                    if (!line) continue;

                    if (line.startsWith("event:")) {
                        const eventType = line.replace("event:", "").trim();
                        let nextLine = "";
                        while (i + 1 < lines.length && !nextLine) {
                            i++;
                            const l = lines[i].trim();
                            if (l.startsWith("data:")) {
                                nextLine = l;
                            }
                        }

                        if (nextLine && nextLine.startsWith("data:")) {
                            const dataStr = nextLine.replace("data:", "").trim();
                            try {
                                const data = JSON.parse(dataStr);
                                handleStreamEvent(eventType, data);
                            } catch (e) {
                                console.error("Failed to parse event JSON data:", e, dataStr);
                            }
                        }
                    }
                }
            }

            // Flush remaining buffer
            if (buffer.trim()) {
                const line = buffer.trim();
                if (line.startsWith("event:")) {
                    const eventType = line.replace("event:", "").trim();
                    const dataLineIndex = buffer.indexOf("data:");
                    if (dataLineIndex !== -1) {
                        const dataStr = buffer.substring(dataLineIndex).replace("data:", "").trim();
                        try {
                            const data = JSON.parse(dataStr);
                            handleStreamEvent(eventType, data);
                        } catch (e) { }
                    }
                }
            }

        } catch (error) {
            alert(`Error: ${error.message}`);
            console.error("Analysis failed:", error);
            setLoading(false);
        }

        function handleStreamEvent(event, data) {
            const progressFill = document.getElementById("header-progress-fill");
            const progressText = document.getElementById("header-progress-text");
            const retryBadge = document.getElementById("header-retry-badge");
            const titleText = document.getElementById("results-title-text");
            const titleIcon = document.getElementById("results-title-icon");

            if (event === "metadata") {
                totalChunksCount = data.total_chunks || 1;
                
                if (data.concepts) {
                    globalConcepts = data.concepts;
                }
                if (data.raw_spacy_arguments) {
                    globalRawArguments = data.raw_spacy_arguments;
                }
                
                renderConceptsAndRawSpacyArgs(globalConcepts, globalRawArguments);

                titleText.textContent = "Extracting Logic...";
                titleIcon.className = "fa-solid fa-microchip text-gold animate-pulse";
                
                progressFill.style.width = "5%";
                progressText.textContent = `Processing chunk 1 of ${totalChunksCount}...`;

                document.getElementById("spacy-concepts-card").classList.remove("hidden");
            }
            else if (event === "chunk_retry") {
                retryBadge.classList.remove("hidden");
                progressText.textContent = `Retrying chunk #${data.chunk_index + 1} (attempt ${data.attempt}/3)...`;
            }
            else if (event === "chunk_result") {
                totalChunksCount = data.total_chunks || totalChunksCount;
                processedChunksCount = data.processed_chunks !== undefined ? data.processed_chunks : processedChunksCount;
                const argumentsListChunk = data.arguments || [];

                retryBadge.classList.add("hidden");

                const pct = Math.min(95, Math.round((processedChunksCount / totalChunksCount) * 100));
                progressFill.style.width = `${pct}%`;
                const displayCount = Math.min(processedChunksCount + 1, totalChunksCount);
                progressText.textContent = `Processing chunk ${displayCount} of ${totalChunksCount}...`;

                argumentsListChunk.forEach((arg) => {
                    const hashStr = (arg.minor_term || "") + "|" + (arg.major_term || "") + "|" + (arg.middle_term || "");
                    if (!seenArguments.has(hashStr)) {
                        seenArguments.add(hashStr);
                        argumentsArray.push(arg);

                        if (arg.is_assumption) {
                            warningCount++;
                            animateValueUpdate(statWarnings, warningCount);
                        } else if (arg.is_valid) {
                            const hasWarnings = arg.violations && arg.violations.some(v => v.is_warning);
                            if (hasWarnings) {
                                warningCount++;
                                animateValueUpdate(statWarnings, warningCount);
                            } else {
                                validCount++;
                                animateValueUpdate(statValid, validCount);
                            }
                        } else {
                            invalidCount++;
                            animateValueUpdate(statInvalid, invalidCount);
                        }
                    }
                });

                argumentsArray.sort((a, b) => (a.global_index || 0) - (b.global_index || 0));

                argumentsList.innerHTML = "";
                resultsCountBadge.textContent = `${argumentsArray.length} Argument${argumentsArray.length > 1 ? 's' : ''} Extracted`;

                argumentsArray.forEach((arg, cardIndex) => {
                    let status = "invalid";
                    if (arg.is_assumption) {
                        status = "warning";
                    } else if (arg.is_valid) {
                        const hasWarnings = arg.violations && arg.violations.some(v => v.is_warning);
                        status = hasWarnings ? "warning" : "valid";
                    }

                    const cardInstance = cardTemplate.content.cloneNode(true);

                    if (arg.is_assumption) {
                        cardInstance.querySelector(".arg-index").textContent = `Assumption #${cardIndex + 1}`;
                        cardInstance.querySelector(".arg-title-area h3").textContent = "Unproven Assumption";
                        const syllogismTitle = cardInstance.querySelector(".syllogism-structure h4");
                        if (syllogismTitle) {
                            syllogismTitle.innerHTML = `<i class="fa-solid fa-triangle-exclamation"></i> Flagged Assumption`;
                        }
                        cardInstance.querySelector(".arg-rationale").classList.add("hidden");
                        cardInstance.querySelector(".arg-body-grid").classList.add("hidden");
                        cardInstance.querySelector(".arg-fallacies-section").classList.add("hidden");
                    } else {
                        cardInstance.querySelector(".arg-index").textContent = `Argument #${cardIndex + 1}`;
                    }

                    cardInstance.querySelector(".excerpt-text").textContent = `"${arg.original_text}"`;

                    if (!arg.is_assumption) {
                        cardInstance.querySelector(".rationale-text").textContent = arg.rationale || "Reconstructed from text context.";

                        const premises = arg.reconstructed_syllogism.premises;
                        const conclusion = arg.reconstructed_syllogism.conclusion;

                        fillPropRow(cardInstance.querySelector(".prop-row.premise-1"), premises[0]);

                        const p2Row = cardInstance.querySelector(".prop-row.premise-2");
                        if (premises && premises.length > 1) {
                            fillPropRow(p2Row, premises[1]);
                        } else {
                            p2Row.classList.add("hidden");
                        }

                        fillPropRow(cardInstance.querySelector(".prop-row.conclusion-prop"), conclusion);

                        const diagramWrapper = cardInstance.querySelector(".svg-diagram-wrapper");
                        diagramWrapper.innerHTML = drawEulerDiagram(arg.minor_term, arg.major_term, arg.middle_term, status, premises, conclusion, cardIndex);

                        cardInstance.querySelector(".term-minor-val").textContent = arg.minor_term || "[None]";
                        cardInstance.querySelector(".term-major-val").textContent = arg.major_term || "[None]";
                        cardInstance.querySelector(".term-middle-val").textContent = arg.middle_term || "[None]";

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
                    }

                    const badge = cardInstance.querySelector(".status-badge");
                    badge.setAttribute("data-status", status);

                    const badgeIcon = badge.querySelector("i");
                    const badgeText = badge.querySelector(".status-text");

                    if (arg.is_assumption) {
                        badgeIcon.className = "fa-solid fa-circle-info";
                        badgeText.textContent = "Assumption";
                    } else if (status === "valid") {
                        badgeIcon.className = "fa-solid fa-circle-check";
                        badgeText.textContent = "Valid";
                    } else if (status === "warning") {
                        badgeIcon.className = "fa-solid fa-circle-info";
                        badgeText.textContent = "Valid (Caveat)";
                    } else {
                        badgeIcon.className = "fa-solid fa-triangle-exclamation";
                        badgeText.textContent = "Fallacious";
                    }

                    argumentsList.appendChild(cardInstance);
                });
            }
            else if (event === "completed") {
                const progressFill = document.getElementById("header-progress-fill");
                const progressText = document.getElementById("header-progress-text");

                progressFill.style.width = "100%";
                const timeInSec = ((performance.now() - startTime) / 1000).toFixed(1);
                progressText.textContent = `Analysis finished in ${timeInSec} sec`;

                setTimeout(() => {
                    setLoading(false);

                    if (argumentsArray.length === 0) {
                        alert("No logical arguments could be identified in the text. Ensure your text contains logical claims, assertions, or assumptions.");
                    } else {
                        if (!window.matchMedia("(min-width: 1024px)").matches) {
                            resultsSection.scrollIntoView({ behavior: "smooth" });
                        }
                    }
                }, 500);
            }
        }
    });

    function setLoading(isLoading) {
        const progressFill = document.getElementById("header-progress-fill");
        const progressContainer = document.getElementById("header-progress-container");
        const progressStatus = document.getElementById("header-progress-status");
        const progressText = document.getElementById("header-progress-text");
        const retryBadge = document.getElementById("header-retry-badge");
        const titleText = document.getElementById("results-title-text");
        const titleIcon = document.getElementById("results-title-icon");

        if (isLoading) {
            analyzeBtn.disabled = true;
            analyzeBtn.querySelector(".btn-text").classList.add("hidden");
            analyzeBtn.querySelector(".btn-loading-spinner").classList.remove("hidden");

            // Show columns immediately when submitted
            resultsSection.classList.remove("hidden");
            document.getElementById("spacy-concepts-card").classList.remove("hidden");
            document.querySelector(".app-container").classList.add("layout-three-columns");

            // Activate progress bar and status in dashboard header
            progressContainer.classList.add("active");
            progressStatus.classList.remove("hidden");

            // Set initial loading states
            progressFill.style.width = "0%";
            progressText.textContent = "Connecting to logic parser...";
            retryBadge.classList.add("hidden");

            titleText.textContent = "Reading Essay & Unifying Terms...";
            titleIcon.className = "fa-solid fa-spinner fa-spin text-gold";
        } else {
            analyzeBtn.disabled = false;
            analyzeBtn.querySelector(".btn-text").classList.remove("hidden");
            analyzeBtn.querySelector(".btn-loading-spinner").classList.add("hidden");

            // Deactivate progress bar and status in dashboard header
            progressContainer.classList.remove("active");
            // Do not hide progressStatus here to avoid UI jump

            // Restore default title and icon
            titleText.textContent = "Analysis";
            titleIcon.className = "fa-solid fa-chart-column";
        }
    }

    function renderConceptsAndRawSpacyArgs(concepts, rawSpacyArgs) {
        const nounChunksContainer = document.getElementById("concepts-noun-chunks");
        const entitiesContainer = document.getElementById("concepts-entities");
        const keyTermsContainer = document.getElementById("concepts-key-terms");

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

        const rawArgsContainer = document.getElementById("raw-spacy-arguments");
        rawArgsContainer.innerHTML = "";
        const rawSpacyArguments = rawSpacyArgs || [];

        if (rawSpacyArguments.length === 0) {
            rawArgsContainer.innerHTML = '<div class="raw-arg-empty">No explicit arguments parsed directly by spaCy. Sending full text to the AI Agent for deep reconstruction.</div>';
        } else {
            rawSpacyArguments.forEach((arg, index) => {
                const item = document.createElement("div");
                item.className = "raw-arg-item animate-slide-up";

                let premisesHtml = "";
                arg.raw_premises.forEach((p, idx) => {
                    premisesHtml += `
                        <div class="raw-arg-prop-row">
                            <span class="label">Premise ${idx + 1}:</span>
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
    }

    function animateValueUpdate(targetElement, newValue) {
        if (!targetElement) return;
        targetElement.textContent = newValue;
        targetElement.classList.add("scale-up-animation");
        setTimeout(() => {
            targetElement.classList.remove("scale-up-animation");
        }, 250);
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

            <!-- Center logic status overlay icon removed to reduce distraction -->
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
