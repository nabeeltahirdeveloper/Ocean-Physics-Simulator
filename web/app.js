(() => {
  "use strict";

  const GROUPS = {
    Wind: [
      ["Wind speed", "windSpeed", 0, 40, 0.1, "m/s"],
      ["Wind direction", "windDirection", 0, 360, 1, "°"],
      ["Wind duration", "windDuration", 0.1, 72, 0.1, "h"],
      ["Fetch", "fetch", 1, 800, 1, "km"],
      ["Gustiness", "gustiness", 0, 0.6, 0.01, ""],
      ["Directional spread", "directionalSpread", 2, 80, 1, "°"],
      ["Air density", "airDensity", 0.8, 1.5, 0.005, "kg/m³"],
    ],
    Earth: [
      ["Gravity", "gravity", 1, 20, 0.01, "m/s²"],
      ["Earth rotation", "earthRotation", 0, 3, 0.01, "×"],
      ["Latitude", "latitude", -90, 90, 0.1, "°"],
      ["Earth radius", "earthRadius", 0.5, 2, 0.01, "×"],
    ],
    Astronomy: [
      ["Moon gravity", "moonGravity", 0, 3, 0.01, "×"],
      ["Moon distance", "moonDistance", 0.8, 1.2, 0.001, "×"],
      ["Moon phase", "moonPhase", 0, 1, 0.01, ""],
      ["Moon declination", "moonDeclination", -28.6, 28.6, 0.1, "°"],
      ["Moon orbit", "moonOrbit", 0, 360, 1, "°"],
      ["Sun gravity", "sunGravity", 0, 3, 0.01, "×"],
      ["Sun distance", "sunDistance", 0.97, 1.03, 0.001, "×"],
      ["Sun position", "sunPosition", 0, 360, 1, "°"],
    ],
    Water: [
      ["Water depth", "depth", 1, 500, 0.5, "m"],
      ["Temperature", "temperature", -2, 35, 0.1, "°C"],
      ["Salinity", "salinity", 0, 42, 0.1, "PSU"],
      ["Surface tension", "surfaceTension", 0.02, 0.1, 0.001, "N/m"],
      ["Viscosity", "viscosity", 0.1, 10, 0.1, "×"],
      ["Wave damping", "damping", 0, 0.001, 0.00001, "1/s"],
      ["Seabed slope", "seabedSlope", -0.15, 0.15, 0.001, ""],
      ["Seabed roughness", "seabedRoughness", 0, 1, 0.01, ""],
      ["Breaking ratio", "breakingLimit", 0.3, 1.2, 0.01, ""],
      ["Coastal reflection", "coastalReflection", 0, 0.8, 0.01, ""],
    ],
    Waves: [
      ["Swell height", "swellHeight", 0, 10, 0.05, "m"],
      ["Swell period", "swellPeriod", 3, 25, 0.1, "s"],
      ["Swell direction", "swellDirection", 0, 360, 1, "°"],
      ["Wave steepness", "waveSteepness", 0.1, 2, 0.01, "×"],
    ],
    Weather: [
      ["Current speed", "currentSpeed", -3, 3, 0.01, "m/s"],
      ["Current direction", "currentDirection", 0, 360, 1, "°"],
      ["Current shear", "currentShear", -0.01, 0.01, 0.0001, "1/s"],
      ["Air pressure", "pressure", 900, 1060, 0.5, "hPa"],
      ["Storm surge", "stormSurge", -1, 8, 0.05, "m"],
      ["Rain intensity", "rainIntensity", 0, 150, 0.5, "mm/h"],
    ],
    Display: [
      ["Simulation speed", "timeScale", 0.05, 500, 0.05, "×"],
      ["Vertical scale", "verticalScale", 0.2, 8, 0.05, "×"],
    ],
  };

  const DEFAULTS = {
    windSpeed: 12, windDirection: 35, windDuration: 6, fetch: 50,
    gustiness: 0.12, directionalSpread: 25, airDensity: 1.225,
    gravity: 9.81, earthRotation: 1, latitude: 24.86, earthRadius: 1,
    moonGravity: 1, moonDistance: 1, moonPhase: 0.5,
    moonDeclination: 5.1, moonOrbit: 0, sunGravity: 1,
    sunDistance: 1, sunPosition: 0, depth: 80, temperature: 18,
    salinity: 35, surfaceTension: 0.074, viscosity: 1, damping: 0.00001,
    seabedSlope: 0, seabedRoughness: 0.15, breakingLimit: 0.78,
    coastalReflection: 0.08, swellHeight: 0.8, swellPeriod: 11,
    swellDirection: 210, waveSteepness: 1, currentSpeed: 0.35,
    currentDirection: 90, currentShear: 0, pressure: 1013.25,
    stormSurge: 0, rainIntensity: 0, timeScale: 1, verticalScale: 1.8,
  };

  const state = { ...DEFAULTS };
  const canvas = document.getElementById("oceanCanvas");
  const ctx = canvas.getContext("2d", { alpha: false });
  const controls = document.getElementById("controlsContainer");
  const tabs = document.getElementById("factorTabs");
  const activeTitle = document.getElementById("activeGroupTitle");
  const statusText = document.querySelector(".status");
  let activeGroup = "Wind";
  let paused = false;
  let simTime = 0;
  let previousTime = performance.now();
  let azimuth = -0.72;
  let elevation = 0.63;
  let zoom = 1;
  let dragging = false;
  let lastPointer = null;
  let seed = 91827;
  let modes = [];
  let significantHeight = 1.2;
  let peakPeriod = 7.5;

  const clamp = (x, a, b) => Math.max(a, Math.min(b, x));
  const radians = d => d * Math.PI / 180;
  const fmt = value => {
    const abs = Math.abs(value);
    if (abs !== 0 && abs < 0.01) return value.toFixed(5);
    if (abs < 10) return value.toFixed(2).replace(/0+$/, "").replace(/\.$/, "");
    return value.toFixed(1).replace(/\.0$/, "");
  };
  const rngFactory = initial => {
    let a = initial >>> 0;
    return () => {
      a += 0x6D2B79F5;
      let t = a;
      t = Math.imul(t ^ t >>> 15, t | 1);
      t ^= t + Math.imul(t ^ t >>> 7, t | 61);
      return ((t ^ t >>> 14) >>> 0) / 4294967296;
    };
  };
  const gaussian = rng => {
    const u = Math.max(rng(), 1e-9);
    return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * rng());
  };

  function rebuildSpectrum() {
    const rng = rngFactory(seed);
    const wind = Math.max(state.windSpeed, 0.2);
    const fetchGrowth = Math.tanh(0.0125 * Math.pow(state.gravity * state.fetch * 1000 / (wind * wind), 0.42));
    const durationGrowth = Math.tanh(state.windDuration * 3600 / Math.max(2500 * wind / state.gravity, 1));
    significantHeight = clamp(
      0.21 * wind * wind / state.gravity *
      Math.min(fetchGrowth, durationGrowth) *
      Math.sqrt(state.airDensity / 1.225) * (1 + .8 * state.gustiness),
      .02, 18
    );
    peakPeriod = clamp(
      5.8 + wind * .18 + Math.log10(Math.max(state.fetch, 1)) * .7,
      1.2, 18
    );
    const baseDirection = radians(state.windDirection);
    const spread = radians(state.directionalSpread);
    const weights = [];
    modes = Array.from({ length: 60 }, (_, i) => {
      const ratio = Math.exp(gaussian(rng) * .5);
      const wavelength = clamp(peakPeriod * peakPeriod * state.gravity / (2 * Math.PI) / ratio, 8, 500);
      const k = 2 * Math.PI / wavelength;
      const angle = baseDirection + gaussian(rng) * spread;
      const spectral = Math.exp(-Math.pow(Math.log(ratio), 2) / .52) / (1 + ratio * ratio * .14);
      weights.push(spectral);
      return { k, angle, phase: rng() * Math.PI * 2, gustPhase: rng() * Math.PI * 2, spectral };
    });
    const total = weights.reduce((a, b) => a + b, 0);
    const target = significantHeight / 4;
    modes.forEach(m => {
      m.amplitude = Math.sqrt(m.spectral / total) * target * .52 * state.waveSteepness;
      const capillary = state.surfaceTension * Math.pow(m.k, 3) / Math.max(1000 + .78 * state.salinity - .2 * state.temperature, 900);
      m.omega = Math.sqrt((state.gravity * m.k + capillary) * Math.tanh(m.k * state.depth));
    });
  }

  function tidalElevation(t) {
    const moonAmp = .356 * state.moonGravity * state.earthRadius ** 2 /
      Math.max(state.gravity / 9.81, .1) / state.moonDistance ** 3 *
      (.5 + .5 * Math.cos(radians(state.moonDeclination)));
    const sunAmp = .164 * state.sunGravity * state.earthRadius ** 2 /
      Math.max(state.gravity / 9.81, .1) / state.sunDistance ** 3;
    const moon = moonAmp * Math.cos(2 * Math.PI * t / 44714 +
      4 * Math.PI * state.moonPhase + radians(2 * state.moonOrbit));
    const sun = sunAmp * Math.cos(2 * Math.PI * t / 43200 + radians(2 * state.sunPosition));
    return moon + sun;
  }

  function surfaceHeight(x, y, t) {
    const currentAngle = radians(state.currentDirection) +
      2 * 7.292115e-5 * state.earthRotation * Math.sin(radians(state.latitude)) * t;
    const u = state.currentSpeed * Math.cos(currentAngle);
    const v = state.currentSpeed * Math.sin(currentAngle);
    const physicalX = x * 250;
    const physicalY = y * 250;
    let z = 0;
    const rainDamping = Math.exp(-(state.damping + state.rainIntensity * 2e-8 + state.seabedRoughness * 2e-6) * t);
    for (const m of modes) {
      const kx = m.k * Math.cos(m.angle);
      const ky = m.k * Math.sin(m.angle);
      const gust = 1 + state.gustiness * Math.sin(.17 * t + m.gustPhase);
      const phase = kx * physicalX + ky * physicalY -
        (m.omega + kx * u + ky * v + kx * state.currentShear * physicalY) * t + m.phase;
      z += m.amplitude * gust * rainDamping * Math.cos(phase);
    }
    const swellK = Math.pow(2 * Math.PI / state.swellPeriod, 2) / state.gravity;
    const swellAngle = radians(state.swellDirection);
    z += state.swellHeight * .42 * Math.cos(
      swellK * (physicalX * Math.cos(swellAngle) + physicalY * Math.sin(swellAngle)) -
      2 * Math.PI * t / state.swellPeriod
    );
    const localDepth = Math.max(.5, state.depth + state.seabedSlope * physicalX);
    z *= clamp(Math.sqrt(state.depth / localDepth), .45, 2.3);
    z += state.coastalReflection * .16 * Math.sin(11 * x + t * .7);
    const breaker = Math.max(state.breakingLimit * localDepth / 2, .1);
    z = clamp(z, -breaker, breaker);
    const rho = 999.8 + .78 * state.salinity - .2 * state.temperature;
    const pressure = -(state.pressure * 100 - 101325) / (rho * state.gravity);
    return z + tidalElevation(t) + pressure + state.stormSurge;
  }

  function resize() {
    const rect = canvas.getBoundingClientRect();
    const dpr = Math.min(devicePixelRatio || 1, 2);
    const width = Math.max(1, Math.floor(rect.width * dpr));
    const height = Math.max(1, Math.floor(rect.height * dpr));
    if (canvas.width !== width || canvas.height !== height) {
      canvas.width = width;
      canvas.height = height;
    }
  }

  function project(x, y, z) {
    const ca = Math.cos(azimuth), sa = Math.sin(azimuth);
    const ce = Math.cos(elevation), se = Math.sin(elevation);
    const xr = x * ca - y * sa;
    const yr = x * sa + y * ca;
    const scaledZ = z * .15 * state.verticalScale;
    const vertical = yr * se - scaledZ * ce;
    const depth = yr * ce + scaledZ * se;
    const scale = Math.min(canvas.width, canvas.height) * .38 * zoom;
    const perspective = 1 / (1.22 + depth * .14);
    return {
      x: canvas.width * .5 + xr * scale * perspective,
      y: canvas.height * .47 + vertical * scale * perspective,
      depth,
      z,
    };
  }

  function render() {
    resize();
    const w = canvas.width, h = canvas.height;
    const bg = ctx.createRadialGradient(w * .52, h * .42, 10, w * .52, h * .42, Math.max(w, h) * .75);
    bg.addColorStop(0, "#0c2b3b");
    bg.addColorStop(.55, "#071a28");
    bg.addColorStop(1, "#030c15");
    ctx.fillStyle = bg;
    ctx.fillRect(0, 0, w, h);

    const cols = w < 900 ? 28 : 38;
    const rows = w < 900 ? 23 : 30;
    const points = [];
    for (let j = 0; j <= rows; j++) {
      const row = [];
      for (let i = 0; i <= cols; i++) {
        const x = i / cols * 2 - 1;
        const y = j / rows * 2 - 1;
        row.push(project(x, y, surfaceHeight(x, y, simTime)));
      }
      points.push(row);
    }
    const polygons = [];
    for (let j = 0; j < rows; j++) {
      for (let i = 0; i < cols; i++) {
        const p = [points[j][i], points[j][i + 1], points[j + 1][i + 1], points[j + 1][i]];
        polygons.push({ p, depth: p.reduce((s, q) => s + q.depth, 0) / 4, z: p.reduce((s, q) => s + q.z, 0) / 4 });
      }
    }
    polygons.sort((a, b) => b.depth - a.depth);
    const range = Math.max(significantHeight * .65 + state.swellHeight * .25, .35);
    for (const poly of polygons) {
      const normalized = clamp((poly.z - state.stormSurge + range) / (range * 2), 0, 1);
      const hue = 201 - normalized * 17;
      const light = 13 + normalized * 45;
      ctx.beginPath();
      ctx.moveTo(poly.p[0].x, poly.p[0].y);
      for (let n = 1; n < 4; n++) ctx.lineTo(poly.p[n].x, poly.p[n].y);
      ctx.closePath();
      ctx.fillStyle = `hsl(${hue} 84% ${light}%)`;
      ctx.fill();
      ctx.strokeStyle = "rgba(114,216,245,.105)";
      ctx.lineWidth = Math.max(0.45, devicePixelRatio * .35);
      ctx.stroke();
    }

    const glow = ctx.createLinearGradient(0, h * .5, 0, h);
    glow.addColorStop(0, "rgba(9,76,103,0)");
    glow.addColorStop(1, "rgba(2,8,14,.38)");
    ctx.fillStyle = glow;
    ctx.fillRect(0, h * .5, w, h * .5);
  }

  function createTabs() {
    tabs.innerHTML = "";
    const abbreviations = ["WND", "EAR", "AST", "H₂O", "WAV", "ENV", "UI"];
    Object.keys(GROUPS).forEach((group, index) => {
      const button = document.createElement("button");
      button.className = "factor-tab" + (group === activeGroup ? " active" : "");
      button.type = "button";
      button.role = "tab";
      button.title = group;
      button.textContent = abbreviations[index];
      button.addEventListener("click", () => {
        activeGroup = group;
        createTabs();
        createControls();
      });
      tabs.append(button);
    });
  }

  function createControls() {
    controls.innerHTML = "";
    activeTitle.textContent = activeGroup;
    for (const [label, key, min, max, step, unit] of GROUPS[activeGroup]) {
      const row = document.createElement("div");
      row.className = "control-row";
      const meta = document.createElement("div");
      meta.className = "control-meta";
      const labelEl = document.createElement("label");
      const id = `factor-${key}`;
      labelEl.htmlFor = id;
      labelEl.textContent = label;
      const value = document.createElement("span");
      value.className = "control-value";
      value.textContent = `${fmt(state[key])}${unit ? ` ${unit}` : ""}`;
      const input = document.createElement("input");
      input.type = "range";
      input.id = id;
      input.min = min;
      input.max = max;
      input.step = step;
      input.value = state[key];
      input.setAttribute("aria-label", label);
      const updateFill = () => input.style.setProperty("--fill", `${(input.value - min) / (max - min) * 100}%`);
      updateFill();
      input.addEventListener("input", () => {
        state[key] = Number(input.value);
        value.textContent = `${fmt(state[key])}${unit ? ` ${unit}` : ""}`;
        updateFill();
        if (!["timeScale", "verticalScale", "currentSpeed", "currentDirection", "pressure", "stormSurge"].includes(key)) rebuildSpectrum();
      });
      meta.append(labelEl, value);
      row.append(meta, input);
      controls.append(row);
    }
  }

  function updateStats() {
    const tide = tidalElevation(simTime);
    document.getElementById("statHeight").textContent = `${significantHeight.toFixed(2)} m`;
    document.getElementById("statPeriod").textContent = `${peakPeriod.toFixed(1)} s`;
    document.getElementById("statTide").textContent = `${tide >= 0 ? "+" : ""}${tide.toFixed(2)} m`;
    document.getElementById("statCurrent").textContent = `${Math.abs(state.currentSpeed).toFixed(2)} m/s`;
    const total = Math.floor(simTime);
    const hours = String(Math.floor(total / 3600)).padStart(2, "0");
    const minutes = String(Math.floor(total % 3600 / 60)).padStart(2, "0");
    const seconds = String(total % 60).padStart(2, "0");
    document.getElementById("simTime").textContent = `${hours}:${minutes}:${seconds}`;
  }

  function animate(now) {
    const dt = Math.min((now - previousTime) / 1000, .1);
    previousTime = now;
    if (!paused) simTime += dt * state.timeScale;
    render();
    updateStats();
    requestAnimationFrame(animate);
  }

  canvas.addEventListener("pointerdown", event => {
    dragging = true;
    lastPointer = [event.clientX, event.clientY];
    canvas.setPointerCapture(event.pointerId);
  });
  canvas.addEventListener("pointermove", event => {
    if (!dragging) return;
    azimuth += (event.clientX - lastPointer[0]) * .007;
    elevation = clamp(elevation + (event.clientY - lastPointer[1]) * .005, .18, 1.22);
    lastPointer = [event.clientX, event.clientY];
  });
  canvas.addEventListener("pointerup", () => { dragging = false; });
  canvas.addEventListener("pointercancel", () => { dragging = false; });
  canvas.addEventListener("wheel", event => {
    event.preventDefault();
    zoom = clamp(zoom * Math.exp(-event.deltaY * .001), .55, 1.8);
  }, { passive: false });

  document.getElementById("pauseButton").addEventListener("click", event => {
    paused = !paused;
    event.currentTarget.textContent = paused ? "▶" : "Ⅱ";
    event.currentTarget.setAttribute("aria-label", paused ? "Resume simulation" : "Pause simulation");
    statusText.textContent = paused ? "PAUSED" : "RUNNING";
    statusText.style.color = paused ? "#ffd86a" : "#4fffb0";
  });
  document.getElementById("resetButton").addEventListener("click", () => {
    seed = (seed + 1013) >>> 0;
    simTime = 0;
    rebuildSpectrum();
  });
  document.getElementById("defaultsButton").addEventListener("click", () => {
    Object.assign(state, DEFAULTS);
    rebuildSpectrum();
    createControls();
  });
  document.getElementById("fullscreenButton").addEventListener("click", () => {
    const shell = document.querySelector(".app-shell");
    if (!document.fullscreenElement) shell.requestFullscreen?.();
    else document.exitFullscreen?.();
  });
  window.addEventListener("keydown", event => {
    if (event.code === "Space" && !["INPUT", "BUTTON"].includes(document.activeElement.tagName)) {
      event.preventDefault();
      document.getElementById("pauseButton").click();
    }
    if (event.key.toLowerCase() === "r" && document.activeElement.tagName !== "INPUT") {
      document.getElementById("resetButton").click();
    }
  });

  createTabs();
  createControls();
  rebuildSpectrum();
  requestAnimationFrame(animate);
})();
