/* =========================================
   AI TEACHING ASSISTANT - APP JS
   Version: 2.3.0
========================================= */

const API = "http://127.0.0.1:8000";

// State
let currentMode = "default";
let currentLanguage = "english";
let lastContext = "";
let lastTopic = "general";
let attentionTimer = null;

/* =========================================
   INITIALIZATION
========================================= */

document.addEventListener("DOMContentLoaded", () => {
    console.log("AI Teaching Assistant UI Initialized");
    loadFileList();
    loadDashboard();
    checkAttentionStatus();
});

/* =========================================
   UTILS
========================================= */

function setResult(id, content, stateClass = "") {
    const el = document.getElementById(id);
    if (!el) return;

    el.className = `result ${stateClass}`;
    
    // Use marked for rich text / math
    if (stateClass === "state-success" || id === "chatResult") {
        if (typeof marked !== "undefined") {
            el.innerHTML = marked.parse(content);
        } else {
            el.innerHTML = content;
        }
        if (window.MathJax) {
            MathJax.typesetPromise([el]);
        }
    } else {
        el.textContent = content;
    }

    el.classList.remove("state-loading", "state-success", "state-error");
    if (stateClass) el.classList.add(stateClass);
}

function setBusy(id, isBusy) {
    const el = document.getElementById(id);
    if (!el) return;

    if (isBusy) {
        el.disabled = true;
        el.classList.add("loading-pulse");
    } else {
        el.disabled = false;
        el.classList.remove("loading-pulse");
    }
}

function handleKeyPress(event) {
    if (event.key === "Enter") {
        sendChat();
    }
}

/* =========================================
   KNOWLEDGE BASE
========================================= */

