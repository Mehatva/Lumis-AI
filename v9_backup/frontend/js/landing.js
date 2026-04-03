/* ═══════════════════════════════════════════════════════════════════════
   LUMIS AI — LANDING PAGE LOGIC
   ═══════════════════════════════════════════════════════════════════════ */

const API_BASE = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1" 
  ? "http://localhost:5001" 
  : "";

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
        console.log("[App] Opening Auth Modal in mode:", mode);
        const overlay = document.getElementById("login-overlay");
        overlay.classList.remove("hidden");
        this.toggleAuthMode(mode);
    },

    closeAuthModal() {
        document.getElementById("login-overlay").classList.add("hidden");
    },

    toggleAuthMode(mode) {
        console.log("[App] Toggling Auth Mode to:", mode);
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
        console.log("[App] Signup Form Submitted");
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

            if (r.ok) {
                Toast.show("Account created! Please check your email for the verification link. 📧", "warning");
                // Do not redirect or log in automatically yet if verification is required
                this.toggleAuthMode('login');
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
                if (result.user && result.user.is_verified === false) {
                    Toast.show("Please verify your email to log in.", "warning");
                    return;
                }
                sessionStorage.setItem("chatiq_token", result.access_token);
                sessionStorage.setItem("chatiq_user", JSON.stringify(result.user));
                Toast.show("Welcome back!");
                this.closeAuthModal();
                this.checkSession(); // Update UI immediately
            } else {
                errEl.textContent = result.error || "Invalid credentials.";
            }
        } catch (e) {
            errEl.textContent = "Server unreachable.";
        }
    },

    async initGoogleAuth() {
        if (this._googleAuthInited) return; 
        
        if (!window.google || !window.google.accounts || !window.google.accounts.id) {
            console.log("[Google Auth] Waiting for SDK...");
            setTimeout(() => this.initGoogleAuth(), 500);
            return;
        }
        
        let clientId = "GOOGLE_CLIENT_ID_PLACEHOLDER"; 
        
        try {
            const r = await fetch(`${API_BASE}/api/auth/config`);
            if (r.ok) {
                const config = await r.json();
                if (config.google_client_id && !config.google_client_id.includes("PLACEHOLDER")) {
                    clientId = config.google_client_id;
                }
            }
        } catch (e) {
            console.warn("[Google Auth] Could not fetch config, using fallback.");
        }

        google.accounts.id.initialize({
            client_id: clientId,
            callback: this.handleGoogleSignIn.bind(this)
        });
        
        this.renderGoogleButtons();
        this._googleAuthInited = true;
    },

    renderGoogleButtons() {
        const loginContainer = document.getElementById("google-login-btn");
        const signupContainer = document.getElementById("google-signup-btn");
        
        const options = {
            theme: "outline",
            size: "large",
            width: "100%",
            height: 40, // Match our refined CSS
            shape: "rectangular"
        };
        
        if (loginContainer) {
            google.accounts.id.renderButton(loginContainer, { ...options, text: "signin_with" });
        }
        
        if (signupContainer) {
            google.accounts.id.renderButton(signupContainer, { ...options, text: "signup_with" });
        }
    },

    async handleGoogleSignIn(response) {
        console.log("Encoded JWT ID token: " + response.credential);
        const errEl = document.getElementById("login-error");
        errEl.textContent = "";

        try {
            const r = await fetch(`${API_BASE}/api/auth/google`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ credential: response.credential })
            });
            const result = await r.json();

            if (r.ok && result.access_token) {
                sessionStorage.setItem("chatiq_token", result.access_token);
                sessionStorage.setItem("chatiq_user", JSON.stringify(result.user));
                Toast.show(`Welcome, ${result.user.name}! 👋`);
                setTimeout(() => window.location.href = "/dashboard", 1000);
            } else {
                errEl.textContent = result.error || "Google login failed.";
            }
        } catch (e) {
            errEl.textContent = "Server unreachable.";
        }
    },

    async socialLogin(provider) {
        const errEl = document.getElementById("login-error");
        errEl.textContent = "";
        
        Toast.show(`${provider.charAt(0).toUpperCase() + provider.slice(1)} integration is in Demo Mode.`, "warning");
    },

    // ─── SESSION & UI ───
    async checkSession() {
        const token = sessionStorage.getItem("chatiq_token");
        const user = JSON.parse(sessionStorage.getItem("chatiq_user") || "null");
        
        if (!token || !user) {
            this.updateUIForGuest();
            return;
        }

        try {
            const r = await fetch(`${API_BASE}/api/dashboard/summary`, {
                headers: { "Authorization": `Bearer ${token}` }
            });
            const data = await r.json();
            
            const hasBusiness = data.businesses && data.businesses.length > 0;
            this.updateUIForUser(user, hasBusiness);
            this._hasBusiness = hasBusiness;
        } catch (e) {
            console.error("Session check failed:", e);
            this.updateUIForGuest();
        }
    },

    updateUIForGuest() {
        document.getElementById("nav-links-guest").classList.remove("hidden");
        document.getElementById("nav-links-user").classList.add("hidden");
        document.getElementById("hero-actions-guest").classList.remove("hidden");
        document.getElementById("hero-actions-user").classList.add("hidden");
    },

    updateUIForUser(user, hasBusiness) {
        document.getElementById("nav-links-guest").classList.add("hidden");
        document.getElementById("nav-links-user").classList.remove("hidden");
        document.getElementById("hero-actions-guest").classList.add("hidden");
        document.getElementById("hero-actions-user").classList.remove("hidden");
        
        document.getElementById("user-display-name").textContent = `Welcome, ${user.name || 'User'}`;
        
        const primaryBtn = document.getElementById("hero-primary-btn");
        if (hasBusiness) {
            primaryBtn.textContent = "Complete Your Profile";
            primaryBtn.onclick = () => window.location.href = "/dashboard";
        } else {
            primaryBtn.textContent = "Get Started Free";
            primaryBtn.onclick = () => this.openAuthModal('signup');
        }

        lucide.createIcons();
    },

    togglePassword(inputId) {
        const input = document.getElementById(inputId);
        if (!input) return;
        
        if (input.type === 'password') {
            input.type = 'text';
            // Update icon to eye-off if needed, but let's keep it simple for now
            // since we don't have a direct reference to the icon element easily here
            // without additional DOM traversal. 
        } else {
            input.type = 'password';
        }
    },

    logout() {
        sessionStorage.clear();
        window.location.reload();
    },

    handleHeroAction() {
        if (this._hasBusiness) {
            window.location.href = "/dashboard";
        } else {
            this.openAuthModal('signup');
        }
    },

    // ─── ONBOARDING WIZARD ───
    openOnboarding() {
        document.getElementById("onboarding-overlay").classList.remove("hidden");
        this.onboardShowStep(1);
    },

    closeOnboarding() {
        document.getElementById("onboarding-overlay").classList.add("hidden");
    },

    onboardShowStep(step) {
        // Hide all steps
        for (let i = 1; i <= 3; i++) {
            const el = document.getElementById(`onboard-step-${i}`);
            if (el) el.classList.add("hidden");
        }
        // Show target step
        const target = document.getElementById(`onboard-step-${step}`);
        if (target) target.classList.remove("hidden");
        lucide.createIcons();
    },

    async onboardCreateBusiness(e) {
        e.preventDefault();
        const name = document.getElementById("onboard-name").value;
        const niche = document.getElementById("onboard-niche").value;
        const token = sessionStorage.getItem("chatiq_token");

        try {
            const r = await fetch(`${API_BASE}/api/dashboard/business`, {
                method: "POST",
                headers: { 
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`
                },
                body: JSON.stringify({ name, niche })
            });
            if (r.ok) {
                Toast.show("Business profile established! ✨");
                this.onboardShowStep(2);
            } else {
                Toast.show("Failed to create business.", "error");
            }
        } catch (e) {
            Toast.show("Server error.", "error");
        }
    },

    onboardSelectPlan(plan) {
        Toast.show(`${plan.charAt(0).toUpperCase() + plan.slice(1)} plan selected!`);
        this.onboardShowStep(3);
    },

    onboardPrevStep(current, prev) {
        this.onboardShowStep(prev);
    },

    async onboardRunMagic(e) {
        e.preventDefault();
        const url = document.getElementById("onboard-url").value;
        const btn = document.getElementById("onboard-import-btn");
        const token = sessionStorage.getItem("chatiq_token");

        btn.disabled = true;
        btn.textContent = "AI is analyzing your brand...";

        try {
            const r = await fetch(`${API_BASE}/api/dashboard/train`, {
                method: "POST",
                headers: { 
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`
                },
                body: JSON.stringify({ url })
            });
            if (r.ok) {
                Toast.show("AI Setup Complete! Redirecting to your dashboard...");
                setTimeout(() => window.location.href = "/dashboard", 2000);
            } else {
                Toast.show("Training failed. Please try again.", "error");
                btn.disabled = false;
                btn.textContent = "Build My AI Assistant";
            }
        } catch (e) {
            Toast.show("Server error.", "error");
            btn.disabled = false;
        }
    },

    onboardComplete() {
        window.location.href = "/dashboard";
    },

    selectPlan(plan) {
        const token = sessionStorage.getItem("chatiq_token");
        if (!token) {
            this.openAuthModal('signup');
            return;
        }
        this.onboardSelectPlan(plan);
    },

    async onboardSelectPlan(plan) {
        const token = sessionStorage.getItem("chatiq_token");
        if (!token) return;

        Toast.show(`Initializing ${plan} setup...`, "info");
        
        try {
            // Fetch summary to get business_id
            const summaryRes = await fetch(`${API_BASE}/api/dashboard/summary`, {
                headers: { "Authorization": `Bearer ${token}` }
            });
            const summary = await summaryRes.json();
            const bid = summary.businesses?.[0]?.id;

            if (!bid) {
                Toast.show("Please complete your profile in the dashboard first.", "warning");
                setTimeout(() => window.location.href = "/dashboard", 2000);
                return;
            }

            const r = await fetch(`${API_BASE}/api/billing/create-order`, {
                method: "POST",
                headers: { 
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`
                },
                body: JSON.stringify({ business_id: bid, plan_type: plan })
            });
            const result = await r.json();

            if (!r.ok || result.error) throw new Error(result.error || "Order creation failed");

            const options = {
                "key": result.key,
                "amount": result.amount,
                "currency": result.currency,
                "name": "Lumis AI",
                "description": `${plan.charAt(0).toUpperCase() + plan.slice(1)} Plan Subscription`,
                "order_id": result.order_id,
                "handler": async (response) => {
                    const verRes = await fetch(`${API_BASE}/api/billing/verify-payment`, {
                        method: "POST",
                        headers: { 
                            "Content-Type": "application/json",
                            "Authorization": `Bearer ${token}`
                        },
                        body: JSON.stringify({
                            razorpay_order_id: response.razorpay_order_id,
                            razorpay_payment_id: response.razorpay_payment_id,
                            razorpay_signature: response.razorpay_signature,
                            business_id: bid,
                            plan_type: plan
                        })
                    });
                    const verResult = await verRes.json();
                    if (verRes.ok) {
                        Toast.show("Payment successful! Welcome to the premium tier. ✨", "success");
                        setTimeout(() => window.location.href = "/dashboard", 2000);
                    } else {
                        Toast.show(verResult.error || "Payment verification failed.", "error");
                    }
                },
                "theme": { "color": "#00d2ff" }
            };
            const rzp = new Razorpay(options);
            rzp.open();
        } catch (e) {
            Toast.show(e.message, "error");
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
    
    // Check for session status
    App.checkSession();

    // Check for URL parameters (Verification success/error)
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('verified') === 'true') {
        Toast.show("Email verified successfully! You can now log in.", "success");
        App.openAuthModal('login');
        // Clean up URL
        window.history.replaceState({}, document.title, window.location.pathname);
    } else if (urlParams.get('error') === 'invalid_token') {
        Toast.show("Invalid or expired verification link.", "error");
    }
});
