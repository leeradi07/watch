// Builds one pledge detail flyer from the data below; the page picks it with data-pledge="1..4".
(function () {
  const PLEDGES = {
    1: {
      kw: "전문성", title: "교섭의 마스터키",
      promise: "교사·연구사·관리자·정책가의 경험으로<br><b>막힌 교섭 해결!</b>",
      howTitle: "네 가지 경험이 <em>열쇠</em>가 됩니다", cols: 2,
      rows: [
        ["교사", "교실의 목소리를 압니다"],
        ["연구사", "근거로 말합니다"],
        ["관리자", "학교 운영의 실제를 압니다"],
        ["정책가", "제도의 언어로 풉니다"],
      ],
      closing: "막힌 교섭 해결!",
    },
    2: {
      kw: "신속성", title: "교권·현안 119",
      promise: "교권 침해·3시 하교제·보결 문제,<br><b>골든타임 내 즉각 출동!</b>",
      howTitle: "이런 현안에 <em>바로</em> 출동합니다", cols: 1,
      rows: [
        ["교권 침해", "선생님 곁으로 바로 갑니다"],
        ["3시 하교제", "현장의 혼란을 바로 짚습니다"],
        ["보결 문제", "과중한 부담을 바로 덜어냅니다"],
      ],
      closing: "골든타임 내 즉각 출동!",
    },
    3: {
      kw: "투명성", title: "클린 메신저",
      promise: "회비 내역부터 공론화 안건까지 회원에게<br><b>투명하게 다이렉트 전달!</b>",
      howTitle: "회원에게 <em>그대로</em> 보여드립니다", cols: 1,
      rows: [
        ["회비 내역", "어디에 쓰였는지 회원이 직접 확인합니다"],
        ["공론화 안건", "결정하기 전에 회원에게 먼저 묻습니다"],
        ["다이렉트 전달", "중간 단계 없이 회원에게 바로 닿습니다"],
      ],
      closing: "투명하게 다이렉트 전달!",
    },
    4: {
      kw: "맞춤형", title: "교육가족 주치의",
      promise: "단체보험 확대부터 저경력 유입·고경력 우대까지<br><b>1:1 맞춤 케어!</b>",
      howTitle: "선생님마다 <em>맞춰</em> 챙깁니다", cols: 2,
      rows: [
        ["단체보험 확대", "교육가족의 든든한 보장"],
        ["저경력 유입", "새내기 선생님을 교총으로"],
        ["고경력 우대", "오래 함께한 선생님께 예우"],
        ["1:1 맞춤 케어", "선생님마다 다른 고민에 맞춰"],
      ],
      closing: "1:1 맞춤 케어!",
    },
  };
  const COLORS = { 1: "#3182f6", 2: "#f04452", 3: "#03b26c", 4: "#fe9800" };

  const sheet = document.getElementById("sheet");
  const n = Number(sheet.dataset.pledge);
  const p = PLEDGES[n];
  const no = String(n).padStart(2, "0");

  const legend = Object.entries(PLEDGES).map(([k, v]) =>
    `<span class="${+k === n ? "on" : ""}"><i style="background:${COLORS[k]}"></i>${v.kw}</span>`).join("");
  const dots = [1, 2, 3, 4].map((k) => `<span class="${k === n ? "on" : ""}"></span>`).join("");
  const rows = p.rows.map(([t, s], i) =>
    `<li><span class="ix">${i + 1}</span><div><p class="t">${t}</p><p class="s">${s}</p></div></li>`).join("");

  sheet.innerHTML = `
    <section class="hero">
      <div class="top">
        <span class="chip"><i></i>부산교총 회장선거 · 배동윤의 4대 약속</span>
        <span class="pager"><b>${no}</b> / 04 <span class="dots">${dots}</span></span>
      </div>
      <div class="head">
        <span class="kw">${p.kw}</span>
        <h1>${p.title}</h1>
        <p class="promise">${p.promise}</p>
      </div>
      <p class="no">${no}</p>
      <div class="panel"><svg viewBox="0 0 300 132" aria-hidden="true">${window.PLEDGE_ART[n - 1]}</svg></div>
    </section>
    <section class="how">
      <h2>${p.howTitle}</h2>
      <ul class="rows ${p.cols === 2 ? "cols-2" : ""}">${rows}</ul>
    </section>
    <section class="band">
      <div><small>배동윤의 약속 ${no} · ${p.kw}</small><strong>${p.closing}</strong></div>
      <span class="mark">${no}</span>
    </section>
    <footer class="foot">
      <div class="who"><img src="assets/candidate.webp" alt=""><div><p class="r">부산교총 회장 후보</p><p class="n">배동윤</p></div></div>
      <div class="legend">${legend}</div>
    </footer>`;
  document.title = `배동윤 약속 ${no} ${p.kw}`;
})();
