    const API_DATA_URL = '/api/data';
    const API_RESET_URL = '/api/reset';
    const API_DATABASE_URL = '/api/database';
    const API_REELFARM_CONFIG_URL = '/api/reelfarm/config';
    const API_REELFARM_MATCHES_URL = '/api/reelfarm/matches';
    const REELFARM_WINDOW_KEY = 'management_table_reelfarm_window_days';

    const countryFlags = {
        'United States': '🇺🇸',
        'United Kingdom': '🇬🇧',
        'Japan': '🇯🇵',
        'Germany': '🇩🇪',
        'Brazil': '🇧🇷',
        'India': '🇮🇳',
        'China': '🇨🇳',
        'France': '🇫🇷',
        'Italy': '🇮🇹',
        'Canada': '🇨🇦',
        'Australia': '🇦🇺',
        'South Korea': '🇰🇷',
        'New Country': '🌐'
    };

    const countryCodes = {
        'United States': 'US',
        'United Kingdom': 'UK',
        'Japan': 'JP',
        'Germany': 'DE',
        'Brazil': 'BR',
        'India': 'IN',
        'China': 'CN',
        'France': 'FR',
        'Italy': 'IT',
        'Canada': 'CA',
        'Australia': 'AU',
        'South Korea': 'KR'
    };

    const tagColors = [
        '#6f76f5',
        '#9b6df3',
        '#d18b45',
        '#c46bd6',
        '#557ee8',
        '#8a8f98'
    ];

    let dbData = [];
    let selectedProductId = null;
    let selectedCountryId = null;
    let currentPage = 'products';
    let productSearch = '';
    let countrySearch = '';
    let latestDatabaseSnapshot = null;
    let reelFarmConfigured = false;
    let reelFarmResults = {};
    let reelFarmLoadingPrefix = '';
    let materialSlideIndexes = {};
    let expandedTopics = {};
    let expandedFormats = {};
    let expandedReelFarmCards = {};
    let materialPageIndexes = {};
    let reelFarmWindowDays = Number(localStorage.getItem(REELFARM_WINDOW_KEY)) || 30;
    if (![7, 14, 30].includes(reelFarmWindowDays)) reelFarmWindowDays = 30;

    function generateId() {
        return Math.random().toString(36).slice(2, 11);
    }

    function createDefaultData() {
        return [
            {
                id: generateId(),
                name: 'Product A',
                logo: '',
                folder: '甲方',
                countries: [
                    {
                        id: generateId(),
                        name: 'United States',
                        concepts: [
                            { id: generateId(), name: 'Tech Focus', count: 45 },
                            { id: generateId(), name: 'Lifestyle', count: 30 }
                        ]
                    },
                    {
                        id: generateId(),
                        name: 'Japan',
                        concepts: [
                            { id: generateId(), name: 'Design/Aesthetics', count: 50 }
                        ]
                    }
                ]
            },
            {
                id: generateId(),
                name: 'Product B',
                logo: '',
                folder: '乙方',
                countries: [
                    {
                        id: generateId(),
                        name: 'Germany',
                        concepts: [
                            { id: generateId(), name: 'Efficiency', count: 28 },
                            { id: generateId(), name: 'Sustainability', count: 18 }
                        ]
                    }
                ]
            }
        ];
    }

    function escapeHtml(value) {
        return String(value ?? '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    function slugPart(value) {
        const cleaned = String(value || '')
            .normalize('NFKD')
            .replace(/[\u0300-\u036f]/g, '')
            .replace(/[^a-zA-Z0-9]+/g, ' ')
            .trim();

        if (!cleaned) return 'Item';

        return cleaned
            .split(/\s+/)
            .map(part => part.charAt(0).toUpperCase() + part.slice(1))
            .join('');
    }

    function codeFromName(value) {
        const cleaned = String(value || '').replace(/[^a-zA-Z0-9 ]+/g, ' ').trim();
        if (!cleaned) return 'APP';
        const alias = cleaned.toLowerCase().replace(/\s+/g, '');
        if (alias === 'delust' || alias === 'dl') return 'DL';
        const compact = cleaned.replace(/\s+/g, '');
        if (compact.length <= 4) return compact.toUpperCase();

        const initials = cleaned
            .split(/\s+/)
            .map(part => part.charAt(0))
            .join('');

        return (initials || compact.slice(0, 4)).toUpperCase();
    }

    function getProductReelFarmCode(product) {
        return (product?.reelFarmCode || codeFromName(product?.name)).toUpperCase();
    }

    function getCountryReelFarmCode(country) {
        return (country?.reelFarmCode || countryCodes[country?.name] || codeFromName(country?.name)).toUpperCase();
    }

    function buildAutomationPrefix(product, country, concept) {
        const countryCode = getCountryReelFarmCode(country);
        const productCode = getProductReelFarmCode(product);
        const topic = slugPart(concept?.group || 'Topic');
        const format = slugPart(concept?.name || 'Format');
        return `${countryCode}-${productCode}-${topic}-${format}`;
    }

    function formatNumber(value) {
        const number = Number(value) || 0;
        return number.toLocaleString();
    }

    function formatPercent(value) {
        const number = Number(value) || 0;
        if (!number) return '0%';
        return `${number.toFixed(1)}%`;
    }

    function formatSchedule(value) {
        if (Array.isArray(value)) {
            return value
                .map(item => item?.cron || item?.schedule || '')
                .filter(Boolean)
                .join(', ') || 'no schedule';
        }

        return value || 'no schedule';
    }

    function getPostTimestamp(post) {
        const value = post?.published_at || '';
        const timestamp = Date.parse(value);
        return Number.isNaN(timestamp) ? null : timestamp;
    }

    function getPostWindowStart() {
        return Date.now() - (Number(reelFarmWindowDays) || 30) * 24 * 60 * 60 * 1000;
    }

    function isPostInSelectedWindow(post) {
        const timestamp = getPostTimestamp(post);
        return timestamp !== null && timestamp >= getPostWindowStart();
    }

    function getWindowedPosts(card) {
        return (card?.posts || []).filter(isPostInSelectedWindow);
    }

    function getSlideIndex(videoId) {
        return Number(materialSlideIndexes[videoId]) || 0;
    }

    function cardStateKey(card) {
        const automation = card?.automation || {};
        const account = card?.account || {};
        return String(
            automation.automation_id
            || automation.title
            || account.tiktok_account_id
            || account.account_username
            || generateId()
        );
    }

    function getMaterialPage(cardKey) {
        return Math.max(0, Number(materialPageIndexes[cardKey]) || 0);
    }

    function getCachedReelFarmResult(concept, prefix) {
        const liveResult = reelFarmResults[prefix];
        if (liveResult) return liveResult;

        if (concept?.reelFarmResult?.prefix === prefix) {
            return concept.reelFarmResult;
        }

        return null;
    }

    function findConceptByPrefix(prefix) {
        for (const product of dbData) {
            for (const country of product.countries || []) {
                for (const concept of country.concepts || []) {
                    if (buildAutomationPrefix(product, country, concept) === prefix) {
                        return concept;
                    }
                }
            }
        }

        return null;
    }

    function setStatus(message, type = 'ok') {
        const status = document.getElementById('serverStatus');
        if (!status) return;

        status.textContent = message;
        status.classList.toggle('error', type === 'error');
    }

    async function loadData() {
        if (window.location.protocol === 'file:') {
            dbData = createDefaultData();
            document.getElementById('launchWarning')?.classList.add('is-visible');
            setStatus('文件模式：未连接数据库', 'error');
            ensureSelection();
            return;
        }

        try {
            const response = await fetch(API_DATA_URL, { cache: 'no-store' });
            if (!response.ok) throw new Error('Failed to load database data.');

            const payload = await response.json();
            dbData = Array.isArray(payload.data) ? payload.data : createDefaultData();
            ensureSelection();
            setStatus('已连接 SQLite 数据库');
        } catch (error) {
            console.error(error);
            dbData = createDefaultData();
            ensureSelection();
            setStatus('后端未连接，当前为临时数据', 'error');
        }
    }

    async function loadReelFarmConfig() {
        if (window.location.protocol === 'file:') {
            reelFarmConfigured = false;
            return;
        }

        try {
            const response = await fetch(API_REELFARM_CONFIG_URL, { cache: 'no-store' });
            if (!response.ok) throw new Error('Failed to load ReelFarm config.');
            const payload = await response.json();
            reelFarmConfigured = Boolean(payload.configured);
        } catch (error) {
            console.error(error);
            reelFarmConfigured = false;
        }
    }

    async function persistData(shouldRender = true) {
        ensureSelection();
        if (shouldRender) renderApp();

        if (window.location.protocol === 'file:') {
            setStatus('文件模式无法保存到数据库', 'error');
            return;
        }

        try {
            setStatus('保存中...');
            const response = await fetch(API_DATA_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ data: dbData })
            });

            if (!response.ok) throw new Error('Failed to save database data.');
            setStatus('已保存到 SQLite 数据库');
        } catch (error) {
            console.error(error);
            setStatus('保存失败，请确认后端服务正在运行', 'error');
        }
    }

    function saveData() {
        persistData(true);
    }

    function getSelectedProduct() {
        return dbData.find(product => product.id === selectedProductId) || null;
    }

    function getSelectedCountry() {
        const product = getSelectedProduct();
        if (!product) return null;

        return (product.countries || []).find(country => country.id === selectedCountryId) || null;
    }

    function normalizeProductFolder(product) {
        if (!['甲方', '乙方'].includes(product.folder)) {
            product.folder = '甲方';
        }

        return product.folder;
    }

    function normalizeFormatGroups(country) {
        if (!country || !Array.isArray(country.concepts)) return;

        country.concepts.forEach(concept => {
            if (!concept.group) concept.group = '默认 Topic';
        });
    }

    function ensureSelection() {
        dbData.forEach(normalizeProductFolder);

        if (!dbData.some(product => product.id === selectedProductId)) {
            selectedProductId = dbData[0]?.id || null;
        }

        const product = getSelectedProduct();
        if (!product) {
            selectedCountryId = null;
            return;
        }

        if (!Array.isArray(product.countries)) product.countries = [];
        if (!product.countries.some(country => country.id === selectedCountryId)) {
            selectedCountryId = product.countries[0]?.id || null;
        }

        product.countries.forEach(normalizeFormatGroups);
    }

    function getStats(scopeProduct = null, scopeCountry = null) {
        const products = scopeProduct ? [scopeProduct] : dbData;
        const countries = products.flatMap(product => product.countries || []);
        const concepts = scopeCountry
            ? (scopeCountry.concepts || [])
            : countries.flatMap(country => country.concepts || []);
        const total = concepts.reduce((sum, concept) => sum + (Number(concept.count) || 0), 0);

        return {
            products: products.length,
            countries: countries.length,
            concepts: concepts.length,
            total
        };
    }

    function getTagColor(text) {
        let hash = 0;
        for (let i = 0; i < String(text).length; i += 1) {
            hash = String(text).charCodeAt(i) + ((hash << 5) - hash);
        }
        return tagColors[Math.abs(hash) % tagColors.length];
    }

    function getFormatGroups(concepts) {
        const groups = [];
        const byName = new Map();

        concepts.forEach(concept => {
            const groupName = concept.group || '默认 Topic';
            if (!byName.has(groupName)) {
                const group = { name: groupName, concepts: [] };
                byName.set(groupName, group);
                groups.push(group);
            }
            byName.get(groupName).concepts.push(concept);
        });

        return groups;
    }

    function topicStateKey(countryId, groupName) {
        return `${countryId || 'none'}::${groupName || '默认 Topic'}`;
    }

    function isTopicExpanded(countryId, groupName) {
        return Boolean(expandedTopics[topicStateKey(countryId, groupName)]);
    }

    function setTopicExpanded(countryId, groupName, isOpen) {
        const key = topicStateKey(countryId, groupName);
        if (isOpen) {
            expandedTopics[key] = true;
        } else {
            delete expandedTopics[key];
        }
    }

    function isFormatExpanded(conceptId) {
        return Boolean(expandedFormats[conceptId]);
    }

    function renderApp() {
        ensureSelection();
        renderMetrics();
        renderBreadcrumbs();
        renderPages();
    }

    function setActivePage(page) {
        currentPage = page;
        renderApp();
    }

    function renderBreadcrumbs() {
        const product = getSelectedProduct();
        const country = getSelectedCountry();
        const crumbs = [
            `<button class="crumb-btn" type="button" onclick="goProducts()">产品总览</button>`
        ];

        if (currentPage !== 'products' && product) {
            crumbs.push('<span>/</span>');
            if (currentPage === 'country') {
                crumbs.push(`<button class="crumb-btn" type="button" onclick="goProduct('${product.id}')">${escapeHtml(product.name || '未命名产品')}</button>`);
            } else {
                crumbs.push(`<span class="crumb-current">${escapeHtml(product.name || '未命名产品')}</span>`);
            }
        }

        if (currentPage === 'country' && country) {
            crumbs.push('<span>/</span>');
            crumbs.push(`<span class="crumb-current">${escapeHtml(country.name || 'New Country')}</span>`);
        }

        document.getElementById('breadcrumbs').innerHTML = crumbs.join('');
    }

    function renderPages() {
        document.querySelectorAll('.page').forEach(page => page.classList.remove('active'));
        const page = document.getElementById(`${currentPage}Page`);
        if (page) page.classList.add('active');

        renderProductsPage();
        renderProductPage();
        renderCountryPage();
    }

    function renderProductsPage() {
        const page = document.getElementById('productsPage');
        page.innerHTML = `
            <section class="page-card">
                <div class="pane-header">
                    <div class="pane-title-row">
                        <div>
                            <h2 class="pane-title">产品总览</h2>
                            <div class="pane-hint">先从甲方 / 乙方文件夹选择产品，再继续进入国家和 Format。</div>
                        </div>
                        <button class="btn primary" type="button" onclick="addNewProduct()">新建产品</button>
                    </div>
                    <input id="productSearch" class="search-input" type="search" placeholder="搜索产品" value="${escapeHtml(productSearch)}" oninput="setProductSearch(this.value)">
                </div>
                <div id="productList" class="list"></div>
            </section>`;
        renderProducts();
    }

    function renderProductPage() {
        const page = document.getElementById('productPage');
        const product = getSelectedProduct();

        if (!product) {
            page.innerHTML = '<section class="page-card"><div class="empty-state"><div class="empty-title">选择或创建一个产品</div></div></section>';
            return;
        }

        page.innerHTML = `
            <section class="page-card">
                <div id="productDetail" class="detail"></div>
            </section>
            <section class="page-card">
                <div class="pane-header">
                    <div class="pane-title-row">
                        <div>
                            <h2 class="pane-title">国家/地区</h2>
                            <div class="pane-hint">点击国家/地区进入 Topic 和 Format。</div>
                        </div>
                        <button class="btn primary" type="button" onclick="addCountryToSelected()">新建国家/地区</button>
                    </div>
                    <input id="countrySearch" class="search-input" type="search" placeholder="搜索国家/地区" value="${escapeHtml(countrySearch)}" oninput="setCountrySearch(this.value)">
                </div>
                <div id="countryList" class="country-grid"></div>
            </section>`;
        renderProductDetail();
        renderCountries();
    }

    function renderCountryPage() {
        const page = document.getElementById('countryPage');
        const country = getSelectedCountry();

        if (!country) {
            page.innerHTML = '<section class="page-card"><div class="empty-state"><div class="empty-title">先选择国家/地区</div></div></section>';
            return;
        }

        page.innerHTML = `
            <section class="country-workspace">
                <aside id="conceptContext" class="country-sidebar"></aside>
                <section class="topic-panel">
                    <div class="topic-panel-head">
                        <div>
                            <h2 class="topic-panel-title">Topic</h2>
                            <div class="context-meta">点开一个 Topic 后，再管理里面的 Format 和 ReelFarm 素材。</div>
                        </div>
                        <button class="btn primary" type="button" onclick="addFormatGroupToSelected()">新建 Topic</button>
                    </div>
                    <div id="conceptList" class="concept-area"></div>
                </section>
            </section>`;
        renderFormats();
    }

    function renderMetrics() {
        const stats = getStats();
        document.getElementById('metrics').innerHTML = [
            ['产品', stats.products],
            ['国家/地区', stats.countries],
            ['创意', stats.concepts],
            ['总数量', stats.total]
        ].map(([label, value]) => `
            <div class="metric">
                <div class="metric-label">${label}</div>
                <div class="metric-value">${value}</div>
            </div>
        `).join('');
    }

    function renderProducts() {
        const list = document.getElementById('productList');
        const query = productSearch.trim().toLowerCase();
        const products = dbData.filter(product => !query || String(product.name).toLowerCase().includes(query));

        if (dbData.length === 0) {
            list.innerHTML = `
                <div class="empty-state">
                    <div class="empty-title">还没有产品</div>
                    <button class="btn primary" type="button" onclick="addNewProduct()">添加第一个产品</button>
                </div>`;
            return;
        }

        if (products.length === 0) {
            list.innerHTML = '<div class="empty-state"><div class="empty-title">没有匹配的产品</div><div>换一个关键词试试。</div></div>';
            return;
        }

        list.innerHTML = ['甲方', '乙方'].map(folder => {
            const folderProducts = products.filter(product => normalizeProductFolder(product) === folder);
            return renderProductFolder(folder, folderProducts);
        }).join('');
    }

    function renderProductFolder(folder, products) {
        return `
            <section class="product-folder">
                <div class="folder-heading">
                    <span>${folder}</span>
                    <span class="folder-count">${products.length} 个产品</span>
                </div>
                <div class="folder-items">
                    ${products.length === 0
                        ? '<div class="item-meta" style="padding: 8px 4px;">暂无产品</div>'
                        : products.map(renderProductItem).join('')}
                </div>
            </section>`;
    }

    function renderProductItem(product) {
            const stats = getStats(product);
            const logo = product.logo
                ? `<img src="${product.logo}" alt="${escapeHtml(product.name)} Logo">`
                : escapeHtml(String(product.name || 'P').slice(0, 1).toUpperCase());

            return `
                <button class="list-item ${product.id === selectedProductId ? 'active' : ''}" type="button" onclick="selectProduct('${product.id}')">
                    <div class="product-row">
                        <span class="logo-chip">${logo}</span>
                        <span class="item-main">
                            <span class="item-name">${escapeHtml(product.name || '未命名产品')}</span>
                            <span class="item-meta">${stats.countries} 个国家/地区 · ${stats.concepts} 个创意 · ${stats.total} 数量</span>
                        </span>
                    </div>
                </button>`;
    }

    function renderProductDetail() {
        const container = document.getElementById('productDetail');
        const product = getSelectedProduct();

        if (!product) {
            container.innerHTML = '<div class="empty-state"><div class="empty-title">选择或创建一个产品</div></div>';
            return;
        }

        const logo = product.logo
            ? `<img src="${product.logo}" alt="${escapeHtml(product.name)} Logo">`
            : 'Logo<br>上传';

        container.innerHTML = `
            <div class="detail-grid">
                <label class="logo-upload" title="点击上传 Logo">
                    ${logo}
                    <input type="file" accept="image/*" style="display:none;" onchange="handleImageUpload(this, '${product.id}')">
                </label>
                <div class="field-stack">
                    <label>
                        <span class="field-label">当前产品</span>
                        <input class="text-input" value="${escapeHtml(product.name || '')}" onchange="updateProductName('${product.id}', this.value)" onblur="updateProductName('${product.id}', this.value)">
                    </label>
                    <label>
                        <span class="field-label">所属文件夹</span>
                        <select class="text-input" onchange="updateProductFolder('${product.id}', this.value)">
                            <option value="甲方" ${normalizeProductFolder(product) === '甲方' ? 'selected' : ''}>甲方</option>
                            <option value="乙方" ${normalizeProductFolder(product) === '乙方' ? 'selected' : ''}>乙方</option>
                        </select>
                    </label>
                    <label>
                        <span class="field-label">ReelFarm 产品代码</span>
                        <input class="text-input" value="${escapeHtml(getProductReelFarmCode(product))}" placeholder="例如 DL"
                            onchange="updateProductReelFarmCode('${product.id}', this.value)"
                            onblur="updateProductReelFarmCode('${product.id}', this.value)">
                    </label>
                    <button class="btn danger" type="button" onclick="deleteProduct('${product.id}')">删除产品</button>
                </div>
            </div>`;
    }

    function renderCountries() {
        const list = document.getElementById('countryList');
        const product = getSelectedProduct();

        if (!product) {
            list.innerHTML = '<div class="empty-state"><div class="empty-title">先选择产品</div></div>';
            return;
        }

        const countries = product.countries || [];
        const query = countrySearch.trim().toLowerCase();
        const filtered = countries.filter(country => !query || String(country.name).toLowerCase().includes(query));

        if (countries.length === 0) {
            list.innerHTML = `
                <div class="empty-state">
                    <div class="empty-title">这个产品还没有国家/地区</div>
                    <button class="btn primary" type="button" onclick="addCountryToSelected()">添加国家/地区</button>
                </div>`;
            return;
        }

        if (filtered.length === 0) {
            list.innerHTML = '<div class="empty-state"><div class="empty-title">没有匹配的国家/地区</div><div>换一个关键词试试。</div></div>';
            return;
        }

        list.innerHTML = filtered.map(country => {
            const concepts = country.concepts || [];
            const total = concepts.reduce((sum, concept) => sum + (Number(concept.count) || 0), 0);
            const flag = countryFlags[country.name] || '🌐';

            return `
                <button class="list-item ${country.id === selectedCountryId ? 'active' : ''}" type="button" onclick="selectCountry('${country.id}')">
                    <div class="country-row">
                        <span class="flag-chip">${flag}</span>
                        <span class="item-main">
                            <span class="item-name">${escapeHtml(country.name || 'New Country')}</span>
                            <span class="item-meta">${concepts.length} 个创意 · ${total} 数量</span>
                        </span>
                    </div>
                </button>`;
        }).join('');
    }

    function renderFormats() {
        const context = document.getElementById('conceptContext');
        const list = document.getElementById('conceptList');
        const product = getSelectedProduct();
        const country = getSelectedCountry();

        if (!product) {
            context.innerHTML = '<div class="country-sidebar-head"><h2 class="country-sidebar-title">创意</h2><div class="context-meta">先选择一个产品。</div></div>';
            list.innerHTML = '<div class="empty-state"><div class="empty-title">暂无上下文</div></div>';
            return;
        }

        if (!country) {
            context.innerHTML = `
                <div class="country-sidebar-head">
                    <h2 class="country-sidebar-title">${escapeHtml(product.name)} 的创意</h2>
                    <div class="context-meta">先为这个产品添加国家/地区。</div>
                </div>
                <button class="btn primary" type="button" onclick="addCountryToSelected()">添加国家/地区</button>`;
            list.innerHTML = '<div class="empty-state"><div class="empty-title">还没有国家/地区</div></div>';
            return;
        }

        const concepts = country.concepts || [];
        normalizeFormatGroups(country);
        const total = concepts.reduce((sum, concept) => sum + (Number(concept.count) || 0), 0);
        const groups = getFormatGroups(concepts);
        const countrySyncKey = `country:${country.id}`;
        const isCountrySyncing = reelFarmLoadingPrefix === countrySyncKey;
        const windowOptions = [7, 14, 30];

        context.innerHTML = `
            <div class="country-sidebar-head">
                <div class="country-title-row">
                    <h2 class="country-sidebar-title">${escapeHtml(country.name)} 的创意</h2>
                    <button class="btn primary" type="button" onclick="syncCurrentCountryReelFarm()" ${isCountrySyncing ? 'disabled' : ''}>${isCountrySyncing ? '同步中...' : '同步当前区'}</button>
                </div>
                <div class="context-meta">${escapeHtml(product.name)} · ${groups.length} 个 Topic · ${concepts.length} 个 Format · ${total} 数量</div>
                <div class="time-filter" role="group" aria-label="ReelFarm 时间维度">
                    <span class="time-filter-label">观察窗口</span>
                    <div class="time-filter-options">
                        ${windowOptions.map(days => `
                            <button class="time-filter-btn ${Number(reelFarmWindowDays) === days ? 'active' : ''}" type="button" onclick="setReelFarmWindow(${days})">${days}day</button>
                        `).join('')}
                    </div>
                </div>
            </div>
            <div class="country-sidebar-fields">
                <label>
                    <span class="field-label">当前国家/地区</span>
                    <input class="text-input" value="${escapeHtml(country.name || '')}"
                        onchange="updateCountryName('${country.id}', this.value)"
                        onblur="updateCountryName('${country.id}', this.value)">
                </label>
                <label>
                    <span class="field-label">ReelFarm 国家代码</span>
                    <input class="text-input" value="${escapeHtml(getCountryReelFarmCode(country))}" placeholder="例如 US"
                        onchange="updateCountryReelFarmCode('${country.id}', this.value)"
                        onblur="updateCountryReelFarmCode('${country.id}', this.value)">
                </label>
            </div>
            <div class="top-actions">
                <button class="btn danger" type="button" onclick="deleteCountry('${country.id}')">删除国家/地区</button>
            </div>`;

        if (concepts.length === 0) {
            list.innerHTML = `
                <div class="empty-state">
                    <div class="empty-title">这个国家/地区还没有创意</div>
                    <button class="btn primary" type="button" onclick="addFormatGroupToSelected()">添加第一个 Topic</button>
                </div>`;
            return;
        }

        list.innerHTML = groups.map(renderFormatGroup).join('');
    }

    function renderFormatGroup(group) {
        const color = getTagColor(group.name);
        const total = group.concepts.reduce((sum, concept) => sum + (Number(concept.count) || 0), 0);
        const country = getSelectedCountry();
        const isOpen = isTopicExpanded(country?.id, group.name);

        return `
            <section class="concept-group ${isOpen ? 'is-open' : ''}">
                <div class="concept-group-header">
                    <div class="concept-group-title" style="border-color:${color}33; background:${color}0f;">
                        <button class="topic-toggle" type="button" data-group="${escapeHtml(group.name)}" onclick="toggleTopic(this.dataset.group)" title="${isOpen ? '收起 Topic' : '展开 Topic'}">
                            <span class="topic-chevron">›</span>
                            <span class="concept-dot" style="background:${color};"></span>
                        </button>
                        <span class="concept-path">Topic</span>
                        <input class="concept-input" value="${escapeHtml(group.name)}"
                            data-group="${escapeHtml(group.name)}"
                            onchange="updateFormatGroup(this.dataset.group, this.value)"
                            onblur="updateFormatGroup(this.dataset.group, this.value)">
                    </div>
                    <button class="btn ghost" type="button" data-group="${escapeHtml(group.name)}" onclick="addFormatToGroup(this.dataset.group)">添加 Format</button>
                    <button class="delete-btn" type="button" data-group="${escapeHtml(group.name)}" onclick="deleteFormatGroup(this.dataset.group)">删除组</button>
                </div>
                <div class="item-meta topic-summary">${group.concepts.length} 个 Format · ${total} 数量</div>
                ${isOpen ? `
                    <div class="concept-group-items">
                        ${group.concepts.map(renderFormatRow).join('')}
                    </div>` : ''}
            </section>`;
    }

    function renderFormatRow(concept) {
        const color = getTagColor(concept.name);
        const product = getSelectedProduct();
        const country = getSelectedCountry();
        const reelFarmHtml = product && country ? renderReelFarmFormat(product, country, concept) : '';
        const isOpen = isFormatExpanded(concept.id);

        return `
            <section class="format-block ${isOpen ? 'is-open' : ''}">
                <div class="concept-row">
                    <button class="format-toggle" type="button" onclick="toggleFormat('${concept.id}')" title="${isOpen ? '收起 Format' : '展开 Format'}">
                        <span class="format-chevron">›</span>
                    </button>
                    <div class="concept-name-shell" style="border-color:${color}33; background:${color}0f;">
                        <span class="concept-dot" style="background:${color};"></span>
                        <input class="concept-input" value="${escapeHtml(concept.name || '')}"
                            onchange="updateFormatName('${concept.id}', this.value)"
                            onblur="updateFormatName('${concept.id}', this.value)">
                    </div>
                    <input class="number-input" type="number" min="0" value="${Number(concept.count) || 0}"
                        onchange="updateFormatCount('${concept.id}', this.value)"
                        onblur="updateFormatCount('${concept.id}', this.value)">
                    <button class="delete-btn" type="button" title="删除 Format" onclick="deleteFormat('${concept.id}')">删除</button>
                </div>
                ${isOpen ? reelFarmHtml : ''}
            </section>`;
    }

    function renderReelFarmFormat(product, country, concept) {
        const prefix = buildAutomationPrefix(product, country, concept);
        const result = getCachedReelFarmResult(concept, prefix);
        const isLoading = reelFarmLoadingPrefix === prefix;
        let body = '';

        if (isLoading) {
            body = '<div class="empty-state"><div class="empty-title">正在从 ReelFarm 拉取...</div></div>';
        } else if (result?.error) {
            body = `<div class="empty-state"><div class="empty-title">同步失败</div><div>${escapeHtml(result.error)}</div></div>`;
        } else if (result?.cards?.length) {
            const visibleCards = result.cards.filter(card => getWindowedPosts(card).length > 0);
            body = `
                <div class="creator-table">
                    <div class="creator-table-head">
                        <div>Creator ↕</div>
                        <div>Posts ↕</div>
                        <div>Slides ↕</div>
                        <div>Views ↕</div>
                        <div>Likes ↕</div>
                        <div>Comments ↕</div>
                        <div>Shares ↕</div>
                        <div>% Engagement ↕</div>
                        <div></div>
                    </div>
                    <div class="reelfarm-cards">${visibleCards.map(renderReelFarmCard).join('')}</div>
                </div>
                ${visibleCards.length
                    ? ''
                    : `<div class="empty-state compact"><div class="empty-title">最近 ${Number(reelFarmWindowDays) || 30} 天没有素材</div><div>这个 Format 有同步记录，但没有匹配当前观察窗口的 posted 素材。</div></div>`}`;
        } else if (result) {
            body = '<div class="empty-state"><div class="empty-title">没有找到匹配 automation</div><div>确认 ReelFarm 里 automation name 是否以这个 prefix 开头。</div></div>';
        } else {
            body = '<div class="item-meta">点击左侧「同步当前区」后，会显示每个 TikTok 账号、slideshow、播放/点赞/评论等数据。</div>';
        }

        return `
            <section class="reelfarm-format">
                <div class="reelfarm-format-head">
                    <div>
                        <span class="automation-prefix">${escapeHtml(prefix)}</span>
                        <div class="item-meta">${escapeHtml(concept.group || '默认 Topic')} · ${escapeHtml(concept.name || 'Format')}</div>
                        ${concept.reelFarmSyncedAt && concept.reelFarmResult?.prefix === prefix
                            ? `<div class="item-meta">上次同步：${escapeHtml(concept.reelFarmSyncedAt)}</div>`
                            : ''}
                    </div>
                </div>
                ${body}
            </section>`;
    }

    function getMetricFromPosts(posts, key) {
        return posts.reduce((sum, post) => sum + (Number(post[key]) || 0), 0);
    }

    function renderReelFarmCard(card) {
        const automation = card.automation || {};
        const account = card.account || {};
        const cardKey = cardStateKey(card);
        const isOpen = Boolean(expandedReelFarmCards[cardKey]);
        const accountName = account.account_username || account.username || account.account_name || automation.tiktok_account_id || '未绑定账号';
        const displayAccount = String(accountName).startsWith('@') ? accountName : `@${accountName}`;
        const accountInitial = String(accountName || '?').replace('@', '').slice(0, 2).toUpperCase() || '?';
        const schedule = formatSchedule(automation.schedule);
        const avatar = account.account_image
            ? `<img src="${escapeHtml(account.account_image)}" alt="">`
            : escapeHtml(accountInitial);
        const posts = getWindowedPosts(card);
        const videos = card.videos || [];
        const views = getMetricFromPosts(posts, 'view_count');
        const likes = getMetricFromPosts(posts, 'like_count');
        const comments = getMetricFromPosts(posts, 'comment_count');
        const shares = getMetricFromPosts(posts, 'share_count');
        const engagement = views > 0 ? ((likes + comments + shares) / views) * 100 : 0;
        const postsByVideo = new Map(posts.map(post => [String(post.video_id), post]));
        const slideshows = videos.filter(video => {
            const isSlideshow = String(video.video_type || '').toLowerCase().includes('slideshow') || Array.isArray(video.slideshow_images);
            return isSlideshow && postsByVideo.has(String(video.video_id));
        });
        const title = automation.title || automation.automation_id || 'Untitled automation';
        const statRows = [
            ['Posts', formatNumber(posts.length)],
            ['Slides', formatNumber(slideshows.length)],
            ['Views', formatNumber(views)],
            ['Likes', formatNumber(likes)],
            ['Comments', formatNumber(comments)],
            ['Shares', formatNumber(shares)],
            ['Engagement', formatPercent(engagement)]
        ];
        const pageSize = 4;
        const totalPages = Math.max(1, Math.ceil(slideshows.length / pageSize));
        const page = Math.min(getMaterialPage(cardKey), totalPages - 1);
        const pageItems = slideshows.slice(page * pageSize, page * pageSize + pageSize);

        return `
            <article class="reelfarm-card ${isOpen ? 'is-open' : ''}">
                <div class="creator-header" role="button" tabindex="0" data-card="${escapeHtml(cardKey)}"
                    onclick="toggleReelFarmCard(this.dataset.card)"
                    onkeydown="if(event.key === 'Enter' || event.key === ' '){ event.preventDefault(); toggleReelFarmCard(this.dataset.card); }">
                    <div class="reelfarm-account">
                        <span class="reelfarm-avatar">${avatar}</span>
                        <span class="creator-meta">
                            <span class="creator-name-line">
                                <span class="creator-name">${escapeHtml(accountName)}</span>
                                <span class="creator-chip">${escapeHtml(automation.status || 'unknown')}</span>
                            </span>
                            <span class="creator-subline">${escapeHtml(displayAccount)} · ${escapeHtml(schedule)} · 最近 ${Number(reelFarmWindowDays) || 30} 天</span>
                        </span>
                    </div>
                    ${statRows.map(([label, value]) => `
                        <div class="creator-stat">
                            <div class="creator-stat-value">${escapeHtml(value)}</div>
                            <div class="creator-stat-label">${escapeHtml(label)}</div>
                        </div>`).join('')}
                    <span class="creator-expand">›</span>
                </div>
                <div class="creator-row-subtitle">${escapeHtml(title)}</div>
                ${isOpen ? `
                    <div class="creator-toolbar">
                        <div class="creator-toolbar-title">Posts by ${escapeHtml(displayAccount)}</div>
                        <div class="creator-toolbar-pill">Recently Published</div>
                    </div>
                    <div class="slideshow-list">
                        ${pageItems.length
                            ? pageItems.map(video => renderMaterialItem(video, postsByVideo.get(String(video.video_id)), accountName, avatar)).join('')
                            : '<div class="item-meta" style="color:#bfb7ad;">暂无素材数据</div>'}
                    </div>
                    ${slideshows.length > pageSize ? `
                        <div class="post-pager">
                            <span>${page + 1}/${totalPages}</span>
                            <div class="post-pager-controls">
                                <button class="post-page-btn" type="button" data-card="${escapeHtml(cardKey)}" ${page === 0 ? 'disabled' : ''} onclick="moveMaterialPage(this.dataset.card, -1)">Previous</button>
                                <button class="post-page-btn" type="button" data-card="${escapeHtml(cardKey)}" ${page >= totalPages - 1 ? 'disabled' : ''} onclick="moveMaterialPage(this.dataset.card, 1)">Next</button>
                            </div>
                        </div>` : ''}
                    ${card.errors?.videos || card.errors?.posts
                        ? `<div class="item-meta" style="padding:0 14px 14px; color:#bfb7ad;">${escapeHtml(card.errors.videos || card.errors.posts)}</div>`
                        : ''}
                ` : ''}
            </article>`;
    }

    function renderMaterialItem(video, post, accountName, avatarHtml) {
        const title = video.hook || post?.title || video.prompt_preview || video.video_id || video.id || 'Slideshow';
        const images = Array.isArray(video.slideshow_images) ? video.slideshow_images : [];
        const imageCount = video.slide_count || images.length;
        const meta = [
            imageCount ? `${imageCount} slides` : '',
            video.finished_at || video.created_at || ''
        ].filter(Boolean).join(' · ');
        const displayAccount = String(accountName || '').startsWith('@') ? accountName : `@${accountName || 'unknown'}`;
        const dataRows = [
            ['Views', post?.view_count],
            ['Likes', post?.like_count],
            ['Comments', post?.comment_count],
            ['Shares', post?.share_count],
            ['Saves', post?.bookmark_count]
        ];

        const content = `
            <div class="slideshow-card-head">
                <div class="slideshow-card-account">
                    <span class="reelfarm-avatar">${avatarHtml}</span>
                    <span>${escapeHtml(displayAccount)}</span>
                </div>
                <span class="tiktok-pill">♪</span>
            </div>
            <div class="material-preview">
                ${renderSlideImage(video, images)}
            </div>
            <div class="slideshow-body">
                <div class="slideshow-title">${escapeHtml(title)}</div>
                <div class="slideshow-meta">${escapeHtml(meta || video.status || 'unknown')}</div>
                <div class="material-data">
                    ${dataRows.map(([label, value]) => `
                        <div class="material-data-cell">
                            <div class="material-data-label">${label}</div>
                            <div class="material-data-value">${post ? formatNumber(value) : '—'}</div>
                        </div>`).join('')}
                </div>
                <div class="slideshow-footer">
                    <span>${post?.published_at ? `Published ${escapeHtml(post.published_at)}` : '暂无 TikTok 发布数据'}</span>
                    <span>${escapeHtml(video.status || '')}</span>
                </div>
            </div>`;

        return `<div class="slideshow-item">${content}</div>`;
    }

    function renderSlideImage(video, images) {
        const videoId = String(video.video_id || video.id || generateId());
        const slideIndex = Math.min(getSlideIndex(videoId), Math.max(0, images.length - 1));
        const current = images[slideIndex];

        if (!current?.image_url) {
            return '<div class="empty-state" style="padding:32px 12px;"><div class="empty-title">暂无图片</div></div>';
        }

        return `
            <img src="${escapeHtml(current.image_url)}" alt="" loading="lazy" decoding="async">
            ${images.length > 1 ? `
                <button class="slide-nav prev" type="button" onclick="moveMaterialSlide('${escapeHtml(videoId)}', -1, ${images.length})" title="上一张">‹</button>
                <button class="slide-nav next" type="button" onclick="moveMaterialSlide('${escapeHtml(videoId)}', 1, ${images.length})" title="下一张">›</button>
                <span class="slide-counter">${slideIndex + 1}/${images.length}</span>
            ` : ''}
        `;
    }

    window.setProductSearch = function(value) {
        productSearch = value;
        renderProducts();
    };

    window.setCountrySearch = function(value) {
        countrySearch = value;
        renderCountries();
    };

    window.goProducts = function() {
        currentPage = 'products';
        renderApp();
    };

    window.goProduct = function(productId) {
        selectedProductId = productId;
        countrySearch = '';
        ensureSelection();
        currentPage = 'product';
        renderApp();
    };

    window.selectProduct = function(productId) {
        selectedProductId = productId;
        countrySearch = '';
        const input = document.getElementById('countrySearch');
        if (input) input.value = '';
        ensureSelection();
        currentPage = 'product';
        renderApp();
    };

    window.selectCountry = function(countryId) {
        selectedCountryId = countryId;
        currentPage = 'country';
        renderApp();
    };

    window.toggleTopic = function(groupName) {
        const country = getSelectedCountry();
        if (!country) return;

        setTopicExpanded(country.id, groupName, !isTopicExpanded(country.id, groupName));
        renderFormats();
    };

    window.toggleFormat = function(conceptId) {
        if (expandedFormats[conceptId]) {
            delete expandedFormats[conceptId];
        } else {
            expandedFormats[conceptId] = true;
        }
        renderFormats();
    };

    window.addNewProduct = function() {
        const product = {
            id: generateId(),
            name: '新产品',
            logo: '',
            folder: '甲方',
            countries: []
        };
        dbData.push(product);
        selectedProductId = product.id;
        selectedCountryId = null;
        currentPage = 'product';
        saveData();
    };

    window.addCountryToSelected = function() {
        let product = getSelectedProduct();
        if (!product) {
            window.addNewProduct();
            product = getSelectedProduct();
        }

        if (!Array.isArray(product.countries)) product.countries = [];
        const country = {
            id: generateId(),
            name: 'New Country',
            concepts: []
        };
        product.countries.push(country);
        selectedCountryId = country.id;
        saveData();
    };

    function ensureCountryForFormat() {
        let product = getSelectedProduct();
        if (!product) {
            window.addNewProduct();
            product = getSelectedProduct();
        }

        let country = getSelectedCountry();
        if (!country) {
            if (!Array.isArray(product.countries)) product.countries = [];
            country = {
                id: generateId(),
                name: 'New Country',
                concepts: []
            };
            product.countries.push(country);
            selectedCountryId = country.id;
        }

        if (!Array.isArray(country.concepts)) country.concepts = [];
        return country;
    }

    window.addFormatGroupToSelected = function() {
        const country = ensureCountryForFormat();
        const nextIndex = getFormatGroups(country.concepts).length + 1;
        const group = `Topic ${nextIndex}`;

        if (!Array.isArray(country.concepts)) country.concepts = [];
        country.concepts.push({
            id: generateId(),
            group,
            name: 'Format',
            count: 0
        });
        setTopicExpanded(country.id, group, true);
        saveData();
    };

    window.addFormatToGroup = function(group) {
        const country = ensureCountryForFormat();
        const groupName = group || '默认 Topic';
        country.concepts.push({
            id: generateId(),
            group: groupName,
            name: 'Format',
            count: 0
        });
        setTopicExpanded(country.id, groupName, true);
        saveData();
    };

    window.addFormatToSelected = function() {
        const country = ensureCountryForFormat();
        const group = getFormatGroups(country.concepts)[0]?.name || '默认 Topic';
        window.addFormatToGroup(group);
    };

    window.updateProductName = function(productId, value) {
        const product = dbData.find(item => item.id === productId);
        if (!product) return;

        const nextValue = value.trim() || product.name || '未命名产品';
        if (product.name === nextValue) return;

        product.name = nextValue;
        saveData();
    };

    window.updateProductFolder = function(productId, folder) {
        const product = dbData.find(item => item.id === productId);
        if (!product) return;
        if (!['甲方', '乙方'].includes(folder)) return;
        if (product.folder === folder) return;

        product.folder = folder;
        saveData();
    };

    window.updateProductReelFarmCode = function(productId, value) {
        const product = dbData.find(item => item.id === productId);
        if (!product) return;

        const nextValue = (value.trim() || codeFromName(product.name)).toUpperCase();
        if (product.reelFarmCode === nextValue) return;

        product.reelFarmCode = nextValue;
        reelFarmResults = {};
        saveData();
    };

    window.updateCountryName = function(countryId, value) {
        const product = getSelectedProduct();
        const country = product?.countries?.find(item => item.id === countryId);
        if (!country) return;

        const nextValue = value.trim() || country.name || 'New Country';
        if (country.name === nextValue) return;

        country.name = nextValue;
        saveData();
    };

    window.updateCountryReelFarmCode = function(countryId, value) {
        const product = getSelectedProduct();
        const country = product?.countries?.find(item => item.id === countryId);
        if (!country) return;

        const nextValue = (value.trim() || countryCodes[country.name] || codeFromName(country.name)).toUpperCase();
        if (country.reelFarmCode === nextValue) return;

        country.reelFarmCode = nextValue;
        reelFarmResults = {};
        saveData();
    };

    window.setReelFarmWindow = function(days) {
        const nextDays = Number(days);
        if (![7, 14, 30].includes(nextDays)) return;
        if (reelFarmWindowDays === nextDays) return;

        reelFarmWindowDays = nextDays;
        localStorage.setItem(REELFARM_WINDOW_KEY, String(nextDays));
        materialPageIndexes = {};
        renderFormats();
    };

    window.updateFormatName = function(conceptId, value) {
        const country = getSelectedCountry();
        const concept = country?.concepts?.find(item => item.id === conceptId);
        if (!concept) return;

        const nextValue = value.trim() || concept.name || 'Format';
        if (concept.name === nextValue) return;

        concept.name = nextValue;
        saveData();
    };

    window.updateFormatGroup = function(oldGroup, value) {
        const country = getSelectedCountry();
        if (!country) return;

        const nextValue = value.trim() || oldGroup || '默认 Topic';
        if (oldGroup === nextValue) return;

        (country.concepts || []).forEach(concept => {
            if ((concept.group || '默认 Topic') === oldGroup) {
                concept.group = nextValue;
            }
        });
        if (isTopicExpanded(country.id, oldGroup)) {
            setTopicExpanded(country.id, oldGroup, false);
            setTopicExpanded(country.id, nextValue, true);
        }
        saveData();
    };

    window.updateFormatCount = function(conceptId, value) {
        const country = getSelectedCountry();
        const concept = country?.concepts?.find(item => item.id === conceptId);
        if (!concept) return;

        const nextValue = Math.max(0, parseInt(value, 10));
        const normalized = Number.isNaN(nextValue) ? concept.count : nextValue;
        if (concept.count === normalized) return;

        concept.count = normalized;
        saveData();
    };

    window.deleteProduct = function(productId) {
        if (!confirm('确定要删除这个产品以及它下面所有国家/地区和创意吗？')) return;

        dbData = dbData.filter(product => product.id !== productId);
        ensureSelection();
        saveData();
    };

    window.deleteCountry = function(countryId) {
        const product = getSelectedProduct();
        if (!product) return;
        if (!confirm('确定要删除这个国家/地区以及它下面所有创意吗？')) return;

        product.countries = (product.countries || []).filter(country => country.id !== countryId);
        ensureSelection();
        saveData();
    };

    window.deleteFormat = function(conceptId) {
        const country = getSelectedCountry();
        if (!country) return;
        if (!confirm('确定要删除这个 Format 吗？')) return;

        country.concepts = (country.concepts || []).filter(concept => concept.id !== conceptId);
        saveData();
    };

    window.deleteFormatGroup = function(group) {
        const country = getSelectedCountry();
        if (!country) return;
        if (!confirm('确定要删除这个 Topic 以及里面所有 Format 吗？')) return;

        country.concepts = (country.concepts || []).filter(concept => (concept.group || '默认 Topic') !== group);
        saveData();
    };

    window.saveReelFarmApiKey = async function() {
        const input = document.getElementById('reelFarmApiKeyInput');
        const apiKey = input?.value?.trim() || '';
        if (!apiKey) {
            setStatus('请先粘贴 ReelFarm API Key', 'error');
            return;
        }

        try {
            setStatus('正在连接 ReelFarm...');
            const response = await fetch(API_REELFARM_CONFIG_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ api_key: apiKey })
            });
            if (!response.ok) throw new Error('Failed to save ReelFarm API key.');
            const payload = await response.json();
            reelFarmConfigured = Boolean(payload.configured);
            setStatus('ReelFarm 已连接');
            renderFormats();
        } catch (error) {
            console.error(error);
            setStatus('ReelFarm 连接失败', 'error');
        }
    };

    async function fetchAndStoreReelFarmPrefix(prefix) {
        const response = await fetch(`${API_REELFARM_MATCHES_URL}?prefix=${encodeURIComponent(prefix)}`, { cache: 'no-store' });
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.error || 'Failed to sync ReelFarm data.');

        reelFarmResults[prefix] = payload;
        const concept = findConceptByPrefix(prefix);
        if (concept) {
            concept.reelFarmResult = payload;
            concept.reelFarmSyncedAt = new Date().toLocaleString();
        }

        return payload;
    }

    window.syncReelFarmPrefix = async function(prefix) {
        if (window.location.protocol === 'file:') {
            setStatus('当前是 file:// 页面，不能调 ReelFarm API', 'error');
            renderFormats();
            return;
        }

        if (!reelFarmConfigured) {
            setStatus('请先连接 ReelFarm API Key', 'error');
            renderFormats();
            return;
        }

        reelFarmLoadingPrefix = prefix;
        renderFormats();

        try {
            const payload = await fetchAndStoreReelFarmPrefix(prefix);
            await persistData(false);
            setStatus(`ReelFarm 已同步：${payload.count} 个 automation`);
        } catch (error) {
            console.error(error);
            reelFarmResults[prefix] = { error: error.message || '同步失败' };
            setStatus('ReelFarm 同步失败', 'error');
        } finally {
            reelFarmLoadingPrefix = '';
            renderFormats();
        }
    };

    window.syncCurrentCountryReelFarm = async function() {
        if (window.location.protocol === 'file:') {
            setStatus('当前是 file:// 页面，不能调 ReelFarm API', 'error');
            renderFormats();
            return;
        }

        if (!reelFarmConfigured) {
            setStatus('请先连接 ReelFarm API Key', 'error');
            renderFormats();
            return;
        }

        const product = getSelectedProduct();
        const country = getSelectedCountry();
        if (!product || !country) return;

        const prefixes = [...new Set((country.concepts || []).map(concept => buildAutomationPrefix(product, country, concept)))];
        if (prefixes.length === 0) {
            setStatus('这个国家/地区还没有 Format', 'error');
            return;
        }

        reelFarmLoadingPrefix = `country:${country.id}`;
        renderFormats();

        let successCount = 0;
        let errorCount = 0;
        try {
            for (const prefix of prefixes) {
                try {
                    await fetchAndStoreReelFarmPrefix(prefix);
                    successCount += 1;
                } catch (error) {
                    console.error(error);
                    reelFarmResults[prefix] = { error: error.message || '同步失败' };
                    errorCount += 1;
                }
            }
            await persistData(false);
            setStatus(`当前区同步完成：${successCount} 个成功${errorCount ? `，${errorCount} 个失败` : ''}`);
        } finally {
            reelFarmLoadingPrefix = '';
            renderFormats();
        }
    };

    window.moveMaterialSlide = function(videoId, direction, total) {
        const current = getSlideIndex(videoId);
        const next = (current + direction + total) % total;
        materialSlideIndexes[videoId] = next;
        renderFormats();
    };

    window.toggleReelFarmCard = function(cardKey) {
        if (expandedReelFarmCards[cardKey]) {
            delete expandedReelFarmCards[cardKey];
        } else {
            expandedReelFarmCards[cardKey] = true;
        }
        renderFormats();
    };

    window.moveMaterialPage = function(cardKey, direction) {
        const current = getMaterialPage(cardKey);
        materialPageIndexes[cardKey] = Math.max(0, current + direction);
        renderFormats();
    };

    window.refreshAllReelFarm = async function() {
        const product = getSelectedProduct();
        const country = getSelectedCountry();
        if (!product || !country) return;

        await window.syncCurrentCountryReelFarm();
    };

    window.handleImageUpload = function(inputElement, productId) {
        const file = inputElement.files[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = function(event) {
            const product = dbData.find(item => item.id === productId);
            if (!product) return;

            product.logo = event.target.result;
            saveData();
        };
        reader.readAsDataURL(file);
    };

    function renderDatabaseSnapshot(snapshot) {
        latestDatabaseSnapshot = snapshot;

        const subtitle = document.getElementById('databaseSubtitle');
        const stats = document.getElementById('databaseStats');
        const json = document.getElementById('databaseJson');
        const updatedAt = snapshot.updated_at ? new Date(snapshot.updated_at).toLocaleString() : '暂无';

        subtitle.textContent = `${snapshot.database_path} · ${snapshot.table} · 更新时间：${updatedAt}`;
        stats.innerHTML = [
            ['产品', snapshot.stats.products],
            ['国家/地区', snapshot.stats.countries],
            ['创意', snapshot.stats.concepts],
            ['总数量', snapshot.stats.total_count]
        ].map(([label, value]) => `
            <div class="database-stat">
                <div class="database-stat-label">${label}</div>
                <div class="database-stat-value">${value}</div>
            </div>
        `).join('');
        json.textContent = JSON.stringify(snapshot.data, null, 2);
    }

    window.openDatabasePanel = async function() {
        const modal = document.getElementById('databaseModal');
        const subtitle = document.getElementById('databaseSubtitle');
        const stats = document.getElementById('databaseStats');
        const json = document.getElementById('databaseJson');

        modal.classList.add('is-open');
        subtitle.textContent = '正在读取数据库...';
        stats.innerHTML = '';
        json.textContent = '正在读取...';

        try {
            const response = await fetch(API_DATABASE_URL, { cache: 'no-store' });
            if (!response.ok) throw new Error('Failed to open database.');

            renderDatabaseSnapshot(await response.json());
            setStatus('数据库视图已打开');
        } catch (error) {
            console.error(error);
            subtitle.textContent = '无法读取数据库，请确认后端服务正在运行。';
            json.textContent = '数据库连接失败。';
            setStatus('数据库打开失败', 'error');
        }
    };

    window.closeDatabasePanel = function(event) {
        if (event && event.target !== event.currentTarget) return;
        document.getElementById('databaseModal').classList.remove('is-open');
    };

    window.copyDatabaseJson = async function() {
        if (!latestDatabaseSnapshot) return;

        try {
            await navigator.clipboard.writeText(JSON.stringify(latestDatabaseSnapshot.data, null, 2));
            setStatus('数据库 JSON 已复制');
        } catch (error) {
            console.error(error);
            setStatus('复制失败，浏览器未授权剪贴板', 'error');
        }
    };

    window.resetDemoData = async function() {
        if (!confirm('确定要恢复示例数据吗？数据库中保存的数据会被覆盖。')) return;

        try {
            const response = await fetch(API_RESET_URL, { method: 'POST' });
            if (!response.ok) throw new Error('Failed to reset database data.');

            const payload = await response.json();
            dbData = Array.isArray(payload.data) ? payload.data : createDefaultData();
            selectedProductId = null;
            selectedCountryId = null;
            ensureSelection();
            renderApp();
            setStatus('示例数据已写入 SQLite');
        } catch (error) {
            console.error(error);
            dbData = createDefaultData();
            selectedProductId = null;
            selectedCountryId = null;
            ensureSelection();
            renderApp();
            saveData();
        }
    };

    window.onload = async function() {
        await loadData();
        await loadReelFarmConfig();
        renderApp();
    };
