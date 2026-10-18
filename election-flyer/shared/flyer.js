// Shared SVG parts (school scene, icons, filters) + burst, fit-to-viewport, ?static.
(function () {
  const NS = "http://www.w3.org/2000/svg";

  // ---- Elementary school scene, 900×380 local box, ground line at y=300 ----
  function schoolWindows() {
    let out = "";
    const floors = [140, 182, 224, 266];
    const cols = [];
    for (let x = 86; x <= 366; x += 40) cols.push(x);
    for (let x = 534; x <= 794; x += 40) cols.push(x);
    floors.forEach((y, f) => {
      cols.forEach((x, c) => {
        if (f === 3 && (c === 3 || c === 12)) return; // side doors
        const lit = (c * 7 + f * 3) % 5 === 0;
        out += `<rect x="${x}" y="${y}" width="28" height="26" rx="2" fill="${lit ? "#e8f3ff" : "#1b64da"}"/>`;
        if (!lit) out += `<path d="M${x + 4} ${y + 22} l10 -18 h5 l-10 18 z" fill="#fff" opacity=".22"/>`;
      });
      // floor slab line
      out += `<rect x="70" y="${y + 32}" width="760" height="3" fill="#8bbcfb"/>`;
    });
    // side doors
    out += `<rect x="206" y="262" width="28" height="38" rx="2" fill="#1e40af"/>`;
    out += `<rect x="654" y="262" width="28" height="38" rx="2" fill="#1e40af"/>`;
    return out;
  }

  // Round-crowned tree: three overlapping lobes + highlight, trunk to the ground line.
  function tree(cx, cy, r) {
    return `<rect x="${cx - 3.5}" y="${cy}" width="7" height="${300 - cy + 4}" rx="2" fill="#1e40af"/>` +
      `<circle cx="${cx - r * 0.55}" cy="${cy + r * 0.2}" r="${r * 0.62}" fill="#1e40af"/>` +
      `<circle cx="${cx + r * 0.55}" cy="${cy + r * 0.25}" r="${r * 0.58}" fill="#1e40af"/>` +
      `<circle cx="${cx}" cy="${cy - r * 0.25}" r="${r * 0.72}" fill="#1e40af"/>` +
      `<circle cx="${cx - r * 0.25}" cy="${cy - r * 0.5}" r="${r * 0.3}" fill="#2a6fe0"/>`;
  }

  const school = `
    <g id="school">
      <!-- far hills + city (Busan skyline haze) -->
      <path d="M-40 236 C 80 186, 200 206, 300 218 S 520 172, 640 204 S 840 184, 940 210 V 300 H -40 Z" fill="#fff" opacity=".1"/>
      <g fill="#fff" opacity=".12">
        <rect x="-10" y="150" width="54" height="150"/><rect x="50" y="122" width="40" height="178"/>
        <rect x="846" y="132" width="48" height="168"/><rect x="900" y="170" width="40" height="130"/>
      </g>

      <!-- main building -->
      <rect x="70" y="128" width="760" height="172" fill="#6ea8fa"/>
      <rect x="62" y="116" width="776" height="14" rx="3" fill="#e8f3ff"/>
      ${schoolWindows()}

      <!-- central tower with clock -->
      <rect x="395" y="80" width="110" height="220" fill="#8bbcfb"/>
      <path d="M383 86 H517 L503 64 H397 Z" fill="#e8f3ff"/>
      <circle cx="450" cy="112" r="23" fill="#fff"/>
      <circle cx="450" cy="112" r="23" fill="none" stroke="#1b64da" stroke-width="3"/>
      <path d="M450 112 V98 M450 112 L461 118" stroke="#1b64da" stroke-width="3.5" stroke-linecap="round"/>
      <rect x="416" y="148" width="22" height="92" rx="3" fill="#1b64da"/>
      <rect x="462" y="148" width="22" height="92" rx="3" fill="#1b64da"/>
      <rect x="404" y="250" width="92" height="9" rx="3" fill="#e8f3ff"/>
      <rect x="418" y="259" width="64" height="41" fill="#1e40af"/>
      <rect x="448" y="259" width="4" height="41" fill="#6ea8fa"/>

      <!-- flagpole -->
      <rect x="607" y="40" width="4" height="260" fill="#fff"/>
      <circle cx="609" cy="38" r="5" fill="#fff"/>
      <path d="M611 46 q 18 -7 38 0 v 24 q -20 -7 -38 0 z" fill="#fff"/>

      <!-- trees -->
      ${tree(24, 262, 40)}${tree(124, 276, 28)}${tree(336, 280, 22)}
      ${tree(560, 278, 22)}${tree(700, 270, 28)}${tree(870, 254, 40)}

      <!-- playground -->
      <rect x="-60" y="300" width="1020" height="140" fill="#1b64da"/>
      <rect x="-60" y="298" width="1020" height="5" fill="#e8f3ff"/>
      <ellipse cx="470" cy="356" rx="330" ry="38" fill="none" stroke="#fff" stroke-opacity=".38" stroke-width="3"/>
      <ellipse cx="470" cy="356" rx="270" ry="24" fill="none" stroke="#fff" stroke-opacity=".2" stroke-width="2"/>
      <path d="M470 318 V 394" stroke="#fff" stroke-opacity=".2" stroke-width="2"/>
      <path d="M96 352 v-30 h64 v30" fill="none" stroke="#fff" stroke-opacity=".8" stroke-width="3.5" stroke-linejoin="round"/>
      <path d="M96 322 l10 8 h44 l10 -8 M106 330 v22 M150 330 v22" fill="none" stroke="#fff" stroke-opacity=".35" stroke-width="2"/>
      <circle cx="232" cy="350" r="7" fill="#fff"/>
      <path d="M228 346 l8 8 M236 346 l-8 8" stroke="#1b64da" stroke-width="1.6"/>
    </g>`;

  const icons = `
    <g id="i-key">
      <circle cx="8" cy="12" r="5.5" fill="#3182f6"/>
      <circle cx="8" cy="12" r="2.2" fill="#e8f3ff"/>
      <path d="M12.5 10.6h9.5v2.8h-2v2.6h-2.6v-2.6h-1.4v1.8h-2.4v-1.8h-1.1z" fill="#3182f6"/>
    </g>
    <g id="i-siren">
      <path d="M5.5 17V12a6.5 6.5 0 0 1 13 0v5z" fill="#3182f6"/>
      <path d="M9 12.2a3 3 0 0 1 3-3" stroke="#e8f3ff" stroke-width="1.6" stroke-linecap="round" fill="none"/>
      <rect x="3.5" y="17" width="17" height="3.6" rx="1.2" fill="#1b64da"/>
      <path d="M12 1.6v2.2M3.4 5.2l1.6 1.5M20.6 5.2 19 6.7M1.4 12h1.8M20.8 12h1.8" stroke="#90c2ff" stroke-width="1.8" stroke-linecap="round"/>
    </g>
    <g id="i-mail">
      <rect x="2" y="5" width="20" height="14.5" rx="2.6" fill="#3182f6"/>
      <path d="M3.4 7.2 12 13.2l8.6-6" stroke="#e8f3ff" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
    </g>
    <g id="i-steth">
      <path d="M5 2.8v5.4a4.5 4.5 0 0 0 9 0V2.8" stroke="#3182f6" stroke-width="2.2" stroke-linecap="round" fill="none"/>
      <path d="M9.5 12.7v2.8a4.8 4.8 0 0 0 9.6 0v-2" stroke="#3182f6" stroke-width="2.2" stroke-linecap="round" fill="none"/>
      <circle cx="19.1" cy="10.6" r="2.9" fill="#1b64da"/>
      <circle cx="19.1" cy="10.6" r="1.1" fill="#e8f3ff"/>
    </g>
    <g id="i-person">
      <circle cx="12" cy="9" r="4.6" fill="currentColor"/>
      <path d="M3.4 22.5a8.6 8.6 0 0 1 17.2 0z" fill="currentColor"/>
    </g>
    <symbol id="tile" viewBox="0 0 80 80" overflow="visible">
      <rect width="80" height="80" rx="20" fill="#fff"/>
    </symbol>
    <g id="cloud">
      <path d="M0 30 a16 16 0 0 1 14 -22 a22 22 0 0 1 40 4 a14 14 0 0 1 18 18 z" fill="#fff"/>
    </g>`;

  const filters = `
    <filter id="echo" x="-10%" y="-10%" width="130%" height="120%">
      <feFlood flood-color="#1e40af" flood-opacity=".55"/>
      <feComposite in2="SourceAlpha" operator="in"/>
      <feOffset dx="-22" dy="8" result="sil"/>
      <feMerge><feMergeNode in="sil"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>`;

  const defs = document.createElementNS(NS, "svg");
  defs.setAttribute("class", "defs");
  defs.setAttribute("aria-hidden", "true");
  defs.innerHTML = `<defs>${filters}${school}${icons}</defs>`;
  document.body.prepend(defs);

  // ---- Impact burst: flat wedges radiating from data-cx/data-cy ----
  document.querySelectorAll("[data-burst]").forEach((g) => {
    const [cx, cy] = g.dataset.burst.split(",").map(Number);
    const R = 1200, n = 22;
    for (let i = 0; i < n; i++) {
      const a = (i / n) * Math.PI * 2 + 0.11;
      const w = i % 3 === 0 ? 0.075 : 0.035;
      const p = document.createElementNS(NS, "polygon");
      const x1 = cx + R * Math.cos(a - w), y1 = cy + R * Math.sin(a - w);
      const x2 = cx + R * Math.cos(a + w), y2 = cy + R * Math.sin(a + w);
      p.setAttribute("points", `${cx},${cy} ${x1.toFixed(1)},${y1.toFixed(1)} ${x2.toFixed(1)},${y2.toFixed(1)}`);
      p.setAttribute("fill", i % 2 ? "#1b64da" : "#5a9cf8");
      p.setAttribute("opacity", i % 2 ? "0.5" : "0.3");
      g.appendChild(p);
    }
  });

  // ---- Fit the A4 artboard to the viewport ----
  const fit = document.getElementById("fit");
  const wrap = document.getElementById("fitWrap");
  function resize() {
    const s = Math.min(1, (window.innerWidth - 32) / 794);
    fit.style.transform = `scale(${s})`;
    wrap.style.width = 794 * s + "px";
    wrap.style.height = 1123 * s + "px";
  }
  if (!matchMedia("print").matches) { resize(); addEventListener("resize", resize); }

  // ---- Use the stock school photo when it is present, else keep the vector scene ----
  const sheet = document.getElementById("sheet");
  document.querySelectorAll("image[data-photo]").forEach((img) => {
    const probe = new Image();
    probe.onload = () => sheet.classList.add("has-photo");
    probe.src = img.getAttribute("href");
  });

  // ---- ?static disables motion (used by the PNG/PDF renderer) ----
  if (new URLSearchParams(location.search).has("static")) {
    sheet.classList.remove("anim");
  }
})();
