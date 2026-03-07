/**
 * PharmAI Auth — Descope authentication class
 * Manages login/logout, session persistence, and UI updates
 */

class DescopeAuth {
  constructor() {
    this.isLoggedIn = false;
    this.user = null;
    this.sdk = null;
    // NOTE: init() is called explicitly from app.js after construction
    // to avoid double-initialization.
  }

  async init() {
    try {
      this.sdk = Descope({ projectId: 'P32OxoFpY0ihVvncEbabQARqzw8I' });

      // Check cached login state first (prevents flash of logged-out UI)
      const saved = localStorage.getItem('pharma_user');
      if (saved) {
        this.user = JSON.parse(saved);
        this.isLoggedIn = true;
        this.updateUI();
        return;
      }

      // Try session token from Descope SDK
      const token = this.sdk.getSessionToken();
      if (token) {
        const info = await this.sdk.me();
        if (info) {
          this.user = info;
          this.isLoggedIn = true;
          localStorage.setItem('pharma_user', JSON.stringify(this.user));
          this.updateUI();
        }
      }
    } catch (e) {
      // Fallback to cached user data on SDK errors
      const saved = localStorage.getItem('pharma_user');
      if (saved) {
        this.user = JSON.parse(saved);
        this.isLoggedIn = true;
        this.updateUI();
      }
    }
    this.setupListeners();
  }

  setupListeners() {
    document.getElementById('loginBtn')?.addEventListener('click', () => this.showModal());
    document.getElementById('logoutBtn')?.addEventListener('click', () => this.logout());
    document.getElementById('closeModal')?.addEventListener('click', () => this.hideModal());

    // Close on backdrop click
    document.getElementById('authModal')?.addEventListener('click', (e) => {
      if (e.target.id === 'authModal') this.hideModal();
    });

    // Descope web component success/error events
    const wc = document.querySelector('descope-wc');
    if (wc) {
      wc.addEventListener('success', (e) => this.onSuccess(e.detail));
      wc.addEventListener('error', () => toast('Authentication failed', 'error'));
    }
  }

  showModal() {
    document.getElementById('authModal')?.classList.add('active');
  }

  hideModal() {
    document.getElementById('authModal')?.classList.remove('active');
  }

  onSuccess(detail) {
    if (detail.user) {
      this.user = {
        email: detail.user.email,
        name: detail.user.name || detail.user.email.split('@')[0],
        loginTime: Date.now(),
      };
      this.isLoggedIn = true;
      localStorage.setItem('pharma_user', JSON.stringify(this.user));
      this.updateUI();
      this.hideModal();
      toast('Signed in successfully!', 'success');
    }
  }

  async logout() {
    try { if (this.sdk) await this.sdk.logout(); } catch (e) { /* ignore */ }
    this.user = null;
    this.isLoggedIn = false;
    localStorage.removeItem('pharma_user');
    this.updateUI();
    toast('Signed out', 'info');
  }

  updateUI() {
    const info = document.getElementById('userInfo');
    const btn = document.getElementById('loginBtn');

    if (this.isLoggedIn && this.user) {
      if (info) info.style.display = 'flex';
      if (btn) btn.style.display = 'none';
      const avatar = document.getElementById('userAvatar');
      const name = document.getElementById('userName');
      if (avatar) avatar.textContent = this.user.name.substring(0, 2).toUpperCase();
      if (name) name.textContent = this.user.name;
    } else {
      if (info) info.style.display = 'none';
      if (btn) btn.style.display = 'inline-block';
    }
  }

  /** Require authentication — shows modal if not logged in, else runs callback */
  requireAuth(cb) {
    if (this.isLoggedIn) {
      cb();
    } else {
      this.showModal();
      toast('Please sign in first', 'warning');
    }
  }
}
