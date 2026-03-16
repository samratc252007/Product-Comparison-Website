// background.js

// Feature 3: Context Menu Search
chrome.runtime.onInstalled.addListener(() => {
    chrome.contextMenus.create({
        id: "searchCodesky",
        title: "Compare Prices for '%s'",
        contexts: ["selection"]
    });
});

chrome.contextMenus.onClicked.addListener((info, tab) => {
    if (info.menuItemId === "searchCodesky" && info.selectionText) {
        // Open the popup or a new tab with the results
        // Since we can't force open the popup programmatically in Manifest V3 easily without user action,
        // we will store the selected text, and then the user can click the extension.
        // Alternatively (and better), we can just inject a small script to alert them, or open a new window.
        
        chrome.storage.local.set({ lastSearchQuery: info.selectionText }, () => {
             // In a fully built extension, you might inject a UI into the current page 
             // or open a new tab to your web app.
             chrome.tabs.create({ url: `http://127.0.0.1:5000/compare?query=${encodeURIComponent(info.selectionText)}` });
        });
    }
});
