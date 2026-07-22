class PanasonicCoolovenCard extends HTMLElement {
  set hass(hass) {
    const oldLang = this._lang;
    this._hass = hass;
    this._lang = hass.language || 'en';
    
    if (!this.content) {
      this.render();
    } else if (oldLang !== this._lang) {
      this.loadTranslations().then(t => this.updateLocalization(t));
    }
  }

  async loadTranslations() {
    try {
      const response = await fetch(`/panasonic_japan_assets/translations/${this._lang}.json`);
      if (!response.ok) throw new Error();
      const json = await response.json();
      return json.card || {};
    } catch (e) {
      const fallback = await fetch(`/panasonic_japan_assets/translations/en.json`);
      const json = await fallback.json();
      return json.card || {};
    }
  }

  async render() {
    this.innerHTML = `
      <ha-card id="card-header">
        <div style="padding: 16px; display: flex; flex-direction: column; gap: 12px;">
          <div>
            <label id="lbl-mode" style="display: block; margin-bottom: 4px; font-weight: 500;"></label>
            <select id="mode-select" style="width: 100%; padding: 8px; border-radius: 4px; border: 1px solid var(--divider-color); background: var(--card-background-color); color: var(--primary-text-color);">
              <option value="off" id="opt-off"></option>
              <option value="quench" id="opt-quench"></option>
              <option value="cold" id="opt-cold"></option>
              <option value="freeze" id="opt-freeze"></option>
            </select>
          </div>
          <div>
            <label id="lbl-time" style="display: block; margin-bottom: 4px; font-weight: 500;"></label>
            <input type="number" id="time-input" value="0" min="0" max="60" style="width: 100%; padding: 8px; border-radius: 4px; border: 1px solid var(--divider-color); background: var(--card-background-color); color: var(--primary-text-color);">
          </div>
          <div>
            <label id="lbl-sec" style="display: block; margin-bottom: 4px; font-weight: 500;"></label>
            <input type="number" id="sec-input" value="10" min="0" max="59" style="width: 100%; padding: 8px; border-radius: 4px; border: 1px solid var(--divider-color); background: var(--card-background-color); color: var(--primary-text-color);">
          </div>
          <mwc-button raised id="exec-btn" style="margin-top: 8px;"></mwc-button>
        </div>
      </ha-card>
    `;
    this.content = this.querySelector('ha-card');
    
    this.querySelector('#exec-btn').addEventListener('click', () => {
      const mode = this.querySelector('#mode-select').value;
      const time = parseInt(this.querySelector('#time-input').value, 10);
      const second = parseInt(this.querySelector('#sec-input').value, 10);
      
      this._hass.callService('panasonic_japan', 'set_cooloven', {
        mode: mode,
        time: isNaN(time) ? 0 : time,
        second: isNaN(second) ? 0 : second
      });
    });

    const t = await this.loadTranslations();
    this.updateLocalization(t);
  }

  updateLocalization(t) {
    this.querySelector('#card-header').header = t.title || "";
    this.querySelector('#lbl-mode').textContent = t.mode || "";
    this.querySelector('#opt-off').textContent = t.off || "";
    this.querySelector('#opt-quench').textContent = t.quench || "";
    this.querySelector('#opt-cold').textContent = t.cold || "";
    this.querySelector('#opt-freeze').textContent = t.freeze || "";    
    this.querySelector('#lbl-time').textContent = t.time || "";
    this.querySelector('#lbl-sec').textContent = t.second || "";
    this.querySelector('#exec-btn').textContent = t.exec || "";
  }

  setConfig(config) {}
  getCardSize() { return 3; }
}

customElements.define('panasonic-cooloven-card', PanasonicCoolovenCard);
window.customCards = window.customCards || [];
window.customCards.push({
  type: 'panasonic-cooloven-card',
  name: 'Panasonic Cooloven Card',
  description: 'Custom card with segregated card translation keys.'
});