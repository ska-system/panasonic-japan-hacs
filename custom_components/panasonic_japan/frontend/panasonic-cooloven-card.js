class PanasonicCoolovenCard extends HTMLElement {
  setConfig(config) {
    if (!config) {
      throw new Error('Invalid configuration');
    }
    this._config = config;
    // yaml設定に appliance_id があればそれを使用、なければ entity を保持する
    this._applianceId = config.appliance_id;
    this._entity = config.entity;
  }

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
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <label id="lbl-mode" style="font-weight: 500; white-space: nowrap;">${t.mode || ''}</label>
            <select id="mode-select" style="width: 160px; padding: 8px; border-radius: 4px; border: 1px solid var(--divider-color); background: var(--card-background-color); color: var(--primary-text-color);">
              <option value="off">${t.off || 'Off'}</option>
              <option value="quench">${t.quench || 'Quench'}</option>
              <option value="cold">${t.cold || 'Cold'}</option>
              <option value="frozen">${t.frozen || 'Frozen'}</option>
            </select>
          </div>
          <div id="time-container" style="display: flex; justify-content: space-between; align-items: center;">
            <label id="lbl-time" style="font-weight: 500; white-space: nowrap;">${t.time || ''}</label>
            <input type="number" id="time-input" style="width: 160px; padding: 8px; text-align: right; border-radius: 4px; border: 1px solid var(--divider-color); background: var(--card-background-color); color: var(--primary-text-color);">
          </div>
          <div id="sec-container" style="display: flex; justify-content: space-between; align-items: center;">
            <label id="lbl-sec" style="font-weight: 500; white-space: nowrap;">${t.second || ''}</label>
            <input type="number" id="sec-input" style="width: 160px; padding: 8px; text-align: right; border-radius: 4px; border: 1px solid var(--divider-color); background: var(--card-background-color); color: var(--primary-text-color);">
          </div>
          <button id="exec-btn" style="width: 100%; padding: 10px; border-radius: 4px; border: none; background: var(--primary-color); color: var(--text-primary-color, #fff); font-weight: 500; cursor: pointer; margin-top: 8px;">${t.exec || 'Execute'}</button>
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
      
      let time = parseInt(timeInput.value, 10);
      let second = parseInt(secInput.value, 10);
      
      if (isNaN(time)) time = 0;
      if (isNaN(second)) second = 0;

      let minTime = 0, maxTime = 60;
      let maxSec = 50;

      if (mode === 'quench') {
        minTime = 0; maxTime = 10;
        maxSec = 50;
        second = Math.floor(second / 10) * 10;
        if (second < 0) second = 0;
        if (second > maxSec) second = maxSec;
      } else if (mode === 'cold') {
        minTime = 10; maxTime = 30;
      } else if (mode === 'freeze' || mode === 'frozen') {
        minTime = 30; maxTime = 60;
      }

      if (time < minTime) time = minTime;
      if (time > maxTime) time = maxTime;

      timeInput.value = time;
      if (secContainer.style.display !== 'none') {
        secInput.value = second;
      }

      if (mode === 'quench' && time === 0 && second === 0) {
        alert('Time and seconds cannot both be 0 in quench mode.');
        return;
      }
      
      const serviceData = {
        mode: mode,
        time: timeContainer.style.display !== 'none' ? time : 0,
        second: secContainer.style.display !== 'none' ? second : 0
      };

      // appliance_id の決定ロジック
      let resolvedApplianceId = this._applianceId;
      
      // YAMLにappliance_idがなく、entityが指定されている場合は属性から取得
      if (!resolvedApplianceId && this._entity && this._hass.states[this._entity]) {
        const entityState = this._hass.states[this._entity];
        if (entityState.attributes && entityState.attributes.appliance_id) {
          resolvedApplianceId = entityState.attributes.appliance_id;
        }
      }

      if (resolvedApplianceId) {
        serviceData.appliance_id = resolvedApplianceId;
      } else {
        console.error("Appliance ID is missing. Please provide 'appliance_id' or a valid 'entity' in the card config.");
      }

      this._hass.callService('panasonic_japan', 'set_cooloven', serviceData);
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
      timeContainer.style.display = 'flex';
      secContainer.style.display = 'flex';
      timeInput.min = 0;
      timeInput.max = 10;
      timeInput.value = 5;
      secInput.min = 0;
      secInput.max = 50;
      secInput.step = 10;
      secInput.value = 0;
    } else if (mode === 'cold') {
      timeContainer.style.display = 'flex';
      secContainer.style.display = 'none';
      timeInput.min = 10;
      timeInput.max = 30;
      timeInput.value = 15;
    } else if (mode === 'freeze' || mode === 'frozen') {
      timeContainer.style.display = 'flex';
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
      'frozen': t.frozen || 'Frozen'
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

  getCardSize() { return 3; }
}

customElements.define('panasonic-cooloven-card', PanasonicCoolovenCard);
window.customCards = window.customCards || [];
window.customCards.push({
  type: 'panasonic-cooloven-card',
  name: 'Panasonic Cooloven Card',
  description: 'Custom card with manual input clamping and truncation logic.'
});
