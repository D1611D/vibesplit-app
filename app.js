/**
 * VibeSplit - Modern Gen-Z Group Expense Splitter
 * Hybrid Multi-Computer Sync Engine with Email OTP Verification
 */

class VibeSplitApp {
  constructor() {
    this.token = localStorage.getItem("vibesplit_token") || "";
    this.theme = localStorage.getItem("vibesplit_theme") || "light";
    this.customApiUrl = localStorage.getItem("vibesplit_api_url") || "";
    this.currentUser = null;
    this.groups = [];
    this.invitations = [];
    this.activeGroup = null;
    this.activeGroupMembers = [];
    this.expenses = [];
    this.balances = null;
    this.currentTab = "expenses";
    this.splitType = "equal";
    this.activeRoastData = {
      debtor_name: "",
      creditor_name: "",
      amount: 0,
      expense_title: "",
      tone: "passive_aggressive",
      payment_handle: ""
    };
    this.activePayData = null;
    this.vibeChartInstance = null;
    this.audioCtx = null;
    this.pendingRegistration = null;
  }

  async init() {
    try {
      // 1. Initialize Theme
      this.setTheme(this.theme, false);

      // 2. Pre-fill custom backend URL if saved
      const urlInput = document.getElementById("custom-backend-url-input");
      if (urlInput && this.customApiUrl) {
        urlInput.value = this.customApiUrl;
      }

      // 3. Check Auth State
      if (!this.token) {
        this.showAuthView();
      } else {
        try {
          const user = await this.api("/api/auth/me");
          if (user && user.id) {
            this.currentUser = user;
            this.showDashboardView();
            await this.loadGroups();
            await this.loadInvitations();
          } else {
            this.showAuthView();
          }
        } catch (err) {
          this.showAuthView();
        }
      }

      this.refreshIcons();
    } catch (err) {
      console.error("Init error:", err);
      this.showAuthView();
    }
  }

  // --- Backend Settings & Multi-Computer Cloud URL ---
  saveCustomBackendUrl() {
    const input = document.getElementById("custom-backend-url-input");
    const val = (input?.value || "").trim().replace(/\/$/, "");
    if (val) {
      this.customApiUrl = val;
      localStorage.setItem("vibesplit_api_url", val);
      this.showToast(`Cloud backend connected to ${val} ⚡`, "success");
    } else {
      this.clearCustomBackendUrl();
    }
    this.closeModal("backend-settings-modal");
    // Reload data with new backend
    if (this.token) {
      this.init();
    }
  }

  clearCustomBackendUrl() {
    this.customApiUrl = "";
    localStorage.removeItem("vibesplit_api_url");
    const input = document.getElementById("custom-backend-url-input");
    if (input) input.value = "";
    this.showToast("Reset to default host", "info");
    this.closeModal("backend-settings-modal");
  }

  // --- Auth View & Dashboard View Toggles ---
  showAuthView() {
    const authView = document.getElementById("auth-view");
    const dashView = document.getElementById("dashboard-view");
    if (authView) authView.classList.remove("hidden");
    if (dashView) dashView.classList.add("hidden");
    this.refreshIcons();
  }

  showDashboardView() {
    const authView = document.getElementById("auth-view");
    const dashView = document.getElementById("dashboard-view");
    if (authView) authView.classList.add("hidden");
    if (dashView) dashView.classList.remove("hidden");
    this.updateHeaderUserProfile();
    this.refreshIcons();
  }

  setAuthMode(mode) {
    const loginForm = document.getElementById("login-form");
    const regContainer = document.getElementById("register-container");
    const loginTab = document.getElementById("auth-tab-login");
    const regTab = document.getElementById("auth-tab-register");

    if (mode === "login") {
      loginForm?.classList.remove("hidden");
      regContainer?.classList.add("hidden");
      if (loginTab) loginTab.className = "py-2 rounded-xl text-xs font-bold transition bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm";
      if (regTab) regTab.className = "py-2 rounded-xl text-xs font-bold transition text-slate-500 dark:text-slate-400 hover:text-slate-900";
    } else {
      loginForm?.classList.add("hidden");
      regContainer?.classList.remove("hidden");
      this.backToRegistrationStep1();
      if (regTab) regTab.className = "py-2 rounded-xl text-xs font-bold transition bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm";
      if (loginTab) loginTab.className = "py-2 rounded-xl text-xs font-bold transition text-slate-500 dark:text-slate-400 hover:text-slate-900";
    }
  }

  // --- Step 1: Send OTP to Email ---
  async handleSendRegistrationOTP(e) {
    e.preventDefault();
    const full_name = document.getElementById("reg-fullname").value.trim();
    const username = document.getElementById("reg-username").value.trim();
    const email = document.getElementById("reg-email").value.trim();
    const password = document.getElementById("reg-password").value;
    const persona = document.querySelector('input[name="reg-persona"]:checked')?.value || "Boba Baron 🧋";
    const payment_handle = document.getElementById("reg-payment-handle")?.value.trim() || "";

    const btn = document.getElementById("btn-send-otp");
    if (btn) btn.innerHTML = `<span>Sending Verification Code... ⏳</span>`;

    try {
      this.pendingRegistration = {
        full_name,
        username,
        email,
        password,
        persona,
        payment_handle
      };

      const res = await this.api("/api/auth/send-otp", {
        method: "POST",
        body: JSON.stringify({ email, full_name })
      });

      document.getElementById("register-step1-form")?.classList.add("hidden");
      document.getElementById("register-step2-otp")?.classList.remove("hidden");
      
      const sentText = document.getElementById("otp-sent-to-text");
      if (sentText) {
        sentText.innerHTML = `We sent a 6-digit code to <strong>${email}</strong>`;
      }

      if (res.dev_otp) {
        this.showToast(`Verification code sent! (Code: ${res.dev_otp}) 📧`, "info");
        const otpInp = document.getElementById("reg-otp-code");
        if (otpInp) otpInp.value = res.dev_otp;
      } else {
        this.showToast(`Verification code dispatched to ${email}! 📧`, "success");
      }

      document.getElementById("reg-otp-code")?.focus();
    } catch (err) {
      this.showToast(`Error: ${err.message}`, "error");
    } finally {
      if (btn) btn.innerHTML = `<span>Send Email Verification Code 📧</span>`;
    }
  }

  backToRegistrationStep1() {
    document.getElementById("register-step1-form")?.classList.remove("hidden");
    document.getElementById("register-step2-otp")?.classList.add("hidden");
  }

  async handleResendOTP() {
    if (!this.pendingRegistration || !this.pendingRegistration.email) {
      this.backToRegistrationStep1();
      return;
    }

    try {
      const res = await this.api("/api/auth/send-otp", {
        method: "POST",
        body: JSON.stringify({
          email: this.pendingRegistration.email,
          full_name: this.pendingRegistration.full_name
        })
      });

      if (res.dev_otp) {
        this.showToast(`New code sent! (Code: ${res.dev_otp}) 📧`, "info");
        const otpInp = document.getElementById("reg-otp-code");
        if (otpInp) otpInp.value = res.dev_otp;
      } else {
        this.showToast(`Fresh verification code sent to ${this.pendingRegistration.email}! 📧`, "success");
      }
    } catch (err) {
      this.showToast(`Error: ${err.message}`, "error");
    }
  }

  // --- Step 2: Verify OTP and Register Account ---
  async handleVerifyAndRegister(e) {
    e.preventDefault();
    const otp_code = document.getElementById("reg-otp-code").value.trim();

    if (!otp_code || otp_code.length < 6) {
      this.showToast("Please enter the complete 6-digit verification code", "error");
      return;
    }

    const btn = document.getElementById("btn-verify-otp");
    if (btn) btn.innerHTML = `<span>Verifying & Activating... ⏳</span>`;

    try {
      const regPayload = {
        ...this.pendingRegistration,
        otp_code
      };

      const res = await this.api("/api/auth/register", {
        method: "POST",
        body: JSON.stringify(regPayload)
      });

      this.token = res.access_token;
      localStorage.setItem("vibesplit_token", this.token);
      this.currentUser = res.user;

      this.showDashboardView();
      this.triggerConfetti();
      this.showToast(`Email verified! Welcome to your personal account ${this.currentUser.full_name}! 🚀`, "success");

      await this.loadGroups();
      await this.loadInvitations();
    } catch (err) {
      this.showToast(`Verification error: ${err.message}`, "error");
    } finally {
      if (btn) btn.innerHTML = `<span>Verify Code & Create Account ✨</span>`;
    }
  }

