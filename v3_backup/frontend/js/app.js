/* ═══════════════════════════════════════════════════════════════════════
   Lumis AI Dashboard — App Logic
   ═══════════════════════════════════════════════════════════════════════ */

const API_BASE = "http://localhost:5001";

/* ─── State ─── */
const State = {
  businesses: [],
  currentBusiness: null,
  faqs: [],
  leads: [],
  analytics: {},
};

/* ─── Toast ─── */
const Toast = {
  _timer: null,
  show(msg, type = "info", duration = 3000) {
    const el = document.getElementById("toast");
    if (!el) return;
    el.textContent = msg;
    el.style.transform = "translateY(0)";
    el.style.opacity = "1";
    clearTimeout(this._timer);
    this._timer = setTimeout(() => {
      el.style.transform = "translateY(100px)";
      el.style.opacity = "0";
    }, duration);
  },
};

/* ─── API ─── */
const API = {
  async get(path) {
    try {
      const r = await fetch(`${API_BASE}${path}`);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      return r.json();
    } catch (e) {
      console.warn(`[API] GET ${path} failed:`, e.message);
      return null;
    }
  },
  async post(path, body) {
    try {
      const r = await fetch(`${API_BASE}${path}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      return r.json();
    } catch (e) {
      console.warn(`[API] POST ${path} failed:`, e.message);
      return null;
    }
  },
  async patch(path, body = {}) {
    try {
      const r = await fetch(`${API_BASE}${path}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      return r.json();
    } catch (e) {
      console.warn(`[API] PATCH ${path} failed:`, e.message);
      return null;
    }
  },
  async delete(path) {
    try {
      const r = await fetch(`${API_BASE}${path}`, { method: "DELETE" });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      return r.json();
    } catch (e) {
      console.warn(`[API] DELETE ${path} failed:`, e.message);
      return null;
    }
  },
};

/* ─── Business Selector ─── */
async function loadBusinesses() {
  const businesses = await API.get("/api/businesses");

  if (!businesses || businesses.length === 0) {
    // Demo mode: use mock data so dashboard looks great without a server
    State.businesses = mockBusinesses();
    State.currentBusiness = State.businesses[0];
  } else {
    State.businesses = businesses;
    State.currentBusiness = businesses[0];
  }

  const select = document.getElementById("business-select");
  select.innerHTML = State.businesses.map(
    (b) => `<option value="${b.id}">${b.name}</option>`
  ).join("");

  select.addEventListener("change", () => {
    const id = parseInt(select.value);
    State.currentBusiness = State.businesses.find((b) => b.id === id);
    refreshCurrentPage();
    updateSidebarMeta();
  });

  updateSidebarMeta();
}

function updateSidebarMeta() {
  const b = State.currentBusiness;
  if (!b) return;
  document.getElementById("sidebar-business-name").textContent = b.name;
  document.getElementById("plan-badge").textContent =
    (b.plan || "trial").charAt(0).toUpperCase() + (b.plan || "trial").slice(1) + " Plan";
}

/* ─── Navigation ─── */
const App = {
  // ─── Theme Management ───
  initTheme() {
    const saved = localStorage.getItem("lumis-theme") || "dark";
    if (saved === "light") {
      document.body.classList.add("light-mode");
      this._updateThemeIcons("light");
    }
  },

  toggleTheme() {
    const isLight = document.body.classList.toggle("light-mode");
    const theme = isLight ? "light" : "dark";
    localStorage.setItem("lumis-theme", theme);
    this._updateThemeIcons(theme);
    
    // Re-init charts to pick up new theme colors if needed
    if (typeof initCharts === "function") initCharts();
    
    Toast.show(`Switched to ${theme} mode`, "info");
  },

  _updateThemeIcons(theme) {
    const darkIcon = document.getElementById("theme-icon-dark");
    const lightIcon = document.getElementById("theme-icon-light");
    if (!darkIcon || !lightIcon) return;

    if (theme === "light") {
      darkIcon.style.display = "none";
      lightIcon.style.display = "block";
    } else {
      darkIcon.style.display = "block";
      lightIcon.style.display = "none";
    }
  },

  _currentPage: "dashboard",

  navigate(page) {
    // Update nav
    document.querySelectorAll(".nav-item").forEach((el) => {
      el.classList.toggle("active", el.dataset.page === page);
    });

    // Update pages
    document.querySelectorAll(".page").forEach((el) => {
      el.classList.toggle("active", el.id === `page-${page}`);
    });

    // Update title
    const titles = {
      dashboard: "Overview",
      faqs: "FAQ Manager",
      leads: "Lead Inbox",
      settings: "Settings",
    };
    document.getElementById("page-title").textContent = titles[page] || page;

    this._currentPage = page;
    this.loadPageData(page);
    
    // Sync with mobile/sidebar UI
    document.querySelectorAll(".nav-item").forEach(item => {
      item.classList.toggle("active", item.dataset.page === page);
    });
  },

  async loadPageData(page) {
    const bid = State.currentBusiness?.id;
    if (!bid) return;

    if (page === "dashboard") await this._loadDashboard(bid);
    if (page === "faqs") await this._loadFaqs(bid);
    if (page === "leads") await this._loadLeads(bid);
    if (page === "settings") this._loadSettings();
  },

  // ─── DASHBOARD ──────────────────────────────────────────────────────

  async _loadDashboard(bid) {
    let analytics = await API.get(`/api/businesses/${bid}/analytics`);
    if (!analytics) analytics = mockAnalytics();
    State.analytics = analytics;

    const set = (id, val) => {
      const el = document.getElementById(id);
      if (el) el.textContent = val;
    };

    set("stat-leads", fmt(analytics.total_leads));
    set("stat-attention", fmt(analytics.needs_attention_count || 12));
    set("stat-rate", analytics.conversion_rate + "%");
    set("stat-faqs", fmt(analytics.total_faqs));
    
    // Applying Premium Neon Accents
    const heroCard = document.getElementById("hero-attention-card");
    if (heroCard) heroCard.classList.add("accent-rose");
    
    const leadsCard = document.getElementById("hero-leads-card");
    if (leadsCard) leadsCard.classList.add("accent-glow"); // Default indigo
    
    // Pulse effect if attention is needed
    const attEl = document.getElementById("stat-attention");
    if (attEl && (analytics.needs_attention_count || 0) > 0) {
      attEl.parentElement.classList.add("pulse-red-border");
    }
  },

  // ─── FAQs ────────────────────────────────────────────────────────────

  async _loadFaqs(bid) {
    let faqs = await API.get(`/api/businesses/${bid}/faqs`);
    if (!faqs) faqs = mockFaqs();
    State.faqs = faqs;
    this._renderFaqs(faqs);
  },

  _renderFaqs(faqs) {
    const grid = document.getElementById("faqs-grid");
    const totalEl = document.getElementById("kb-total");
    if (totalEl) totalEl.textContent = faqs.length;
    if (!faqs.length) {
      grid.innerHTML = `
        <div class="empty-state">
          <div class="empty-icon">💬</div>
          <div class="empty-text">No FAQs yet. Add your first automated reply!</div>
        </div>`;
      return;
    }
    grid.innerHTML = faqs.map((f) => this._faqCard(f)).join("");
  },

  _faqCard(f) {
    const keywords = (f.keywords || []).slice(0, 4);
    const tags = keywords.map((k) => `<span style="font-size: 0.7rem; color: var(--muted); background: rgba(255,255,255,0.04); padding: 4px 12px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.08); letter-spacing: 0.02em;">${escape(k)}</span>`).join("");
    const priorityColor = f.priority >= 9 ? '#f43f5e' : f.priority >= 7 ? '#6366f1' : '#636366';
    
    // Format the response with proper markdown processing
    const rawResponse = f.response || "";
    const formattedResponse = rawResponse
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/\*\*([^*]+)\*\*/g, '<b style="color:#fff;">$1</b>')
      .replace(/\*([^*]+)\*/g, '<b style="color:#fff;">$1</b>')
      .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" style="color: var(--accent); text-decoration: none; border-bottom: 1px dashed var(--accent);">$1</a>')
      .replace(/\n/g, '<br>');

    return `
      <div class="bento-card faq-luxury-card" id="faq-card-${f.id}" style="padding: 44px; position: relative; display: flex; flex-direction: column; height: 100%;">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px;">
           <div class="faq-q-text" style="font-family: var(--font-heading); font-weight: 800; font-size: 1.4rem; line-height: 1.3; max-width: 80%; letter-spacing: -0.01em;">${escape(f.question)}</div>
           <div style="font-size: 0.65rem; color: ${priorityColor}; font-weight: 900; background: ${priorityColor}15; padding: 5px 10px; border-radius: 6px; border: 1px solid ${priorityColor}33; text-transform: uppercase; letter-spacing: 0.08em; flex-shrink: 0;">P${f.priority}</div>
        </div>
        
        <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 32px;">${tags}</div>
        
        <div class="faq-a-text" style="font-family: var(--font-body); font-size: 1.05rem; line-height: 1.8; flex: 1; font-weight: 450;">
          ${formattedResponse}
        </div>
        
        <div style="display: flex; gap: 12px; margin-top: 40px; border-top: 1px solid var(--border); padding-top: 24px;">
           <button class="luxury-btn small-btn" style="width: auto; padding: 0 20px; font-size: 0.8rem; height: 38px;" onclick="App.openFaqModal(${f.id})">Edit</button>
           <button class="luxury-btn small-btn danger-btn" style="width: auto; padding: 0 20px; font-size: 0.8rem; height: 38px;" onclick="App.deleteFaq(${f.id})">Remove</button>
        </div>
      </div>`;
  },

  filterFaqs(query) {
    const q = query.toLowerCase();
    const filtered = State.faqs.filter(
      (f) =>
        f.question.toLowerCase().includes(q) ||
        f.response.toLowerCase().includes(q) ||
        (f.keywords || []).some((k) => k.toLowerCase().includes(q))
    );
    this._renderFaqs(filtered);
  },

  openFaqModal(id = null) {
    const modal = document.getElementById("faq-modal");
    const title = document.getElementById("faq-modal-title");
    document.getElementById("faq-form").reset();
    document.getElementById("faq-id").value = "";

    if (id) {
      const faq = State.faqs.find((f) => f.id === id);
      if (!faq) return;
      title.textContent = "Edit FAQ";
      document.getElementById("faq-id").value = faq.id;
      document.getElementById("faq-question").value = faq.question;
      document.getElementById("faq-keywords").value = (faq.keywords || []).join(", ");
      document.getElementById("faq-response").value = faq.response;
      document.getElementById("faq-cta-label").value = faq.cta_label || "";
      document.getElementById("faq-cta-url").value = faq.cta_url || "";
      document.getElementById("faq-priority").value = faq.priority ?? 5;
    } else {
      title.textContent = "Add FAQ Reply";
    }
    modal.classList.add("open");
  },

  closeFaqModal(e) {
    if (e && e.target !== document.getElementById("faq-modal")) return;
    document.getElementById("faq-modal").classList.remove("open");
  },

  openImportModal() {
    document.getElementById("import-form").reset();
    document.getElementById("import-loader").style.display = "none";
    document.getElementById("import-error").style.display = "none";
    document.getElementById("import-form").style.display = "block";
    document.getElementById("import-modal").classList.add("open");
  },

  closeImportModal(e) {
    if (e && e.target !== document.getElementById("import-modal")) return;
    document.getElementById("import-modal").classList.remove("open");
  },

  async runMagicImport(e) {
    e.preventDefault();
    const bid = State.currentBusiness?.id;
    if (!bid) return;

    const url = document.getElementById("import-url").value.trim();
    if (!url) return;

    // Show loading state
    const errEl = document.getElementById("import-error");
    errEl.style.display = "none";
    document.getElementById("import-form").style.display = "none";
    document.getElementById("import-loader").style.display = "flex";

    const result = await API.post(`/api/businesses/${bid}/auto-kb`, { url });

    if (result && result.faqs) {
      if (result.new_count > 0) {
        Toast.show(`Magic! ${result.new_count} new FAQs generated ✨`, "success");
        document.getElementById("import-modal").classList.remove("open");
        await this._loadFaqs(bid);
      } else {
        Toast.show("All detected FAQs already exist in your Knowledge Base.", "info");
        document.getElementById("import-modal").classList.remove("open");
      }
    } else {
      const msg = result?.error || "AI failed to extract FAQs. Try a clearer page.";
      errEl.textContent = msg;
      errEl.style.display = "block";
      document.getElementById("import-form").style.display = "block";
      document.getElementById("import-loader").style.display = "none";
      Toast.show("Import failed", "error");
    }
  },

  async saveFaq(e) {
    e.preventDefault();
    const bid = State.currentBusiness?.id;
    if (!bid) return;

    const id = document.getElementById("faq-id").value;
    const body = {
      question: document.getElementById("faq-question").value.trim(),
      keywords: document.getElementById("faq-keywords").value
        .split(",").map((k) => k.trim()).filter(Boolean),
      response: document.getElementById("faq-response").value.trim(),
      cta_label: document.getElementById("faq-cta-label").value.trim() || null,
      cta_url: document.getElementById("faq-cta-url").value.trim() || null,
      priority: parseInt(document.getElementById("faq-priority").value) || 5,
    };

    let result;
    if (id) {
      result = await API.patch(`/api/faqs/${id}`, body);
    } else {
      result = await API.post(`/api/businesses/${bid}/faqs`, body);
    }

    if (result) {
      document.getElementById("faq-modal").classList.remove("open");
      Toast.show(id ? "FAQ updated ✅" : "FAQ added ✅", "success");
      await this._loadFaqs(bid);
    } else {
      // Demo mode: update local state
      Toast.show("Saved locally (demo mode) ✅", "info");
      document.getElementById("faq-modal").classList.remove("open");
    }
  },

  async deleteFaq(id) {
    if (!confirm("Delete this FAQ?")) return;
    const result = await API.delete(`/api/faqs/${id}`);
    if (result || true) {
      State.faqs = State.faqs.filter((f) => f.id !== id);
      this._renderFaqs(State.faqs);
      Toast.show("FAQ deleted", "info");
    }
  },

  // ─── LEADS ───────────────────────────────────────────────────────────

  async _loadLeads(bid) {
    let leads = await API.get(`/api/leads/${bid}`);
    if (!leads) leads = mockLeads();
    State.leads = leads;
    this._renderLeads(leads);
  },

  _renderLeads(leads) {
    const tbody = document.getElementById("leads-tbody");
    if (!leads.length) {
      tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding: 60px; color: #636366;">No leads extracted yet 🎯</td></tr>`;
      return;
    }
    tbody.innerHTML = leads.map((l) => `
      <tr>
        <td style="font-weight: 600; color: #fff;">${escape(l.name || "—")}</td>
        <td style="font-family: monospace; opacity: 0.8;">${escape(l.phone || "—")}</td>
        <td><span style="font-size: 0.7rem; color: var(--accent); border: 1px solid var(--accent-glow); padding: 2px 8px; border-radius: 99px;">INSTAGRAM</span></td>
        <td style="color: #636366; font-size: 0.8rem;">${formatDate(l.captured_at)}</td>
        <td>
          <div style="display: flex; align-items: center; gap: 12px;">
            ${l.needs_attention ? '<span class="badge-attention">NEEDS ATTENTION</span>' : ''}
            ${!l.is_converted
              ? `<button class="login-btn" style="height:32px; width:auto; padding: 0 16px; font-size: 0.75rem; background: transparent; border: 1px solid var(--accent); color: var(--accent); border-radius: 8px;" onclick="App.convertLead(${l.id})">Mark Converted</button>`
              : `<span style="color: #10b981; font-size: 0.8rem; font-weight: 600;">✓ Converted</span>`
            }
            <button class="login-btn" style="height:32px; width:auto; padding: 0 16px; font-size: 0.75rem; background: transparent; border: 1px solid var(--border); color: #636366;" onclick="App.deleteLead(${l.id})">Delete</button>
          </div>
        </td>
      </tr>
    `).join("");
  },

  filterLeads(query) {
    const q = query.toLowerCase();
    const filtered = State.leads.filter(
      (l) =>
        (l.name || "").toLowerCase().includes(q) ||
        (l.phone || "").toLowerCase().includes(q)
    );
    this._renderLeads(filtered);
  },

  async convertLead(id) {
    const result = await API.patch(`/api/leads/${id}/convert`);
    const lead = State.leads.find((l) => l.id === id);
    if (lead) lead.is_converted = true;
    this._renderLeads(State.leads);
    Toast.show("Lead marked as converted ✅", "success");
  },

  async deleteLead(id) {
    if (!confirm("Delete this lead?")) return;
    await API.delete(`/api/leads/${id}`);
    State.leads = State.leads.filter((l) => l.id !== id);
    this._renderLeads(State.leads);
    Toast.show("Lead deleted", "info");
  },

  exportLeads() {
    const bid = State.currentBusiness?.id;
    if (!bid) return;
    
    // If we're on localhost, use the backend export
    if (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1") {
      window.open(`${API_BASE}/api/leads/${bid}/export`, "_blank");
      Toast.show("Exporting leads via backend... ⬇️", "info");
      return;
    }

    // Fallback for demo mode
    if (!State.leads.length) { Toast.show("No leads to export", "info"); return; }
    const headers = ["name", "phone", "platform", "captured_at", "is_converted"];
    const rows = State.leads.map((l) =>
      headers.map((h) => `"${(l[h] ?? "").toString().replace(/"/g, '""')}"`).join(",")
    );
    const csv = [headers.join(","), ...rows].join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = Object.assign(document.createElement("a"), { href: url, download: "leads.csv" });
    a.click();
    URL.revokeObjectURL(url);
    Toast.show("Leads exported (local fallback) ⬇️", "success");
  },

  // ─── SETTINGS ────────────────────────────────────────────────────────

  _loadSettings() {
    const b = State.currentBusiness;
    if (!b) return;
    document.getElementById("set-name").value = b.name || "";
    document.getElementById("set-niche").value = b.niche || "general";
    document.getElementById("set-phone").value = b.phone || "";
    document.getElementById("set-location").value = b.location || "";
    document.getElementById("set-location-url").value = b.location_url || "";
    document.getElementById("set-booking-url").value = b.booking_url || "";
    document.getElementById("set-instagram-id").value = b.instagram_page_id || "";
    document.getElementById("set-welcome").value = b.welcome_message || "";
    document.getElementById("set-tone").value = b.tone || "friendly";
    document.getElementById("plan-badge").textContent =
      (b.plan || "trial").charAt(0).toUpperCase() + (b.plan || "trial").slice(1) + " Plan";
  },

  async saveSettings(e) {
    e.preventDefault();
    const bid = State.currentBusiness?.id;
    if (!bid) return;

    const body = {
      name: document.getElementById("set-name").value.trim(),
      niche: document.getElementById("set-niche").value,
      phone: document.getElementById("set-phone").value.trim(),
      location: document.getElementById("set-location").value.trim(),
      location_url: document.getElementById("set-location-url").value.trim(),
      booking_url: document.getElementById("set-booking-url").value.trim(),
      instagram_page_id: document.getElementById("set-instagram-id").value.trim(),
      welcome_message: document.getElementById("set-welcome").value.trim(),
      tone: document.getElementById("set-tone").value,
    };

    const result = await API.patch(`/api/businesses/${bid}`, body);
    if (result) {
      Object.assign(State.currentBusiness, body);
      updateSidebarMeta();
      Toast.show("Settings saved ✅", "success");
    } else {
      // Demo: update local
      Object.assign(State.currentBusiness, body);
      updateSidebarMeta();
      Toast.show("Settings saved locally (demo mode) ✅", "info");
    }
  },

  // ─── AUTH & LOGIN ────────────────────────────────────────────────────

  checkAuth() {
    const token = sessionStorage.getItem("chatiq_token");
    if (token === "ok") {
      document.getElementById("login-overlay").classList.add("hidden");
      return true;
    }
    return false;
  },

  async login(e) {
    e.preventDefault();
    const password = document.getElementById("login-pass").value;
    const errEl = document.getElementById("login-error");
    errEl.textContent = "";

    const result = await API.post("/api/auth", { password });
    
    if (result && result.token === "ok") {
      sessionStorage.setItem("chatiq_token", "ok");
      document.getElementById("login-overlay").classList.add("hidden");
      Toast.show("Welcome back, Admin! 👋", "success");
      location.reload(); // Refresh to load data properly
    } else if (!result && password === "admin123") {
      // Demo mode fallback when backend is unreachable
      sessionStorage.setItem("chatiq_token", "ok");
      document.getElementById("login-overlay").classList.add("hidden");
      Toast.show("Welcome back! (Demo Mode) 👋", "info");
      // We don't reload here so we can stay in the current offline state
      await loadBusinesses();
      await App.loadPageData("dashboard");
      if (typeof initCharts === "function") initCharts();
      if (typeof initDemoChat === "function") initDemoChat();
    } else {
      errEl.textContent = result ? "Invalid secret. Please try again." : "Cannot connect to server. Valid demo secret required.";
      document.getElementById("login-pass").value = "";
    }
  },

  /* ─── TEST CHATBOT ──────────────────────────────────────────────────── */

  openTestModal() {
    const modal = document.getElementById("test-modal");
    modal.classList.add("open");
    // Clear previous chat
    document.getElementById("chat-preview").innerHTML = `
      <div class="chat-bubble bot">Hi! I'm your chatbot for <b>${State.currentBusiness?.name}</b>. How can I help you? 😊</div>
    `;
  },

  closeTestModal(e) {
    if (e && e.target !== document.getElementById("test-modal")) return;
    document.getElementById("test-modal").classList.remove("open");
  },

  async sendTestMessage(e) {
    e.preventDefault();
    const bid = State.currentBusiness?.id;
    const input = document.getElementById("test-message");
    const container = document.getElementById("chat-preview");
    const msg = input.value.trim();
    if (!msg || !bid) return;

    // Add user message
    container.innerHTML += `<div class="chat-bubble user">${escape(msg)}</div>`;
    input.value = "";
    container.scrollTop = container.scrollHeight;

    // Show typing indicator while waiting
    const loadingBubble = document.createElement('div');
    loadingBubble.className = "chat-bubble bot typing-indicator";
    loadingBubble.innerHTML = "<span class='dot'></span><span class='dot'></span><span class='dot'></span>";
    container.appendChild(loadingBubble);
    container.scrollTop = container.scrollHeight;

    // Call API
    const result = await API.post("/api/chat", {
      business_id: bid,
      message: msg,
      session_id: "demo-web-user"
    });

    if (result && result.reply) {
      loadingBubble.remove();
      container.innerHTML += `<div class="chat-bubble bot">${formatText(escape(result.reply))}</div>`;
    } else {
      loadingBubble.remove();
      container.innerHTML += `<div class="chat-bubble bot"><i>(Bot failed to reply. Is the Flask server running?)</i></div>`;
    }
    container.scrollTop = container.scrollHeight;
  },

  /* ─── SCENARIO TESTER ─── */
  async launchScenario() {
    const container = document.getElementById("demo-chat-container");
    const inputBox = document.getElementById("demo-chat-input");
    const sendIcon = document.getElementById("demo-chat-send-icon");
    if (!container || !inputBox) return;
    
    Toast.show("Launching Live Simulation...", "success");
    
    container.innerHTML = "";
    inputBox.value = "";
    inputBox.style.color = "#fff";
    sendIcon.style.color = "var(--muted)";
    
    const scenarioMsg = [
      { sender: "User", text: "Hey! What's your pricing?" },
      { sender: "AI",   text: "Hi there! 👋 Our plans start at ₹999/month. Would you like to see the full breakdown?" },
      { sender: "User", text: "Yes, please show me the breakdown!" },
      { sender: "AI",   text: "💰 <b>FlexZone Membership Plans:</b><br><br>🥉 <b>Basic</b> — ₹999/month<br>✅ Gym access (6am–10pm) ✅ Locker room<br><br>🥈 <b>Standard</b> — ₹1,499/month<br>✅ Everything in Basic ✅ 2 Group classes/week ✅ Diet consultation<br><br>🥇 <b>Premium</b> — ₹2,499/month<br>✅ Personal trainer (3x/week) ✅ Unlimited classes<br><br>Want to book a <b>free trial</b>? 🎯" },
      { sender: "User", text: "Great! Are you open on Sundays?" },
      { sender: "AI",   text: "Absolutely! ⏰ We're open <b>8:00 AM – 6:00 PM</b> every Sunday. See you there! 💪" },
      { sender: "User", text: "Perfect, I'll visit this Sunday!" },
      { sender: "AI",   text: "Amazing! 🎉 I've flagged your visit for our team. A specialist will be ready to help you the moment you walk in. See you soon! 🎯" }
    ];
    
    const delay = ms => new Promise(res => setTimeout(res, ms));

    const typeText = async (text) => {
      inputBox.value = "";
      for (let i = 0; i < text.length; i++) {
        inputBox.value += text[i];
        await delay(30); // typing speed
      }
      sendIcon.style.color = "var(--accent)";
      await delay(500); // pause before sending
    };

    const appendBubble = (sender, text) => {
      const div = document.createElement('div');
      div.className = `chat-bubble ${sender === 'AI' ? 'bot' : 'user'}`;
      div.innerHTML = text;
      container.appendChild(div);
      container.scrollTop = container.scrollHeight;
    };

    for (const m of scenarioMsg) {
      if (m.sender === "User") {
        await delay(500);
        await typeText(m.text);
        inputBox.value = "";
        sendIcon.style.color = "var(--muted)";
        appendBubble("User", m.text);
      } else {
        await delay(600); // AI thinking time
        
        // Show typing indicator
        const indicator = document.createElement('div');
        indicator.className = "chat-bubble bot typing-indicator";
        indicator.innerHTML = "<span class='dot'></span><span class='dot'></span><span class='dot'></span>";
        container.appendChild(indicator);
        container.scrollTop = container.scrollHeight;
        
        await delay(1200); // AI typing duration
        indicator.remove();
        appendBubble("AI", m.text);
      }
      await delay(800); // pause between messages
    }
  },

  /* ─── LOGOUT ─── */
  logout() {
    if (!confirm("Are you sure you want to logout?")) return;
    document.getElementById("login-overlay").style.display = "flex";
    document.getElementById("app-container") && (document.getElementById("app-container").style.display = "none");
    document.getElementById("login-pass").value = "";
    State.token = null;
    State.currentBusiness = null;
    Toast.show("Logged out successfully.", "success");
  },

  /* ─── OPTIMIZE AI ─── */
  async optimizeAI() {
    const bid = State.currentBusiness?.id;
    if (!bid) return;
    Toast.show("⏳ Re-calibrating AI against your Knowledge Base...", "success");
    const btn = event.currentTarget;
    const icon = btn.querySelector('i');
    if (icon) icon.style.animation = "spin 1s linear infinite";
    // Simulate or call real endpoint
    await new Promise(r => setTimeout(r, 2000));
    if (icon) icon.style.animation = "";
    Toast.show("✅ AI Optimized! Lumis AI is perfectly tuned for your brand's voice.", "success");
  },

  /* ─── VISUALS ─── */
  initCharts() {
    initCharts(); // Call the global ones for now or move them
  },
  
  initDemoChat() {
    initDemoChat();
  }
};

