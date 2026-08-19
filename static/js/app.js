/**
 * COMPETITOR RADAR — FRONTEND APPLICATION CONTROLLER
 * Single-Page Client Application connecting strictly via secure /api/competitor-radar endpoint
 */

document.addEventListener("DOMContentLoaded", () => {
  // Global Application State
  const state = {
    sessionId: null,
    companyData: null,
    discoveredCompetitors: [],
    selectedCompetitor: null,
    analysisResult: null
  };

  // DOM Elements
  const prefillBtn = document.getElementById("prefill-btn");
  const scanForm = document.getElementById("scan-form");
  const scanBtn = document.getElementById("scan-btn");
  const scanLoading = document.getElementById("scan-loading");
  const scanError = document.getElementById("scan-error");

  const competitorsSection = document.getElementById("competitors");
  const competitorCardsGrid = document.getElementById("competitor-cards-grid");

  const analysisSection = document.getElementById("analysis-form");
  const selectedCompHeader = document.getElementById("selected-comp-header");
  const observationForm = document.getElementById("observation-form");
  const analyzeBtn = document.getElementById("analyze-btn");
  const analyzeLoading = document.getElementById("analyze-loading");
  const analyzeError = document.getElementById("analyze-error");

  const intelligenceSection = document.getElementById("intelligence");
  const intelligenceContent = document.getElementById("intelligence-content");

  const responsesSection = document.getElementById("responses");
  const responsesGrid = document.getElementById("responses-grid");
  const companyTargetSpan = document.getElementById("company-target-span");

  // Helper: Smooth Scroll
  function scrollToSection(sectionId) {
    const el = document.getElementById(sectionId);
    if (el) {
      el.scrollIntoView({ behavior: "smooth" });
    }
  }

  // 1. Prefill PayFlow Demo Data
  if (prefillBtn) {
    prefillBtn.addEventListener("click", () => {
      document.getElementById("company_name").value = "PayFlow";
      document.getElementById("what_we_do").value = "Instant bank-to-bank transfers and small-business payouts.";
      document.getElementById("target_customers").value = "Consumers, freelancers and small businesses.";
      document.getElementById("region").value = "India, expanding to Southeast Asia.";
      document.getElementById("differentiator").value = "Sub-second settlement using direct bank rail integration with no wallet.";
    });
  }

  // 2. Handle Competitor Scan (Discovery Stage)
  if (scanForm) {
    scanForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      
      const company_name = document.getElementById("company_name").value.trim() || "PayFlow";
      const what_we_do = document.getElementById("what_we_do").value.trim();
      const target_customers = document.getElementById("target_customers").value.trim();
      const region = document.getElementById("region").value.trim();
      const differentiator = document.getElementById("differentiator").value.trim();

      state.companyData = { company_name, what_we_do, target_customers, region, differentiator };
      if (companyTargetSpan) companyTargetSpan.textContent = company_name;

      // UI Loading State
      scanForm.style.display = "none";
      scanError.style.display = "none";
      scanLoading.style.display = "block";

      try {
        const response = await fetch("/api/competitor-radar", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            action: "discover",
            session_id: state.sessionId,
            company_name,
            what_we_do,
            target_customers,
            region,
            differentiator
          })
        });

        const data = await response.json();
        scanLoading.style.display = "none";

        if (!response.ok || !data.success) {
          throw new Error(data.error || "Unable to complete the competitor scan.");
        }

        state.sessionId = data.session_id;
        state.discoveredCompetitors = data.competitors || [];

        // Render Results
        renderCompetitorCards(state.discoveredCompetitors, data.raw_text);
        competitorsSection.style.display = "block";
        scrollToSection("competitors");

      } catch (err) {
        scanLoading.style.display = "none";
        scanError.style.display = "block";
        scanForm.style.display = "block";
        document.getElementById("scan-error-msg").textContent = err.message || "Unable to complete the competitor analysis.";
      }
    });
  }

  // Render Competitor Cards
  function renderCompetitorCards(competitors, rawText = "") {
    competitorCardsGrid.innerHTML = "";

    if (!competitors || competitors.length === 0) {
      competitorCardsGrid.innerHTML = `
        <div style="grid-column: span 3;" class="error-card">
          <div class="error-title">No reliable competitors found</div>
          <p class="error-desc" style="margin-bottom: 16px;">No active competitors matched the provided market description or the agent output could not be parsed automatically.</p>
          ${rawText ? `
            <div style="margin-top: 16px; text-align: left; background: rgba(0,0,0,0.4); border: 1px solid var(--border-muted); border-radius: var(--radius-lg); padding: 16px;">
              <div style="font-size: 0.75rem; color: var(--accent-lime); font-weight: 700; margin-bottom: 8px;">RAW LYZR AGENT RESPONSE:</div>
              <pre style="font-size: 0.85rem; color: var(--text-secondary); white-space: pre-wrap; word-break: break-word;">${escapeHtml(rawText)}</pre>
            </div>
          ` : ''}
          <div style="margin-top: 20px;">
            <button type="button" onclick="document.getElementById('scan-form').dispatchEvent(new Event('submit'))" class="btn-primary">
              ↻ RETRY DISCOVERY SCAN
            </button>
          </div>
        </div>
      `;
      return;
    }

    competitors.forEach((comp, idx) => {
      const card = document.createElement("div");
      card.className = "comp-result-card";
      card.dataset.index = idx;

      card.innerHTML = `
        <div>
          <div class="comp-header">
            <h3 class="comp-name">${escapeHtml(comp.name)}</h3>
            <span class="badge ${comp.confidence === 'HIGH' ? 'badge-lime' : 'badge-muted'}">${escapeHtml(comp.confidence || 'HIGH')} CONFIDENCE</span>
          </div>
          <p class="comp-why">${escapeHtml(comp.why)}</p>
        </div>
        <div>
          <div class="comp-meta">
            <span>📍 ${escapeHtml(comp.region || 'Regional')}</span>
            <span>🏷️ ${escapeHtml(comp.category || 'Competitor')}</span>
          </div>
          <button class="btn-secondary track-btn" style="width: 100%; justify-content: center;">
            TRACK THIS COMPETITOR
          </button>
        </div>
      `;

      card.querySelector(".track-btn").addEventListener("click", () => {
        selectCompetitor(idx, card);
      });

      competitorCardsGrid.appendChild(card);
    });
  }

  // Human Competitor Selection Handler
  function selectCompetitor(index, selectedCardEl) {
    state.selectedCompetitor = state.discoveredCompetitors[index];

    // Highlight Card
    document.querySelectorAll(".comp-result-card").forEach(c => c.classList.remove("selected-card"));
    selectedCardEl.classList.add("selected-card");

    // Update Section 6 Analysis Form
    selectedCompHeader.textContent = `Selected Competitor: ${state.selectedCompetitor.name}`;
    document.getElementById("selected-comp-name-input").value = state.selectedCompetitor.name;

    analysisSection.style.display = "block";
    scrollToSection("analysis-form");
  }

  // 3. Handle Competitor Analysis Stage
  if (observationForm) {
    observationForm.addEventListener("submit", async (e) => {
      e.preventDefault();

      const competitor_name = state.selectedCompetitor ? state.selectedCompetitor.name : "Cashfree Payments";
      const previous_payout_fee = document.getElementById("previous_payout_fee").value.trim();
      const previous_settlement = document.getElementById("previous_settlement").value.trim();
      const previous_service = document.getElementById("previous_service").value.trim();
      const other_observation = document.getElementById("other_observation").value.trim();

      observationForm.style.display = "none";
      analyzeError.style.display = "none";
      analyzeLoading.style.display = "block";

      try {
        const response = await fetch("/api/competitor-radar", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            action: "analyze",
            session_id: state.sessionId,
            company_name: state.companyData?.company_name || "PayFlow",
            what_we_do: state.companyData?.what_we_do,
            competitor_name,
            previous_payout_fee,
            previous_settlement,
            previous_service,
            other_observation
          })
        });

        const data = await response.json();
        analyzeLoading.style.display = "none";

        if (!response.ok || !data.success) {
          throw new Error(data.error || "Unable to complete the competitor analysis.");
        }

        state.analysisResult = data.analysis;
        renderChangeDetection(state.analysisResult, competitor_name);

        intelligenceSection.style.display = "block";
        scrollToSection("intelligence");

        // CHANGE DETECTED Rule
        if (state.analysisResult.change_detected) {
          renderResponseOptions(state.analysisResult.response_options || []);
          responsesSection.style.display = "block";
        } else {
          responsesSection.style.display = "none";
        }

      } catch (err) {
        analyzeLoading.style.display = "none";
        analyzeError.style.display = "block";
        observationForm.style.display = "block";
        document.getElementById("analyze-error-msg").textContent = err.message || "Unable to complete the competitor analysis.";
      }
    });
  }

  // Render Change Detection Section
  function renderChangeDetection(analysis, compName) {
    if (!analysis.change_detected) {
      intelligenceContent.innerHTML = `
        <div class="analysis-report-card">
          <div class="status-hero-banner">
            <div>
              <span class="eyebrow" style="margin-bottom: 8px;">OBSERVATION REPORT</span>
              <div class="status-badge-large" style="color: var(--text-secondary);">
                <span>NO MATERIAL CHANGE</span>
              </div>
            </div>
            <span class="badge badge-muted">COMPETITOR: ${escapeHtml(compName)}</span>
          </div>
          <div style="padding: 24px 0;">
            <p style="font-size: 1.15rem; color: var(--text-secondary);">
              No meaningful competitive change was detected between the previous benchmark and current market observations for <strong>${escapeHtml(compName)}</strong>. No response options are recommended at this time.
            </p>
          </div>
        </div>
      `;
      return;
    }

    intelligenceContent.innerHTML = `
      <div class="analysis-report-card">
        <div class="status-hero-banner">
          <div>
            <span class="eyebrow" style="margin-bottom: 8px;">AI ANALYSIS</span>
            <div class="status-badge-large accent-text">
              <span>MATERIAL CHANGE DETECTED</span>
            </div>
          </div>
          <span class="badge badge-lime">TARGET: ${escapeHtml(compName)}</span>
        </div>

        <div class="report-grid">
          <div class="report-block">
            <h4>WHAT CHANGED</h4>
            <p>${escapeHtml(analysis.what_changed)}</p>
          </div>

          <div class="report-block">
            <h4>WHY IT MATTERS</h4>
            <p>${escapeHtml(analysis.why_it_matters)}</p>
          </div>

          <div class="report-block">
            <h4>ASSESSMENT</h4>
            <p>${escapeHtml(analysis.assessment)}</p>
          </div>

          <div class="report-block">
            <h4>CURRENT FINDINGS</h4>
            <p>${escapeHtml(analysis.current_findings)}</p>
          </div>
        </div>
      </div>
    `;
  }

  // Render Response Options Cards
  function renderResponseOptions(options) {
    responsesGrid.innerHTML = "";

    if (!options || options.length === 0) {
      responsesGrid.innerHTML = `
        <div style="grid-column: span 3;" class="editorial-card">
          <h4 class="card-title">Hold & Monitor</h4>
          <p class="card-body">Continue observing market shifts without immediate position execution.</p>
        </div>
      `;
      return;
    }

    options.forEach((opt, idx) => {
      const card = document.createElement("div");
      card.className = `option-card ${opt.is_hold_and_monitor ? 'hold-option' : ''}`;

      card.innerHTML = `
        <div>
          <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;">
            <span class="step-label">PATH 0${idx + 1}</span>
            ${opt.is_hold_and_monitor ? '<span class="badge badge-muted">RECOMMENDED BASELINE</span>' : ''}
          </div>
          <h3 class="option-title">${escapeHtml(opt.title)}</h3>
          <p class="option-desc">${escapeHtml(opt.description)}</p>
        </div>
        <div>
          <div class="option-section-title">WHY IT MAKES SENSE</div>
          <p class="option-reasoning">${escapeHtml(opt.why_it_makes_sense)}</p>
          
          ${opt.risk_consideration ? `
            <div class="option-section-title">RISK / CONSIDERATION</div>
            <p class="option-risk">${escapeHtml(opt.risk_consideration)}</p>
          ` : ''}
        </div>
      `;

      responsesGrid.appendChild(card);
    });
  }

  // Helper: HTML Escaping
  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }
});
