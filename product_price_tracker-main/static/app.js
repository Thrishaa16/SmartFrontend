// API Base URL
const API_BASE = window.location.origin;

// Global variables
let priceChart = null;
let modalChart = null;

// Initialize the app
document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
    loadProducts(); // Initial load with loading indicator
});

function setupEventListeners() {
    document.getElementById('refreshBtn').addEventListener('click', () => {
        triggerScrape();
    });

    // Add product button
    document.getElementById('addProductBtn').addEventListener('click', () => {
        showAddProductModal();
    });

    // Product detail modal
    const modal = document.getElementById('productModal');
    const closeBtn = document.querySelector('.close');
    
    closeBtn.addEventListener('click', () => {
        modal.classList.add('hidden');
    });

    window.addEventListener('click', (event) => {
        if (event.target === modal) {
            modal.classList.add('hidden');
        }
    });

    // Add product modal
    const addModal = document.getElementById('addProductModal');
    const closeAddBtn = document.querySelector('.close-add');
    const cancelAddBtn = document.getElementById('cancelAddBtn');
    
    closeAddBtn.addEventListener('click', () => {
        hideAddProductModal();
    });
    
    cancelAddBtn.addEventListener('click', () => {
        hideAddProductModal();
    });

    window.addEventListener('click', (event) => {
        if (event.target === addModal) {
            hideAddProductModal();
        }
    });

    // Form submission
    document.getElementById('addProductForm').addEventListener('submit', handleAddProduct);
    
    // Auto-detect platform from URL
    document.getElementById('productUrl').addEventListener('input', autoDetectPlatform);
}

let isLoading = false;

async function loadProducts(silent = false) {
    if (isLoading) return; // Prevent multiple simultaneous loads
    
    isLoading = true;
    if (!silent) {
        showLoading();
    }
    
    try {
        const response = await fetch(`${API_BASE}/api/products/summary`);
        const result = await response.json();
        
        if (result.success) {
            displayProducts(result.data);
            updateStats(result.data);
            updateLastRefreshTime(); // Update refresh time indicator
            if (!silent) {
                hideLoading();
            }
        } else {
            if (!silent) {
                showError(result.error || 'Failed to load products');
            }
        }
    } catch (error) {
        if (!silent) {
            showError('Error connecting to server: ' + error.message);
        }
    } finally {
        isLoading = false;
    }
}

