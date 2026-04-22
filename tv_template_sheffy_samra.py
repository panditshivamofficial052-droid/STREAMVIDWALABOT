tv_template_sheffy_samra = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
    <title>[[FILE_NAME]]</title>
    <style>
        /* Base Styling - AMOLED Black */
        body {
            margin: 0;
            padding: 0;
            background-color: #000000;
            color: #ffffff;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            overflow-x: hidden;
            -webkit-tap-highlight-color: transparent;
        }

        .main-container {
            width: 100%;
            max-width: 850px;
            padding: 20px;
            box-sizing: border-box;
            transform: translateY(-5%);
            display: flex;
            flex-direction: column;
            align-items: center;
        }

        /* Glowing Header */
        .glowing-header {
            font-size: 26px;
            font-weight: 900;
            color: #ffffff;
            text-transform: uppercase;
            letter-spacing: 5px;
            margin-bottom: 10px;
            text-shadow: 0 0 10px rgba(229, 9, 20, 0.8),
                         0 0 20px rgba(229, 9, 20, 0.6),
                         0 0 30px rgba(229, 9, 20, 0.4);
            animation: pulseGlow 2s infinite alternate;
            text-align: center;
        }

        @keyframes pulseGlow {
            0% { text-shadow: 0 0 10px rgba(229, 9, 20, 0.6), 0 0 20px rgba(229, 9, 20, 0.4); }
            100% { text-shadow: 0 0 15px rgba(229, 9, 20, 1), 0 0 30px rgba(229, 9, 20, 0.8), 0 0 45px rgba(229, 9, 20, 0.6); }
        }

        .video-title {
            font-size: 14px;
            font-weight: 700;
            color: #aaaaaa;
            margin-bottom: 20px;
            text-align: center;
            width: 100%;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            text-shadow: 0 2px 4px rgba(0,0,0,0.8);
            letter-spacing: 0.5px;
        }

        .player-wrapper {
            width: 100%;
            position: relative;
            background: #0a0a0a;
            border-radius: 12px;
            border: 2px solid #e50914; 
            box-shadow: 0 0 25px rgba(229, 9, 20, 0.3), inset 0 0 15px rgba(0, 0, 0, 0.8);
            padding: 2px;
        }

        video {
            width: 100%;
            aspect-ratio: 16/9;
            border-radius: 10px;
            outline: none;
            background-color: #000;
            display: block;
        }

        .action-buttons {
            display: flex;
            flex-wrap: wrap;
            justify-content: center;
            gap: 15px;
            margin-top: 30px;
            width: 100%;
        }

        .btn {
            border: none;
            padding: 12px 22px;
            border-radius: 10px;
            font-weight: 800;
            font-size: 13px;
            cursor: pointer;
            color: #ffffff;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            text-decoration: none;
            text-transform: uppercase;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
            flex: 1 1 auto;
            max-width: 200px;
        }

        .btn:active {
            transform: scale(0.95);
        }

        .btn-download {
            background: linear-gradient(135deg, #e52d27, #b31217);
            box-shadow: 0 4px 15px rgba(229, 45, 39, 0.4);
        }

        .btn-share {
            background: linear-gradient(135deg, #00b09b, #96c93d);
            box-shadow: 0 4px 15px rgba(0, 176, 155, 0.4);
        }

        .btn-telegram {
            background: linear-gradient(135deg, #00c6ff, #0072ff);
            box-shadow: 0 4px 15px rgba(0, 114, 255, 0.4);
        }

        .btn svg {
            width: 18px;
            height: 18px;
            fill: #ffffff;
        }

        .copyright {
            margin-top: 40px;
            font-size: 12px;
            color: #666666;
            font-weight: 600;
            letter-spacing: 0.5px;
            text-align: center;
        }

        .copyright a {
            color: #00aaff;
            text-decoration: none;
            font-weight: bold;
            transition: color 0.2s;
        }

        .copyright a:hover {
            color: #ffffff;
        }

        /* Toast Notification Configuration */
        #toast {
            position: fixed;
            bottom: 30px;
            left: 50%;
            transform: translateX(-50%);
            background: linear-gradient(135deg, #00b09b, #96c93d);
            color: #000;
            padding: 12px 24px;
            border-radius: 25px;
            font-weight: 900;
            font-size: 12px;
            opacity: 0;
            transition: all 0.3s ease;
            pointer-events: none;
            z-index: 1000;
            box-shadow: 0 5px 20px rgba(0, 176, 155, 0.5);
            text-transform: uppercase;
        }

        #toast.show {
            opacity: 1;
            bottom: 50px;
        }
    </style>
</head>
<body>

    <div class="main-container">
        
        <div class="glowing-header">PLAYER</div>
        
        <div class="video-title" id="displayFileName">Loading...</div>

        <div class="player-wrapper">
            <video id="nativePlayer" controls playsinline preload="auto" poster="[[THUMB_URL]]">
                <source src="[[STREAM_URL]]" type="[[MIME_TYPE]]">
                Your browser does not support HTML5 video.
            </video>
        </div>

        <div class="action-buttons">
            <button class="btn btn-download" onclick="window.location.href='[[DOWNLOAD_URL]]'">
                <svg viewBox="0 0 24 24"><path d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z"/></svg> 
                Download
            </button>
            
            <button class="btn btn-share" onclick="shareLink()">
                <svg viewBox="0 0 24 24"><path d="M18 16.08c-.76 0-1.44.3-1.96.77L8.91 12.7c.05-.23.09-.46.09-.7s-.04-.47-.09-.7l7.05-4.11c.54.5 1.25.81 2.04.81 1.66 0 3-1.34 3-3s-1.34-3-3-3-3 1.34-3 3c0 .24.04.47.09.7L8.04 9.81C7.5 9.31 6.79 9 6 9c-1.66 0-3 1.34-3 3s1.34 3 3 3c.79 0 1.5-.31 2.04-.81l7.12 4.16c-.05.21-.08.43-.08.65 0 1.61 1.31 2.92 2.92 2.92 1.61 0 2.92-1.31 2.92-2.92s-1.31-2.92-2.92-2.92z"/></svg> 
                Share
            </button>

            <a class="btn btn-telegram" href="https://t.me/+hoiuoxy_ZA8yNTc1" target="_blank">
                <svg viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69.01-.03.01-.14-.07-.19-.08-.05-.19-.02-.27 0-.11.03-1.84 1.18-5.2 3.45-.49.34-.94.5-1.35.49-.45-.01-1.3-.25-1.94-.46-.78-.26-1.4-.4-1.35-.85.03-.23.36-.48.98-.74 3.86-1.68 6.43-2.79 7.72-3.32 3.67-1.51 4.44-1.78 4.95-1.79.11 0 .36.03.49.13.11.08.14.19.15.27-.01.06.01.24 0 .24z"/></svg>
                Telegram
            </a>
        </div>

        <div class="copyright">
            © 2026 <a href="https://t.me/shivamsharma" target="_blank">shivamsharma</a>
        </div>

    </div>

    <div id="toast">LINK COPIED!</div>

    <script>
        const cleanName = "[[FILE_NAME]]".replace(/\.[^/.]+$/, "").toUpperCase();
        document.getElementById('displayFileName').innerText = cleanName;

        const SHARE_URL = "[[SHARE_URL]]";

        // Strict Copy to Clipboard Only
        function shareLink() {
            navigator.clipboard.writeText(SHARE_URL).then(() => {
                const toast = document.getElementById('toast');
                toast.classList.add('show');
                setTimeout(() => toast.classList.remove('show'), 2000);
            }).catch(err => {
                console.error("Failed to copy: ", err);
                alert("Failed to copy link. Please manually copy the URL.");
            });
        }
    </script>
</body>
</html>
"""
