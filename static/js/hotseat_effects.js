// static/js/hotseat_effects.js
console.log("hotseat_effects.js: File loaded.");

let tremorInterval = null;
let inactivityTimeout = null;
let criticalTimeout = null;

const timerBar = document.getElementById('inactivity-timer-bar');
const modal = document.getElementById('critical-warning-modal');

const typingSound = document.getElementById('typing-sound');
const rumbleSound = document.getElementById('rumble-sound');

function startTremor() {
    if (!tremorInterval) {
        tremorInterval = setInterval(() => {
            document.body.classList.add('hotseat-tremor');
            setTimeout(() => document.body.classList.remove('hotseat-tremor'), 500);
        }, 30000); // A tremor every 30 seconds
    }
}

function stopTremor() {
    clearInterval(tremorInterval);
    tremorInterval = null;
}

function resetInactivityTimer() {
    clearTimeout(inactivityTimeout);
    clearTimeout(criticalTimeout);
    if (timerBar) timerBar.classList.remove('glowing');
    if (modal) modal.style.display = 'none';

    inactivityTimeout = setTimeout(() => {
        if (timerBar) timerBar.classList.add('glowing');
    }, 45000); // Warn after 45 seconds of inactivity

    criticalTimeout = setTimeout(() => {
        if (modal) modal.style.display = 'flex';
        if (rumbleSound) rumbleSound.play();
    }, 60000); // Critical modal after 60 seconds
}

function playTypingSound() {
    if (typingSound) {
        typingSound.currentTime = 0;
        typingSound.play().catch(e => console.error("Sound play failed:", e));
    }
}

// Global functions to be called by the theme switcher
window.activateHotseatEffects = () => {
    console.log("Activating Hotseat Effects");
    startTremor();
    resetInactivityTimer();
    window.addEventListener('mousemove', resetInactivityTimer);
    window.addEventListener('keydown', resetInactivityTimer);
    window.addEventListener('keydown', playTypingSound); // Play sound on keydown
};

window.deactivateHotseatEffects = () => {
    console.log("Deactivating Hotseat Effects");
    stopTremor();
    clearTimeout(inactivityTimeout);
    clearTimeout(criticalTimeout);
    if (timerBar) timerBar.classList.remove('glowing');
    if (modal) modal.style.display = 'none';
    window.removeEventListener('mousemove', resetInactivityTimer);
    window.removeEventListener('keydown', resetInactivityTimer);
    window.removeEventListener('keydown', playTypingSound);
};

// Check if the theme is active on page load
if (document.body.classList.contains('theme-hotseat')) {
    window.activateHotseatEffects();
}