function displayProducts(products) {
    const tbody = document.getElementById('productsTableBody');
    
    if (products.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center">No products found. Add products to utils/products.csv</td></tr>';
        return;
    }

    tbody.innerHTML = products.map(product => {
        // Handle products that haven't been scraped yet
        const hasPrice = product.current_price !== null && product.current_price !== undefined;
        const currentPrice = hasPrice ? product.current_price : null;
        const originalPrice = hasPrice ? (product.original_price || product.current_price) : null;
        const threshold = product.threshold || 0;
        
        // Check discount only if price exists
        const hasDiscount = hasPrice && currentPrice < originalPrice;
        const discountPercent = hasDiscount 
            ? (((originalPrice - currentPrice) / originalPrice) * 100).toFixed(1) + '%'
            : '0%';
        
        // Price change calculation
        const priceChange = product.price_change_percent !== null && product.price_change_percent !== undefined
            ? (product.price_change_percent > 0 ? '+' : '') + product.price_change_percent.toFixed(2) + '%'
            : hasPrice ? 'N/A' : 'Not scraped';
        const priceChangeClass = product.price_change_percent !== null && product.price_change_percent !== undefined
            ? (product.price_change_percent < 0 ? 'positive' : product.price_change_percent > 0 ? 'negative' : '')
            : '';
        
        // Check if current price meets threshold
        const meetsThreshold = hasPrice && currentPrice <= threshold;
        const thresholdStatus = hasPrice 
            ? (meetsThreshold 
                ? '<span class="badge badge-success">Price Met!</span>' 
                : `<span style="color: #dc3545;">Above by Rs ${(currentPrice - threshold).toFixed(2)}</span>`)
            : '<span style="color: #999;">Pending</span>';

        return `
            <tr>
                <td><strong>${escapeHtml(product.name)}</strong></td>
                <td><span class="badge badge-info">${escapeHtml(product.platform)}</span></td>
                <td>
                    ${hasPrice 
                        ? `<strong>Rs ${currentPrice.toFixed(2)}</strong>
                           ${hasDiscount ? `<br><small style="text-decoration: line-through; color: #666;">Rs ${originalPrice.toFixed(2)}</small>` : ''}`
                        : '<span style="color: #999; font-style: italic;">Not yet scraped</span>'}
                </td>
                <td>
                    <strong style="color: #667eea;">Rs ${threshold.toFixed(2)}</strong>
                    ${hasPrice ? thresholdStatus : ''}
                </td>
                <td class="price-change ${priceChangeClass}">${priceChange}</td>
                <td>
                    ${hasPrice 
                        ? (hasDiscount 
                            ? `<span class="badge badge-success">Discount: ${discountPercent}</span>` 
                            : '<span class="badge badge-danger">No Discount</span>')
                        : '<span class="badge" style="background: #e0e0e0; color: #666;">Pending</span>'}
                </td>
                <td>
                    ${hasPrice 
                        ? `<button class="btn-small" onclick="viewProductHistory('${escapeHtml(product.name)}')">
                               View History
                           </button>`
                        : ''}
                    <a href="${escapeHtml(product.url)}" target="_blank" class="btn-small" style="text-decoration: none; margin-left: 5px;">
                        Visit
                    </a>
                    <button class="btn-small btn-danger" onclick="deleteProduct('${escapeHtml(product.name)}')" style="margin-left: 5px;" title="Delete this product">
                        Delete
                    </button>
                </td>
            </tr>
        `;
    }).join('');
}

function updateStats(products) {
    const totalProducts = products.length;
    
    // Only count products that have been scraped
    const scrapedProducts = products.filter(p => p.current_price !== null && p.current_price !== undefined);
    const discountProducts = scrapedProducts.filter(p => {
        const originalPrice = p.original_price || p.current_price;
        return p.current_price < originalPrice;
    }).length;
    
    // Count products that meet their threshold
    const productsAtThreshold = scrapedProducts.filter(p => 
        p.current_price <= p.threshold
    ).length;
    
    const avgDiscount = scrapedProducts.length > 0
        ? scrapedProducts.reduce((sum, p) => {
            const originalPrice = p.original_price || p.current_price;
            const discount = p.current_price < originalPrice
                ? ((originalPrice - p.current_price) / originalPrice * 100)
                : 0;
            return sum + discount;
        }, 0) / scrapedProducts.length
        : 0;

    document.getElementById('totalProducts').textContent = totalProducts;
    document.getElementById('discountProducts').textContent = discountProducts;
    document.getElementById('avgDiscount').textContent = scrapedProducts.length > 0 ? avgDiscount.toFixed(1) + '%' : '-';
    
    // Update threshold met stat if element exists
    const thresholdMetEl = document.getElementById('thresholdMet');
    if (thresholdMetEl) {
        thresholdMetEl.textContent = productsAtThreshold + ' / ' + scrapedProducts.length;
    }
}

async function viewProductHistory(productName) {
    showLoading();
    try {
        const [historyResponse, summaryResponse] = await Promise.all([
            fetch(`${API_BASE}/api/prices/history?name=${encodeURIComponent(productName)}&limit=30`),
            fetch(`${API_BASE}/api/products/summary`)
        ]);

        const historyResult = await historyResponse.json();
        const summaryResult = await summaryResponse.json();

        if (historyResult.success && summaryResult.success) {
            const product = summaryResult.data.find(p => p.name === productName);
            showProductModal(product, historyResult.data);
        } else {
            showError('Failed to load product history');
        }
    } catch (error) {
        showError('Error loading product history: ' + error.message);
    } finally {
        hideLoading();
    }
}

