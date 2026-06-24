/**
 * ==========================================================================
 * JavaScript Controller for Interactive Clock Learning Program
 * ==========================================================================
 */

document.addEventListener('DOMContentLoaded', () => {
    // --- State Variables ---
    let totalSeconds = 9 * 3600; // Default: 9:00 AM (9 * 3600 seconds)
    let totalSecondsFloat = 9 * 3600; // Floating-point seconds accumulator for smooth drag math
    let startSeconds = 9 * 3600; // Saved start time for reset
    let showSeconds = true;
    let activeHand = null;
    let prevDragAngle = 0;
    
    // --- DOM Elements ---
    // Screens
    const setupScreen = document.getElementById('setup-screen');
    const studyScreen = document.getElementById('study-screen');
    
    // Setup Inputs
    const toggleSecondsInput = document.getElementById('toggle-seconds');
    const startAmpmSelect = document.getElementById('start-ampm');
    const startHourSelect = document.getElementById('start-hour');
    const startMinuteSelect = document.getElementById('start-minute');
    const btnStart = document.getElementById('btn-start');
    
    // Study Controls
    const btnBack = document.getElementById('btn-back');
    const btnReset = document.getElementById('btn-reset');
    
    // Clock Face Elements
    const clockOuter = document.querySelector('.clock-outer');
    const clockFace = document.getElementById('clock-face');
    const clockNumbersContainer = document.getElementById('clock-numbers');
    const clockTicksContainer = document.getElementById('clock-ticks');
    const hourHand = document.getElementById('hour-hand');
    const minuteHand = document.getElementById('minute-hand');
    const secondHand = document.getElementById('second-hand');
    const showMinuteGuidesCheckbox = document.getElementById('show-minute-guides');
    
    // Routine Elements
    const routineCard = document.getElementById('routine-card');
    const routineIllustration = document.getElementById('routine-illustration');
    const routineTitle = document.getElementById('routine-title');
    const routineDesc = document.getElementById('routine-desc');
    
    // Quiz Elements
    const quizOverlay = document.getElementById('quiz-overlay');
    const btnReveal = document.getElementById('btn-reveal');
    const btnHideAnswer = document.getElementById('btn-hide-answer');
    const alwaysShowDigitalCheckbox = document.getElementById('always-show-digital');
    const digAmpm = document.getElementById('dig-ampm');
    const digTime = document.getElementById('dig-time');
    const digSecContainer = document.getElementById('dig-sec-container');
    const digSec = document.getElementById('dig-sec');

    // --- Routine Schedule Configuration ---
    const routines = [
        {
            start: 0, end: 6 * 3600, // 00:00 - 06:00
            title: "새근새근 잠자는 시간",
            desc: "쿨쿨, 깊은 잠에 들어 꿈나라를 여행해요. 몸과 마음이 쑥쑥 자라납니다.",
            illustration: "💤",
            class: "routine-sleep"
        },
        {
            start: 6 * 3600, end: 7.5 * 3600, // 06:00 - 07:30
            title: "기상 및 아침 준비",
            desc: "새로운 하루가 시작되었어요! 기지개를 크게 켜고 자리에서 일어나요.",
            illustration: "🌅",
            class: "routine-wakeup"
        },
        {
            start: 7.5 * 3600, end: 8.5 * 3600, // 07:30 - 08:30
            title: "맛있는 아침 식사",
            desc: "아침밥은 하루의 에너지가 돼요. 골고루 든든하게 먹어요.",
            illustration: "🍞",
            class: "routine-breakfast"
        },
        {
            start: 8.5 * 3600, end: 9 * 3600, // 08:30 - 09:00
            title: "학교 가는 시간 (등교)",
            desc: "책가방을 메고 친구들과 선생님을 만나러 힘차게 걸어가요. 차 조심해서 걷기!",
            illustration: "🎒",
            class: "routine-toschool"
        },
        {
            start: 9 * 3600, end: 12 * 3600, // 09:00 - 12:00
            title: "즐거운 학교 수업",
            desc: "선생님 말씀에 귀를 기울이고 적극적으로 대답하며 지식을 쌓아요.",
            illustration: "✏️",
            class: "routine-schoollife"
        },
        {
            start: 12 * 3600, end: 13 * 3600, // 12:00 - 13:00
            title: "행복한 점심 시간",
            desc: "기다리고 기다리던 점심시간! 친구들과 맛있는 급식을 먹어요.",
            illustration: "🍱",
            class: "routine-lunch"
        },
        {
            start: 13 * 3600, end: 15.5 * 3600, // 13:00 - 15:30
            title: "오후 활동 및 공부",
            desc: "오후 수업을 듣거나 도서관에서 재미있는 책을 읽으며 꿈을 키워요.",
            illustration: "📚",
            class: "routine-study"
        },
        {
            start: 15.5 * 3600, end: 18 * 3600, // 15:30 - 18:00
            title: "신나는 자유 시간 (놀이)",
            desc: "숙제도 하고 놀이터에서 친구들과 축구도 하며 재미있게 뛰어놀아요.",
            illustration: "⚽",
            class: "routine-play"
        },
        {
            start: 18 * 3600, end: 19.5 * 3600, // 18:00 - 19:30
            title: "가족과의 저녁 식사",
            desc: "집으로 돌아와 가족들과 함께 따뜻한 밥을 먹으며 오늘 일어난 일을 이야기해요.",
            illustration: "🍲",
            class: "routine-dinner"
        },
        {
            start: 19.5 * 3600, end: 21 * 3600, // 19:30 - 21:00
            title: "가족 시간 및 독서",
            desc: "내일 공부할 준비를 마친 뒤, 가족들과 거실에서 오순도순 이야기하거나 독서를 해요.",
            illustration: "🏠",
            class: "routine-family"
        },
        {
            start: 21 * 3600, end: 22 * 3600, // 21:00 - 22:00
            title: "하루 마무리 & 씻기",
            desc: "양치를 깨끗이 하고 샤워를 한 뒤, 편안한 잠옷으로 갈아입어요.",
            illustration: "🧼",
            class: "routine-bedprep"
        },
        {
            start: 22 * 3600, end: 24 * 3600, // 22:00 - 24:00
            title: "새근새근 잠자는 시간",
            desc: "밤이 깊었어요. 내일의 활기찬 하루를 위해 눈을 감고 예쁜 꿈을 꿔요.",
            illustration: "💤",
            class: "routine-sleep"
        }
    ];

    // --- Draw Clock Elements (Numbers and Ticks) ---
    function initializeClockFace() {
        clockNumbersContainer.innerHTML = '';
        clockTicksContainer.innerHTML = '';
        
        // 1. Create Numbers 1 to 12
        for (let i = 1; i <= 12; i++) {
            const numberEl = document.createElement('div');
            numberEl.className = 'clock-number';
            numberEl.innerText = i;
            clockNumbersContainer.appendChild(numberEl);
        }
        
        // 2. Create Ticks and Minute Labels (0-59)
        for (let i = 0; i < 60; i++) {
            const angleDeg = i * 6;
            
            // Ticks lines (rendered & rotated responsively)
            const tickEl = document.createElement('div');
            tickEl.className = 'clock-tick';
            if (i % 5 === 0) {
                tickEl.classList.add('five-min');
            }
            tickEl.style.transform = `translateX(-50%) rotate(${angleDeg}deg)`;
            clockTicksContainer.appendChild(tickEl);
            
            // Minute guides (ALL numbers 0 to 59)
            const guideEl = document.createElement('div');
            guideEl.className = 'clock-tick-label';
            if (i % 5 === 0) {
                guideEl.classList.add('five-min-label');
            }
            guideEl.innerText = i; 
            clockTicksContainer.appendChild(guideEl);
        }
    }

    // --- Dynamic Positioning based on Rendered Size ---
    function positionClockNumbersAndGuides() {
        const rect = clockFace.getBoundingClientRect();
        const size = rect.width;
        if (size === 0) return; // Not visible/rendered yet
        
        const numberRadius = size * 0.355;
        const tickRadius = size * 0.44;
        
        // Reposition numbers
        const numberEls = clockNumbersContainer.querySelectorAll('.clock-number');
        numberEls.forEach((numberEl, idx) => {
            const i = idx + 1;
            const angleRad = (i * 30) * (Math.PI / 180);
            numberEl.style.left = `calc(50% + ${numberRadius * Math.sin(angleRad)}px)`;
            numberEl.style.top = `calc(50% - ${numberRadius * Math.cos(angleRad)}px)`;
        });
        
        // Reposition tick labels
        const tickLabelEls = clockTicksContainer.querySelectorAll('.clock-tick-label');
        tickLabelEls.forEach((labelEl, idx) => {
            const i = idx;
            const angleRad = (i * 6) * (Math.PI / 180);
            labelEl.style.left = `calc(50% + ${tickRadius * Math.sin(angleRad)}px)`;
            labelEl.style.top = `calc(50% - ${tickRadius * Math.cos(angleRad)}px)`;
        });
    }

    // --- Time Conversion Helpers ---
    function formatTime(secs) {
        // Wrap 24 hours
        secs = (secs % 86400 + 86400) % 86400;
        
        const h24 = Math.floor(secs / 3600);
        const m = Math.floor((secs % 3600) / 60);
        const s = Math.round(secs) % 60; // Natural (integer) seconds only
        
        const isPM = h24 >= 12;
        const ampmText = isPM ? "오후" : "오전";
        
        let h12 = h24 % 12;
        if (h12 === 0) h12 = 12; // 0 o'clock is 12 in 12-hour format
        
        const hString = h12.toString().padStart(2, '0');
        const mString = m.toString().padStart(2, '0');
        const sString = s.toString().padStart(2, '0');
        
        return {
            h24,
            h12,
            m,
            s,
            isPM,
            ampmText,
            digitalString: `${hString}:${mString}`,
            fullTooltipString: `${ampmText} ${h12}시 ${m}분`
        };
    }

    // --- Update UI elements based on state `totalSeconds` ---
    function updateUI() {
        const timeInfo = formatTime(totalSeconds);
        
        // 1. Rotate Clock Hands
        // Hour Hand: 12 hours = 43200 seconds = 360 degrees. 1 deg = 120 secs.
        const hourAngle = (totalSeconds % 43200) / 120; 
        hourHand.style.transform = `translateX(-50%) rotate(${hourAngle}deg)`;
        
        // Minute Hand: 60 minutes = 3600 seconds = 360 degrees. 1 deg = 10 secs.
        const minuteAngle = (totalSeconds % 3600) / 10;
        minuteHand.style.transform = `translateX(-50%) rotate(${minuteAngle}deg)`;
        
        // Keep hand labels upright
        const hourLabel = hourHand.querySelector('.hand-cap-label');
        const minuteLabel = minuteHand.querySelector('.hand-cap-label');
        if (hourLabel) hourLabel.style.transform = `translateX(-50%) translateY(5px) rotate(${-hourAngle}deg)`;
        if (minuteLabel) minuteLabel.style.transform = `translateX(-50%) translateY(20px) rotate(${-minuteAngle}deg)`;
        
        // Second Hand: 60 seconds = 360 degrees. 1 deg = 1/6 secs (6 deg per sec).
        if (showSeconds) {
            const secondAngle = (totalSeconds % 60) * 6;
            secondHand.style.transform = `translateX(-50%) rotate(${secondAngle}deg)`;
            secondHand.style.display = 'block';
            digSecContainer.style.display = 'inline-block';
        } else {
            secondHand.style.display = 'none';
            digSecContainer.style.display = 'none';
        }
        
        // 2. Update Routine Display
        updateRoutine(timeInfo.h24 * 3600 + timeInfo.m * 60 + timeInfo.s);
        
        // 4. Update Digital Clock Quiz display
        digAmpm.innerText = timeInfo.ampmText;
        digTime.innerText = `${timeInfo.h12.toString().padStart(2, '0')}:${timeInfo.m.toString().padStart(2, '0')}`;
        digSec.innerText = timeInfo.s.toString().padStart(2, '0');
    }

    // --- Update Routine Section ---
    function updateRoutine(secondsInDay) {
        // Find matching routine
        const matched = routines.find(r => secondsInDay >= r.start && secondsInDay < r.end) || routines[routines.length - 1];
        
        // Remove all routine styling classes
        routines.forEach(r => {
            if (r.class) routineCard.classList.remove(r.class);
        });
        
        // Add new class
        if (matched.class) {
            routineCard.classList.add(matched.class);
        }
        
        // Update texts (removed time badge updates)
        routineIllustration.innerHTML = `<div class="illustration-placeholder">${matched.illustration}</div>`;
        routineTitle.innerText = matched.title;
        routineDesc.innerText = matched.desc;
    }

    // --- Angle Calculation for Dragging ---
    function getAngleFromPoint(clientX, clientY) {
        const rect = clockFace.getBoundingClientRect();
        const cx = rect.left + rect.width / 2;
        const cy = rect.top + rect.height / 2;
        
        const dx = clientX - cx;
        const dy = clientY - cy;
        
        // Angle in degrees from 12 o'clock (0 to 360 clockwise)
        let angle = Math.atan2(dx, -dy) * (180 / Math.PI);
        if (angle < 0) angle += 360;
        return angle;
    }

    // --- Update Time based on delta offset ---
    function updateClockTime(deltaSeconds) {
        totalSeconds += deltaSeconds;
        
        // Keep within 24 hours (0 to 86400)
        totalSeconds = (totalSeconds % 86400 + 86400) % 86400;
        
        updateUI();
    }

    // --- Event Listeners for Dragging Hands ---
    function setupDragging() {
        const onDragStart = (e) => {
            const targetHand = e.target.closest('.hand');
            if (!targetHand) return;
            
            const handType = targetHand.getAttribute('data-hand');
            if (handType !== 'hour' && handType !== 'minute') return;
            
            activeHand = handType;
            clockOuter.classList.add('dragging');
            
            const clientX = e.clientX || (e.touches && e.touches[0].clientX);
            const clientY = e.clientY || (e.touches && e.touches[0].clientY);
            
            prevDragAngle = getAngleFromPoint(clientX, clientY);
            
            // Snap seconds to 0 once at the start of drag
            const rem = totalSeconds % 60;
            totalSeconds = totalSeconds - rem;
            updateUI();
            
            e.preventDefault(); // Prevent text selection/scrolling
        };
        
        const onDragMove = (e) => {
            if (!activeHand) return;
            
            const clientX = e.clientX || (e.touches && e.touches[0].clientX);
            const clientY = e.clientY || (e.touches && e.touches[0].clientY);
            
            if (clientX === undefined || clientY === undefined) return;
            
            const currentAngle = getAngleFromPoint(clientX, clientY);
            
            let dAngle = currentAngle - prevDragAngle;
            // Handle cross-boundary wrapping (e.g. from 359deg to 1deg or vice versa)
            if (dAngle > 180) dAngle -= 360;
            if (dAngle < -180) dAngle += 360;
            
            let deltaSeconds = 0;
            if (activeHand === 'minute') {
                // Minute hand: 360 deg = 3600 sec. So 1 deg = 10 sec.
                deltaSeconds = dAngle * 10;
            } else if (activeHand === 'hour') {
                // Hour hand: 360 deg = 12 hours = 43200 sec. So 1 deg = 120 sec.
                deltaSeconds = dAngle * 120;
            }
            
            updateClockTime(deltaSeconds);
            prevDragAngle = currentAngle;
            
            e.preventDefault();
        };
        
        const onDragEnd = () => {
            if (activeHand) {
                activeHand = null;
                clockOuter.classList.remove('dragging');
            }
        };

        // Desktop Mouse Events
        clockFace.addEventListener('mousedown', onDragStart);
        window.addEventListener('mousemove', onDragMove);
        window.addEventListener('mouseup', onDragEnd);
        
        // Mobile Touch Events
        clockFace.addEventListener('touchstart', onDragStart, { passive: false });
        window.addEventListener('touchmove', onDragMove, { passive: false });
        window.addEventListener('touchend', onDragEnd);
    }

    // --- General App Event Handlers ---
    
    // Toggle Minute Guides
    showMinuteGuidesCheckbox.addEventListener('change', (e) => {
        if (e.target.checked) {
            clockFace.classList.add('show-guides');
        } else {
            clockFace.classList.remove('show-guides');
        }
    });

    // Quiz Reveal/Hide answer
    btnReveal.addEventListener('click', () => {
        quizOverlay.classList.remove('active');
    });

    btnHideAnswer.addEventListener('click', () => {
        quizOverlay.classList.add('active');
    });

    alwaysShowDigitalCheckbox.addEventListener('change', (e) => {
        if (e.target.checked) {
            quizOverlay.classList.remove('active');
            btnHideAnswer.style.display = 'none'; // Cannot hide in always-show mode
        } else {
            quizOverlay.classList.add('active');
            btnHideAnswer.style.display = 'block';
        }
    });

    // Setup: Start App
    btnStart.addEventListener('click', () => {
        showSeconds = toggleSecondsInput.checked;
        
        // Compute selected starting time
        const ampm = startAmpmSelect.value;
        let hour = parseInt(startHourSelect.value);
        const minute = parseInt(startMinuteSelect.value);
        
        // Convert to 24 hour
        if (ampm === "PM" && hour < 12) {
            hour += 12;
        } else if (ampm === "AM" && hour === 12) {
            hour = 0;
        }
        
        startSeconds = (hour * 3600) + (minute * 60);
        totalSecondsFloat = startSeconds;
        totalSeconds = startSeconds;
        
        // Refresh & Transition
        updateUI();
        
        // Reset quiz overlay state according to checkbox
        if (alwaysShowDigitalCheckbox.checked) {
            quizOverlay.classList.remove('active');
        } else {
            quizOverlay.classList.add('active');
        }
        
        setupScreen.classList.remove('active');
        studyScreen.classList.add('active');
        
        // Recalculate and position clock face elements once layout is rendered visible
        setTimeout(positionClockNumbersAndGuides, 50);
    });

    // Study: Back to Setup
    btnBack.addEventListener('click', () => {
        studyScreen.classList.remove('active');
        setupScreen.classList.add('active');
    });

    // Study: Reset time to initial setting
    btnReset.addEventListener('click', () => {
        totalSecondsFloat = startSeconds;
        totalSeconds = startSeconds;
        updateUI();
        
        // Re-hide answer unless 'always show' is active
        if (!alwaysShowDigitalCheckbox.checked) {
            quizOverlay.classList.add('active');
        }
    });

    // --- Init App ---
    initializeClockFace();
    setupDragging();
    
    // Watch for window resize to scale clock numbers and guides
    window.addEventListener('resize', positionClockNumbersAndGuides);
});
