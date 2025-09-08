/**
 * Pagination Component for Device Simulator
 * Provides reusable pagination UI and functionality
 */

class PaginationComponent {
    constructor(containerId, onPageChange, options = {}) {
        this.container = document.getElementById(containerId);
        this.onPageChange = onPageChange;
        this.options = {
            showInfo: true,
            showSizeSelector: true,
            maxVisiblePages: 5,
            pageSizes: [10, 20, 50, 100],
            defaultPageSize: 20,
            ...options
        };
        
        this.currentPage = 1;
        this.totalPages = 1;
        this.totalItems = 0;
        this.pageSize = this.options.defaultPageSize;
        this.loading = false;
        
        if (!this.container) {
            console.error(`Pagination container with ID '${containerId}' not found`);
            return;
        }
        
        // Re-render on language change
        document.addEventListener('languageChanged', () => this.render());

        this.render();
    }
    
    /**
     * Update pagination state and re-render
     */
    update(paginationData) {
        if (!paginationData) return;
        
        this.currentPage = paginationData.page || 1;
        this.totalPages = paginationData.pages || 1;
        this.totalItems = paginationData.total || 0;
        this.pageSize = paginationData.per_page || this.pageSize;
        
        this.render();
    }
    
    /**
     * Set loading state
     */
    setLoading(loading) {
        this.loading = loading;
        this.render();
    }
    
    /**
     * Go to specific page
     */
    goToPage(page) {
        if (page < 1 || page > this.totalPages || page === this.currentPage || this.loading) {
            return;
        }
        
        this.currentPage = page;
        this.setLoading(true);
        
        if (this.onPageChange) {
            this.onPageChange(page, this.pageSize);
        }
    }
    
    /**
     * Change page size
     */
    changePageSize(newSize) {
        if (newSize === this.pageSize || this.loading) return;
        
        this.pageSize = newSize;
        this.currentPage = 1; // Reset to first page
        this.setLoading(true);
        
        if (this.onPageChange) {
            this.onPageChange(1, newSize);
        }
    }
    
    /**
     * Get visible page numbers for pagination controls
     */
    getVisiblePages() {
        const maxVisible = this.options.maxVisiblePages;
        const current = this.currentPage;
        const total = this.totalPages;
        
        if (total <= maxVisible) {
            return Array.from({ length: total }, (_, i) => i + 1);
        }
        
        const half = Math.floor(maxVisible / 2);
        let start = Math.max(1, current - half);
        let end = Math.min(total, start + maxVisible - 1);
        
        if (end - start + 1 < maxVisible) {
            start = Math.max(1, end - maxVisible + 1);
        }
        
        return Array.from({ length: end - start + 1 }, (_, i) => start + i);
    }
    
    /**
     * Render pagination component
     */
    render() {
        if (!this.container) return;
        
        const hasData = this.totalItems > 0;
        const hasPagination = this.totalPages > 1;
        
        this.container.innerHTML = `
            <div class="pagination-wrapper ${this.loading ? 'loading' : ''}">
                ${this.options.showInfo ? this.renderInfo() : ''}
                ${hasPagination ? this.renderPagination() : ''}
                ${this.options.showSizeSelector && hasData ? this.renderSizeSelector() : ''}
            </div>
        `;
        
        this.attachEventListeners();
    }
    
    /**
     * Render pagination info
     */
    renderInfo() {
        if (this.totalItems === 0) {
            const text = (window.i18n ? window.i18n.t('common.pagination.empty') : 'No items to display');
            return `<div class="pagination-info">${text}</div>`;
        }
        
        const start = (this.currentPage - 1) * this.pageSize + 1;
        const end = Math.min(this.currentPage * this.pageSize, this.totalItems);
        
        const text = (window.i18n 
            ? window.i18n.t('common.pagination.showing', { start, end, total: this.totalItems })
            : `Showing ${start}-${end} of ${this.totalItems} items`
        );
        return `<div class="pagination-info">${text}</div>`;
    }
    
    /**
     * Render pagination controls
     */
    renderPagination() {
        const visiblePages = this.getVisiblePages();
        const hasPrev = this.currentPage > 1;
        const hasNext = this.currentPage < this.totalPages;
        
        let paginationHTML = '<div class="pagination-controls">';
        
        // Previous button
        paginationHTML += `
            <button class="pagination-btn ${!hasPrev || this.loading ? 'disabled' : ''}" 
                    data-page="${this.currentPage - 1}" 
                    ${!hasPrev || this.loading ? 'disabled' : ''}
                    title="${window.i18n ? window.i18n.t('common.pagination.prev') : 'Previous'}">
                <i class="fas fa-chevron-left"></i>
            </button>
        `;
        
        // First page if not visible
        if (visiblePages[0] > 1) {
            paginationHTML += `
                <button class="pagination-btn" data-page="1">1</button>
                ${visiblePages[0] > 2 ? '<span class="pagination-ellipsis">...</span>' : ''}
            `;
        }
        
        // Visible page numbers
        visiblePages.forEach(page => {
            paginationHTML += `
                <button class="pagination-btn ${page === this.currentPage ? 'active' : ''} ${this.loading ? 'disabled' : ''}" 
                        data-page="${page}"
                        ${this.loading ? 'disabled' : ''}>
                    ${page}
                </button>
            `;
        });
        
        // Last page if not visible
        if (visiblePages[visiblePages.length - 1] < this.totalPages) {
            paginationHTML += `
                ${visiblePages[visiblePages.length - 1] < this.totalPages - 1 ? '<span class="pagination-ellipsis">...</span>' : ''}
                <button class="pagination-btn" data-page="${this.totalPages}">${this.totalPages}</button>
            `;
        }
        
        // Next button
        paginationHTML += `
            <button class="pagination-btn ${!hasNext || this.loading ? 'disabled' : ''}" 
                    data-page="${this.currentPage + 1}"
                    ${!hasNext || this.loading ? 'disabled' : ''}
                    title="${window.i18n ? window.i18n.t('common.pagination.next') : 'Next'}">
                <i class="fas fa-chevron-right"></i>
            </button>
        `;
        
        paginationHTML += '</div>';
        
        return paginationHTML;
    }
    