function showProductModal(product, history) {
    const modal = document.getElementById('productModal');
    const modalTitle = document.getElementById('modalTitle');
    
    modalTitle.textContent = product.name;
    modal.classList.remove('hidden');

    // Create price history chart
    const ctx = document.getElementById('modalChart').getContext('2d');
    
    if (modalChart) {
        modalChart.destroy();
    }

    const labels = history.map(h => new Date(h.date).toLocaleDateString()).reverse();
    const prices = history.map(h => h.price).reverse();
    const thresholds = history.map(h => h.threshold).reverse();

    modalChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Price',
                data: prices,
                borderColor: 'rgb(102, 126, 234)',
                backgroundColor: 'rgba(102, 126, 234, 0.1)',
                tension: 0.4,
                fill: true
            }, {
                label: 'Threshold',
                data: thresholds,
                borderColor: 'rgb(220, 53, 69)',
                backgroundColor: 'rgba(220, 53, 69, 0.1)',
                borderDash: [5, 5],
                tension: 0.4,
                fill: false
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            },
            scales: {
                y: {
                    beginAtZero: false,
                    ticks: {
                        callback: function(value) {
                            return 'Rs ' + value.toFixed(2);
                        }
                    }
                }
            }
        }
    });

    // Create price history table
    const tableContainer = document.getElementById('priceHistoryTable');
    tableContainer.innerHTML = `
        <h3 style="margin-top: 30px;">Price History</h3>
        <div class="table-container">
            <table class="products-table">
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Price (Rs)</th>
                        <th>Threshold (Rs)</th>
                        <th>Platform</th>
                    </tr>
                </thead>
                <tbody>
                    ${history.slice().reverse().map(item => `
                        <tr>
                            <td>${new Date(item.date).toLocaleString()}</td>
                            <td>${item.price.toFixed(2)}</td>
                            <td>${item.threshold.toFixed(2)}</td>
                            <td>${escapeHtml(item.platform)}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>
    `;
}

async function triggerScrape() {
    const refreshBtn = document.getElementById('refreshBtn');
    refreshBtn.disabled = true;
    refreshBtn.textContent = 'Scraping...';
    showLoading();

    try {
        const response = await fetch(`${API_BASE}/api/scrape`, {
            method: 'POST'
        });
        const result = await response.json();

        if (result.success) {
            // Wait a bit then reload products
            setTimeout(() => {
                loadProducts();
                refreshBtn.disabled = false;
                refreshBtn.textContent = 'Refresh Prices';
            }, 3000);
        } else {
            showError(result.error || 'Failed to trigger scrape');
            refreshBtn.disabled = false;
            refreshBtn.textContent = 'Refresh Prices';
        }
    } catch (error) {
        showError('Error triggering scrape: ' + error.message);
        refreshBtn.disabled = false;
        refreshBtn.textContent = 'Refresh Prices';
    }
}

function showLoading() {
    document.getElementById('loading').classList.remove('hidden');
    document.getElementById('error').classList.add('hidden');
}

function hideLoading() {
    document.getElementById('loading').classList.add('hidden');
}

function showError(message) {
    const errorDiv = document.getElementById('error');
    errorDiv.textContent = message;
    errorDiv.classList.remove('hidden');
    hideLoading();
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showAddProductModal() {
    const modal = document.getElementById('addProductModal');
    modal.classList.remove('hidden');
    document.getElementById('addProductForm').reset();
    document.getElementById('addProductError').classList.add('hidden');
}

function hideAddProductModal() {
    const modal = document.getElementById('addProductModal');
    modal.classList.add('hidden');
    document.getElementById('addProductForm').reset();
    document.getElementById('addProductError').classList.add('hidden');
}

function autoDetectPlatform() {
    const urlInput = document.getElementById('productUrl');
    const platformSelect = document.getElementById('productPlatform');
    const url = urlInput.value.toLowerCase();
    
    if (url.includes('amazon')) {
        platformSelect.value = 'amazon';
    } else if (url.includes('flipkart')) {
        platformSelect.value = 'flipkart';
    }
}

async function handleAddProduct(event) {
    event.preventDefault();
    
    const errorDiv = document.getElementById('addProductError');
    errorDiv.classList.add('hidden');
    
    const formData = {
        name: document.getElementById('productName').value.trim(),
        url: document.getElementById('productUrl').value.trim(),
        platform: document.getElementById('productPlatform').value,
        threshold: parseFloat(document.getElementById('productThreshold').value)
    };
    
    // Client-side validation
    if (!formData.name) {
        showAddProductError('Product name is required');
        return;
    }
    
    if (!formData.url) {
        showAddProductError('Product URL is required');
        return;
    }
    
    if (!formData.platform) {
        showAddProductError('Please select a platform');
        return;
    }
    
    if (!formData.threshold || formData.threshold <= 0) {
        showAddProductError('Please enter a valid desired price (greater than 0)');
        return;
    }
    
    try {
        const submitBtn = event.target.querySelector('button[type="submit"]');
        submitBtn.disabled = true;
        submitBtn.textContent = 'Adding...';
        
        const response = await fetch(`${API_BASE}/api/products`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });
        
        const result = await response.json();
        
        if (result.success) {
            hideAddProductModal();
            // Reload products to show the new one
            loadProducts();
            // Show success message
            showSuccessMessage('Product added successfully!');
        } else {
            showAddProductError(result.error || 'Failed to add product');
        }
    } catch (error) {
        showAddProductError('Error adding product: ' + error.message);
    } finally {
        const submitBtn = event.target.querySelector('button[type="submit"]');
        submitBtn.disabled = false;
        submitBtn.textContent = 'Add Product';
    }
}

function showAddProductError(message) {
    const errorDiv = document.getElementById('addProductError');
    errorDiv.textContent = message;
    errorDiv.classList.remove('hidden');
}

function showSuccessMessage(message) {
    // Create a temporary success message
    const successDiv = document.createElement('div');
    successDiv.style.cssText = 'position: fixed; top: 20px; right: 20px; background: #28a745; color: white; padding: 15px 20px; border-radius: 6px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); z-index: 10000; animation: slideIn 0.3s ease;';
    successDiv.textContent = message;
    document.body.appendChild(successDiv);
    
    setTimeout(() => {
        successDiv.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => {
            document.body.removeChild(successDiv);
        }, 300);
    }, 3000);
}

async function deleteProduct(productName) {
    // Show confirmation dialog
    if (!confirm(`Are you sure you want to delete "${productName}"?\n\nThis action cannot be undone.`)) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/api/products/${encodeURIComponent(productName)}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (result.success) {
            showSuccessMessage(`Product "${productName}" deleted successfully!`);
            // Reload products to reflect the deletion
            loadProducts();
        } else {
            showError(`Failed to delete product: ${result.error || 'Unknown error'}`);
        }
    } catch (error) {
        showError('Error deleting product: ' + error.message);
    }
}

// Add CSS animations for success message
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// Auto-refresh every 30 seconds to show updated prices (silent refresh)
setInterval(() => {
    loadProducts(true); // Silent refresh - no loading indicator
}, 30 * 1000);

// Show last update time
function updateLastRefreshTime() {
    const now = new Date();
    const timeString = now.toLocaleTimeString();
    // Add a small indicator showing last refresh time
    const header = document.querySelector('header');
    if (header && !document.getElementById('lastRefresh')) {
        const refreshIndicator = document.createElement('div');
        refreshIndicator.id = 'lastRefresh';
        refreshIndicator.style.cssText = 'font-size: 0.85em; color: #666; margin-top: 5px;';
        refreshIndicator.textContent = `Last updated: ${timeString}`;
        header.appendChild(refreshIndicator);
    } else if (document.getElementById('lastRefresh')) {
        document.getElementById('lastRefresh').textContent = `Last updated: ${timeString}`;
    }
}

// Initial load is already handled in DOMContentLoaded

