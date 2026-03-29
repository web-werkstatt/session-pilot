// === DASHBOARD MISC ===
// guessDescription, funny quotes, confetti effect

function guessDescription(name, image) {
    const n = name.toLowerCase();
    const i = image.toLowerCase();
    if (n.includes('portainer')) return 'Docker Management UI';
    if (n.includes('traefik')) return 'Reverse Proxy / Load Balancer';
    if (n.includes('nginx')) return 'Web Server / Reverse Proxy';
    if (n.includes('redis')) return 'In-Memory Cache / Message Broker';
    if (n.includes('postgres') || n.includes('mariadb') || n.includes('mysql')) return 'Database';
    if (n.includes('grafana')) return 'Monitoring Dashboard';
    if (n.includes('prometheus')) return 'Metrics Collection';
    if (n.includes('gitea')) return 'Git Server';
    if (n.includes('directus')) return 'Headless CMS';
    if (n.includes('ghost')) return 'Blog Platform';
    if (n.includes('celery') || n.includes('worker')) return 'Background Worker';
    if (n.includes('beat')) return 'Task Scheduler';
    if (i.includes('redis')) return 'Redis Cache';
    if (i.includes('postgres')) return 'PostgreSQL DB';
    if (i.includes('nginx')) return 'Nginx Server';
    return image.split(':')[0].split('/').pop();
}

// Lustige Entwickler-Sprüche
const funnyQuotes = [
    "Mass Container Deployment Unit... 🚀",
    "Looking for the missing semicolon... 🔍",
    "Converting coffee to code... ☕",
    "99 little bugs in the code, 99 little bugs... 🐛",
    "Compiling excuses for the boss... 📋",
    "Deleting node_modules for the 47th time... 📁",
    "Consulting Stack Overflow... 📚",
    "Waking up containers... 🐳",
    "Running git blame... 🕵️",
    "Trying to understand Docker... 🤔",
    "README.md is being ignored... 📄",
    "Generating random bugs... 🎲",
    "Deleting System32... just kidding! 😅",
    "Backup? What backup? 💾",
    "It works on my machine... 🖥️",
    "chmod 777 on everything... 🔓",
    "sudo make me a sandwich 🥪",
    "while(true) { coffee++; } ☕",
    "DNS still propagating... ⏳",
    "Waiting for npm install... 📦"
];

function showFunnyQuote() {
    const quote = funnyQuotes[Math.floor(Math.random() * funnyQuotes.length)];
    document.getElementById('funnyQuote').textContent = quote;
}

// Konfetti-Effekt für neue Projekte
function launchConfetti() {
    const colors = ['#ff0', '#0f0', '#0ff', '#f0f', '#f00', '#00f'];
    for (let i = 0; i < 50; i++) {
        const confetti = document.createElement('div');
        confetti.style.cssText = `
            position: fixed;
            width: 10px;
            height: 10px;
            background: ${colors[Math.floor(Math.random() * colors.length)]};
            left: ${Math.random() * 100}vw;
            top: -10px;
            opacity: 1;
            border-radius: ${Math.random() > 0.5 ? '50%' : '0'};
            pointer-events: none;
            z-index: 9999;
            animation: confettiFall ${2 + Math.random() * 2}s linear forwards;
        `;
        document.body.appendChild(confetti);
        setTimeout(() => confetti.remove(), 4000);
    }
}

// Konfetti Animation
const style = document.createElement('style');
style.textContent = `
    @keyframes confettiFall {
        to {
            top: 100vh;
            opacity: 0;
            transform: rotate(${Math.random() * 720}deg);
        }
    }
`;
document.head.appendChild(style);
