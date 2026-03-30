/* ═══════════════════════════════════════════════════════════════════════
   LUMIS AI — LANDING PAGE LOGIC
   ═══════════════════════════════════════════════════════════════════════ */

const API_BASE = window.location.origin;

// ─── UTILITIES ───
const Toast = {
    show(msg, type = "success") {
        const el = document.getElementById("toast");
        el.textContent = msg;
        el.style.background = type === "success" ? "#10b981" : type === "warning" ? "#f59e0b" : "#ef4444";
        el.style.color = "#fff";
        el.style.opacity = "1";
        el.style.transform = "translateY(0)";
        setTimeout(() => {
            el.style.opacity = "0";
            el.style.transform = "translateY(100px)";
        }, 3000);
    }
};

// ─── AUTHENTICATION ───
const App = {
    openAuthModal(mode = 'signup') {
        const overlay = document.getElementById("login-overlay");
        overlay.classList.remove("hidden");
        this.toggleAuthMode(mode);
    },

    closeAuthModal() {
        document.getElementById("login-overlay").classList.add("hidden");
    },

    toggleAuthMode(mode) {
        const loginForm = document.getElementById("login-form");
        const signupForm = document.getElementById("signup-form");
        if (mode === 'signup') {
            loginForm.style.display = "none";
            signupForm.style.display = "block";
        } else {
            loginForm.style.display = "block";
            signupForm.style.display = "none";
        }
    },

    async signup(e) {
        e.preventDefault();
        const name = document.getElementById("signup-name").value;
        const email = document.getElementById("signup-email").value;
        const password = document.getElementById("signup-pass").value;
        const errEl = document.getElementById("signup-error");
        errEl.textContent = "";

        try {
            const r = await fetch(`${API_BASE}/api/auth/signup`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ name, email, password })
            });
            const result = await r.json();

            if (r.ok && result.access_token) {
                sessionStorage.setItem("chatiq_token", result.access_token);
                sessionStorage.setItem("chatiq_user", JSON.stringify(result.user));
                Toast.show(`Welcome, ${result.user.name}! 👋`);
                setTimeout(() => window.location.href = "/dashboard", 1000);
            } else {
                errEl.textContent = result.error || "Signup failed.";
            }
        } catch (e) {
            errEl.textContent = "Server unreachable.";
        }
    },

    async login(e) {
        e.preventDefault();
        const email = document.getElementById("login-email").value;
        const password = document.getElementById("login-pass").value;
        const errEl = document.getElementById("login-error");
        errEl.textContent = "";

        try {
            const r = await fetch(`${API_BASE}/api/auth/login`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email, password })
            });
            const result = await r.json();

            if (r.ok && result.access_token) {
                sessionStorage.setItem("chatiq_token", result.access_token);
                sessionStorage.setItem("chatiq_user", JSON.stringify(result.user));
                Toast.show("Welcome back!");
                setTimeout(() => window.location.href = "/dashboard", 1000);
            } else {
                errEl.textContent = result.error || "Invalid credentials.";
            }
        } catch (e) {
            errEl.textContent = "Server unreachable.";
        }
    }
};

// ─── SCROLL EFFECTS ───
window.addEventListener('scroll', () => {
    const nav = document.getElementById("navbar");
    if (window.scrollY > 50) {
        nav.classList.add("scrolled");
    } else {
        nav.classList.remove("scrolled");
    }

    // Reveal elements
    const reveals = document.querySelectorAll(".reveal");
    reveals.forEach(el => {
        const rect = el.getBoundingClientRect();
        if (rect.top < window.innerHeight - 100) {
            el.classList.add("active");
        }
    });
});

// Trigger initial reveal
document.addEventListener("DOMContentLoaded", () => {
    const reveals = document.querySelectorAll(".reveal");
    reveals.forEach(el => {
        const rect = el.getBoundingClientRect();
        if (rect.top < window.innerHeight) {
            el.classList.add("active");
        }
    });
    
    // Check if already logged in
    const token = sessionStorage.getItem("chatiq_token");
    if (token) {
        // Option to redirect to dashboard immediately
        // window.location.href = "/dashboard";
    }
});