  async handleAuthSubmit(e, mode) {
    e.preventDefault();

    if (mode === "register") {
      return this.handleSendRegistrationOTP(e);
    }

    try {
      const username_or_email = document.getElementById("login-identifier").value.trim();
      const password = document.getElementById("login-password").value;

      const res = await this.api("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ username_or_email, password })
      });

      this.token = res.access_token;
      localStorage.setItem("vibesplit_token", this.token);
      this.currentUser = res.user;

      this.showDashboardView();
      this.triggerConfetti();
      this.showToast(`Welcome back, ${this.currentUser.full_name}! 🚀`, "success");

      await this.loadGroups();
      await this.loadInvitations();
    } catch (err) {
      this.showToast(`Login failed: ${err.message}`, "error");
    }
  }

  handleLogout() {
    this.token = "";
    localStorage.removeItem("vibesplit_token");
    this.currentUser = null;
    this.groups = [];
    this.activeGroup = null;
    this.showAuthView();
    this.showToast("Signed out of your personal account safely ✨", "info");
  }

  // --- Group Invitations & Notification System ---
  async loadInvitations() {
    if (!this.currentUser) return;
    try {
      this.invitations = await this.api("/api/invitations");
      this.renderInvitations();
    } catch (err) {
      console.error("Load invitations error:", err);
    }
  }

  renderInvitations() {
    const banner = document.getElementById("pending-invites-banner");
    const sBadge = document.getElementById("sidebar-invite-badge");
    const mBadge = document.getElementById("mobile-invite-badge");
    const listContainer = document.getElementById("invitations-list-container");

    const count = (this.invitations || []).length;

    // Badges update
    [sBadge, mBadge].forEach(b => {
      if (b) {
        if (count > 0) {
          b.textContent = count;
          b.classList.remove("hidden");
        } else {
          b.classList.add("hidden");
        }
      }
    });

    // Top Banner update
    if (banner) {
      if (count > 0) {
        banner.classList.remove("hidden");
        const first = this.invitations[0];
        const descEl = document.getElementById("pending-invites-desc");
        if (descEl) {
          descEl.innerHTML = `<strong>${first.inviter_name}</strong> invited you to join <strong>${first.group_emoji} ${first.group_name}</strong>${count > 1 ? ` (and ${count - 1} other groups)` : ''}!`;
        }
      } else {
        banner.classList.add("hidden");
      }
    }

    // Modal List update
    if (listContainer) {
      if (count === 0) {
        listContainer.innerHTML = `
          <div class="text-center py-8">
            <span class="text-3xl block mb-2">🎉</span>
            <div class="text-sm font-bold text-slate-800 dark:text-white">No pending invitations</div>
            <p class="text-xs text-slate-500 dark:text-slate-400 mt-1">You are up to date on all group tabs!</p>
          </div>
        `;
      } else {
        listContainer.innerHTML = this.invitations.map(inv => `
          <div class="p-3.5 rounded-2xl bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-white/5 space-y-3">
            <div class="flex items-start space-x-3">
              <span class="w-10 h-10 rounded-xl bg-violet-100 dark:bg-violet-900/40 text-violet-600 dark:text-violet-300 flex items-center justify-center text-xl shrink-0">
                ${inv.group_emoji}
              </span>
              <div class="flex-1 min-w-0">
                <h4 class="text-sm font-extrabold text-slate-900 dark:text-white truncate">${inv.group_name}</h4>
                <p class="text-[11px] text-slate-500 dark:text-slate-400 truncate">${inv.group_description || 'Group expense tab'}</p>
                <div class="text-[10px] text-violet-600 dark:text-violet-400 font-semibold mt-1">
                  Invited by ${inv.inviter_name} (@${inv.inviter_username})
                </div>
              </div>
            </div>

            <div class="flex items-center space-x-2 pt-1 border-t border-slate-200 dark:border-white/5">
              <button onclick="app.handleRespondInvitation(${inv.id}, 'accept')" class="flex-1 py-1.5 bg-gradient-to-r from-violet-600 to-pink-600 hover:from-violet-500 hover:to-pink-500 text-white rounded-xl text-xs font-bold transition shadow-sm">
                Accept & Join 🚀
              </button>
              <button onclick="app.handleRespondInvitation(${inv.id}, 'decline')" class="px-3 py-1.5 bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-300 rounded-xl text-xs font-bold transition">
                Decline
              </button>
            </div>
          </div>
        `).join("");
      }
    }

    this.refreshIcons();
  }

  async handleRespondInvitation(inviteId, action) {
    try {
      const res = await this.api(`/api/invitations/${inviteId}/respond`, {
        method: "POST",
        body: JSON.stringify({ action })
      });

      if (action === "accept") {
        this.triggerConfetti();
        this.showToast(res.message, "success");
        this.closeModal("invitations-modal");
        await this.loadGroups();
        if (res.group_id) {
          await this.changeActiveGroup(res.group_id);
        }
      } else {
        this.showToast("Invitation declined", "info");
      }

      await this.loadInvitations();
    } catch (err) {
      this.showToast(`Error: ${err.message}`, "error");
    }
  }

  // --- Theme Management ---
  setTheme(themeName, notify = true) {
    this.theme = themeName;
    localStorage.setItem("vibesplit_theme", themeName);

    const root = document.documentElement;
    root.classList.remove("dark", "pastel");

    if (themeName === "dark") {
      root.classList.add("dark");
    } else if (themeName === "pastel") {
      root.classList.add("pastel");
    }

    ["light", "dark", "pastel"].forEach(t => {
      const btn = document.getElementById(`theme-btn-${t}`);
      if (btn) {
        if (t === themeName) {
          btn.className = "flex-1 py-1.5 rounded-lg text-xs font-bold transition flex items-center justify-center space-x-1 bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm";
        } else {
          btn.className = "flex-1 py-1.5 rounded-lg text-xs font-bold transition flex items-center justify-center space-x-1 text-slate-500 dark:text-slate-400 hover:text-slate-900";
        }
      }
    });

    if (this.vibeChartInstance) {
      this.renderVibeChart(this.vibeChartBreakdown || {});
    }

    if (notify) {
      this.showToast(`Theme switched to ${themeName.toUpperCase()} ✨`, "info");
    }
  }

  toggleMobileDrawer(open) {
    const sidebar = document.getElementById("sidebar");
    const backdrop = document.getElementById("mobile-drawer-backdrop");
    if (!sidebar || !backdrop) return;

    if (open) {
      sidebar.classList.remove("-translate-x-full");
      backdrop.classList.remove("hidden");
    } else {
      sidebar.classList.add("-translate-x-full");
      backdrop.classList.add("hidden");
    }
  }

  // --- API Client (Direct Cloud API or Relative Backend with Fail-Safe Fallback) ---
  async api(endpoint, options = {}) {
    const baseUrl = this.customApiUrl || "";
    const url = baseUrl ? `${baseUrl.replace(/\/$/, '')}${endpoint}` : endpoint;

    const headers = {
      "Content-Type": "application/json",
      ...(this.token ? { "Authorization": `Bearer ${this.token}` } : {}),
      ...(options.headers || {})
    };

    const config = {
      ...options,
      headers
    };

    try {
      const res = await fetch(url, config);
      const contentType = res.headers.get("content-type") || "";

      // If hosted statically on GitHub Pages without a backend proxy, /api/ returns 404 HTML -> Fallback to client data engine
      if ((res.status === 404 || !contentType.includes("json")) && (window.location.origin.includes("github.io") || !baseUrl)) {
        return this.localDataEngine(endpoint, options);
      }

      if (res.status === 401) {
        localStorage.removeItem("vibesplit_token");
        this.token = "";
        this.showAuthView();
      }

      let data;
      if (contentType.includes("json")) {
        data = await res.json();
      } else {
        const text = await res.text();
        if (!res.ok) {
          throw new Error(`Server returned status ${res.status}. Please check your Cloud Backend Settings URL.`);
        }
        data = { message: text };
      }

      if (!res.ok) {
        let errorMsg = "API request failed";
        if (typeof data.detail === "string") {
          errorMsg = data.detail;
        } else if (Array.isArray(data.detail)) {
          errorMsg = data.detail.map(d => {
            const field = d.loc ? d.loc[d.loc.length - 1] : "";
            return field ? `${field}: ${d.msg}` : d.msg;
          }).join(", ");
        } else if (data.message) {
          errorMsg = data.message;
        } else if (typeof data.detail === "object" && data.detail !== null) {
          errorMsg = JSON.stringify(data.detail);
        }
        throw new Error(errorMsg);
      }
      return data;
    } catch (err) {
      if ((window.location.origin.includes("github.io") || !baseUrl) && (err.message.includes("Unexpected token") || err.message.includes("Failed to fetch") || err.message.includes("status 404") || err.message.includes("HTML"))) {
        return this.localDataEngine(endpoint, options);
      }
      console.error(`API [${endpoint}] Error:`, err);
      throw err;
    }
  }

  // --- Built-In Client-Side Engine for Static GitHub Pages Fallback ---
  localDataEngine(endpoint, options = {}) {
    const method = options.method || "GET";
    const body = options.body ? JSON.parse(options.body) : {};

    const getStore = (k, def = []) => {
      try { return JSON.parse(localStorage.getItem(`vibesplit_local_${k}`)) || def; } catch(e) { return def; }
    };
    const setStore = (k, v) => localStorage.setItem(`vibesplit_local_${k}`, JSON.stringify(v));

    let users = getStore("users", []);
    let groups = getStore("groups", []);
    let groupMembers = getStore("group_members", []);
    let expenses = getStore("expenses", []);
    let invitations = getStore("invitations", []);
    let otps = getStore("otps", []);

    // 1. Send OTP
    if (endpoint === "/api/auth/send-otp" && method === "POST") {
      const email = (body.email || "").toLowerCase().trim();
      const code = `${Math.floor(100000 + Math.random() * 900000)}`;
      otps.push({ email, code, expires: Date.now() + 600000 });
      setStore("otps", otps);
      return { message: `Verification code sent to ${email}`, email, dev_otp: code };
    }

    // 2. Verify OTP
    if (endpoint === "/api/auth/verify-otp" && method === "POST") {
      return { message: "Verification code confirmed! ✨", email: body.email, valid: true };
    }

    // 3. Auth Register
    if (endpoint === "/api/auth/register" && method === "POST") {
      const exists = users.find(u => u.username.toLowerCase() === body.username.toLowerCase() || u.email.toLowerCase() === body.email.toLowerCase());
      if (exists) throw new Error("Username or Email already registered");

      const newUser = {
        id: users.length + 1,
        username: body.username.toLowerCase(),
        email: body.email.toLowerCase(),
        password: body.password,
        full_name: body.full_name,
        persona: body.persona || "Boba Baron 🧋",
        payment_handle: body.payment_handle || "",
        avatar_url: `https://api.dicebear.com/7.x/bottts/svg?seed=${body.username}`,
        created_at: new Date().toISOString()
      };
      users.push(newUser);
      setStore("users", users);

      const token = `local-token-${newUser.id}-${Date.now()}`;
      return { access_token: token, token_type: "bearer", user: newUser };
    }

    // 4. Auth Login
    if (endpoint === "/api/auth/login" && method === "POST") {
      const identifier = (body.username_or_email || "").toLowerCase();
      const user = users.find(u => u.username.toLowerCase() === identifier || u.email.toLowerCase() === identifier);
      if (!user || user.password !== body.password) {
        throw new Error("Invalid username/email or password");
      }
      const token = `local-token-${user.id}-${Date.now()}`;
      return { access_token: token, token_type: "bearer", user };
    }

    // 5. Auth Me
    if (endpoint === "/api/auth/me") {
      if (this.currentUser) return this.currentUser;
      if (users.length > 0) return users[0];
      throw new Error("Not authenticated");
    }

    // 6. Groups
    if (endpoint === "/api/groups" && method === "GET") {
      const uid = this.currentUser?.id || 1;
      const userGroups = groups.filter(g => {
        const isMem = groupMembers.some(gm => gm.group_id === g.id && gm.user_id === uid);
        return isMem || g.created_by_user_id === uid;
      });
      return userGroups.map(g => ({
        ...g,
        member_count: groupMembers.filter(gm => gm.group_id === g.id).length || 1,
        total_expense: expenses.filter(e => e.group_id === g.id).reduce((sum, e) => sum + e.amount, 0),
        user_net_balance: 0.0
      }));
    }

    if (endpoint === "/api/groups" && method === "POST") {
      const uid = this.currentUser?.id || 1;
      const newGroup = {
        id: groups.length + 1,
        name: body.name,
        emoji: body.emoji || "🏖️",
        theme_color: body.theme_color || "violet",
        description: body.description || "",
        created_by_user_id: uid,
        created_at: new Date().toISOString()
      };
      groups.push(newGroup);
      setStore("groups", groups);

      groupMembers.push({ id: groupMembers.length + 1, group_id: newGroup.id, user_id: uid, role: "admin", joined_at: new Date().toISOString() });
      setStore("group_members", groupMembers);

      return { ...newGroup, member_count: 1, total_expense: 0, user_net_balance: 0 };
    }

    // 7. Group Members
    if (endpoint.startsWith("/api/groups/") && endpoint.endsWith("/members") && method === "GET") {
      const gid = parseInt(endpoint.split("/")[3]);
      const gMems = groupMembers.filter(gm => gm.group_id === gid);
      return gMems.map(gm => {
        const u = users.find(usr => usr.id === gm.user_id) || { full_name: "Member", username: "member", persona: "Member" };
        return {
          user_id: gm.user_id,
          role: gm.role,
          full_name: u.full_name,
          username: u.username,
          avatar_url: u.avatar_url || `https://api.dicebear.com/7.x/bottts/svg?seed=${u.username}`,
          persona: u.persona,
          payment_handle: u.payment_handle || "",
          joined_at: gm.joined_at
        };
      });
    }

    if (endpoint.startsWith("/api/groups/") && endpoint.endsWith("/members") && method === "POST") {
      const gid = parseInt(endpoint.split("/")[3]);
      const search = (body.username_or_email || "").toLowerCase().trim();
      let targetUser = users.find(u => u.username.toLowerCase() === search || u.email.toLowerCase() === search);
      
      if (!targetUser) {
        targetUser = {
          id: users.length + 1,
          username: search,
          email: `${search}@vibesplit.io`,
          password: "password123",
          full_name: search.charAt(0).toUpperCase() + search.slice(1),
          persona: "Vibe Explorer ✨",
          payment_handle: `${search}@upi`,
          avatar_url: `https://api.dicebear.com/7.x/bottts/svg?seed=${search}`,
          created_at: new Date().toISOString()
        };
        users.push(targetUser);
        setStore("users", users);
      }

      if (!groupMembers.some(gm => gm.group_id === gid && gm.user_id === targetUser.id)) {
        groupMembers.push({ id: groupMembers.length + 1, group_id: gid, user_id: targetUser.id, role: "member", joined_at: new Date().toISOString() });
        setStore("group_members", groupMembers);
      }

      return { message: `Added ${targetUser.full_name} to group`, user_id: targetUser.id };
    }

    // 8. Expenses
    if (endpoint.startsWith("/api/groups/") && endpoint.endsWith("/expenses") && method === "GET") {
      const gid = parseInt(endpoint.split("/")[3]);
      const gExpenses = expenses.filter(e => e.group_id === gid);
      return gExpenses.map(e => {
        const payer = users.find(u => u.id === e.paid_by_user_id) || { full_name: "Payer", username: "payer" };
        const creator = users.find(u => u.id === e.created_by_user_id) || payer;
        const splitsWithNames = (e.splits || []).map(s => {
          const u = users.find(usr => usr.id === s.user_id) || { full_name: "Member", username: "member" };
          return {
            ...s,
            full_name: u.full_name,
            username: u.username,
            avatar_url: u.avatar_url
          };
        });
        return {
          ...e,
          payer_name: payer.full_name,
          payer_username: payer.username,
          creator_username: creator.username,
          splits: splitsWithNames,
          reactions: e.reactions || []
        };
      });
    }

    if (endpoint === "/api/expenses" && method === "POST") {
      const uid = this.currentUser?.id || 1;
      const newExp = {
        id: expenses.length + 1,
        group_id: body.group_id,
        title: body.title,
        category: body.category || "food",
        amount: body.amount,
        currency: "₹",
        created_by_user_id: uid,
        paid_by_user_id: body.paid_by_user_id || uid,
        split_type: body.split_type || "equal",
        created_at: new Date().toISOString(),
        splits: (body.splits || []).map(s => ({
          user_id: s.user_id,
          owed_amount: s.owed_amount,
          split_value: s.split_value || 1.0,
          is_settled: (s.user_id === body.paid_by_user_id) ? 1 : 0
        })),
        reactions: []
      };
      expenses.unshift(newExp);
      setStore("expenses", expenses);
      return newExp;
    }

    // Default Fallback
    return [];
  }

  // --- Audio Synthesis Safe Guard ---
  playTone(type = "chime") {
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (!AudioCtx) return;
      if (!this.audioCtx) {
        this.audioCtx = new AudioCtx();
      }
      const ctx = this.audioCtx;
      if (ctx.state === "suspended") {
        ctx.resume().catch(() => {});
      }
      const now = ctx.currentTime;
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);

      if (type === "chime") {
        osc.type = "sine";
        osc.frequency.setValueAtTime(523.25, now);
        osc.frequency.exponentialRampToValueAtTime(1046.50, now + 0.3);
        gain.gain.setValueAtTime(0.2, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.4);
        osc.start(now);
        osc.stop(now + 0.4);
      } else if (type === "pop") {
        osc.type = "triangle";
        osc.frequency.setValueAtTime(440, now);
        osc.frequency.exponentialRampToValueAtTime(880, now + 0.1);
        gain.gain.setValueAtTime(0.15, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.1);
        osc.start(now);
        osc.stop(now + 0.1);
      }
    } catch (e) {}
  }

  // --- Toast Notifications ---
  showToast(message, type = "success") {
    const container = document.getElementById("toast-container");
    if (!container) return;

    const toast = document.createElement("div");
    const bgColors = {
      success: "bg-emerald-50 dark:bg-emerald-950/90 border-emerald-300 dark:border-emerald-500/50 text-emerald-900 dark:text-emerald-200",
      error: "bg-rose-50 dark:bg-rose-950/90 border-rose-300 dark:border-rose-500/50 text-rose-900 dark:text-rose-200",
      info: "bg-violet-50 dark:bg-violet-950/90 border-violet-300 dark:border-violet-500/50 text-violet-900 dark:text-violet-200",
      roast: "bg-pink-50 dark:bg-pink-950/90 border-pink-300 dark:border-pink-500/50 text-pink-900 dark:text-pink-200"
    };
    const icons = {
      success: "check-circle",
      error: "alert-circle",
      info: "info",
      roast: "flame"
    };

    toast.className = `glass-panel border px-4 py-3 rounded-2xl shadow-xl flex items-center space-x-3 text-xs font-semibold transform transition-all duration-300 pointer-events-auto ${bgColors[type] || bgColors.info}`;
    toast.innerHTML = `
      <i data-lucide="${icons[type] || 'bell'}" class="w-4 h-4 shrink-0"></i>
      <span>${message}</span>
    `;

    container.appendChild(toast);
    this.refreshIcons();

    setTimeout(() => {
      toast.classList.add("opacity-0", "translate-x-4");
      setTimeout(() => toast.remove(), 300);
    }, 3500);
  }

  triggerConfetti() {
    this.playTone("chime");
    try {
      if (typeof window.confetti === "function") {
        window.confetti({
          particleCount: 80,
          spread: 70,
          origin: { y: 0.6 },
          colors: ['#7C3AED', '#EC4899', '#06B6D4', '#10B981', '#FBBF24']
        });
      }
    } catch(e) {}
  }

  updateHeaderUserProfile() {
    if (!this.currentUser) return;
    const nameEl = document.getElementById("sidebar-user-name");
    const personaEl = document.getElementById("sidebar-user-persona");
    const avatarEl = document.getElementById("sidebar-user-avatar");

    if (nameEl) nameEl.textContent = this.currentUser.full_name;
    if (personaEl) personaEl.textContent = this.currentUser.persona || `@${this.currentUser.username}`;
    if (avatarEl) avatarEl.src = this.currentUser.avatar_url || `https://api.dicebear.com/7.x/bottts/svg?seed=${this.currentUser.username}`;
  }

  // --- Groups Management ---
  async loadGroups() {
    try {
      this.groups = await this.api("/api/groups");
      const groupSelect = document.getElementById("sidebar-group-select");
      if (groupSelect) {
        groupSelect.innerHTML = "";
      }

      if (!this.groups || this.groups.length === 0) {
        if (groupSelect) {
          const opt = document.createElement("option");
          opt.value = "";
          opt.textContent = "No Groups (Click + New)";
          groupSelect.appendChild(opt);
        }
        this.activeGroup = null;
        this.activeGroupMembers = [];
        this.expenses = [];
        this.balances = null;
        this.renderCleanDashboardEmptyState();
        return;
      }

      this.groups.forEach((g) => {
        const opt = document.createElement("option");
        opt.value = g.id;
        opt.textContent = `${g.emoji} ${g.name}`;
        if (groupSelect) groupSelect.appendChild(opt);
      });

      const activeId = this.activeGroup ? this.activeGroup.id : this.groups[0].id;
      const exists = this.groups.find(g => g.id === activeId);
      await this.changeActiveGroup(exists ? activeId : this.groups[0].id);
    } catch (err) {
      console.error("Load groups error:", err);
    }
  }

  renderCleanDashboardEmptyState() {
    const heroTitle = document.getElementById("group-hero-title");
    const heroEmoji = document.getElementById("group-hero-emoji");
    const heroDesc = document.getElementById("group-hero-desc");
    const memberPill = document.getElementById("group-member-pill");
    const mobileTitle = document.getElementById("mobile-header-title");
    const mobileEmoji = document.getElementById("mobile-header-emoji");

    if (heroTitle) heroTitle.textContent = "Welcome to VibeSplit ⚡";
    if (heroEmoji) heroEmoji.textContent = "✨";
    if (heroDesc) heroDesc.textContent = "Create your first group tab to start tracking & splitting expenses!";
    if (memberPill) memberPill.textContent = "0 Groups";
    if (mobileTitle) mobileTitle.textContent = "VibeSplit";
    if (mobileEmoji) mobileEmoji.textContent = "⚡";

    const totalEl = document.getElementById("stat-total-spent");
    const netEl = document.getElementById("stat-net-balance");
    const netSub = document.getElementById("stat-net-subtitle");
    const simCountEl = document.getElementById("stat-simplified-count");

    if (totalEl) totalEl.textContent = "₹0.00";
    if (netEl) {
      netEl.textContent = "₹0.00";
      netEl.className = "text-2xl font-display font-black text-slate-700 dark:text-slate-300 mt-1";
    }
    if (netSub) netSub.textContent = "Clean Slate ✨";
    if (simCountEl) simCountEl.textContent = "0 Debts";

    const countEl = document.getElementById("expenses-count-text");
    if (countEl) countEl.textContent = "(0 expenses)";

    const expensesList = document.getElementById("expenses-list");
    if (expensesList) {
      expensesList.innerHTML = `
        <div class="glass-panel rounded-3xl p-8 sm:p-12 text-center space-y-4 shadow-sm border border-dashed border-violet-300 dark:border-violet-500/30">
          <div class="w-16 h-16 rounded-3xl bg-gradient-to-tr from-violet-100 to-pink-100 dark:from-violet-950/40 dark:to-pink-950/40 text-violet-600 dark:text-violet-300 mx-auto flex items-center justify-center text-3xl shadow-sm">
            🚀
          </div>
          <div>
            <h3 class="font-display font-extrabold text-xl sm:text-2xl text-slate-900 dark:text-white">Your Dashboard is Fresh & Clean!</h3>
            <p class="text-xs sm:text-sm text-slate-500 dark:text-slate-400 mt-1.5 max-w-md mx-auto">
              You don't have any expense groups yet. Create one for your trip, house, dinner party, or project to get started!
            </p>
          </div>
          <div class="pt-2">
            <button onclick="app.openModal('create-group-modal')" class="px-6 py-3 bg-gradient-to-r from-violet-600 via-pink-600 to-rose-600 hover:from-violet-500 hover:to-pink-500 text-white font-display font-bold text-sm rounded-xl shadow-lg shadow-violet-500/25 transition hover:scale-105 active:scale-95 flex items-center space-x-2 mx-auto">
              <i data-lucide="plus" class="w-4 h-4"></i>
              <span>Create Your First Group 🚀</span>
            </button>
          </div>
        </div>
      `;
    }

    const memberBalances = document.getElementById("member-balances-list");
    if (memberBalances) {
      memberBalances.innerHTML = `
        <div class="p-8 text-center bg-slate-50 dark:bg-slate-900/60 rounded-2xl col-span-2 border border-slate-200 dark:border-white/5">
          <span class="text-3xl block mb-1">⚖️</span>
          <div class="text-sm font-bold text-slate-800 dark:text-white">No active group</div>
          <p class="text-xs text-slate-500 dark:text-slate-400 mt-1">Create a group to see member balances.</p>
        </div>
      `;
    }

    const simplifiedDebts = document.getElementById("simplified-debts-list");
    if (simplifiedDebts) {
      simplifiedDebts.innerHTML = `
        <div class="p-6 text-center bg-slate-50 dark:bg-slate-900/60 rounded-2xl border border-slate-200 dark:border-white/5">
          <span class="text-3xl block mb-1">✨</span>
          <h4 class="font-display font-bold text-sm text-slate-800 dark:text-white">Zero Debts</h4>
          <p class="text-xs text-slate-500 dark:text-slate-400 mt-1">Create a group and add expenses to start calculating debts.</p>
        </div>
      `;
    }

    const activityList = document.getElementById("activity-list");
    if (activityList) {
      activityList.innerHTML = `<p class="text-xs text-slate-400 text-center py-6">No activity recorded yet</p>`;
    }

    this.refreshIcons();
  }

  async changeActiveGroup(groupId) {
    if (!groupId) {
      this.activeGroup = null;
      this.renderCleanDashboardEmptyState();
      return;
    }
    groupId = parseInt(groupId);
    this.activeGroup = this.groups.find(g => g.id === groupId) || this.groups[0];
    
    const select = document.getElementById("sidebar-group-select");
    if (select) select.value = groupId;

    if (this.activeGroup) {
      const heroTitle = document.getElementById("group-hero-title");
      const heroEmoji = document.getElementById("group-hero-emoji");
      const heroDesc = document.getElementById("group-hero-desc");
      const memberPill = document.getElementById("group-member-pill");
      const mobileTitle = document.getElementById("mobile-header-title");
      const mobileEmoji = document.getElementById("mobile-header-emoji");

      if (heroTitle) heroTitle.textContent = this.activeGroup.name;
      if (heroEmoji) heroEmoji.textContent = this.activeGroup.emoji;
      if (heroDesc) heroDesc.textContent = this.activeGroup.description || "Group expenses and vibe tracker";
      if (memberPill) memberPill.textContent = `${this.activeGroup.member_count} Members`;
      if (mobileTitle) mobileTitle.textContent = this.activeGroup.name;
      if (mobileEmoji) mobileEmoji.textContent = this.activeGroup.emoji;
    }

    await this.refreshActiveGroupData();
  }

  async refreshActiveGroupData() {
    if (!this.activeGroup) return;
    const gid = this.activeGroup.id;

    try {
      this.activeGroupMembers = await this.api(`/api/groups/${gid}/members`);
      this.expenses = await this.api(`/api/groups/${gid}/expenses`);
      this.renderExpenses();

      this.balances = await this.api(`/api/groups/${gid}/balances`);
      this.renderBalances();
      this.renderSimplifiedDebts();

      this.updateHeroStats();
      await this.loadActivity();

      if (this.currentTab === "vibe-check") {
        await this.loadVibeCheck();
      }

      this.populateExpenseModalMembers();
      this.refreshIcons();
    } catch (err) {
      console.error("Refresh group data error:", err);
    }
  }

  updateHeroStats() {
    if (!this.balances) return;

    const totalEl = document.getElementById("stat-total-spent");
    if (totalEl) totalEl.textContent = `₹${this.balances.total_spent.toLocaleString('en-IN')}`;

    const userBal = this.balances.balances.find(b => b.user_id === this.currentUser?.id);
    const net = userBal ? userBal.net_balance : 0.0;
    const netEl = document.getElementById("stat-net-balance");
    const netSub = document.getElementById("stat-net-subtitle");

    if (netEl) {
      if (net > 0) {
        netEl.textContent = `+₹${Math.abs(net).toLocaleString('en-IN')}`;
        netEl.className = "text-2xl font-display font-black text-emerald-600 dark:text-emerald-400 mt-1";
        if (netSub) netSub.textContent = "You are owed";
      } else if (net < 0) {
        netEl.textContent = `-₹${Math.abs(net).toLocaleString('en-IN')}`;
        netEl.className = "text-2xl font-display font-black text-rose-600 dark:text-rose-400 mt-1";
        if (netSub) netSub.textContent = "You owe group";
      } else {
        netEl.textContent = "₹0.00";
        netEl.className = "text-2xl font-display font-black text-slate-700 dark:text-slate-300 mt-1";
        if (netSub) netSub.textContent = "All settled up ✨";
      }
    }

    const simCountEl = document.getElementById("stat-simplified-count");
    if (simCountEl) {
      const count = this.balances.simplified_debts ? this.balances.simplified_debts.length : 0;
      simCountEl.textContent = `${count} ${count === 1 ? 'Debt' : 'Debts'}`;
    }
  }

  async handleCreateGroup(e) {
    e.preventDefault();
    const name = document.getElementById("new-group-name").value;
    const emoji = document.getElementById("new-group-emoji").value;
    const theme_color = document.getElementById("new-group-theme").value;
    const description = document.getElementById("new-group-desc").value;

    try {
      const newGroup = await this.api("/api/groups", {
        method: "POST",
        body: JSON.stringify({ name, emoji, theme_color, description })
      });
      this.closeModal("create-group-modal");
      this.showToast(`Group '${name}' launched! 🚀`, "success");
      await this.loadGroups();
      await this.changeActiveGroup(newGroup.id);
    } catch (err) {
      this.showToast(`Error: ${err.message}`, "error");
    }
  }

  async handleAddMember(e) {
    e.preventDefault();
    const identifier = document.getElementById("add-member-identifier").value;
    if (!this.activeGroup) return;

    try {
      await this.api(`/api/groups/${this.activeGroup.id}/members`, {
        method: "POST",
        body: JSON.stringify({ username_or_email: identifier })
      });
      this.closeModal("add-member-modal");
      document.getElementById("add-member-identifier").value = "";
      this.showToast(`Invitation sent to '${identifier}'! 🔔`, "success");
      await this.refreshActiveGroupData();
    } catch (err) {
      this.showToast(`Error: ${err.message}`, "error");
    }
  }

  // --- Expenses Rendering & Strict Permissions ---
  renderExpenses() {
    const container = document.getElementById("expenses-list");
    const countEl = document.getElementById("expenses-count-text");
    if (!container) return;

    const filtered = this.getFilteredExpenses();
    if (countEl) countEl.textContent = `(${filtered.length} expenses)`;

    if (filtered.length === 0) {
      container.innerHTML = `
        <div class="glass-panel rounded-3xl p-10 text-center">
          <span class="text-4xl block mb-2">💸</span>
          <h4 class="font-display font-bold text-base text-slate-800 dark:text-white">No expenses recorded yet</h4>
          <p class="text-xs text-slate-500 dark:text-slate-400 mt-1 max-w-sm mx-auto">
            Click "+ Add Expense" or try "Magic AI Split" to add the first tab!
          </p>
          <button onclick="app.openModal('nlp-modal')" class="mt-4 px-4 py-2 bg-gradient-to-r from-violet-600 to-pink-600 rounded-xl text-xs font-bold text-white shadow-md transition hover:scale-105">
            Try Magic AI Split ✨
          </button>
        </div>
      `;
      this.refreshIcons();
      return;
    }

    const categoryIcons = {
      food: "🍕",
      drink: "🧋",
      travel: "✈️",
      party: "🪩",
      housing: "🏠",
      vibes: "✨",
      other: "📦"
    };

    container.innerHTML = filtered.map(exp => {
      const isCreator = (this.currentUser && exp.created_by_user_id === this.currentUser.id);
      const isPayer = (this.currentUser && exp.paid_by_user_id === this.currentUser.id);
      const canManage = isCreator || isPayer;

      const splitsHtml = (exp.splits || []).map(sp => {
        const isSettled = sp.is_settled;

        return `
          <div class="flex items-center justify-between p-2.5 rounded-xl bg-slate-50 dark:bg-slate-900/70 border ${isSettled ? 'border-emerald-300 dark:border-emerald-500/20 bg-emerald-50/50 dark:bg-emerald-950/10' : 'border-slate-200 dark:border-white/5'} text-xs">
            <div class="flex items-center space-x-2.5">
              <img src="${sp.avatar_url || `https://api.dicebear.com/7.x/bottts/svg?seed=${sp.username}`}" class="w-6 h-6 rounded-lg bg-violet-100 dark:bg-violet-900/40" />
              <div>
                <span class="font-bold text-slate-800 dark:text-white">${sp.full_name}</span>
                <span class="text-[10px] text-slate-500 dark:text-slate-400">(@${sp.username})</span>
              </div>
            </div>

            <div class="flex items-center space-x-2.5">
              <span class="font-mono font-bold ${isSettled ? 'text-slate-400 line-through' : 'text-slate-800 dark:text-slate-200'}">
                ₹${Number(sp.owed_amount || 0).toFixed(2)}
              </span>

              ${isSettled ? `
                <span class="px-2 py-0.5 rounded-full bg-emerald-100 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-300 text-[10px] font-bold flex items-center space-x-1">
                  <i data-lucide="check" class="w-3.5 h-3.5"></i>
                  <span>Settled</span>
                </span>
              ` : `
                <span class="px-2 py-0.5 rounded-full bg-amber-100 dark:bg-amber-500/20 text-amber-800 dark:text-amber-300 text-[10px] font-bold">
                  Unpaid
                </span>
              `}

              ${canManage ? `
                <button onclick="app.handleToggleSplitSettled(${exp.id}, ${sp.user_id})" class="p-1.5 rounded-lg text-xs font-semibold transition ${isSettled ? 'bg-slate-200 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white' : 'bg-emerald-600 hover:bg-emerald-500 text-white shadow'}" title="${isSettled ? 'Mark Unsettled' : 'Confirm Payment Received & Settle'}">
                  <i data-lucide="${isSettled ? 'rotate-ccw' : 'check-check'}" class="w-3.5 h-3.5"></i>
                </button>
              ` : ''}

              ${!isSettled && sp.user_id !== this.currentUser?.id ? `
                <button onclick="app.openRoastModal('${sp.full_name}', '${exp.payer_name}', ${sp.owed_amount}, '${exp.title.replace(/'/g, "\\'")}')" class="p-1.5 bg-pink-100 dark:bg-pink-900/30 text-pink-700 dark:text-pink-300 hover:bg-pink-200 rounded-lg transition" title="Send Gen-Z AI Nudge / Roast">
                  💅
                </button>
              ` : ''}
            </div>
          </div>
        `;
      }).join("");

      const reactionsHtml = (exp.reactions || []).map(r => `
        <button onclick="app.handleReact(${exp.id}, '${r.emoji}')" class="reaction-btn px-2 py-1 rounded-lg bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-white/10 text-xs flex items-center space-x-1 hover:border-violet-500 transition">
          <span>${r.emoji}</span>
          <span class="text-[10px] font-bold text-slate-700 dark:text-slate-300">${r.count}</span>
        </button>
      `).join("");

      return `
        <div class="glass-panel rounded-2xl sm:rounded-3xl p-4 sm:p-5 shadow-sm transition hover:border-violet-300 dark:hover:border-violet-500/40 space-y-3.5">
          
          <div class="flex items-start justify-between gap-3">
            <div class="flex items-start space-x-3">
              <div class="w-11 h-11 rounded-2xl bg-violet-50 dark:bg-violet-950/40 border border-violet-200 dark:border-violet-500/20 flex items-center justify-center text-xl shrink-0">
                ${categoryIcons[exp.category] || '💸'}
              </div>
              <div>
                <div class="flex items-center space-x-2 flex-wrap">
                  <h4 class="font-display font-extrabold text-base text-slate-900 dark:text-white leading-snug">${exp.title}</h4>
                  <span class="text-[10px] uppercase font-bold px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
                    ${exp.category}
                  </span>
                </div>

                <div class="flex flex-wrap items-center gap-1.5 mt-1 text-xs text-slate-500 dark:text-slate-400">
                  <span>Paid by <strong class="text-violet-700 dark:text-violet-300 font-bold">${exp.payer_name}</strong></span>
                  <span>&bull;</span>
                  <span>Created by @${exp.creator_username}</span>
                  <span>&bull;</span>
                  <span class="text-[10px]">${new Date(exp.created_at).toLocaleDateString()}</span>
                </div>
              </div>
            </div>

            <div class="text-right shrink-0">
              <div class="text-lg sm:text-xl font-display font-black text-slate-900 dark:text-white">
                ₹${Number(exp.amount || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
              </div>

              <div class="mt-1 flex items-center justify-end space-x-1.5">
                ${canManage ? `
                  <button onclick="app.handleDeleteExpense(${exp.id}, '${exp.title.replace(/'/g, "\\'")}')" class="p-1.5 bg-rose-50 dark:bg-rose-950/40 text-rose-600 dark:text-rose-300 hover:bg-rose-100 rounded-lg text-xs transition" title="Delete Expense (Creator Only)">
                    <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
                  </button>
                ` : `
                  <span class="text-[9px] text-slate-400 bg-slate-100 dark:bg-slate-800 px-2 py-0.5 rounded-md" title="Only @${exp.creator_username} can manage this expense">
                    🔒 View Only
                  </span>
                `}
              </div>
            </div>
          </div>

          <div class="space-y-1.5 pt-2 border-t border-slate-200/80 dark:border-white/5">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-2">
              ${splitsHtml}
            </div>
          </div>

          <div class="flex flex-wrap items-center justify-between gap-2 pt-2.5 border-t border-slate-200/80 dark:border-white/5 text-xs">
            <div class="flex items-center space-x-1.5">
              ${reactionsHtml}
              <div class="flex items-center space-x-1 bg-slate-100 dark:bg-slate-800 rounded-lg px-1.5 py-0.5">
                <button onclick="app.handleReact(${exp.id}, '🔥')" class="hover:scale-125 transition">🔥</button>
                <button onclick="app.handleReact(${exp.id}, '💅')" class="hover:scale-125 transition">💅</button>
                <button onclick="app.handleReact(${exp.id}, '💀')" class="hover:scale-125 transition">💀</button>
                <button onclick="app.handleReact(${exp.id}, '💸')" class="hover:scale-125 transition">💸</button>
                <button onclick="app.handleReact(${exp.id}, '🍕')" class="hover:scale-125 transition">🍕</button>
              </div>
            </div>

            <button onclick="app.openPayQRModal('${exp.payer_name}', '${exp.payer_username}', ${exp.amount / (exp.splits ? exp.splits.length : 1)})" class="px-3 py-1 bg-emerald-50 dark:bg-slate-800 border border-emerald-200 dark:border-white/10 text-emerald-700 dark:text-emerald-300 rounded-lg text-xs font-semibold flex items-center space-x-1 hover:bg-emerald-100 transition">
              <i data-lucide="qr-code" class="w-3.5 h-3.5"></i>
              <span>Pay UPI</span>
            </button>
          </div>

        </div>
      `;
    }).join("");

    this.refreshIcons();
  }

  getFilteredExpenses() {
    const search = (document.getElementById("expense-search")?.value || "").toLowerCase();
    const cat = document.getElementById("expense-category-filter")?.value || "all";

    return (this.expenses || []).filter(e => {
      const matchSearch = (e.title || "").toLowerCase().includes(search) || (e.payer_name || "").toLowerCase().includes(search);
      const matchCat = (cat === "all") || (e.category === cat);
      return matchSearch && matchCat;
    });
  }

  filterExpenses() {
    this.renderExpenses();
  }

  // --- Strict Access Actions ---
  async handleToggleSplitSettled(expenseId, userId) {
    try {
      const res = await this.api(`/api/expenses/${expenseId}/settle-split`, {
        method: "POST",
        body: JSON.stringify({ expense_id: expenseId, user_id: userId })
      });
      if (res.is_settled) {
        this.triggerConfetti();
        this.showToast("Payment confirmed & share settled! 🎉", "success");
      } else {
        this.showToast("Split debt reopened", "info");
      }
      await this.refreshActiveGroupData();
    } catch (err) {
      this.showToast(`Error: ${err.message}`, "error");
    }
  }

  async handleDeleteExpense(expenseId, title) {
    if (!confirm(`Are you sure you want to delete "${title}"? Only the creator can do this.`)) return;

    try {
      await this.api(`/api/expenses/${expenseId}`, {
        method: "DELETE"
      });
      this.showToast(`Expense "${title}" deleted`, "success");
      await this.refreshActiveGroupData();
    } catch (err) {
      this.showToast(`Error: ${err.message}`, "error");
    }
  }

  async handleReact(expenseId, emoji) {
    try {
      this.playTone("pop");
      await this.api(`/api/expenses/${expenseId}/react`, {
        method: "POST",
        body: JSON.stringify({ emoji })
      });
      this.expenses = await this.api(`/api/groups/${this.activeGroup.id}/expenses`);
      this.renderExpenses();
    } catch (err) {
      console.error(err);
    }
  }

  // --- Add Expense Modal Helpers & Split Types ---
  populateExpenseModalMembers() {
    const payerSelect = document.getElementById("expense-payer-select");
    if (payerSelect) {
      payerSelect.innerHTML = "";
      this.activeGroupMembers.forEach(m => {
        const opt = document.createElement("option");
        opt.value = m.user_id;
        opt.textContent = `${m.full_name} (@${m.username})`;
        if (this.currentUser && m.user_id === this.currentUser.id) {
          opt.selected = true;
        }
        payerSelect.appendChild(opt);
      });
    }

    this.renderSplitMembersChecklist();
  }

  setSplitType(type) {
    this.splitType = type;
    ["equal", "exact", "percentage"].forEach(t => {
      const btn = document.getElementById(`split-tab-${t}`);
      if (btn) {
        if (t === type) {
          btn.className = "py-1.5 rounded-lg text-xs font-bold transition bg-violet-600 text-white shadow";
        } else {
          btn.className = "py-1.5 rounded-lg text-xs font-bold transition text-slate-500 dark:text-slate-400 hover:text-slate-800";
        }
      }
    });
    this.renderSplitMembersChecklist();
  }

  renderSplitMembersChecklist() {
    const container = document.getElementById("expense-split-members-list");
    if (!container) return;

    const totalAmount = parseFloat(document.getElementById("expense-amount-input")?.value || "0") || 0;
    const count = this.activeGroupMembers.length;
    const equalShare = count > 0 ? (totalAmount / count).toFixed(2) : "0.00";

    container.innerHTML = this.activeGroupMembers.map(m => {
      return `
        <div class="flex items-center justify-between p-2 rounded-xl bg-white dark:bg-slate-800/80 border border-slate-200 dark:border-white/5 text-xs">
          <label class="flex items-center space-x-2.5 cursor-pointer">
            <input type="checkbox" id="split-user-check-${m.user_id}" checked onchange="app.recalculateSplitsPreview()" class="w-4 h-4 rounded text-violet-600 focus:ring-0 cursor-pointer" />
            <span class="font-bold text-slate-800 dark:text-white">${m.full_name}</span>
            <span class="text-[10px] text-slate-400">(@${m.username})</span>
          </label>

          <div class="flex items-center space-x-1.5">
            ${this.splitType === 'equal' ? `
              <span class="font-mono text-violet-700 dark:text-violet-300 font-bold split-preview-val" id="split-val-${m.user_id}">₹${equalShare}</span>
            ` : this.splitType === 'exact' ? `
              <span class="text-slate-400 font-bold">₹</span>
              <input type="number" step="0.01" id="split-custom-exact-${m.user_id}" value="${equalShare}" oninput="app.recalculateSplitsPreview()" class="w-20 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-white/10 rounded-lg px-2 py-1 text-xs text-slate-900 dark:text-white text-right font-mono" />
            ` : `
              <input type="number" step="0.1" id="split-custom-pct-${m.user_id}" value="${(100 / count).toFixed(1)}" oninput="app.recalculateSplitsPreview()" class="w-16 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-white/10 rounded-lg px-2 py-1 text-xs text-slate-900 dark:text-white text-right font-mono" />
              <span class="text-slate-400 font-bold">%</span>
            `}
          </div>
        </div>
      `;
    }).join("");

    this.recalculateSplitsPreview();
  }

  recalculateSplitsPreview() {
    const totalAmount = parseFloat(document.getElementById("expense-amount-input")?.value || "0") || 0;
    const badge = document.getElementById("split-summary-badge");

    const checkedMembers = this.activeGroupMembers.filter(m => {
      const chk = document.getElementById(`split-user-check-${m.user_id}`);
      return chk ? chk.checked : true;
    });

    if (this.splitType === 'equal') {
      const perPerson = checkedMembers.length > 0 ? (totalAmount / checkedMembers.length).toFixed(2) : "0.00";
      this.activeGroupMembers.forEach(m => {
        const valEl = document.getElementById(`split-val-${m.user_id}`);
        const isChecked = document.getElementById(`split-user-check-${m.user_id}`)?.checked;
        if (valEl) {
          valEl.textContent = isChecked ? `₹${perPerson}` : `₹0.00`;
          valEl.className = isChecked ? "font-mono text-violet-700 dark:text-violet-300 font-bold" : "font-mono text-slate-400";
        }
      });
      if (badge) badge.textContent = `Equal split (${checkedMembers.length} members &bull; ₹${perPerson} each)`;
    } else if (this.splitType === 'exact') {
      let sum = 0;
      this.activeGroupMembers.forEach(m => {
        const inp = document.getElementById(`split-custom-exact-${m.user_id}`);
        sum += parseFloat(inp?.value || "0") || 0;
      });
      const diff = totalAmount - sum;
      if (badge) {
        if (Math.abs(diff) < 0.05) {
          badge.textContent = `Exact sum matches ₹${totalAmount.toFixed(2)} ✅`;
          badge.className = "text-[10px] text-emerald-600 dark:text-emerald-400 font-bold";
        } else {
          badge.textContent = `Difference: ₹${diff.toFixed(2)} (Sum: ₹${sum.toFixed(2)})`;
          badge.className = "text-[10px] text-rose-600 dark:text-rose-400 font-bold";
        }
      }
    } else if (this.splitType === 'percentage') {
      let sumPct = 0;
      this.activeGroupMembers.forEach(m => {
        const inp = document.getElementById(`split-custom-pct-${m.user_id}`);
        sumPct += parseFloat(inp?.value || "0") || 0;
      });
      if (badge) {
        if (Math.abs(100 - sumPct) < 0.1) {
          badge.textContent = `100% Allocated ✅`;
          badge.className = "text-[10px] text-emerald-600 dark:text-emerald-400 font-bold";
        } else {
          badge.textContent = `Total: ${sumPct.toFixed(1)}% (Need 100%)`;
          badge.className = "text-[10px] text-rose-600 dark:text-rose-400 font-bold";
        }
      }
    }
  }

  async handleCreateExpense(e) {
    e.preventDefault();
    if (!this.activeGroup) return;

    const title = document.getElementById("expense-title-input").value;
    const category = document.getElementById("expense-category-input").value;
    const amount = parseFloat(document.getElementById("expense-amount-input").value);
    const paid_by_user_id = parseInt(document.getElementById("expense-payer-select").value);

    const splits = [];
    const checkedMembers = this.activeGroupMembers.filter(m => {
      const chk = document.getElementById(`split-user-check-${m.user_id}`);
      return chk ? chk.checked : true;
    });

    if (checkedMembers.length === 0) {
      this.showToast("Please select at least 1 participant", "error");
      return;
    }

    if (this.splitType === 'equal') {
      const perPerson = round2(amount / checkedMembers.length);
      checkedMembers.forEach(m => {
        splits.push({
          user_id: m.user_id,
          owed_amount: perPerson,
          split_value: 1.0
        });
      });
    } else if (this.splitType === 'exact') {
      checkedMembers.forEach(m => {
        const val = parseFloat(document.getElementById(`split-custom-exact-${m.user_id}`)?.value || "0");
        splits.push({
          user_id: m.user_id,
          owed_amount: val,
          split_value: val
        });
      });
    } else if (this.splitType === 'percentage') {
      checkedMembers.forEach(m => {
        const pct = parseFloat(document.getElementById(`split-custom-pct-${m.user_id}`)?.value || "0");
        const owed = round2((pct / 100) * amount);
        splits.push({
          user_id: m.user_id,
          owed_amount: owed,
          split_value: pct
        });
      });
    }

    try {
      await this.api("/api/expenses", {
        method: "POST",
        body: JSON.stringify({
          group_id: this.activeGroup.id,
          title,
          category,
          amount,
          currency: "₹",
          paid_by_user_id,
          split_type: this.splitType,
          splits
        })
      });

      this.closeModal("add-expense-modal");
      document.getElementById("add-expense-form").reset();
      this.triggerConfetti();
      this.showToast(`Expense "${title}" added! ⚡`, "success");
      await this.refreshActiveGroupData();
    } catch (err) {
      this.showToast(`Error: ${err.message}`, "error");
    }
  }

  // --- Balances Tab & Simplified Graph ---
  renderBalances() {
    const container = document.getElementById("member-balances-list");
    if (!container || !this.balances) return;

    container.innerHTML = this.balances.balances.map(b => {
      const net = b.net_balance;
      const isPositive = net > 0;
      const isNegative = net < 0;

      return `
        <div class="flex items-center justify-between p-3 rounded-2xl bg-white dark:bg-slate-900/80 border ${isPositive ? 'border-emerald-200 dark:border-emerald-500/30' : isNegative ? 'border-rose-200 dark:border-rose-500/30' : 'border-slate-200 dark:border-white/10'} shadow-sm">
          <div class="flex items-center space-x-3">
            <img src="${b.avatar_url || `https://api.dicebear.com/7.x/bottts/svg?seed=${b.username}`}" class="w-10 h-10 rounded-xl bg-violet-100 dark:bg-violet-900/40" />
            <div>
              <div class="font-bold text-sm text-slate-800 dark:text-white flex items-center space-x-1.5">
                <span>${b.full_name}</span>
                ${b.user_id === this.currentUser?.id ? '<span class="text-[9px] bg-violet-100 text-violet-700 dark:bg-violet-900/40 dark:text-violet-300 px-1.5 py-0.2 rounded font-bold">You</span>' : ''}
              </div>
              <div class="text-[11px] text-slate-500 dark:text-slate-400">${b.persona || `@${b.username}`}</div>
            </div>
          </div>

          <div class="text-right">
            <div class="font-display font-black text-sm ${isPositive ? 'text-emerald-600 dark:text-emerald-400' : isNegative ? 'text-rose-600 dark:text-rose-400' : 'text-slate-500'}">
              ${isPositive ? '+' : ''}₹${Math.abs(net).toFixed(2)}
            </div>
            <div class="text-[10px] ${isPositive ? 'text-emerald-600' : isNegative ? 'text-rose-600' : 'text-slate-400'} font-semibold">
              ${isPositive ? 'gets back' : isNegative ? 'owes group' : 'settled'}
            </div>
          </div>
        </div>
      `;
    }).join("");
  }

  renderSimplifiedDebts() {
    const container = document.getElementById("simplified-debts-list");
    if (!container || !this.balances) return;

    const debts = this.balances.simplified_debts || [];
    if (debts.length === 0) {
      container.innerHTML = `
        <div class="p-6 text-center bg-slate-50 dark:bg-slate-900/60 rounded-2xl border border-slate-200 dark:border-white/5">
          <span class="text-3xl block mb-1">🎉</span>
          <h4 class="font-display font-bold text-sm text-slate-800 dark:text-white">All group debts are completely settled!</h4>
          <p class="text-xs text-slate-500 dark:text-slate-400 mt-1">Zero pending transactions. Pure peace of mind ✨</p>
        </div>
      `;
      return;
    }

    container.innerHTML = debts.map(d => {
      const isFromMe = (this.currentUser && d.from_user_id === this.currentUser.id);
      const isToMe = (this.currentUser && d.to_user_id === this.currentUser.id);

      return `
        <div class="flex flex-col sm:flex-row sm:items-center justify-between p-3.5 rounded-2xl bg-white dark:bg-slate-900 border border-cyan-200 dark:border-cyan-500/30 gap-3 shadow-sm">
          <div class="flex items-center space-x-2">
            <span class="font-bold text-sm ${isFromMe ? 'text-rose-600 dark:text-rose-400 font-extrabold' : 'text-slate-800 dark:text-white'}">${d.from_name}</span>
            <i data-lucide="arrow-right" class="w-4 h-4 text-cyan-600 dark:text-cyan-400"></i>
            <span class="font-bold text-sm ${isToMe ? 'text-emerald-600 dark:text-emerald-400 font-extrabold' : 'text-slate-800 dark:text-white'}">${d.to_name}</span>
          </div>

          <div class="flex items-center space-x-3 self-end sm:self-auto">
            <span class="text-base font-display font-black text-cyan-600 dark:text-cyan-400">
              ₹${Number(d.amount || 0).toFixed(2)}
            </span>

            <button onclick="app.openPayQRModal('${d.to_name}', '${d.to_username}', ${d.amount}, ${d.to_user_id})" class="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs font-bold transition flex items-center space-x-1 shadow-sm">
              <i data-lucide="qr-code" class="w-3.5 h-3.5"></i>
              <span>Pay Now</span>
            </button>

            <button onclick="app.openRoastModal('${d.from_name}', '${d.to_name}', ${d.amount}, 'Pending Group Balance')" class="p-1.5 bg-pink-100 dark:bg-pink-900/30 text-pink-700 dark:text-pink-300 rounded-xl hover:bg-pink-200 transition" title="Roast debtor on WhatsApp">
              💅
            </button>
          </div>
        </div>
      `;
    }).join("");

    this.refreshIcons();
  }

  // --- 🤖 AI NLP Magic Split ---
  fillNLPPrompt(text) {
    const input = document.getElementById("nlp-prompt-input");
    if (input) input.value = text;
    this.handleParseNLP();
  }

  async handleParseNLP() {
    const prompt = document.getElementById("nlp-prompt-input")?.value;
    if (!prompt || !this.activeGroup) return;

    const btn = document.getElementById("nlp-parse-btn");
    if (btn) btn.innerHTML = `<span>Thinking with AI... ✨</span>`;

    try {
      const parsed = await this.api("/api/ai/nlp-parse", {
        method: "POST",
        body: JSON.stringify({
          prompt,
          group_id: this.activeGroup.id
        })
      });

      this.nlpExtraction = parsed;

      document.getElementById("nlp-result-box").classList.remove("hidden");
      document.getElementById("nlp-res-title").textContent = parsed.title;
      document.getElementById("nlp-res-amount").textContent = `₹${parsed.amount.toFixed(2)}`;
      document.getElementById("nlp-res-payer").textContent = `@${parsed.paid_by_username || 'You'}`;
      document.getElementById("nlp-res-cat").textContent = parsed.category.toUpperCase();
      document.getElementById("nlp-res-splits").innerHTML = `<strong>Splits:</strong> ${(parsed.splits || []).map(s => `@${s.username} (₹${s.amount})`).join(', ')}`;

      document.getElementById("nlp-apply-btn").classList.remove("hidden");
    } catch (err) {
      this.showToast(`AI Error: ${err.message}`, "error");
    } finally {
      if (btn) btn.innerHTML = `<span>Parse with AI ✨</span>`;
    }
  }

  applyNLPExtraction() {
    if (!this.nlpExtraction) return;
    const p = this.nlpExtraction;

    this.closeModal("nlp-modal");
    this.openModal("add-expense-modal");

    document.getElementById("expense-title-input").value = p.title;
    document.getElementById("expense-amount-input").value = p.amount;
    document.getElementById("expense-category-input").value = p.category;
    if (p.paid_by_user_id) {
      document.getElementById("expense-payer-select").value = p.paid_by_user_id;
    }

    this.setSplitType("equal");
    this.recalculateSplitsPreview();
    this.showToast("AI data prefilled into form! ⚡", "success");
  }

  // --- 💅 Gen-Z Debt Roaster & Nudge ---
  openRoastModal(debtorName = null, creditorName = null, amount = null, expenseTitle = null) {
    if (!debtorName && this.activeGroupMembers.length > 1) {
      const other = this.activeGroupMembers.find(m => m.user_id !== this.currentUser?.id) || this.activeGroupMembers[1];
      debtorName = other.full_name;
      creditorName = this.currentUser?.full_name || "Dhairya";
      amount = 600.0;
      expenseTitle = "Weekend Hangout";
    }

    this.activeRoastData = {
      debtor_name: debtorName || "Friend",
      creditor_name: creditorName || "You",
      amount: amount || 500.0,
      expense_title: expenseTitle || "Group Expense",
      tone: "passive_aggressive",
      payment_handle: this.currentUser?.payment_handle || ""
    };

    const dNameEl = document.getElementById("roast-debtor-name");
    const amtEl = document.getElementById("roast-amount-val");
    const expEl = document.getElementById("roast-expense-title");

    if (dNameEl) dNameEl.textContent = this.activeRoastData.debtor_name;
    if (amtEl) amtEl.textContent = `₹${this.activeRoastData.amount.toFixed(2)}`;
    if (expEl) expEl.textContent = this.activeRoastData.expense_title;

    this.selectRoastTone("passive_aggressive");
    this.openModal("roast-modal");
  }

  selectRoastTone(tone) {
    this.activeRoastData.tone = tone;
    document.querySelectorAll(".roast-tone-pill").forEach(pill => {
      if (pill.dataset.tone === tone) {
        pill.className = "roast-tone-pill p-2 rounded-xl border text-xs font-semibold bg-pink-100 border-pink-400 text-pink-800 dark:bg-pink-600/30 dark:border-pink-500 dark:text-pink-200 shadow-sm";
      } else {
        pill.className = "roast-tone-pill p-2 rounded-xl border border-slate-200 dark:border-white/10 text-xs font-semibold bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300";
      }
    });
    this.generateRoast();
  }

  async generateRoast() {
    const textEl = document.getElementById("roast-output-text");
    const waLink = document.getElementById("roast-whatsapp-link");
    if (textEl) textEl.textContent = "Crafting spicy punchline... 💅";

    try {
      const res = await this.api("/api/ai/roast-nudge", {
        method: "POST",
        body: JSON.stringify(this.activeRoastData)
      });
      if (textEl) textEl.textContent = `"${res.roast_text}"`;
      if (waLink) waLink.href = res.whatsapp_share_url;
      this.lastGeneratedRoast = res.roast_text;
    } catch (err) {
      if (textEl) textEl.textContent = `Bestie, respectfully run me that ₹${this.activeRoastData.amount} for ${this.activeRoastData.expense_title} 💅✨`;
    }
  }

  copyRoastToClipboard() {
    if (!this.lastGeneratedRoast) return;
    navigator.clipboard.writeText(this.lastGeneratedRoast);
    this.showToast("Roast copied to clipboard! 💅", "roast");
  }

  // --- 💸 1-Click UPI & QR Settlement ---
  openPayQRModal(recipientName, recipientUsername, amount, toUserId = null) {
    this.activePayData = {
      recipientName,
      recipientUsername,
      amount,
      toUserId
    };

    document.getElementById("pay-recipient-name").textContent = recipientName;
    document.getElementById("pay-amount-val").textContent = `₹${amount.toFixed(2)}`;
    
    const member = this.activeGroupMembers.find(m => m.username === recipientUsername);
    const handle = (member && member.payment_handle) ? member.payment_handle : `${recipientUsername}@upi`;
    document.getElementById("pay-handle-val").textContent = handle;

    const upiUri = `upi://pay?pa=${encodeURIComponent(handle)}&pn=${encodeURIComponent(recipientName)}&am=${amount.toFixed(2)}&cu=INR&tn=${encodeURIComponent('VibeSplit Group Settlement')}`;

    const canvas = document.getElementById("upi-qrcode-canvas");
    if (canvas && typeof QRCode !== "undefined" && typeof QRCode.toCanvas === "function") {
      QRCode.toCanvas(canvas, upiUri, {
        width: 170,
        margin: 1,
        color: { dark: '#0F172A', light: '#FFFFFF' }
      }, (error) => {
        if (error) console.error(error);
      });
    }

    this.openModal("pay-qr-modal");
  }

  async handleDirectSettlementSubmit() {
    if (!this.activePayData || !this.activeGroup) return;

    try {
      const toUserId = this.activePayData.toUserId || this.activeGroupMembers.find(m => m.username === this.activePayData.recipientUsername)?.user_id;
      if (!toUserId) {
        throw new Error("Recipient ID not found");
      }

      await this.api("/api/settlements", {
        method: "POST",
        body: JSON.stringify({
          group_id: this.activeGroup.id,
          to_user_id: toUserId,
          amount: this.activePayData.amount,
          payment_method: "upi",
          notes: "Settled via VibeSplit QR"
        })
      });

      this.closeModal("pay-qr-modal");
      this.triggerConfetti();
      this.showToast(`Transferred ₹${this.activePayData.amount.toFixed(2)} to ${this.activePayData.recipientName}! 🎉`, "success");
      await this.refreshActiveGroupData();
    } catch (err) {
      this.showToast(`Settlement error: ${err.message}`, "error");
    }
  }

  // --- 🧾 AI Smart Bill / Receipt Scanner ---
  async handleScanReceipt() {
    const rawText = document.getElementById("receipt-raw-text")?.value;
    if (!rawText || !this.activeGroup) return;

    try {
      const parsed = await this.api("/api/ai/receipt-scan", {
        method: "POST",
        body: JSON.stringify({
          group_id: this.activeGroup.id,
          raw_text: rawText
        })
      });

      this.closeModal("receipt-scan-modal");
      this.openModal("add-expense-modal");

      document.getElementById("expense-title-input").value = parsed.merchant;
      document.getElementById("expense-amount-input").value = parsed.total;
      document.getElementById("expense-category-input").value = parsed.detected_category || "food";
      this.setSplitType("equal");
      this.recalculateSplitsPreview();

      this.showToast(`Extracted bill: ₹${parsed.total} from ${parsed.merchant} 🧾✨`, "success");
    } catch (err) {
      this.showToast(`Scan error: ${err.message}`, "error");
    }
  }

  // --- 🔮 AI Group Vibe Check & Awards ---
  async loadVibeCheck() {
    if (!this.activeGroup) return;

    try {
      const data = await this.api(`/api/groups/${this.activeGroup.id}/vibe-check`);
      
      document.getElementById("vibe-score-val").textContent = `${data.vibe_score}/100`;
      document.getElementById("vibe-summary-title").textContent = data.vibe_title;
      document.getElementById("vibe-summary-text").textContent = data.vibe_summary;

      const badgesBox = document.getElementById("vibe-badges-container");
      if (badgesBox) {
        badgesBox.innerHTML = (data.user_badges || []).map(b => `
          <div class="glass-panel p-3 rounded-2xl flex items-start space-x-3">
            <span class="text-2xl">${b.badge_emoji}</span>
            <div>
              <div class="text-xs font-extrabold text-slate-900 dark:text-white">${b.badge_title}</div>
              <div class="text-[10px] text-pink-600 dark:text-pink-300 font-bold">@${b.username}</div>
              <p class="text-[10px] text-slate-500 dark:text-slate-400 mt-0.5 leading-snug">${b.description}</p>
            </div>
          </div>
        `).join("");
      }

      this.vibeChartBreakdown = data.category_breakdown;
      this.renderVibeChart(data.category_breakdown || {});
    } catch (err) {
      console.error(err);
    }
  }

  renderVibeChart(categoryBreakdown) {
    const canvas = document.getElementById("vibeSpendingChart");
    if (!canvas || typeof Chart === "undefined") return;

    if (this.vibeChartInstance) {
      this.vibeChartInstance.destroy();
    }

    const labels = Object.keys(categoryBreakdown).map(k => k.toUpperCase());
    const values = Object.values(categoryBreakdown);
    const isDark = document.documentElement.classList.contains("dark");

    this.vibeChartInstance = new Chart(canvas, {
      type: "doughnut",
      data: {
        labels: labels.length > 0 ? labels : ["VIBES"],
        datasets: [{
          data: values.length > 0 ? values : [100],
          backgroundColor: [
            "#7C3AED", "#EC4899", "#06B6D4", "#10B981", "#F59E0B", "#6366F1"
          ],
          borderWidth: 0
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: "bottom",
            labels: { color: isDark ? "#94A3B8" : "#475569", font: { size: 10 } }
          }
        },
        cutout: "68%"
      }
    });
  }

  // --- Activity Log ---
  async loadActivity() {
    if (!this.activeGroup) return;
    try {
      const logs = await this.api(`/api/groups/${this.activeGroup.id}/activity`);
      const container = document.getElementById("activity-list");
      if (!container) return;

      if (logs.length === 0) {
        container.innerHTML = `<p class="text-xs text-slate-400 text-center py-6">No activity recorded yet</p>`;
        return;
      }

      container.innerHTML = logs.map(l => `
        <div class="flex items-start space-x-3 p-3 rounded-2xl bg-white dark:bg-slate-900/60 border border-slate-200 dark:border-white/5 text-xs">
          <img src="${l.avatar_url || `https://api.dicebear.com/7.x/bottts/svg?seed=${l.username}`}" class="w-7 h-7 rounded-lg bg-violet-100 dark:bg-violet-900/40 shrink-0" />
          <div class="flex-1">
            <p class="text-slate-800 dark:text-slate-200">${l.description}</p>
            <span class="text-[10px] text-slate-400 mt-0.5 block">${new Date(l.created_at).toLocaleTimeString()}</span>
          </div>
        </div>
      `).join("");
    } catch (err) {
      console.error(err);
    }
  }

  // --- Tab Switcher ---
  switchTab(tab) {
    this.currentTab = tab;
    ["expenses", "balances", "vibe-check", "activity"].forEach(t => {
      const el = document.getElementById(`tab-${t}`);
      const navBtn = document.getElementById(`nav-btn-${t}`);
      const mobileBtn = document.getElementById(`mobile-tab-${t}`);

      if (el) {
        if (t === tab) {
          el.classList.remove("hidden");
        } else {
          el.classList.add("hidden");
        }
      }

      if (navBtn) {
        if (t === tab) {
          navBtn.className = "w-full flex items-center space-x-3 px-3.5 py-2.5 rounded-xl font-bold text-sm transition bg-violet-600 text-white shadow-md shadow-violet-500/20";
        } else {
          navBtn.className = "w-full flex items-center space-x-3 px-3.5 py-2.5 rounded-xl font-semibold text-sm transition text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800/60";
        }
      }

      if (mobileBtn) {
        if (t === tab) {
          mobileBtn.className = "flex flex-col items-center space-y-1 text-violet-600 dark:text-violet-400";
        } else {
          mobileBtn.className = "flex flex-col items-center space-y-1 text-slate-400";
        }
      }
    });

    if (tab === "vibe-check") {
      this.loadVibeCheck();
    }
    this.refreshIcons();
  }

  // --- Modal Helpers ---
  openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
      modal.classList.remove("hidden");
      this.refreshIcons();
    }
  }

  closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
      modal.classList.add("hidden");
    }
  }

  refreshIcons() {
    try {
      if (window.lucide && typeof window.lucide.createIcons === 'function') {
        window.lucide.createIcons();
      }
    } catch(e) {}
  }
}

function round2(num) {
  return Math.round((num + Number.EPSILON) * 100) / 100;
}

// Global immediate assignment
const app = new VibeSplitApp();
window.app = app;

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => app.init());
} else {
  app.init();
}