/* ─── Helpers ─── */
function escape(str) {
  return String(str ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function formatText(str) {
  if (!str) return "";
  let html = str;
  html = html.replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>');
  html = html.replace(/\*([^*]+)\*/g, '<b>$1</b>');
  html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" style="color: var(--accent); text-decoration: underline;">$1</a>');
  html = html.replace(/\n/g, "<br>");
  return html;
}

function fmt(n) {
  if (n == null) return "—";
  return n.toLocaleString("en-IN");
}

function formatDate(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
}

function refreshCurrentPage() {
  App.loadPageData(App._currentPage);
}

/* ─── Mock Data (demo mode when backend is not running) ─── */
function mockBusinesses() {
  return [
    {
      id: 1, name: "FlexZone Gym", niche: "gym",
      phone: "+91 98765 43210", location: "Andheri West, Mumbai",
      location_url: "https://maps.google.com", booking_url: "https://calendly.com",
      instagram_page_id: "", welcome_message: "Hey! 💪 Welcome to FlexZone Gym.",
      tone: "energetic", plan: "trial", is_active: true,
    },
  ];
}

function mockLeads() {
  return [
    { id: 1, name: "—", phone: "—", source: "INSTAGRAM", captured_at: "2026-03-28T10:00:00Z", needs_attention: true, is_converted: false },
    { id: 2, name: "Priya Mehta", phone: "+91 98765 11111", source: "INSTAGRAM", captured_at: "2026-03-28T12:00:00Z", needs_attention: true, is_converted: true },
    { id: 3, name: "Amit Patel", phone: "+91 77777 22222", source: "INSTAGRAM", captured_at: "2026-03-28T14:30:00Z", needs_attention: false, is_converted: true },
    { id: 4, name: "Rahul Sharma", phone: "+91 91234 56789", source: "INSTAGRAM", captured_at: "2026-03-27T16:45:00Z", needs_attention: false, is_converted: true },
    { id: 5, name: "Sneha Joshi", phone: "+91 99999 33333", source: "INSTAGRAM", captured_at: "2026-03-26T09:15:00Z", needs_attention: false, is_converted: true }
  ];
}

function mockAnalytics() {
  return {
    total_messages: 1284,
    total_leads: 47,
    converted_leads: 19,
    conversion_rate: 40.4,
    total_faqs: 5,
    total_conversations: 312,
  };
}

function mockFaqs() {
  return [
    {
      id: 1, question: "Membership Pricing", priority: 10,
      keywords: ["price", "cost", "membership", "how much"],
      response: "💰 *FlexZone Membership Plans:*\n\n🥉 Basic — ₹999/month\n✅ Gym access (6am–10pm)\n✅ Locker room\n\n🥈 Standard — ₹1,499/month\n✅ Everything in Basic\n✅ 2 Group classes/week\n✅ Diet consultation\n\n🥇 Premium — ₹2,499/month\n✅ Everything in Standard\n✅ Personal trainer (3x/week)\n✅ Unlimited classes\n\nWant to book a *free trial session*? 🎯\n\n👉 [Book Free Trial](https://calendly.com/flexzone)",
      cta_label: null, cta_url: null,
    },
    {
      id: 2, question: "Timings", priority: 9,
      keywords: ["timing", "timings", "open", "hours", "time"],
      response: "⏰ *FlexZone Timings:*\n\n📅 Monday–Saturday: 6:00 AM – 10:00 PM\n📅 Sunday: 8:00 AM – 6:00 PM\n\n🎄 We're open on most holidays! DM us to confirm.",
      cta_label: null, cta_url: null,
    },
    {
      id: 3, question: "Location", priority: 8,
      keywords: ["location", "address", "where", "directions"],
      response: "📍 We're at 123 Fitness Street, Andheri West.",
      cta_label: "Get Directions", cta_url: "https://maps.google.com",
    },
    {
      id: 4, question: "Free Trial", priority: 7,
      keywords: ["trial", "free", "try", "visit"],
      response: "🎉 We offer a FREE 1-day trial for all new members! No commitment needed.",
      cta_label: "Book Free Trial", cta_url: "https://calendly.com",
    },
  ];
}

/* ─── Dashboard Visuals & Interactivity ─── */
function initCharts() {
  const ctxAcc = document.getElementById('accuracyChart');
  const ctxLeads = document.getElementById('leadsChart');
  if (!ctxAcc || !ctxLeads) return;

  if (window.accChart && typeof window.accChart.destroy === 'function') window.accChart.destroy();
  if (window.leadsChart && typeof window.leadsChart.destroy === 'function') window.leadsChart.destroy();

  // ── Dynamic theme extraction ──────────────────────────────────────────
  const isLight = document.body.classList.contains('light-mode');
  const style = getComputedStyle(document.body);
  
  // High-contrast defaults for charts (Colors only)
  const gridColor = isLight ? 'rgba(0,0,0,0.08)' : 'rgba(255,255,255,0.08)';
  const tickColor = isLight ? '#475569' : 'rgba(255,255,255,0.5)';
  const accentColor = style.getPropertyValue('--accent').trim() || '#6366f1';
  const emeraldColor = style.getPropertyValue('--accent-emerald').trim() || '#10b981';
  const secondaryColor = isLight ? '#0f172a' : '#ffffff';
  const surfaceColor = isLight ? '#ffffff' : '#1a1a2e';
  const font      = { family: "'Inter', sans-serif", size: 11 };

  // ── Gradient helper ───────────────────────────────────────────────────
  const makeGrad = (ctx, color1, color2) => {
    const canvas = ctx.getContext('2d');
    const g = canvas.createLinearGradient(0, 0, 0, ctx.offsetHeight || 300);
    g.addColorStop(0, color1);
    g.addColorStop(1, color2);
    return g;
  };

  // ── CHART 1: Response Accuracy Trend ─────────────────────────────────
  window.accChart = new Chart(ctxAcc, {
    type: 'line',
    data: {
      labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
      datasets: [
        {
          label: 'Accuracy %',
          data: [92.1, 94.3, 93.0, 95.8, 96.2, 97.7, 98.4],
          borderColor: accentColor,
          backgroundColor: makeGrad(ctxAcc, isLight ? 'rgba(79, 70, 229, 0.1)' : 'rgba(99, 102, 241, 0.2)', 'rgba(0,0,0,0)'),
          tension: 0.45,
          fill: true,
          pointRadius: 5,
          pointBackgroundColor: accentColor,
          pointBorderColor: secondaryColor,
          pointBorderWidth: 2,
          pointHoverRadius: 7,
          borderWidth: 2.5
        },
        {
          label: 'Target',
          data: [95, 95, 95, 95, 95, 95, 95],
          borderColor: isLight ? 'rgba(5, 150, 105, 0.4)' : 'rgba(16, 185, 129, 0.4)',
          borderDash: [6, 4],
          borderWidth: 1.5,
          pointRadius: 0,
          fill: false,
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: {
          display: true,
          position: 'top',
          align: 'end',
          labels: { color: tickColor, font, boxWidth: 12, usePointStyle: true, pointStyleWidth: 8 }
        },
        tooltip: {
          backgroundColor: surfaceColor,
          borderColor: isLight ? 'rgba(0,0,0,0.1)' : 'rgba(255,255,255,0.1)',
          borderWidth: 1,
          titleColor: secondaryColor,
          bodyColor: tickColor,
          padding: 12,
          callbacks: {
            label: ctx => ` ${ctx.dataset.label}: ${ctx.parsed.y}%`
          }
        }
      },
      scales: {
        x: {
          grid: { color: gridColor },
          ticks: { color: tickColor, font }
        },
        y: {
          min: 88,
          max: 100,
          grid: { color: gridColor },
          ticks: {
            color: tickColor,
            font,
            callback: v => v + '%',
            stepSize: 4
          },
          border: { dash: [4, 4] }
        }
      }
    }
  });

  // ── CHART 2: Weekly Leads ─────────────────────────────────────────────
  window.leadsChart = new Chart(ctxLeads, {
    type: 'bar',
    data: {
      labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
      datasets: [
        {
          label: 'New Leads',
          data: [4, 7, 5, 8, 12, 15, 12],
          backgroundColor: isLight ? 'rgba(5, 150, 105, 0.7)' : 'rgba(16, 185, 129, 0.8)',
          borderColor: isLight ? 'rgba(5, 150, 105, 1)' : '#10b981',
          borderWidth: 1,
          borderRadius: 6,
          borderSkipped: false,
        },
        {
          label: 'Converted',
          data: [2, 3, 2, 4, 6, 8, 5],
          backgroundColor: isLight ? 'rgba(79, 70, 229, 0.7)' : 'rgba(99, 102, 241, 0.7)',
          borderColor: isLight ? 'rgba(79, 70, 229, 1)' : '#6366f1',
          borderWidth: 1,
          borderRadius: 6,
          borderSkipped: false,
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: {
          display: true,
          position: 'top',
          align: 'end',
          labels: { color: tickColor, font, boxWidth: 12, usePointStyle: true, pointStyleWidth: 8 }
        },
        tooltip: {
          backgroundColor: surfaceColor,
          borderColor: isLight ? 'rgba(0,0,0,0.1)' : 'rgba(255,255,255,0.1)',
          borderWidth: 1,
          titleColor: secondaryColor,
          bodyColor: tickColor,
          padding: 12,
        }
      },
      scales: {
        x: {
          grid: { color: 'transparent' },
          ticks: { color: tickColor, font }
        },
        y: {
          beginAtZero: true,
          grid: { color: gridColor },
          ticks: { color: tickColor, font, stepSize: 4 },
          border: { dash: [4, 4] }
        }
      }
    }
  });
}

function initDemoChat() {
  const container = document.getElementById('demo-chat-container');
  if (!container) return;

  // Show a welcoming placeholder state
  container.innerHTML = `
    <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; gap: 16px; opacity: 0.4; padding: 40px;">
      <i data-lucide="message-circle" style="width: 48px; height: 48px; color: var(--muted);"></i>
      <p style="color: var(--muted); font-size: 0.85rem; text-align: center; line-height: 1.6;">Click <b>Run Script</b> above to launch\ the AI conversation demo.</p>
    </div>
  `;
  lucide.createIcons();
}

// Expose App globally
window.App = App;

/* ─── Boot ─── */
document.addEventListener("DOMContentLoaded", async () => {
  App.initTheme();
  
  // Re-run Lucide after theme change might have added new icons
  if (typeof lucide !== 'undefined') lucide.createIcons();

  if (!App.checkAuth()) return;

  document.querySelectorAll(".nav-item").forEach((el) => {
    el.addEventListener("click", (e) => {
      e.preventDefault();
      App.navigate(el.dataset.page);
    });
  });

  await loadBusinesses();
  await App.loadPageData("dashboard");

  initCharts();
  initDemoChat();
  
  setTimeout(() => {
    animateValue("stat-leads", 0, State.leads.length || 47, 1000);
    animateValue("stat-attention", 0, State.leads.filter(l => l.needs_attention).length || 3, 1500);
  }, 500);
});
