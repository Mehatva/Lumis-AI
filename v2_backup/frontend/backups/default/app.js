/* ═══════════════════════════════════════════════════════════════════════
   ChatIQ Dashboard — App Logic
   ═══════════════════════════════════════════════════════════════════════ */

const API_BASE = "";

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
      dashboard: "Dashboard",
      faqs: "FAQ Manager",
      leads: "Lead Inbox",
      settings: "Settings",
    };
    document.getElementById("page-title").textContent = titles[page] || page;

    this._currentPage = page;
    this.loadPageData(page);
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

    set("stat-messages", fmt(analytics.total_messages));
    set("stat-leads", fmt(analytics.total_leads));
    set("stat-attention", fmt(analytics.needs_attention_count || 0));
    set("stat-rate", analytics.conversion_rate + "%");
    set("stat-faqs", fmt(analytics.total_faqs));
    
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
    const tags = keywords.map((k) => `<span style="font-size: 0.7rem; color: #636366; background: #121215; padding: 2px 8px; border-radius: 99px; border: 1px solid rgba(255,255,255,0.05);">${k}</span>`).join("");
    return `
      <div class="bento-card faq-luxury-card" id="faq-card-${f.id}">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
           <div class="faq-q">${escape(f.question)}</div>
           <div style="font-size: 0.7rem; color: #10b981; font-weight: 800; opacity: 0.6;">P${f.priority}</div>
        </div>
        <div style="display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 16px;">${tags}</div>
        <div class="faq-a">${escape(f.response)}</div>
        <div style="display: flex; gap: 8px; margin-top: auto; padding-top: 24px;">
           <button class="login-btn" style="background: #121215; color: #fff; width: auto; padding: 0 16px; font-size: 0.75rem; height: 32px;" onclick="App.openFaqModal(${f.id})">Refine</button>
           <button class="login-btn" style="background: transparent; border: 1px solid rgba(239, 68, 68, 0.2); color: #ef4444; width: auto; padding: 0 16px; font-size: 0.75rem; height: 32px;" onclick="App.deleteFaq(${f.id})">Delete</button>
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
              ? `<button class="login-btn" style="height:32px; width:auto; padding: 0 16px; font-size: 0.75rem; background: var(--accent); color: #000;" onclick="App.convertLead(${l.id})">Mark Converted</button>`
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
    } else {
      errEl.textContent = "Invalid secret. Please try again.";
      document.getElementById("login-pass").value = "";
    }
  },

  // ─── TEST CHATBOT ────────────────────────────────────────────────────

  testWebhook() {
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

    // Call API
    const result = await API.post("/api/chat", {
      business_id: bid,
      message: msg,
      session_id: "demo-web-user"
    });

    if (result && result.reply) {
      container.innerHTML += `<div class="chat-bubble bot">${result.reply.replace(/\n/g, "<br>")}</div>`;
    } else {
      container.innerHTML += `<div class="chat-bubble bot"><i>(Bot failed to reply. Is the Flask server running?)</i></div>`;
    }
    container.scrollTop = container.scrollHeight;
  },
};

/* ─── Helpers ─── */
function escape(str) {
  return String(str ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
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
      response: "💰 Our gym plans start from ₹999/month. We have Basic, Standard, and Premium tiers.",
      cta_label: "Book Free Trial", cta_url: "https://calendly.com",
    },
    {
      id: 2, question: "Timings", priority: 9,
      keywords: ["timing", "timings", "open", "hours"],
      response: "⏰ We're open Mon–Sat: 6am–10pm and Sunday: 8am–6pm.",
      cta_label: null, cta_url: null,
    },
    {
      id: 3, question: "Location", priority: 8,
      keywords: ["location", "address", "where", "directions"],
      response: "📍 We're at 123 Fitness Street, Andheri West, Mumbai.",
      cta_label: "Get Directions", cta_url: "https://maps.google.com",
    },
    {
      id: 4, question: "Free Trial", priority: 7,
      keywords: ["trial", "free", "try", "visit", "new"],
      response: "🎉 We offer a FREE 1-day trial for all new members! No commitment needed.",
      cta_label: "Book Free Trial", cta_url: "https://calendly.com",
    },
  ];
}

function mockLeads() {
  return [
    { id: 1, name: "Rahul Sharma", phone: "+91 91234 56789", platform: "instagram", captured_at: new Date(Date.now() - 86400000).toISOString(), is_converted: true },
    { id: 2, name: "Priya Mehta", phone: "+91 98765 11111", platform: "instagram", captured_at: new Date(Date.now() - 3600000 * 3).toISOString(), is_converted: false },
    { id: 3, name: "Amit Patel", phone: "+91 77777 22222", platform: "instagram", captured_at: new Date(Date.now() - 3600000 * 6).toISOString(), is_converted: false },
    { id: 4, name: "Sneha Joshi", phone: "+91 99999 33333", platform: "instagram", captured_at: new Date(Date.now() - 86400000 * 2).toISOString(), is_converted: true },
  ];
}

/* ─── Boot ─── */
document.addEventListener("DOMContentLoaded", async () => {
  // 1. Check Auth first
  if (!App.checkAuth()) return;

  // 2. Wire nav clicks
  document.querySelectorAll(".nav-item").forEach((el) => {
    el.addEventListener("click", (e) => {
      e.preventDefault();
      App.navigate(el.dataset.page);
    });
  });

  // 3. Load businesses, then load dashboard data
  await loadBusinesses();
  await App.loadPageData("dashboard");
});
