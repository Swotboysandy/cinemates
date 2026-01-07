# Watch Party App

## Setup
1. Open this folder in your terminal: `cd watch-party-app`
2. Run `npm install` (if you haven't already).
3. Run `npm run dev`.

## How to Tunnel (Cloudflare)
Since you mentioned using Cloudflare Tunnel:
1. Start the app locally (it usually runs on port 5173).
2. Run your tunnel command: `cloudflared tunnel --url http://localhost:5173`
3. Share the generated public URL with your friend.

## How to Use
1. **You**: Open the app (local or public URL). Copy your ID.
2. **Friend**: Open the app (public URL).
3. **Connect**: Send your ID to your friend. They paste it into the "Remote ID" box and click **Connect**.
4. **Call**: Your webcams should start automatically (allow permissions).
5. **Watch**: 
   - The Big Buck Bunny video loads by default.
   - Paste a direct link to an MP4/WebM file to change the video.
   - Play/Pause/Seek will sync between both of you!

## Note
- This app uses **PeerJS** for peer-to-peer connections. Even if you use a tunnel, the video sync data goes directly between peers (via WebRTC/WebSockets).
- Browsers might block autoplay, so interact with the page (click play) if video doesn't start effectively.
