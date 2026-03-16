document.addEventListener('DOMContentLoaded', () => {
    const searchBtn = document.getElementById('searchBtn');
    const searchInput = document.getElementById('searchInput');
    const resultsArea = document.getElementById('resultsArea');
    const loadingUI = document.getElementById('loading');
    const errorBox = document.getElementById('errorBox');
    const themeToggle = document.getElementById('themeToggle');
    const settingsBtn = document.getElementById('settingsBtn');
    const settingsMenu = document.getElementById('settingsMenu');
    const cheapestOnlyToggle = document.getElementById('cheapestOnlyToggle');
    const recentSearchesBtn = document.getElementById('recentSearchesBtn');
    const recentSearchesContainer = document.getElementById('recentSearchesContainer');
    const recentSearchesList = document.getElementById('recentSearchesList');
    const clearHistoryBtn = document.getElementById('clearHistoryBtn');
    const saveOptions = document.getElementById('saveOptions');
    const saveExcelBtn = document.getElementById('saveExcelBtn');
    const amazonSettingsLink = document.getElementById('amazonSettingsLink');
    const walmartSettingsLink = document.getElementById('walmartSettingsLink');
    
    // Premium Feature Elements
    const focusModeToggle = document.getElementById('focusModeToggle');
    const premiumActions = document.getElementById('premiumActions');
    const applyCouponsBtn = document.getElementById('applyCouponsBtn');
    const sortDealsBtn = document.getElementById('sortDealsBtn');
    const savePdfBtn = document.getElementById('savePdfBtn');
    
    let currentResults = { amazon: [], walmart: [] }; // Store results for export
    let couponsApplied = false;

    // --- Feature 2: Recent Searches ---
    function loadRecentSearches() {
        chrome.storage.local.get(['recentSearches'], (result) => {
            const searches = result.recentSearches || [];
            recentSearchesList.innerHTML = '';
            
            if (searches.length === 0) {
                recentSearchesList.innerHTML = '<li style="font-size: 11px; color:#7f8c8d;">No recent searches</li>';
            } else {
                searches.forEach(term => {
                    const li = document.createElement('li');
                    li.className = 'search-tag';
                    li.textContent = term;
                    li.addEventListener('click', () => {
                        searchInput.value = term;
                        searchBtn.click();
                        recentSearchesContainer.classList.add('hidden');
                    });
                    recentSearchesList.appendChild(li);
                });
            }
        });
    }

    recentSearchesBtn.addEventListener('click', () => {
        recentSearchesContainer.classList.toggle('hidden');
        if (!recentSearchesContainer.classList.contains('hidden')) {
            loadRecentSearches();
        }
    });

    clearHistoryBtn.addEventListener('click', () => {
        chrome.storage.local.set({ recentSearches: [] }, () => {
            loadRecentSearches();
        });
    });

    function saveSearchTerm(term) {
        chrome.storage.local.get(['recentSearches'], (result) => {
            let searches = result.recentSearches || [];
            searches = searches.filter(s => s.toLowerCase() !== term.toLowerCase());
            searches.unshift(term);
            if (searches.length > 5) searches.pop();
            chrome.storage.local.set({ recentSearches: searches });
        });
    }

    settingsBtn.addEventListener('click', () => {
        settingsMenu.classList.toggle('hidden');
        
        const query = searchInput.value.trim();
        if (query) {
            amazonSettingsLink.href = `https://www.amazon.com/s?k=${encodeURIComponent(query)}`;
            walmartSettingsLink.href = `https://www.walmart.com/search?q=${encodeURIComponent(query)}`;
        } else {
            amazonSettingsLink.href = "https://www.amazon.com";
            walmartSettingsLink.href = "https://www.walmart.com";
        }
    });

    // --- Export Functions ---
    function formatPrice(priceStr) {
        const cleaned = priceStr.replace(/[^0-9.]/g, '');
        return cleaned ? parseFloat(cleaned) : 0;
    }

    function exportToCSV() {
        if (!currentResults.amazon.length && !currentResults.walmart.length) return;
        
        let csvContent = "data:text/csv;charset=utf-8,";
        csvContent += "Store,Product Title,Price,Rating,Link\n";
        
        currentResults.amazon.slice(0, 4).forEach(item => {
            const price = item.product_price ? item.product_price.replace(',', '') : "Check Site";
            const title = item.product_title ? item.product_title.replace(/"/g, '""') : "";
            const rating = item.product_rating || "";
            csvContent += `Amazon,"${title}","${price}","${rating}","${item.product_url}"\n`;
        });
        
        currentResults.walmart.slice(0, 4).forEach(item => {
            const price = item.price && item.price.currentPrice ? `Rs ${item.price.currentPrice.toFixed(2)}` : "Check Site";
            const title = item.title ? item.title.replace(/"/g, '""') : "";
            const rating = item.ratings || "";
            const link = item.link && item.link.startsWith('http') ? item.link : `https://www.walmart.com${item.link}`;
            csvContent += `Walmart,"${title}","${price}","${rating}","${link}"\n`;
        });
        
        const encodedUri = encodeURI(csvContent);
        const link = document.createElement("a");
        link.setAttribute("href", encodedUri);
        link.setAttribute("download", `prices_${searchInput.value}.csv`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }

    function exportToExcel() {
        if (!currentResults.amazon.length && !currentResults.walmart.length) return;
        
        let tableHTML = `<table border="1"><tr><th>Store</th><th>Product Title</th><th>Price</th><th>Rating</th><th>Link</th></tr>`;
        
        currentResults.amazon.slice(0, 4).forEach(item => {
            const price = item.product_price || "Check Site";
            const rating = item.product_rating || "";
            tableHTML += `<tr><td>Amazon</td><td>${item.product_title}</td><td>${price}</td><td>${rating}</td><td><a href="${item.product_url}">Link</a></td></tr>`;
        });
        
        currentResults.walmart.slice(0, 4).forEach(item => {
            const price = item.price && item.price.currentPrice ? `Rs ${item.price.currentPrice.toFixed(2)}` : "Check Site";
            const rating = item.ratings || "";
            const link = item.link && item.link.startsWith('http') ? item.link : `https://www.walmart.com${item.link}`;
            tableHTML += `<tr><td>Walmart</td><td>${item.title}</td><td>${price}</td><td>${rating}</td><td><a href="${link}">Link</a></td></tr>`;
        });
        
        tableHTML += `</table>`;
        const blob = new Blob([tableHTML], { type: "application/vnd.ms-excel" });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = `prices_${searchInput.value}.xls`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }

    function exportToPDF() {
        if (!currentResults.amazon.length && !currentResults.walmart.length) return;
        window.print(); // Simple PDF export via print dialog for extension
    }

    saveExcelBtn.addEventListener('click', exportToExcel);
    if (savePdfBtn) savePdfBtn.addEventListener('click', exportToPDF);
    
    // --- Premium Features Logic ---
    
    // 1. Focus Mode
    if (focusModeToggle) {
        focusModeToggle.addEventListener('change', (e) => {
            const items = document.querySelectorAll('.product-item');
            if (e.target.checked) {
                items.forEach(item => item.classList.add('focus-mode'));
            } else {
                items.forEach(item => item.classList.remove('focus-mode'));
            }
        });
    }

    // 2. Auto-Sort Deals
    if (sortDealsBtn) {
        sortDealsBtn.addEventListener('click', () => {
            if (!currentResults.amazon.length && !currentResults.walmart.length) return;
            
            const sortContainer = (selector) => {
                const container = document.querySelector(selector);
                if (!container) return;
                const items = Array.from(container.querySelectorAll('.product-item'));
                items.sort((a, b) => {
                    const getPrice = (el) => {
                        const text = el.querySelector('.product-price').textContent;
                        const num = formatPrice(text);
                        return num || 999999;
                    };
                    return getPrice(a) - getPrice(b);
                });
                container.innerHTML = '';
                items.forEach(item => container.appendChild(item));
            };
            
            sortContainer('.store-section:nth-child(1)'); // Amazon
            sortContainer('.store-section:nth-child(2)'); // Walmart
            
            sortDealsBtn.innerHTML = `<i class="fas fa-check"></i> Sorted`;
            setTimeout(() => {
                sortDealsBtn.innerHTML = `<i class="fas fa-sort-amount-down-alt"></i> Sort`;
            }, 2000);
        });
    }

    // 3. Apply Coupons
    if (applyCouponsBtn) {
        applyCouponsBtn.addEventListener('click', () => {
            if (couponsApplied || (!currentResults.amazon.length && !currentResults.walmart.length)) return;
            
            applyCouponsBtn.innerHTML = `<i class="fas fa-spinner fa-spin"></i> Applying...`;
            applyCouponsBtn.disabled = true;
            resultsArea.classList.add('applying-coupons');
            
            setTimeout(() => {
                const prices = document.querySelectorAll('.product-price');
                prices.forEach(priceEl => {
                    const currentText = priceEl.textContent;
                    const match = currentText.match(/Rs ([\d,.]+)/);
                    if (match) {
                        const currentPrice = parseFloat(match[1].replace(/,/g, ''));
                        const discounted = currentPrice * 0.9; // 10% off
                        priceEl.innerHTML = `<span style="text-decoration: line-through; font-size: 11px; color: #95a5a6;">Rs ${currentPrice.toFixed(2)}</span> <br> <span class="price-drop">Rs ${discounted.toFixed(2)}</span>`;
                    }
                });
                
                resultsArea.classList.remove('applying-coupons');
                applyCouponsBtn.innerHTML = `<i class="fas fa-check"></i> Code Applied (-10%)`;
                applyCouponsBtn.style.background = '#2ecc71';
                couponsApplied = true;
            }, 1500);
        });
    }

    // 4. Track Bouttons Delegation & History Button
    resultsArea.addEventListener('click', (e) => {
        // Track Button Logic
        if (e.target.closest('.track-btn')) {
            const btn = e.target.closest('.track-btn');
            const isTracked = btn.classList.contains('tracked');
            if (isTracked) {
                btn.classList.remove('tracked');
                btn.innerHTML = `+ Track`;
            } else {
                btn.classList.add('tracked');
                btn.innerHTML = `<i class="fas fa-check"></i> Tracked`;
            }
        }
        
        // History Graph Logic
        if (e.target.closest('.history-btn')) {
            const btn = e.target.closest('.history-btn');
            let graph = btn.closest('.product-details').querySelector('.trend-graph');
            
            if (!graph) {
                // Create a mock graph
                graph = document.createElement('div');
                graph.className = 'trend-graph';
                btn.closest('.product-details').appendChild(graph);
            }
            
            if (graph.style.display === 'block') {
                graph.style.display = 'none';
            } else {
                graph.style.display = 'block';
            }
        }
    });

    // Allow Enter key to trigger search
    searchInput.addEventListener('keypress', function (e) {
        if (e.key === 'Enter') {
            searchBtn.click();
        }
    });

    searchBtn.addEventListener('click', async () => {
        const query = searchInput.value.trim();
        if (!query) return;

        saveSearchTerm(query);
        recentSearchesContainer.classList.add('hidden');

        // Reset UI Context
        errorBox.classList.add('hidden');
        resultsArea.classList.add('hidden');
        saveOptions.classList.add('hidden');
        if (premiumActions) premiumActions.classList.add('hidden');
        settingsMenu.classList.add('hidden');
        resultsArea.innerHTML = '';
        loadingUI.classList.remove('hidden');
        
        // Reset state
        couponsApplied = false;
        if (applyCouponsBtn) {
            applyCouponsBtn.disabled = false;
            applyCouponsBtn.innerHTML = `<i class="fas fa-ticket-alt"></i> Coupons`;
            applyCouponsBtn.style.background = '';
        }
        if (focusModeToggle) focusModeToggle.checked = false;

        try {
            // Note: Flask server MUST be running on port 5000 and have CORS enabled
            const response = await fetch(`http://127.0.0.1:5000/api/extension/compare?query=${encodeURIComponent(query)}`);

            if (!response.ok) {
                throw new Error('Server returned an error. Ensure app.py is running.');
            }

            const data = await response.json();
            currentResults = data; // Save for export

            // Build Results View
            let html = '';

            // Render Amazon Section
            html += `
                <div class="store-section">
                    <div class="store-header amazon">
                        <h3>Amazon Results</h3>
                    </div>
            `;

            if (data.amazon && data.amazon.length > 0) {
                data.amazon.slice(0, 4).forEach(item => {
                    let price = item.product_price ? item.product_price : "Check Site";
                    if (price.includes('$')) {
                        // Assuming basic conversion or just display string manip for UI purposes
                        // For a real app, you'd fetch exchange rates.
                        const num = formatPrice(price);
                        if(num > 0) price = `Rs ${(num * 83).toFixed(2)}`; // Rough conversion
                    }
                    const rating = item.product_rating ? `⭐ ${item.product_rating}` : '';
                    const image = item.product_photo || 'https://via.placeholder.com/60';

                    html += `
                        <div class="product-item">
                            <img class="product-image" src="${image}" alt="Product">
                            <div class="product-details">
                                <a href="${item.product_url}" target="_blank" class="product-title">${item.product_title}</a>
                                <div class="product-footer">
                                    <span class="product-price">${price}</span>
                                    <div style="display:flex; gap:6px; align-items:center;">
                                        <span class="product-rating">${rating}</span>
                                        <button class="track-btn" title="Enable Price Drop Alerts (Coming Soon)">+ Track</button>
                                        <button class="history-btn" title="View 30-day Price Trend"><i class="fas fa-chart-line"></i></button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    `;
                });
            } else {
                html += `<p style="font-size: 13px; color: #7f8c8d;">No results found.</p>`;
            }
            html += `</div>`; // Close Amazon Section

            // Render Walmart Section
            html += `
                <div class="store-section">
                    <div class="store-header walmart">
                        <h3>Walmart Results</h3>
                    </div>
            `;

            if (data.walmart && data.walmart.length > 0) {
                data.walmart.slice(0, 4).forEach(item => {
                    const price = item.price && item.price.currentPrice ? `Rs ${(item.price.currentPrice * 83).toFixed(2)}` : "Check Site"; // Rough conversion
                    const rating = item.ratings ? `⭐ ${item.ratings}` : '';
                    const image = item.image || 'https://via.placeholder.com/60';
                    const link = item.link && item.link.startsWith('http') ? item.link : `https://www.walmart.com${item.link}`;

                    html += `
                        <div class="product-item">
                            <img class="product-image" src="${image}" alt="Product">
                            <div class="product-details">
                                <a href="${link}" target="_blank" class="product-title">${item.title}</a>
                                <div class="product-footer">
                                    <span class="product-price">${price}</span>
                                    <div style="display:flex; gap:6px; align-items:center;">
                                        <span class="product-rating">${rating}</span>
                                        <button class="track-btn" title="Enable Price Drop Alerts (Coming Soon)">+ Track</button>
                                        <button class="history-btn" title="View 30-day Price Trend"><i class="fas fa-chart-line"></i></button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    `;
                });
            } else {
                html += `<p style="font-size: 13px; color: #7f8c8d;">No results found.</p>`;
            }
            html += `</div>`; // Close Walmart Section

            resultsArea.innerHTML = html;
            loadingUI.classList.add('hidden');
            resultsArea.classList.remove('hidden');
            
            if ((data.amazon && data.amazon.length > 0) || (data.walmart && data.walmart.length > 0)) {
                saveOptions.classList.remove('hidden');
                if (premiumActions) premiumActions.classList.remove('hidden'); // Show premium buttons
            }

        } catch (error) {
            loadingUI.classList.add('hidden');
            errorBox.textContent = `Error: Cannot connect to server. Make sure your Python Flask app is running locally.`;
            errorBox.classList.remove('hidden');
        }
    });
});
