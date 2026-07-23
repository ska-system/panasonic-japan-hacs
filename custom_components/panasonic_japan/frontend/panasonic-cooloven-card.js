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
      try {
        const fallback = await fetch(`/panasonic_japan_assets/translations/en.json`);
        const json = await fallback.json();
        return json.card || {};
      } catch (err) {
        return {};
      }
    }
  }

  async render() {
    const t = await this.loadTranslations();
    
    this.innerHTML = `
      <ha-card header="${t.title || ''}">
        <div style="padding: 16px; display: flex; flex-direction: column; gap: 12px;">
          <div>
            <label id="lbl-mode" style="display: block; margin-bottom: 4px; font-weight: 500;">${t.mode || ''}</label>
            <select id="mode-select" style="width: 100%; padding: 8px; border-radius: 4px; border: 1px solid var(--divider-color); background: var(--card-background-color); color: var(--primary-text-color);">
              <option value="off">${t.off || 'Off'}</option>
              <option value="quench">${t.quench || 'Quench'}</option>
              <option value="cold">${t.cold || 'Cold'}</option>
              <option value="freeze">${t.freeze || 'Freeze'}</option>
            </select>
          </div>
          <div id="time-container">
            <label id="lbl-time" style="display: block; margin-bottom: 4px; font-weight: 500;">${t.time || ''}</label>
            <input type="number" id="time-input" style="width: 100%; padding: 8px; border-radius: 4px; border: 1px solid var(--divider-color); background: var(--card-background-color); color: var(--primary-text-color);">
          </div>
          <div id="sec-container">
            <label id="lbl-sec" style="display: block; margin-bottom: 4px; font-weight: 500;">${t.second || ''}</label>
            <input type="number" id="sec-input" style="width: 100%; padding: 8px; border-radius: 4px; border: 1px solid var(--divider-color); background: var(--card-background-color); color: var(--primary-text-color);">
          </div>
          <mwc-button raised id="exec-btn" style="margin-top: 8px;">${t.exec || 'Execute'}</mwc-button>
        </div>
      </ha-card>
    `;
    
    this.content = this.querySelector('ha-card');
    const modeSelect = this.querySelector('#mode-select');
    
    modeSelect.addEventListener('change', () => this.updateFormState());
    
    this.querySelector('#exec-btn').addEventListener('click', () => {
      const mode = modeSelect.value;
      const timeContainer = this.querySelector('#time-container');
      const secContainer = this.querySelector('#sec-container');
      const timeInput = this.querySelector('#time-input');
      const secInput = this.querySelector('#sec-input');
      
      const time = parseInt(timeInput.value, 10);
      const second = parseInt(secInput.value, 10);
      
      if (mode === 'quench' && (isNaN(time) || time === 0) && (isNaN(second) || second === 0)) {
        alert('Time and seconds cannot both be 0 in quench mode.');
        return;
      }
      
      this._hass.callService('panasonic_japan', 'set_cooloven', {
        mode: mode,
        time: timeContainer.style.display !== 'none' && !isNaN(time) ? time : 0,
        second: secContainer.style.display !== 'none' && !isNaN(second) ? second : 0
      });
    });

    this.updateFormState();
  }

  updateFormState() {
    const mode = this.querySelector('#mode-select').value;
    const timeContainer = this.querySelector('#time-container');
    const secContainer = this.querySelector('#sec-container');
    const timeInput = this.querySelector('#time-input');
    const secInput = this.querySelector('#sec-input');

    if (mode === 'off') {
      timeContainer.style.display = 'none';
      secContainer.style.display = 'none';
    } else if (mode === 'quench') {
      timeContainer.style.display = 'block';
      secContainer.style.display = 'block';
      timeInput.min = 0;
      timeInput.max = 10;
      timeInput.value = 5;
      secInput.min = 0;
      secInput.max = 50;
      secInput.step = 10;
      secInput.value = 0;
    } else if (mode === 'cold') {
      timeContainer.style.display = 'block';
      secContainer.style.display = 'none';
      timeInput.min = 10;
      timeInput.max = 30;
      timeInput.value = 15;
    } else if (mode === 'freeze' || mode === 'frozen') {
      timeContainer.style.display = 'block';
      secContainer.style.display = 'none';
      timeInput.min = 30;
      timeInput.max = 60;
      timeInput.value = 45;
    }
  }

  updateLocalization(t) {
    if (!this.content) return;
    this.content.header = t.title || "";
    const lblMode = this.querySelector('#lbl-mode');
    if (lblMode) lblMode.textContent = t.mode || "";
    
    const options = {
      'off': t.off || 'Off',
      'quench': t.quench || 'Quench',
      'cold': t.cold || 'Cold',
      'freeze': t.freeze || 'Freeze'
    };
    for (const [val, text] of Object.entries(options)) {
      const opt = this.querySelector(`option[value="${val}"]`);
      if (opt) opt.textContent = text;
    }

    const lblTime = this.querySelector('#lbl-time');
    if (lblTime) lblTime.textContent = t.time || "";
    const lblSec = this.querySelector('#lbl-sec');
    if (lblSec) lblSec.textContent = t.second || "";
    const execBtn = this.querySelector('#exec-btn');
    if (execBtn) execBtn.textContent = t.exec || "";
  }

  setConfig(config) {}
  getCardSize() { return 3; }
}

customElements.define('panasonic-cooloven-card', PanasonicCoolovenCard);
window.customCards = window.customCards || [];
window.customCards.push({
  type: 'panasonic-cooloven-card',
  name: 'Panasonic Cooloven Card',
  description: 'Custom card with dynamic input constraints based on mode.'
});