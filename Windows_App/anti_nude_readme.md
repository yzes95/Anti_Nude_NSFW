AntiWebNSFW – Automated NSFW Detection and Lock System

AntiWebNSFW is a system for detecting NSFW (Not Safe for Work) content in web traffic and enforcing local restrictions when such content is found. It combines AI-powered detection, proxy-based filtering, and system-level enforcement to help users create a safer browsing environment.

🔑 Features
1. Content Analysis Service (detector_service.py)

FastAPI-based REST API for text and image analysis.

NudeNet for image classification and Tesseract OCR for text-in-image detection.

Configurable thresholds and encrypted settings storage.

Endpoints:

POST /analyze → Analyze text or base64 images.

POST /lock → Lock device for a set duration.

GET /status → View lock status.

2. Web Proxy Filter (nsfw_proxy_addon.py)

A mitmproxy addon that inspects HTTP traffic.

Detects explicit words in page text.

Extracts and analyzes images (URLs and data URIs).

Blocks pages and triggers device lock when NSFW content is detected.

3. Device Lock Overlay (overlay_lock.py)

Enforces a system-wide lock when NSFW content is confirmed.

Lock mechanisms include:

Keyboard suppression.

Mouse cursor “jail.”

Win32 input blocking.

Fullscreen Tkinter overlay with countdown timer.

Lock automatically lifts after the timer expires.

🚧 Future Enhancements

🌐 Web Portal – Project website with description, live demos, and downloads.

🗄 Database Integration (MySQL) – User management for admins, moderators, and end-users.

🧠 Custom Model Training – Train and refine AI detection models for better accuracy.

💰 Donation Scheme – Allow contributions to support ongoing development.

🏆 Gamification – Achievements, encouragement, and rewards system (e.g., “7 Days Clean Surfing” badge).

⚡ In Short

AntiWebNSFW is more than just a blocker. It’s a self-regulation and motivation tool combining AI detection, proxy-level filtering, and gamified reinforcement to encourage healthier online habits.