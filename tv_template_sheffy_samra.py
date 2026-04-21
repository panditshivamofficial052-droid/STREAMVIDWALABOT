tv_template_sheffy_samra = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
    <title>[[FILE_NAME]] - SAMRA TV</title>
    <style>
        :root {
            --brand-color: #e50914;
            --bottom-bar-bg: linear-gradient(to top, rgba(0,0,0,0.9), transparent);
            --controls-bg: rgba(15, 15, 15, 0.95);
            --theme-color: #e50914;
        }

        body { margin: 0; background: #f0f0f0; color: white; font-family: sans-serif; -webkit-tap-highlight-color: transparent; overflow-x: hidden; }
        
        .video-wrapper { position: relative; width: 100%; aspect-ratio: 16/9; background: #000; box-shadow: 0 5px 20px rgba(0,0,0,0.5); overflow: hidden; }
        .video-wrapper video { position: absolute; top: 0; left: 0; width: 100%; height: 100%; object-fit: contain; outline: none; transition: 0.3s ease; }
        
        .focusable { transition: 0.2s; outline: none; border: 2px solid transparent; }
        .focusable.focused { border-color: #fff !important; box-shadow: 0 0 20px #fff !important; transform: scale(1.1); background: rgba(255,255,255,0.2) !important; border-radius: 8px; z-index: 10; }
        
        #osd { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.8); padding: 12px 20px; border-radius: 12px; font-size: 16px; font-weight: bold; opacity: 0; transition: opacity 0.3s; z-index: 100; border: 2px solid rgba(229,9,20,0.5); text-align: center; pointer-events: none; }

        #volHud { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); width: 70px; height: 70px; background: rgba(0,0,0,0.7); border-radius: 50%; display: flex; flex-direction: column; align-items: center; justify-content: center; color: white; font-weight: bold; font-size: 13px; opacity: 0; transition: opacity 0.2s; pointer-events: none; z-index: 110; border: 2px solid var(--brand-color); backdrop-filter: blur(5px); }

        #topBranding { position: absolute; top: 15px; left: 15px; font-size: 14px; font-weight: 900; color: #e50914; text-shadow: 0 2px 10px rgba(0,0,0,0.9); z-index: 100; opacity: 0.5; transition: 0.3s ease; pointer-events: none; }
        .ui-awake #topBranding { opacity: 1; }

        #displayFileName { font-size: 13px; font-weight: 600; color: #ddd; max-width: 65%; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; text-shadow: 0 2px 5px rgba(0,0,0,0.9); opacity: 0.5; transition: 0.3s ease; }
        .ui-awake #displayFileName { opacity: 1; }

        .bottom-info-bar { position: absolute; bottom: 0; left: 0; width: 100%; display: flex; justify-content: space-between; align-items: flex-end; padding: 15px; background: transparent; box-sizing: border-box; z-index: 8; height: 100px; transition: 0.3s ease; pointer-events: none; }
        .ui-awake .bottom-info-bar { background: var(--bottom-bar-bg); transform: translateY(-60px); }

        #tvControls { position: absolute; bottom: 10px; left: 50%; transform: translateX(-50%) translateY(20px); width: 95%; background: var(--controls-bg); backdrop-filter: blur(15px); padding: 10px 15px; box-sizing: border-box; opacity: 0; transition: all 0.3s ease; z-index: 99; border-radius: 12px; border: 1px solid rgba(255,255,255,0.1); box-shadow: 0 10px 30px rgba(0,0,0,0.8); pointer-events: none; }
        .ui-awake #tvControls { opacity: 1; transform: translateX(-50%) translateY(0); pointer-events: auto; }
        
        /* Thin 2px Seekbar with White Buffer line */
        .tv-progress-bg { width: 100%; height: 2px; background: rgba(255,255,255,0.2); border-radius: 2px; margin-bottom: 10px; position: relative; cursor: pointer; }
        .tv-buffer-fill { height: 100%; background: rgba(255,255,255,0.7); position: absolute; top: 0; left: 0; border-radius: 2px; z-index: 1; pointer-events: none; transition: width 0.2s; }
        .tv-progress-fill { height: 100%; background: var(--theme-color); width: 0%; border-radius: 2px; box-shadow: 0 0 10px var(--theme-color); position: relative; z-index: 2; pointer-events: none;}
        
        #seekTooltip { position: absolute; top: -25px; background: rgba(229, 9, 20, 0.9); color: white; padding: 3px 6px; border-radius: 4px; font-size: 11px; font-weight: bold; pointer-events: none; opacity: 0; transition: opacity 0.2s; transform: translateX(-50%); white-space: nowrap; z-index: 10; }
        
        .tv-status-bar { display: flex; justify-content: space-between; align-items: center; }
        .tv-btn { background: none; border: none; color: white; cursor: pointer; display: flex; align-items: center; justify-content: center; padding: 5px; border-radius: 50%; }
        .tv-btn svg { width: 24px; height: 24px; fill: white; }
        
        #tvTime { font-weight: bold; font-size: 12px; font-variant-numeric: tabular-nums; opacity: 0.8; letter-spacing: 0.5px; }

        .tv-menu-btn { position: absolute; top: 15px; right: 15px; background: rgba(0,0,0,0.7); color: white; width: 35px; height: 35px; border-radius: 50%; display: flex; align-items: center; justify-content: center; opacity: 0; transition: 0.3s; z-index: 150; cursor: pointer; border: 2px solid transparent; pointer-events: none; }
        .ui-awake .tv-menu-btn { opacity: 1; pointer-events: auto; }
        .tv-menu-btn svg { width: 20px; height: 20px; fill: white; }

        /* 25% Smaller Menu */
        .tv-menu { display: none; position: absolute; top: 55px; right: 15px; background: rgba(15,15,15,0.98); border-radius: 8px; border: 1px solid #444; z-index: 200; min-width: 120px; overflow-y: auto; scrollbar-width: none; backdrop-filter: blur(15px); box-shadow: 0 10px 30px rgba(0,0,0,0.9); font-size: 11px; }
        .tv-menu::-webkit-scrollbar { display: none; }
        .menu-item { padding: 8px 12px; color: white; cursor: pointer; border-bottom: 1px solid #2a2a2a; outline: none; }
        .menu-item.focused { background: var(--theme-color); font-weight: bold; }
        .menu-title { background: #111; color: #aaa; font-size: 10px; padding: 8px 12px; border-bottom: 2px solid #333; font-weight: bold; position: sticky; top: 0; z-index: 2; text-transform: uppercase; }
        .active-speed, .active-fit { color: #00ff88 !important; font-weight: bold; }
        
        .dt-zone { position: absolute; top: 0; bottom: 80px; z-index: 5; user-select: none; }
        .dt-left { left: 0; width: 35%; }
        .dt-right { right: 0; width: 35%; }
        .dt-center { left: 35%; width: 30%; }

        .video-wrapper.peek-mode #tvControls { opacity: 1; transform: translateX(-50%) translateY(0); background: transparent; border: none; box-shadow: none; pointer-events: none; }
        .video-wrapper.peek-mode .tv-status-bar { opacity: 0; }

        .video-wrapper.fullscreen-mode { position: fixed !important; top: 0; left: 0; width: 100vw !important; height: 100vh !important; z-index: 9999 !important; border-radius: 0 !important; background: #000; }
        .video-wrapper.fullscreen-mode #tvControls { bottom: max(15px, env(safe-area-inset-bottom)); width: calc(95% - env(safe-area-inset-left) - env(safe-area-inset-right)); }
        
        /* White Action Bar */
        .content { padding: 15px; max-width: 800px; margin: 0 auto; }
        .action-bar { background: #ffffff; padding: 12px 20px; display: flex; justify-content: space-around; border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); align-items: center; }
        .action-btn { background: #111; color: #fff; border: none; padding: 10px 24px; border-radius: 8px; font-weight: 900; font-size: 12px; cursor: pointer; display: flex; align-items: center; gap: 8px; transition: 0.2s; box-shadow: 0 4px 10px rgba(0,0,0,0.2); }
        .action-btn:active { transform: scale(0.95); background: var(--brand-color); }
        
        #toast { position: fixed; bottom: 30px; left: 50%; transform: translateX(-50%); background: #00ff88; color: #000; padding: 10px 20px; border-radius: 20px; font-weight: bold; font-size: 12px; opacity: 0; transition: 0.3s ease; z-index: 20000; pointer-events: none; box-shadow: 0 4px 15px rgba(0,255,136,0.4); }
        #toast.show { opacity: 1; bottom: 50px; }
    </style>
</head>
<body>

    <div class="video-wrapper" id="videoWrapper">
        <div id="topBranding">PLAYER</div>

        <div id="tvMenuBtn" class="tv-menu-btn focusable" onclick="toggleMenu()">
            <svg viewBox="0 0 24 24"><path d="M12 8c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2zm0 2c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2zm0 6c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2z"/></svg>
        </div>

        <div id="tvMenu" class="tv-menu">
            <div class="menu-title">Speed</div>
            <div class="menu-item focusable" onclick="setTvSpeed(0.5, this)">0.5x Slow</div>
            <div class="menu-item focusable active-speed" onclick="setTvSpeed(1.0, this)">1.0x Normal</div>
            <div class="menu-item focusable" onclick="setTvSpeed(2.0, this)">2.0x Fast</div>
            <div class="menu-item focusable" onclick="setTvSpeed(3.0, this)">3.0x Max</div>
            
            <div class="menu-title">Display</div>
            <div class="menu-item focusable active-fit" onclick="setTvFitMode('contain', this)">Fit</div>
            <div class="menu-item focusable" onclick="setTvFitMode('cover', this)">Crop</div>
            <div class="menu-item focusable" onclick="setTvFitMode('fill', this)">Stretch</div>
        </div>

        <div class="dt-zone dt-left" id="dtLeft"></div>
        <div class="dt-zone dt-center" id="dtCenter"></div>
        <div class="dt-zone dt-right" id="dtRight"></div>

        <video id="player" playsinline preload="auto">
            <source src="[[STREAM_URL]]" type="[[MIME_TYPE]]">
        </video>

        <div id="osd"></div>
        
        <div id="volHud">
            <svg viewBox="0 0 24 24" width="20" height="20" fill="white"><path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/></svg>
            <span id="volText">100%</span>
        </div>

        <div class="bottom-info-bar" id="bottomInfoBar">
            <div class="movie-title" id="displayFileName">Loading...</div>
        </div>

        <div id="tvControls">
            <div class="tv-progress-bg focusable" id="tvProgressBg" onclick="seekClick(event)">
                <div id="seekTooltip">0:00</div>
                <div class="tv-buffer-fill" id="tvBuffer"></div>
                <div class="tv-progress-fill" id="tvProgress"></div>
            </div>
            <div class="tv-status-bar">
                <button id="tvPlayPauseBtn" class="tv-btn focusable" onclick="togglePlay(false)">
                    <svg id="tvPlayIcon" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
                    <svg id="tvPauseIcon" viewBox="0 0 24 24" style="display:none;"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/></svg>
                </button>
                <div id="tvTime">0:00 / 0:00</div>
                <button id="tvFullScreenBtn" class="tv-btn focusable" onclick="toggleFS()">
                    <svg viewBox="0 0 24 24"><path d="M7 14H5v5h5v-2H7v-3zm-2-4h2V7h3V5H5v5zm12 7h-3v2h5v-5h-2v3zM14 5v2h3v3h2V5h-5z"/></svg>
                </button>
            </div>
        </div>
    </div>

    <div class="content">
        <div class="action-bar">
            <button class="action-btn" onclick="window.location.href='[[STREAM_URL]]'">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="white"><path d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z"/></svg> DOWNLOAD
            </button>
            <button class="action-btn" onclick="shareLink()">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="white"><path d="M18 16.08c-.76 0-1.44.3-1.96.77L8.91 12.7c.05-.23.09-.46.09-.7s-.04-.47-.09-.7l7.05-4.11c.54.5 1.25.81 2.04.81 1.66 0 3-1.34 3-3s-1.34-3-3-3-3 1.34-3 3c0 .24.04.47.09.7L8.04 9.81C7.5 9.31 6.79 9 6 9c-1.66 0-3 1.34-3 3s1.34 3 3 3c.79 0 1.5-.31 2.04-.81l7.12 4.16c-.05.21-.08.43-.08.65 0 1.61 1.31 2.92 2.92 2.92 1.61 0 2.92-1.31 2.92-2.92s-1.31-2.92-2.92-2.92z"/></svg> SHARE
            </button>
        </div>
    </div>

    <div id="toast">LINK COPIED!</div>

    <script>
        const video = document.getElementById('player');
        const wrapper = document.getElementById('videoWrapper');
        const tvMenu = document.getElementById('tvMenu');
        const tvControls = document.getElementById('tvControls');
        const seekbar = document.getElementById('tvProgressBg');
        const seekTooltip = document.getElementById('seekTooltip');

        let controlsTimeout, menuTimeout, peekTimer;
        let isMenuOpen = false;

        const cleanName = "[[FILE_NAME]]".replace(/\.[^/.]+$/, "").toUpperCase();
        document.getElementById('displayFileName').innerText = cleanName;

        video.addEventListener('loadedmetadata', () => {
            video.play().then(() => {
                showOSD("PLAYING");
                wakeUI();
            }).catch(() => {
                showOSD("TAP TO PLAY");
                wakeUI();
            });
        });

        function showOSD(text) {
            const osd = document.getElementById('osd');
            osd.innerText = text; osd.style.opacity = 1;
            setTimeout(() => osd.style.opacity = 0, 1000);
        }

        function wakeUI() {
            wrapper.classList.remove('peek-mode');
            wrapper.classList.add('ui-awake');
            clearTimeout(controlsTimeout);
            controlsTimeout = setTimeout(forceHide, 3500);
        }

        function forceHide() {
            if (video.paused || isMenuOpen) return;
            wrapper.classList.remove('ui-awake');
        }

        function handleSingleTap() {
            if (isMenuOpen) { toggleMenu(); return; }
            if (wrapper.classList.contains('ui-awake')) forceHide();
            else wakeUI();
        }

        wrapper.addEventListener('click', (e) => {
            if(e.target.closest('#tvControls') || e.target.closest('#tvMenuBtn') || e.target.closest('#tvMenu') || e.target.closest('.dt-zone')) return;
            handleSingleTap();
        });

        wrapper.addEventListener('mousemove', (e) => {
            if(e.pointerType === 'mouse') wakeUI();
        });

        video.addEventListener('volumechange', () => {
            wakeUI();
            const volHud = document.getElementById('volHud');
            const volText = document.getElementById('volText');
            volText.innerText = Math.round(video.volume * 100) + "%";
            volHud.style.opacity = 1;
            clearTimeout(window.volTimeout);
            window.volTimeout = setTimeout(() => volHud.style.opacity = 0, 1000);
        });

        function togglePlay(silent = false) {
            if(video.paused) { video.play(); showOSD("PLAY"); } 
            else { video.pause(); showOSD("PAUSE"); }
            if(!silent) wakeUI();
        }

        video.addEventListener('play', () => { 
            document.getElementById('tvPlayIcon').style.display='none'; 
            document.getElementById('tvPauseIcon').style.display='block'; 
        });
        video.addEventListener('pause', () => { 
            document.getElementById('tvPlayIcon').style.display='block'; 
            document.getElementById('tvPauseIcon').style.display='none'; 
            wakeUI();
        });

        function formatTime(s) {
            if (isNaN(s) || s < 0) return "0:00";
            let h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sec = Math.floor(s % 60);
            if (h > 0) return h + ":" + (m < 10 ? "0" + m : m) + ":" + (sec < 10 ? "0" + sec : sec);
            return m + ":" + (sec < 10 ? "0" + sec : sec);
        }

        function syncSeekbarLive() {
            if(!video.duration) return;
            const p = (video.currentTime / video.duration) * 100;
            document.getElementById('tvProgress').style.width = p + '%';
            
            let rem = video.duration - video.currentTime;
            document.getElementById('tvTime').innerText = formatTime(video.currentTime) + " / " + formatTime(video.duration) + " (-" + formatTime(rem) + ")";
        }
        video.addEventListener('timeupdate', syncSeekbarLive);

        // Buffer Progress Logic
        video.addEventListener('progress', () => {
            if (video.duration > 0 && video.buffered.length > 0) {
                for (let i = 0; i < video.buffered.length; i++) {
                    if (video.buffered.start(video.buffered.length - 1 - i) <= video.currentTime) {
                        let bufferedEnd = video.buffered.end(video.buffered.length - 1 - i);
                        let p = (bufferedEnd / video.duration) * 100;
                        document.getElementById('tvBuffer').style.width = p + '%';
                        break;
                    }
                }
            }
        });

        function seekClick(e) {
            let rect = seekbar.getBoundingClientRect();
            let pos = (e.clientX || (e.touches && e.touches[0].clientX) - rect.left) / rect.width;
            video.currentTime = pos * video.duration;
            syncSeekbarLive();
            wakeUI();
        }

        seekbar.addEventListener('mousemove', (e) => {
            if(!video.duration) return;
            let rect = seekbar.getBoundingClientRect();
            let pos = (e.clientX - rect.left) / rect.width;
            pos = Math.max(0, Math.min(1, pos));
            seekTooltip.innerText = formatTime(pos * video.duration);
            seekTooltip.style.left = (pos * 100) + '%';
            seekTooltip.style.opacity = 1;
        });
        seekbar.addEventListener('mouseleave', () => { seekTooltip.style.opacity = 0; });

        let skipAccumulator = 0;
        let skipExecTimer = null;
        let singleTapTimer = null;
        let lastTapTime = 0;
        let lastTapDir = '';
        
        let holdTimer = null;
        let isHolding = false;
        let originalSpeed = 1;

        function formatSkipOSD(val) {
            let abs = Math.abs(val);
            let h = Math.floor(abs / 3600), m = Math.floor((abs % 3600) / 60), s = abs % 60;
            let str = "";
            if (h > 0) str += h + "h ";
            if (m > 0 || h > 0) str += m + "m ";
            str += s + "s";
            return val > 0 ? `+${str} ⏩` : `⏪ -${str}`;
        }

        function registerSkipTap(direction) {
            let now = Date.now();
            if (now - lastTapTime < 400 && lastTapDir === direction) {
                clearTimeout(singleTapTimer);
                skipAccumulator += (direction === 'right' ? 10 : -10);
                showOSD(formatSkipOSD(skipAccumulator));
                
                if(!wrapper.classList.contains('ui-awake')) {
                    wrapper.classList.add('peek-mode');
                    clearTimeout(peekTimer);
                    peekTimer = setTimeout(() => wrapper.classList.remove('peek-mode'), 1500);
                }

                clearTimeout(skipExecTimer);
                skipExecTimer = setTimeout(() => {
                    video.currentTime += skipAccumulator;
                    syncSeekbarLive();
                    skipAccumulator = 0; lastTapDir = '';
                }, 600);
            } else {
                skipAccumulator = 0;
                singleTapTimer = setTimeout(handleSingleTap, 300);
            }
            lastTapTime = now; lastTapDir = direction;
        }

        document.getElementById('dtLeft').addEventListener('pointerdown', (e) => { e.stopPropagation(); registerSkipTap('left'); });
        document.getElementById('dtRight').addEventListener('pointerdown', (e) => { e.stopPropagation(); registerSkipTap('right'); });

        let lastTapC = 0, centerTapTimer;
        document.getElementById('dtCenter').addEventListener('pointerdown', (e) => {
            e.stopPropagation(); let now = Date.now();
            if(now - lastTapC < 300) { 
                clearTimeout(centerTapTimer); togglePlay(false); 
            } else {
                centerTapTimer = setTimeout(handleSingleTap, 300);
            }
            lastTapC = now; 
        });

        const startHold = (e) => {
            if(e.target.closest('#tvControls') || e.target.closest('.tv-menu-btn') || e.target.closest('#tvMenu')) return;
            holdTimer = setTimeout(() => {
                isHolding = true; originalSpeed = video.playbackRate; video.playbackRate = 2.0; showOSD("⏩ 2x Speed");
            }, 600);
        };
        const endHold = () => {
            clearTimeout(holdTimer);
            if(isHolding) { video.playbackRate = originalSpeed; isHolding = false; document.getElementById('osd').style.opacity = 0; }
        };
        wrapper.addEventListener('pointerdown', startHold);
        wrapper.addEventListener('pointerup', endHold);
        wrapper.addEventListener('pointercancel', endHold);

        let startY = 0, startVol = 1, isVolSwipe = false;
        const volHud = document.getElementById('volHud');
        const volText = document.getElementById('volText');

        wrapper.addEventListener('pointerdown', (e) => {
            if(e.target.closest('#tvControls') || e.target.closest('.tv-menu-btn') || e.target.closest('#tvMenu')) return;
            if(e.clientX > window.innerWidth * 0.6) {
                startY = e.clientY; startVol = video.volume; isVolSwipe = true;
            }
        });
        wrapper.addEventListener('pointermove', (e) => {
            if(isVolSwipe && e.pointerType === 'touch') {
                let deltaY = startY - e.clientY;
                if(Math.abs(deltaY) > 20) {
                    clearTimeout(holdTimer); 
                    let newVol = Math.max(0, Math.min(1, startVol + (deltaY / 200)));
                    video.volume = newVol;
                    volText.innerText = Math.round(newVol * 100) + "%";
                    volHud.style.opacity = 1;
                    clearTimeout(window.volTimeout);
                    window.volTimeout = setTimeout(() => volHud.style.opacity = 0, 1000);
                }
            }
        });
        wrapper.addEventListener('pointerup', () => { isVolSwipe = false; });

        function toggleMenu() {
            isMenuOpen = !isMenuOpen;
            tvMenu.style.display = isMenuOpen ? 'block' : 'none';
            if(isMenuOpen) { wakeUI(); resetMenuTimer(); } 
            else clearTimeout(menuTimeout);
        }
        function resetMenuTimer() { clearTimeout(menuTimeout); if (isMenuOpen) menuTimeout = setTimeout(toggleMenu, 5000); }
        function setTvSpeed(s, el) { video.playbackRate = s; document.querySelectorAll('.menu-item').forEach(i => i.classList.remove('active-speed')); el.classList.add('active-speed'); toggleMenu(); showOSD("Speed: " + s + "x"); }
        function setTvFitMode(mode, el) { video.style.objectFit = mode; document.querySelectorAll('.menu-item').forEach(i => i.classList.remove('active-fit')); el.classList.add('active-fit'); toggleMenu(); showOSD("Mode: " + mode.toUpperCase()); }

        function toggleFS() {
            if (!document.fullscreenElement && !document.webkitFullscreenElement) {
                if (wrapper.requestFullscreen) wrapper.requestFullscreen();
                else if (wrapper.webkitRequestFullscreen) wrapper.webkitRequestFullscreen();
                wrapper.classList.add('fullscreen-mode');
                if(screen.orientation && screen.orientation.lock) screen.orientation.lock('landscape').catch(()=>{});
            } else {
                if (document.exitFullscreen) document.exitFullscreen();
                else if (document.webkitExitFullscreen) document.webkitExitFullscreen();
                wrapper.classList.remove('fullscreen-mode');
                if(screen.orientation && screen.orientation.unlock) screen.orientation.unlock();
            }
        }
        document.addEventListener('fullscreenchange', () => { if(!document.fullscreenElement) wrapper.classList.remove('fullscreen-mode'); });
        document.addEventListener('webkitfullscreenchange', () => { if(!document.webkitFullscreenElement) wrapper.classList.remove('fullscreen-mode'); });

        function shareLink() {
            if (navigator.share) {
                navigator.share({ title: '[[FILE_NAME]]', url: window.location.href });
            } else {
                navigator.clipboard.writeText(window.location.href).then(() => {
                    const toast = document.getElementById('toast');
                    toast.classList.add('show');
                    setTimeout(() => toast.classList.remove('show'), 2000);
                });
            }
        }
    </script>
</body>
</html>
"""