async function uploadPDFs() {
    const fileInput = document.getElementById("pdfFiles");
    if (!fileInput.files.length) {
        setResult("pdfResult", "Please select files first.", "state-error");
        return;
    }

    setBusy("uploadBtn", true);
    setResult("pdfResult", "Uploading and indexing...", "state-loading");

    const formData = new FormData();
    for (const file of fileInput.files) {
        formData.append("files", file);
    }

    try {
        const response = await fetch(`${API}/upload_pdf/`, {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        if (response.ok) {
            setResult("pdfResult", data.message, "state-success");
            fileInput.value = "";
            loadFileList();
            loadDashboard(); // Update stats
        } else {
            setResult("pdfResult", data.detail || "Upload failed.", "state-error");
        }
    } catch (err) {
        setResult("pdfResult", "Could not reach backend.", "state-error");
    } finally {
        setBusy("uploadBtn", false);
    }
}

async function buildDB() {
    setBusy("buildBtn", true);
    setResult("pdfResult", "Building index from all files...", "state-loading");

    try {
        const response = await fetch(`${API}/build_db/`, { method: "POST" });
        const data = await response.json();

        if (response.ok) {
            setResult("pdfResult", data.message, "state-success");
            loadFileList();
            loadDashboard();
        } else {
            setResult("pdfResult", data.detail || "Rebuild failed.", "state-error");
        }
    } catch (err) {
        setResult("pdfResult", "Could not reach backend.", "state-error");
    } finally {
        setBusy("buildBtn", false);
    }
}

async function loadFileList() {
    const container = document.getElementById("fileListContainer");
    const section = document.getElementById("fileListSection");

    try {
        const response = await fetch(`${API}/files/`);
        const data = await response.json();

        if (response.ok && data.files && data.files.length > 0) {
            section.style.display = "block";
            container.innerHTML = data.files.map(file => `
                <div class="file-item">
                    <div class="file-info">
                        <span class="file-name">📄 ${file.filename}</span>
                        <span class="file-meta">${file.pages} pages · ${file.chunks} chunks</span>
                    </div>
                </div>
            `).join("");
        } else {
            section.style.display = "none";
        }
    } catch (err) {
        console.error("Failed to load file list:", err);
    }
}

/* =========================================
   OCR
========================================= */

async function extractText() {
    const imgInput = document.getElementById("imageFile");
    if (!imgInput.files.length) {
        setResult("ocrResult", "Select an image first.", "state-error");
        return;
    }

    setBusy("ocrBtn", true);
    setResult("ocrResult", "Running OCR...", "state-loading");

    const formData = new FormData();
    formData.append("image", imgInput.files[0]);

    try {
        const response = await fetch(`${API}/ocr/`, {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            setResult("ocrResult", data.detail || "OCR failed.", "state-error");
            return;
        }

        const output = data.extracted_text;
        const metaParts = [];
        if (data.confidence) metaParts.push(`Confidence: ${data.confidence.toFixed(1)}%`);
        if (data.method) metaParts.push(`Method: ${data.method}`);
        if (data.processing_time_ms) metaParts.push(`${data.processing_time_ms.toFixed(0)}ms`);

        const metaLine = metaParts.length
            ? "\n\n---\n" + metaParts.join("  ·  ")
            : "";

        setResult("ocrResult", output + metaLine, "state-success");
    } catch (err) {
        setResult("ocrResult", "Could not reach backend.", "state-error");
    } finally {
        setBusy("ocrBtn", false);
    }
}

function copyToChat() {
    const ocrResult = document.getElementById("ocrResult");
    const chatInput = document.getElementById("chatInput");
    chatInput.value = ocrResult.textContent.trim();
    chatInput.focus();
}

/* =========================================
   EXPLANATION MODES & LANGUAGE
========================================= */

function setMode(mode) {
    currentMode = mode;
    document.querySelectorAll(".mode-btn").forEach(btn => {
        btn.classList.toggle("active", btn.dataset.mode === mode);
    });
}

function setLanguage(lang) {
    currentLanguage = lang;
    console.log("Language set to:", lang);
}

/* =========================================
   CHAT / RAG
========================================= */

async function sendChat() {
    const questionInput = document.getElementById("chatInput");
    const question = questionInput.value.trim();
    if (!question) return;

    setBusy("askBtn", true);
    setResult("chatResult", "⏳ Analyzing context and generating answer...", "state-loading");
    
    // Hide quiz area until new response comes in
    document.getElementById("quizActionArea").style.display = "none";
    document.getElementById("quizResult").style.display = "none";

    try {
        const response = await fetch(`${API}/chat/`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ 
                question, 
                mode: currentMode,
                language: currentLanguage
            })
        });

        const data = await response.json();

        if (!response.ok) {
            setResult("chatResult", data.detail || "Failed to generate answer.", "state-error");
            return;
        }

        lastContext = data.context_text || "";
        lastTopic = data.source_details && data.source_details.length > 0 
                    ? data.source_details[0].subject 
                    : "general";

        const answerText = data.answer || "No answer returned.";

        // Build rich source citations
        let sourceMd = "";
        const sourceDetails = data.source_details || [];
        if (sourceDetails.length > 0) {
            const lines = sourceDetails.map(s => {
                const page = s.page ? ` (Page ${s.page})` : "";
                return `- 📄 **${s.filename}**${page}`;
            });
            const unique = [...new Set(lines)];
            sourceMd = "\n\n---\n### 📚 Sources\n" + unique.join("\n");
        }

        // Add timing info
        if (data.processing_time_ms) {
            const modeLabel = currentMode.charAt(0).toUpperCase() + currentMode.slice(1);
            const langLabel = currentLanguage.charAt(0).toUpperCase() + currentLanguage.slice(1);
            sourceMd += `\n\n*${modeLabel} mode · ${langLabel} · Response in ${(data.processing_time_ms / 1000).toFixed(1)}s*`;
        }

        setResult("chatResult", answerText + sourceMd);
        
        // Show Quiz button
        if (lastContext) {
            document.getElementById("quizActionArea").style.display = "block";
        }
        
        loadDashboard(); // Update stats
    } catch (err) {
        setResult("chatResult", "Could not reach backend.", "state-error");
    } finally {
        setBusy("askBtn", false);
    }
}

/* =========================================
   QUIZ LOGIC
========================================= */