    /**
     * Render page size selector
     */
    renderSizeSelector() {
        const label = window.i18n ? window.i18n.t('common.pagination.per_page') : 'Items per page:';
        return `
            <div class="pagination-size-selector">
                <label for="page-size-select">${label}</label>
                <select id="page-size-select" ${this.loading ? 'disabled' : ''}>
                    ${this.options.pageSizes.map(size => 
                        `<option value="${size}" ${size === this.pageSize ? 'selected' : ''}>${size}</option>`
                    ).join('')}
                </select>
            </div>
        `;
    }
    
    /**
     * Attach event listeners
     */
    attachEventListeners() {
        if (!this.container) return;
        
        // Page buttons
        this.container.querySelectorAll('.pagination-btn[data-page]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const page = parseInt(btn.dataset.page);
                this.goToPage(page);
            });
        });
        
        // Page size selector
        const sizeSelect = this.container.querySelector('#page-size-select');
        if (sizeSelect) {
            sizeSelect.addEventListener('change', (e) => {
                const newSize = parseInt(e.target.value);
                this.changePageSize(newSize);
            });
        }
    }
    
    /**
     * Reset pagination to first page
     */
    reset() {
        this.currentPage = 1;
        this.totalPages = 1;
        this.totalItems = 0;
        this.render();
    }
    
    /**
     * Get current pagination state
     */
    getState() {
        return {
            page: this.currentPage,
            pageSize: this.pageSize,
            totalPages: this.totalPages,
            totalItems: this.totalItems
        };
    }
}

/**
 * Infinite Scroll Component
 * Provides infinite scroll functionality for lists
 */
class InfiniteScrollComponent {
    constructor(containerId, loadMoreCallback, options = {}) {
        this.container = document.getElementById(containerId);
        this.loadMoreCallback = loadMoreCallback;
        this.options = {
            threshold: 200, // pixels from bottom to trigger load
            debounceMs: 300,
            ...options
        };
        
        this.loading = false;
        this.hasMore = true;
        this.currentPage = 1;
        this.debounceTimer = null;
        
        if (!this.container) {
            console.error(`Infinite scroll container with ID '${containerId}' not found`);
            return;
        }
        
        this.init();
    }
    
    /**
     * Initialize infinite scroll
     */
    init() {
        this.container.addEventListener('scroll', this.handleScroll.bind(this));
        
        // Add loading indicator
        this.loadingIndicator = document.createElement('div');
        this.loadingIndicator.className = 'infinite-scroll-loading';
        const loadingText = window.i18n ? window.i18n.t('common.pagination.loading_more') : 'Loading more items...';
        this.loadingIndicator.innerHTML = `
            <div class="loading-spinner">
                <i class="fas fa-spinner fa-spin"></i>
                <span>${loadingText}</span>
            </div>
        `;
        this.loadingIndicator.style.display = 'none';
        this.container.appendChild(this.loadingIndicator);

        // Update loading text on language change
        document.addEventListener('languageChanged', () => {
            const txt = window.i18n ? window.i18n.t('common.pagination.loading_more') : 'Loading more items...';
            const span = this.loadingIndicator.querySelector('span');
            if (span) span.textContent = txt;
        });
    }
    
    /**
     * Handle scroll event
     */
    handleScroll() {
        if (this.loading || !this.hasMore) return;
        
        clearTimeout(this.debounceTimer);
        this.debounceTimer = setTimeout(() => {
            const { scrollTop, scrollHeight, clientHeight } = this.container;
            const distanceFromBottom = scrollHeight - scrollTop - clientHeight;
            
            if (distanceFromBottom <= this.options.threshold) {
                this.loadMore();
            }
        }, this.options.debounceMs);
    }
    
    /**
     * Load more items
     */
    async loadMore() {
        if (this.loading || !this.hasMore) return;
        
        this.setLoading(true);
        this.currentPage++;
        
        try {
            const result = await this.loadMoreCallback(this.currentPage);
            
            if (result && result.hasMore !== undefined) {
                this.hasMore = result.hasMore;
            }
            
            if (result && result.items && result.items.length === 0) {
                this.hasMore = false;
            }
            
        } catch (error) {
            console.error('Error loading more items:', error);
            this.currentPage--; // Revert page increment on error
        } finally {
            this.setLoading(false);
        }
    }
    
    /**
     * Set loading state
     */
    setLoading(loading) {
        this.loading = loading;
        this.loadingIndicator.style.display = loading ? 'block' : 'none';
    }
    
    /**
     * Reset infinite scroll
     */
    reset() {
        this.currentPage = 1;
        this.hasMore = true;
        this.loading = false;
        this.setLoading(false);
    }
    
    /**
     * Set whether there are more items to load
     */
    setHasMore(hasMore) {
        this.hasMore = hasMore;
        if (!hasMore) {
            this.setLoading(false);
        }
    }
    
    /**
     * Destroy infinite scroll component
     */
    destroy() {
        if (this.container) {
            this.container.removeEventListener('scroll', this.handleScroll.bind(this));
            if (this.loadingIndicator && this.loadingIndicator.parentNode) {
                this.loadingIndicator.parentNode.removeChild(this.loadingIndicator);
            }
        }
        clearTimeout(this.debounceTimer);
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { PaginationComponent, InfiniteScrollComponent };
}