async function generateQuiz() {
    const quizBtn = document.getElementById("genQuizBtn");
    const quizResult = document.getElementById("quizResult");
    
    setBusy("genQuizBtn", true);
    quizResult.style.display = "block";
    quizResult.innerHTML = "<p class='state-loading'>✨ Crafting custom quiz for you...</p>";

    try {
        const response = await fetch(`${API}/quiz/`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                topic: lastTopic,
                context_text: lastContext,
                num_questions: 3,
                language: currentLanguage
            })
        });

        const data = await response.json();

        if (!response.ok || data.error) {
            quizResult.innerHTML = `<p class='state-error'>${data.error || "Quiz generation failed."}</p>`;
            return;
        }

        renderQuiz(data.quiz);
    } catch (err) {
        quizResult.innerHTML = "<p class='state-error'>Could not reach backend for quiz.</p>";
    } finally {
        setBusy("genQuizBtn", false);
    }
}

function renderQuiz(questions) {
    const container = document.getElementById("quizResult");
    
    let html = `<h3>🧠 Topic Check: ${lastTopic.replace(/_/g, ' ')}</h3>`;
    
    questions.forEach((q, idx) => {
        const qId = `q_${idx}`;
        html += `
            <div class="quiz-card" id="card_${qId}">
                <div class="quiz-question">${idx + 1}. ${q.question}</div>
                <div class="quiz-options">
                    ${q.options ? q.options.map((opt, oIdx) => `
                        <div class="quiz-option" onclick="selectOption('${qId}', ${oIdx}, '${q.answer.replace(/'/g, "\\'")}', '${q.explanation.replace(/'/g, "\\'")}')">
                            ${opt}
                        </div>
                    `).join("") : `
                        <p class="muted">Short answer - think about it then check the answer.</p>
                        <button class="btn-outline" onclick="showShortAnswer('${qId}', '${q.answer.replace(/'/g, "\\'")}', '${q.explanation.replace(/'/g, "\\'")}')">Show Answer</button>
                    `}
                </div>
                <div id="feedback_${qId}" class="quiz-explanation" style="display: none;"></div>
            </div>
        `;
    });

    container.innerHTML = html;
}

function selectOption(qId, oIdx, correctAnswer, explanation) {
    const card = document.getElementById(`card_${qId}`);
    const options = card.querySelectorAll(".quiz-option");
    const feedback = document.getElementById(`feedback_${qId}`);
    
    // Prevent multiple selections
    if (card.dataset.answered === "true") return;
    card.dataset.answered = "true";

    let isCorrect = false;
    options.forEach((opt, idx) => {
        if (idx === oIdx) {
            opt.classList.add("selected");
            // Check if this option text matches correct answer
            if (opt.textContent.trim() === correctAnswer) {
                opt.classList.add("correct");
                isCorrect = true;
            } else {
                opt.classList.add("incorrect");
            }
        } else if (opt.textContent.trim() === correctAnswer) {
            opt.classList.add("correct"); // Highlight correct one
        }
    });

    feedback.style.display = "block";
    feedback.innerHTML = `<strong>${isCorrect ? "✅ Correct!" : "❌ Not quite."}</strong> ${explanation}`;
    
    // Record analytics
    recordScore(isCorrect ? 1 : 0, 1);
}

function showShortAnswer(qId, answer, explanation) {
    const feedback = document.getElementById(`feedback_${qId}`);
    feedback.style.display = "block";
    feedback.innerHTML = `<strong>Reference Answer:</strong> ${answer}<br><br><strong>Explanation:</strong> ${explanation}`;
    recordScore(1, 1); // Give credit for review
}

async function recordScore(score, total) {
    try {
        await fetch(`${API}/quiz/score/`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                topic: lastTopic,
                score,
                total,
                quiz_type: "mcq"
            })
        });
        loadDashboard(); // Refresh stats
    } catch (err) {
        console.error("Score recording failed", err);
    }
}

/* =========================================
   DASHBOARD
========================================= */

async function loadDashboard() {
    try {
        const response = await fetch(`${API}/dashboard/`);
        const data = await response.json();

        if (!response.ok) return;

        // Stats
        document.getElementById("statQuestions").textContent = data.stats.total_questions;
        document.getElementById("statQuizzes").textContent = data.stats.total_quizzes;
        document.getElementById("statAvgScore").textContent = `${data.stats.average_quiz_score}%`;
        document.getElementById("statDocs").textContent = data.stats.documents_indexed;

        // Topic Mastery
        const topicList = document.getElementById("topicList");
        if (data.topic_summary.length > 0) {
            topicList.innerHTML = data.topic_summary.map(t => `
                <div class="topic-item">
                    <div class="topic-info">
                        <strong>${t.topic.replace(/_/g, ' ')}</strong>
                        <span>${t.mastery_score}% mastery</span>
                    </div>
                    <div class="mastery-bar-bg">
                        <div class="mastery-bar-fill" style="width: ${t.mastery_score}%"></div>
                    </div>
                </div>
            `).join("");
        } else {
            topicList.innerHTML = "<p class='muted'>No data available yet.</p>";
        }

        // Activity
        const timeline = document.getElementById("activityTimeline");
        if (data.recent_activity.length > 0) {
            timeline.innerHTML = data.recent_activity.map(a => {
                const date = new Date(a.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                const icon = a.type === "question" ? "❓" : "📝";
                const label = a.type === "question" ? "Asked about" : "Took quiz on";
                return `
                    <div class="activity-item">
                        <div class="activity-time">${date}</div>
                        <div>${icon} ${label} <strong>${a.topic.replace(/_/g, ' ')}</strong></div>
                    </div>
                `;
            }).join("");
        } else {
            timeline.innerHTML = "<p class='muted'>No recent activity.</p>";
        }

    } catch (err) {
        console.error("Dashboard failed to load", err);
    }
}

/* =========================================
   ATTENTION TRACKING
========================================= */

async function startAttention() {
    try {
        const response = await fetch(`${API}/attention/start`, { method: "POST" });
        const data = await response.json();
        
        if (data.status === "started" || data.status === "already_active") {
            setResult("attentionResult", "Attention tracking started. Please look at the camera.", "state-success");
            
            // Poll for status
            if (attentionTimer) clearInterval(attentionTimer);
            attentionTimer = setInterval(checkAttentionStatus, 2000);
            
            // Try to start local video for feedback if on same machine
            startLocalVideo();
        }
    } catch (err) {
        setResult("attentionResult", "Failed to start attention tracker.", "state-error");
    }
}

async function stopAttention() {
    try {
        const response = await fetch(`${API}/attention/stop`, { method: "POST" });
        const data = await response.json();
        
        if (attentionTimer) clearInterval(attentionTimer);
        attentionTimer = null;
        
        const results = data.last_results || {};
        const score = results.attention_score || 0;
        setResult("attentionResult", `Session Stopped. Final Attention Score: ${score}%`, "state-success");
        
        stopLocalVideo();
    } catch (err) {
        setResult("attentionResult", "Failed to stop attention tracker.", "state-error");
    }
}

async function checkAttentionStatus() {
    try {
        const response = await fetch(`${API}/attention/status`);
        const data = await response.json();
        
        if (data.active) {
            const results = data.results || {};
            const score = results.attention_score || 0;
            const label = score > 70 ? "Focused" : "Distracted";
            document.getElementById("attentionResult").innerHTML = `
                <div style="font-size: 1.2rem; font-weight: 800; color: ${score > 70 ? 'green' : 'red'}">
                    ${label} (${score}%)
                </div>
                <div class="muted">Live monitoring active...</div>
            `;
        }
    } catch (err) {
        console.error("Failed to check attention status", err);
    }
}

function startLocalVideo() {
    const video = document.getElementById("attentionVideo");
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        navigator.mediaDevices.getUserMedia({ video: true })
            .then(stream => {
                video.srcObject = stream;
                video.play();
            })
            .catch(err => {
                console.warn("Could not access local webcam for UI feedback:", err);
            });
    }
}

function stopLocalVideo() {
    const video = document.getElementById("attentionVideo");
    if (video.srcObject) {
        video.srcObject.getTracks().forEach(track => track.stop());
        video.srcObject = null;
    }
}