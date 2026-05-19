    const API_DATA_URL = '/api/data';
    const API_RESET_URL = '/api/reset';
    const API_DATABASE_URL = '/api/database';
    const API_REELFARM_CONFIG_URL = '/api/reelfarm/config';
    const API_REELFARM_MATCHES_URL = '/api/reelfarm/matches';
    const API_REELFARM_SYNC_PREFIX_URL = '/api/reelfarm/sync-prefix';
    const API_REELFARM_SYNC_COUNTRY_URL = '/api/reelfarm/sync-country';
    const API_AUTH_LOGIN_URL = '/api/auth/login';
    const API_AUTH_LOGOUT_URL = '/api/auth/logout';
    const API_ROASTER_URL = '/api/roaster';
    const API_KEYS_URL = '/api/api-keys';
    const API_KEYS_REVOKE_URL = '/api/api-keys/revoke';
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
        'Germany': 'GE',
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

    const roasterRoles = [
        { key: 'leader', label: 'Leader', group: '负责人' },
        { key: 'pm', label: 'PM', group: '负责人' },
        { key: 'backend', label: '后台', group: '负责人' },
        { key: 'slideshow', label: 'Slideshow', group: '执行人' },
        { key: 'shortVideo', label: 'Short video', group: '执行人' },
        { key: 'reddit', label: 'Reddit', group: '执行人' },
        { key: 'seo', label: 'SEO', group: '执行人' },
        { key: 'twitter', label: 'Twitter', group: '执行人' },
        { key: 'influencer', label: 'Influencer', group: '执行人' }
    ];

    let dbData = [];
    let selectedProductId = null;
    let selectedCountryId = null;
    let currentPage = 'products';
    let currentWorkspaceTool = 'slideshow';
    let productSearch = '';
    let countrySearch = '';
    let latestDatabaseSnapshot = null;
    let roasterState = { people: [], assignments: {} };
    let externalApiKeys = [];
    let dirtyCountryCodeIds = new Set();
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

    function personInitials(value) {
        const name = String(value || '').trim();
        if (!name) return '?';
        if (/^[a-zA-Z]/.test(name)) return name.slice(0, 1).toUpperCase();
        return name.slice(0, 1);
    }

    function personColorClass(personId) {
        let hash = 0;
        for (let i = 0; i < String(personId).length; i += 1) {
            hash = String(personId).charCodeAt(i) + ((hash << 5) - hash);
        }
        return `tone-${Math.abs(hash) % 6}`;
    }

    function createPersonId(name) {
        const base = String(name || '')
            .normalize('NFKD')
            .replace(/[\u0300-\u036f]/g, '')
            .replace(/[^a-zA-Z0-9\u4e00-\u9fa5]+/g, '-')
            .replace(/^-+|-+$/g, '')
            .toLowerCase() || 'person';
        let candidate = base;
        let index = 2;
        const existing = new Set((roasterState.people || []).map(person => person.id));
        while (existing.has(candidate)) {
            candidate = `${base}-${index}`;
            index += 1;
        }
        return candidate;
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

    function buildCountryAutomationPrefix(product, country) {
        const countryCode = getCountryReelFarmCode(country);
        const productCode = getProductReelFarmCode(product);
        return `${countryCode}-${productCode}`;
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

    function formatUtcReadable(value) {
        const date = new Date(value || '');
        if (Number.isNaN(date.getTime())) return value || '';

        const year = date.getUTCFullYear();
        const month = String(date.getUTCMonth() + 1).padStart(2, '0');
        const day = String(date.getUTCDate()).padStart(2, '0');
        const hours = String(date.getUTCHours()).padStart(2, '0');
        const minutes = String(date.getUTCMinutes()).padStart(2, '0');
        return `${year}/${month}/${day} ${hours}:${minutes} UTC`;
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
        const value = post?.published_at_meta || post?.published_at || '';
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

    function getCreatorKey(card) {
        const account = card?.account || {};
        const automation = card?.automation || {};
        return String(
            account.tiktok_account_id
            || automation.tiktok_account_id
            || account.account_username
            || account.username
            || account.account_name
            || automation.automation_id
            || automation.title
            || ''
        ).trim();
    }

    function getReelFarmCreatorCount(result) {
        const creatorKeys = new Set();
        (result?.cards || []).forEach(card => {
            const key = getCreatorKey(card);
            if (key) creatorKeys.add(key);
        });
        return creatorKeys.size;
    }

    function getFormatAutoCount(product, country, concept) {
        const prefix = product && country && concept ? buildAutomationPrefix(product, country, concept) : '';
        const result = prefix ? getCachedReelFarmResult(concept, prefix) : null;
        if (result?.cards) return getReelFarmCreatorCount(result);

        return Number(concept?.count) || 0;
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

    function getCachedCountryReelFarmResult(country, prefix) {
        const liveResult = reelFarmResults[prefix];
        if (liveResult) return liveResult;

        if (country?.reelFarmResult?.prefix === prefix) {
            return country.reelFarmResult;
        }

        return null;
    }

    function storeReelFarmResultOnConcept(concept, payload) {
        if (!concept) return;

        concept.reelFarmResult = payload;
        concept.reelFarmSyncedAt = new Date().toLocaleString();
        concept.count = getReelFarmCreatorCount(payload);
    }

    function getReelFarmMaterialCount(result) {
        return (result?.cards || []).reduce((sum, card) => sum + (card?.videos || []).length, 0);
    }

    function storeReelFarmResultOnCountry(country, payload) {
        if (!country) return;

        country.reelFarmResult = payload;
        country.reelFarmSyncedAt = new Date().toLocaleString();
        country.creatorCount = getReelFarmCreatorCount(payload);
        country.materialCount = getReelFarmMaterialCount(payload);
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

    function findReelFarmContextByPrefix(prefix) {
        for (const product of dbData) {
            for (const country of product.countries || []) {
                for (const concept of country.concepts || []) {
                    if (buildAutomationPrefix(product, country, concept) === prefix) {
                        return { product, country, concept };
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

    function setAuthError(message = '') {
        const error = document.getElementById('authError');
        if (!error) return;

        error.textContent = message;
        error.classList.toggle('is-visible', Boolean(message));
    }

    function setAuthLoading(isLoading) {
        const button = document.getElementById('adminLoginButton');
        if (!button) return;

        button.disabled = isLoading;
        button.textContent = isLoading ? '正在进入...' : '进入中台';
    }

    function showAuthGate() {
        document.querySelector('.app')?.classList.add('is-locked');
        document.getElementById('authOverlay')?.classList.add('is-visible');
        setAuthError('');
        window.requestAnimationFrame(() => document.getElementById('adminUsername')?.focus());
    }

    function hideAuthGate() {
        document.getElementById('authOverlay')?.classList.remove('is-visible');
        document.querySelector('.app')?.classList.remove('is-locked');
    }

    async function startAuthenticatedApp() {
        hideAuthGate();
        await loadData();
        await loadReelFarmConfig();
        await loadRoasterState();
        renderApp();
    }

    async function resetAuthOnRefresh() {
        if (window.location.protocol === 'file:') return;

        try {
            await fetch(API_AUTH_LOGOUT_URL, { method: 'POST', cache: 'no-store' });
        } catch (error) {
            console.error(error);
        }
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

    function defaultRoasterState() {
        return {
            people: [
                { id: 'han', name: 'han' },
                { id: 'li-zihan', name: '李梓瞻' },
                { id: 'ding-lifeng', name: '丁立峰' },
                { id: 'wang-hengjia', name: '王恒加' },
                { id: 'jj', name: 'JJ' },
                { id: 'doris', name: 'Doris' },
                { id: 'mina', name: 'Mina' }
            ],
            assignments: {}
        };
    }

    function normalizeRoasterState(state) {
        const fallback = defaultRoasterState();
        return {
            people: Array.isArray(state?.people) && state.people.length ? state.people : fallback.people,
            assignments: state?.assignments && typeof state.assignments === 'object' ? state.assignments : {}
        };
    }

    async function loadRoasterState() {
        if (window.location.protocol === 'file:') {
            roasterState = defaultRoasterState();
            return;
        }

        try {
            const response = await fetch(API_ROASTER_URL, { cache: 'no-store' });
            if (!response.ok) throw new Error('Failed to load Roaster data.');
            roasterState = normalizeRoasterState(await response.json());
        } catch (error) {
            console.error(error);
            roasterState = defaultRoasterState();
            setStatus('Roaster 数据加载失败', 'error');
        }
    }

    async function persistRoasterState(shouldRender = true) {
        roasterState = normalizeRoasterState(roasterState);
        if (shouldRender) renderRoaster();

        if (window.location.protocol === 'file:') {
            setStatus('文件模式无法保存 Roaster', 'error');
            return;
        }

        try {
            const response = await fetch(API_ROASTER_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ state: roasterState })
            });
            const payload = await response.json().catch(() => ({}));
            if (!response.ok) throw new Error(payload.error || 'Failed to save Roaster data.');
            roasterState = normalizeRoasterState(payload.state);
            setStatus('Roaster 已保存');
        } catch (error) {
            console.error(error);
            setStatus('Roaster 保存失败', 'error');
        }
    }

    function roasterProductRows() {
        return [...dbData].sort((a, b) => {
            const folderOrder = normalizeProductFolder(a).localeCompare(normalizeProductFolder(b), 'zh-Hans');
            if (folderOrder) return folderOrder;
            return String(a.name || '').localeCompare(String(b.name || ''), 'zh-Hans');
        });
    }

    function getRoasterAssignment(productId, roleKey) {
        if (!roasterState.assignments[productId]) roasterState.assignments[productId] = {};
        if (!Array.isArray(roasterState.assignments[productId][roleKey])) {
            roasterState.assignments[productId][roleKey] = [];
        }

        const validPeople = new Set((roasterState.people || []).map(person => person.id));
        roasterState.assignments[productId][roleKey] = roasterState.assignments[productId][roleKey]
            .filter(personId => validPeople.has(personId));
        return roasterState.assignments[productId][roleKey];
    }

    function getRoasterPerson(personId) {
        return (roasterState.people || []).find(person => person.id === personId) || null;
    }

    function renderPersonChip(person, options = {}) {
        const removable = Boolean(options.removable);
        const assigned = Boolean(options.assigned);
        const removeAction = options.removeAction || '';
        const deleteAction = options.deleteAction || '';
        const className = assigned ? 'person-chip assignment-chip' : 'person-chip';
        const closeButton = removable
            ? `<button class="person-chip-remove" type="button" onclick="${removeAction}" title="移出">×</button>`
            : '';
        const deleteButton = deleteAction
            ? `<button class="person-chip-delete" type="button" onclick="${deleteAction}" title="删除人员">删除</button>`
            : '';

        return `
            <span class="${className} ${personColorClass(person.id)}" draggable="true" ondragstart="handlePersonDragStart(event, '${escapeHtml(person.id)}')">
                <span class="person-avatar">${escapeHtml(personInitials(person.name))}</span>
                <span class="person-name">${escapeHtml(person.name)}</span>
                ${closeButton}
                ${deleteButton}
            </span>`;
    }

    function renderRoaster() {
        const board = document.getElementById('roasterBoard');
        if (!board) return;

        roasterState = normalizeRoasterState(roasterState);
        const products = roasterProductRows();
        const people = roasterState.people || [];
        const rows = products.map(product => {
            const productLogo = product.logo
                ? `<img src="${escapeHtml(product.logo)}" alt="${escapeHtml(product.name || '产品')} Logo">`
                : escapeHtml(String(product.name || 'P').slice(0, 1).toUpperCase());
            const roleCells = roasterRoles.map(role => {
                const assigned = getRoasterAssignment(product.id, role.key)
                    .map(personId => getRoasterPerson(personId))
                    .filter(Boolean);
                const chips = assigned.map(person => renderPersonChip(person, {
                    assigned: true,
                    removable: true,
                    removeAction: `removeRoasterAssignment('${escapeHtml(product.id)}', '${escapeHtml(role.key)}', '${escapeHtml(person.id)}')`
                })).join('');

                return `
                    <td>
                        <div class="roaster-dropzone ${assigned.length ? '' : 'is-empty'}"
                             ondragover="handleRoasterDragOver(event)"
                             ondrop="handleRoasterDrop(event, '${escapeHtml(product.id)}', '${escapeHtml(role.key)}')">
                            ${chips || '<span>拖入人员</span>'}
                        </div>
                    </td>`;
            }).join('');

            return `
                <tr>
                    <td class="roaster-attr">${escapeHtml(normalizeProductFolder(product))}</td>
                    <td class="roaster-product">
                        <div class="roaster-product-cell">
                            <span class="roaster-product-logo">${productLogo}</span>
                            <span class="roaster-app-name">${escapeHtml(product.name || '未命名产品')}</span>
                        </div>
                    </td>
                    ${roleCells}
                </tr>`;
        }).join('');

        board.innerHTML = `
            <div class="roaster-toolbar">
                <div>
                    <h2>Roaster</h2>
                    <p>人员可以从这里拖到下面任意职责格子，同一个格子可以放多个人。</p>
                </div>
                <form class="roaster-person-form" onsubmit="addRoasterPerson(event)">
                    <input id="roasterPersonName" class="text-input" type="text" placeholder="添加人员">
                    <button class="btn primary" type="submit">添加</button>
                </form>
            </div>
            <div class="roaster-people">
                ${people.map(person => renderPersonChip(person, {
                    deleteAction: `deleteRoasterPerson('${escapeHtml(person.id)}')`
                })).join('')}
            </div>
            <div class="roaster-table-wrap">
                <table class="roaster-table">
                    <thead>
                        <tr class="roaster-group-row">
                            <th></th>
                            <th></th>
                            <th colspan="3">负责人</th>
                            <th colspan="6">执行人</th>
                        </tr>
                        <tr>
                            <th>属性</th>
                            <th>产品</th>
                            ${roasterRoles.map(role => `<th>${escapeHtml(role.label)}</th>`).join('')}
                        </tr>
                    </thead>
                    <tbody>
                        ${rows || '<tr><td colspan="11" class="roaster-empty-cell">还没有产品，请先在 Slide Show 里新建 App。</td></tr>'}
                    </tbody>
                </table>
            </div>`;
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
        renderWorkspaceTool();
        if (currentWorkspaceTool === 'roaster') {
            ensureSelection();
            renderRoaster();
            return;
        }

        if (currentWorkspaceTool !== 'slideshow') return;

        ensureSelection();
        renderMetrics();
        renderBreadcrumbs();
        renderPages();
    }

    function renderWorkspaceTool() {
        document.querySelectorAll('.tool-page').forEach(page => page.classList.remove('active'));
        document.getElementById(`${currentWorkspaceTool}Tool`)?.classList.add('active');

        document.querySelectorAll('[data-tool-target]').forEach(button => {
            button.classList.toggle('active', button.dataset.toolTarget === currentWorkspaceTool);
        });
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
            const product = getSelectedProduct();
            const prefix = product ? buildCountryAutomationPrefix(product, country) : '';
            const result = getCachedCountryReelFarmResult(country, prefix);
            const creatorCount = result?.cards ? getReelFarmCreatorCount(result) : (Number(country.creatorCount) || 0);
            const materialCount = result?.cards ? getReelFarmMaterialCount(result) : (Number(country.materialCount) || 0);
            const flag = countryFlags[country.name] || '🌐';

            return `
                <button class="list-item ${country.id === selectedCountryId ? 'active' : ''}" type="button" onclick="selectCountry('${country.id}')">
                    <div class="country-row">
                        <span class="flag-chip">${flag}</span>
                        <span class="item-main">
                            <span class="item-name">${escapeHtml(country.name || 'New Country')}</span>
                            <span class="item-meta">${creatorCount} 个账号 · ${materialCount} 个素材</span>
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
            context.innerHTML = '<div class="country-sidebar-head"><h2 class="country-sidebar-title">素材库</h2><div class="context-meta">先选择一个产品。</div></div>';
            list.innerHTML = '<div class="empty-state"><div class="empty-title">暂无上下文</div></div>';
            return;
        }

        if (!country) {
            context.innerHTML = `
                <div class="country-sidebar-head">
                    <h2 class="country-sidebar-title">${escapeHtml(product.name)} 的素材库</h2>
                    <div class="context-meta">先为这个产品添加国家/地区。</div>
                </div>
                <button class="btn primary" type="button" onclick="addCountryToSelected()">添加国家/地区</button>`;
            list.innerHTML = '<div class="empty-state"><div class="empty-title">还没有国家/地区</div></div>';
            return;
        }

        const prefix = buildCountryAutomationPrefix(product, country);
        const result = getCachedCountryReelFarmResult(country, prefix);
        const creatorCount = result?.cards ? getReelFarmCreatorCount(result) : (Number(country.creatorCount) || 0);
        const materialCount = result?.cards ? getReelFarmMaterialCount(result) : (Number(country.materialCount) || 0);
        const countrySyncKey = `country:${country.id}`;
        const isCountrySyncing = reelFarmLoadingPrefix === countrySyncKey;
        const windowOptions = [7, 14, 30];

        context.innerHTML = `
            <div class="country-sidebar-head">
                <div class="country-title-row">
                    <h2 class="country-sidebar-title">${escapeHtml(country.name)} 素材库</h2>
                    <button class="btn primary" type="button" onclick="syncCurrentCountryReelFarm()" ${isCountrySyncing ? 'disabled' : ''}>${isCountrySyncing ? '同步中...' : '同步当前区'}</button>
                </div>
                <div class="context-meta">${escapeHtml(product.name)} · ${creatorCount} 个账号 · ${materialCount} 个素材</div>
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
                        oninput="draftCountryReelFarmCode('${country.id}', this.value)"
                        onchange="updateCountryReelFarmCode('${country.id}', this.value)"
                        onblur="updateCountryReelFarmCode('${country.id}', this.value)">
                </label>
            </div>
            <div class="top-actions">
                <button class="btn danger" type="button" onclick="deleteCountry('${country.id}')">删除国家/地区</button>
            </div>`;

        list.innerHTML = renderCountryReelFarm(product, country);
    }

    function renderCountryReelFarm(product, country) {
        const prefix = buildCountryAutomationPrefix(product, country);
        const result = getCachedCountryReelFarmResult(country, prefix);
        const isLoading = reelFarmLoadingPrefix === `country:${country.id}`;
        let body = '';

        if (isLoading) {
            body = '<div class="empty-state"><div class="empty-title">正在从 ReelFarm 拉取这个国家/地区的全部素材...</div></div>';
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
                    : `<div class="empty-state compact"><div class="empty-title">最近 ${Number(reelFarmWindowDays) || 30} 天没有素材</div><div>这个国家/地区有同步记录，但没有匹配当前观察窗口的 posted 素材。</div></div>`}`;
        } else if (result) {
            body = '<div class="empty-state"><div class="empty-title">没有找到匹配 automation</div><div>确认 ReelFarm 里 automation name 是否以这个国家/产品 prefix 开头。</div></div>';
        } else {
            body = '<div class="item-meta">点击左侧「同步当前区」后，会显示这个国家/地区下每个 TikTok 账号和所有素材数据。后续可基于这些数据让 AI 再做创意方向分类。</div>';
        }

        return `
            <section class="reelfarm-format">
                <div class="reelfarm-format-head">
                    <div>
                        <span class="automation-prefix">${escapeHtml(prefix)}</span>
                        <div class="item-meta">国家/地区素材池 · 暂不按 Topic / Format 分类</div>
                        ${country.reelFarmSyncedAt && country.reelFarmResult?.prefix === prefix
                            ? `<div class="item-meta">上次同步：${escapeHtml(country.reelFarmSyncedAt)}</div>`
                            : ''}
                    </div>
                </div>
                ${body}
            </section>`;
    }

    function renderFormatGroup(group) {
        const color = getTagColor(group.name);
        const product = getSelectedProduct();
        const country = getSelectedCountry();
        const total = group.concepts.reduce((sum, concept) => sum + getFormatAutoCount(product, country, concept), 0);
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
        const autoCount = getFormatAutoCount(product, country, concept);

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
                    <div class="number-input number-display" title="同步 ReelFarm 后自动计算 Creator / TikTok 账号数量">${autoCount}</div>
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
        const title = video.hook || post?.title || video.video_id || video.id || 'Slideshow';
        const images = Array.isArray(video.slideshow_images) ? video.slideshow_images : [];
        const imageCount = video.slide_count || images.length;
        const publishedReadable = post?.published_at_readable || formatUtcReadable(post?.published_at_meta || post?.published_at || '');
        const meta = imageCount ? `${imageCount} slides` : '';
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
                    <span>${publishedReadable ? `Published ${escapeHtml(publishedReadable)}` : '暂无 TikTok 发布数据'}</span>
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
        currentWorkspaceTool = 'slideshow';
        currentPage = 'products';
        renderApp();
    };

    window.goProduct = function(productId) {
        currentWorkspaceTool = 'slideshow';
        selectedProductId = productId;
        countrySearch = '';
        ensureSelection();
        currentPage = 'product';
        renderApp();
    };

    window.selectProduct = function(productId) {
        currentWorkspaceTool = 'slideshow';
        selectedProductId = productId;
        countrySearch = '';
        const input = document.getElementById('countrySearch');
        if (input) input.value = '';
        ensureSelection();
        currentPage = 'product';
        renderApp();
    };

    window.selectCountry = function(countryId) {
        currentWorkspaceTool = 'slideshow';
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

    window.setWorkspaceTool = function(tool) {
        if (!['slideshow', 'roaster'].includes(tool)) return;
        currentWorkspaceTool = tool;
        renderApp();
    };

    window.handlePersonDragStart = function(event, personId) {
        event.dataTransfer.setData('text/plain', personId);
        event.dataTransfer.effectAllowed = 'copy';
    };

    window.handleRoasterDragOver = function(event) {
        event.preventDefault();
        event.dataTransfer.dropEffect = 'copy';
    };

    window.handleRoasterDrop = function(event, productId, roleKey) {
        event.preventDefault();
        const personId = event.dataTransfer.getData('text/plain');
        if (!personId || !getRoasterPerson(personId)) return;

        const assigned = getRoasterAssignment(productId, roleKey);
        if (!assigned.includes(personId)) assigned.push(personId);
        persistRoasterState(true);
    };

    window.removeRoasterAssignment = function(productId, roleKey, personId) {
        const assigned = getRoasterAssignment(productId, roleKey);
        roasterState.assignments[productId][roleKey] = assigned.filter(id => id !== personId);
        persistRoasterState(true);
    };

    window.addRoasterPerson = function(event) {
        event.preventDefault();
        const input = document.getElementById('roasterPersonName');
        const name = input?.value.trim();
        if (!name) return;

        roasterState.people.push({ id: createPersonId(name), name });
        if (input) input.value = '';
        persistRoasterState(true);
    };

    window.deleteRoasterPerson = function(personId) {
        const person = getRoasterPerson(personId);
        if (!person) return;
        if (!confirm(`确定删除 ${person.name} 吗？这个人会从所有职责格子里移除。`)) return;

        roasterState.people = roasterState.people.filter(item => item.id !== personId);
        Object.values(roasterState.assignments || {}).forEach(roleMap => {
            Object.keys(roleMap || {}).forEach(roleKey => {
                roleMap[roleKey] = (roleMap[roleKey] || []).filter(id => id !== personId);
            });
        });
        persistRoasterState(true);
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
        if (country.reelFarmCode === nextValue && !dirtyCountryCodeIds.has(countryId)) return;

        country.reelFarmCode = nextValue;
        dirtyCountryCodeIds.delete(countryId);
        reelFarmResults = {};
        saveData();
    };

    window.draftCountryReelFarmCode = function(countryId, value) {
        const product = getSelectedProduct();
        const country = product?.countries?.find(item => item.id === countryId);
        if (!country) return;

        country.reelFarmCode = value.trim().toUpperCase();
        dirtyCountryCodeIds.add(countryId);
        reelFarmResults = {};
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
        const context = findReelFarmContextByPrefix(prefix);
        const response = await fetch(API_REELFARM_SYNC_PREFIX_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                prefix,
                product_id: context?.product?.id || '',
                country_id: context?.country?.id || '',
                concept_id: context?.concept?.id || '',
                product_code: context?.product ? getProductReelFarmCode(context.product) : '',
                country_code: context?.country ? getCountryReelFarmCode(context.country) : ''
            })
        });
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.error || 'Failed to sync ReelFarm data.');

        const result = payload.result || payload;
        reelFarmResults[prefix] = result;
        const concept = context?.concept || findConceptByPrefix(prefix);
        storeReelFarmResultOnConcept(concept, result);

        return result;
    }

    async function fetchAndStoreReelFarmCountry(product, country) {
        const prefix = buildCountryAutomationPrefix(product, country);
        const response = await fetch(API_REELFARM_SYNC_COUNTRY_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                prefix,
                product_id: product?.id || '',
                country_id: country?.id || '',
                product_code: getProductReelFarmCode(product),
                country_code: getCountryReelFarmCode(country)
            })
        });
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.error || 'Failed to sync ReelFarm country data.');

        const result = payload.result || payload;
        reelFarmResults[prefix] = result;
        storeReelFarmResultOnCountry(country, result);
        return result;
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

        reelFarmLoadingPrefix = `country:${country.id}`;
        renderFormats();

        try {
            const result = await fetchAndStoreReelFarmCountry(product, country);
            setStatus(`当前区同步完成：${getReelFarmCreatorCount(result)} 个账号，${getReelFarmMaterialCount(result)} 个素材`);
        } catch (error) {
            console.error(error);
            const prefix = buildCountryAutomationPrefix(product, country);
            reelFarmResults[prefix] = { error: error.message || '同步失败' };
            setStatus('ReelFarm 同步失败', 'error');
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

    function renderExternalApiKeys() {
        const list = document.getElementById('apiKeyList');
        if (!list) return;

        if (!externalApiKeys.length) {
            list.innerHTML = '<div class="item-meta">还没有外部 API Key。</div>';
            return;
        }

        list.innerHTML = externalApiKeys.map(key => `
            <div class="api-key-row ${key.active ? '' : 'is-revoked'}">
                <div>
                    <div class="api-key-name">${escapeHtml(key.name || 'External AI')}</div>
                    <div class="api-key-meta">${escapeHtml(key.prefix || 'deca_...')} · ${(key.permissions || []).map(escapeHtml).join(', ') || '无权限'} · ${key.active ? 'active' : 'revoked'}</div>
                </div>
                ${key.active
                    ? `<button class="btn danger" type="button" onclick="revokeExternalApiKey('${escapeHtml(key.id)}')">停用</button>`
                    : '<span class="item-meta">已停用</span>'}
            </div>
        `).join('');
    }

    async function loadExternalApiKeys() {
        const list = document.getElementById('apiKeyList');
        if (list) list.innerHTML = '<div class="item-meta">正在读取 API Keys...</div>';

        try {
            const response = await fetch(API_KEYS_URL, { cache: 'no-store' });
            const payload = await response.json().catch(() => ({}));
            if (!response.ok) throw new Error(payload.error || 'Failed to load API keys.');
            externalApiKeys = payload.keys || [];
            renderExternalApiKeys();
        } catch (error) {
            console.error(error);
            if (list) list.innerHTML = '<div class="item-meta">API Keys 读取失败。</div>';
        }
    }

    function showGeneratedApiKey(key) {
        const container = document.getElementById('generatedApiKey');
        if (!container) return;

        container.innerHTML = `
            <div class="generated-api-key-label">新 Key 只显示一次，请现在复制给外部 AI。</div>
            <code>${escapeHtml(key)}</code>
            <button class="btn ghost" type="button" onclick="copyText('${escapeHtml(key)}')">复制</button>
        `;
    }

    window.openDatabasePanel = async function() {
        const modal = document.getElementById('databaseModal');
        const subtitle = document.getElementById('databaseSubtitle');
        const stats = document.getElementById('databaseStats');
        const json = document.getElementById('databaseJson');

        modal.classList.add('is-open');
        subtitle.textContent = '不会自动读取完整数据库，需要时可手动加载。';
        stats.innerHTML = '';
        json.textContent = '数据库 JSON 暂未加载。';
        latestDatabaseSnapshot = null;
        document.getElementById('generatedApiKey').innerHTML = '';
        loadExternalApiKeys();
        setStatus('数据库面板已打开');
    };

    window.refreshDatabasePanel = async function() {
        const subtitle = document.getElementById('databaseSubtitle');
        const stats = document.getElementById('databaseStats');
        const json = document.getElementById('databaseJson');

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

    window.copyText = async function(value) {
        try {
            await navigator.clipboard.writeText(value);
            setStatus('已复制');
        } catch (error) {
            console.error(error);
            setStatus('复制失败，浏览器未授权剪贴板', 'error');
        }
    };

    window.createExternalApiKey = async function(event) {
        event.preventDefault();
        const input = document.getElementById('apiKeyName');
        const name = input?.value.trim() || 'External AI';

        try {
            const response = await fetch(API_KEYS_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name })
            });
            const payload = await response.json().catch(() => ({}));
            if (!response.ok) throw new Error(payload.error || 'Failed to create API key.');
            if (input) input.value = '';
            showGeneratedApiKey(payload.key);
            await loadExternalApiKeys();
            setStatus('API Key 已生成');
        } catch (error) {
            console.error(error);
            setStatus('API Key 生成失败', 'error');
        }
    };

    window.revokeExternalApiKey = async function(id) {
        if (!confirm('确定要停用这个 API Key 吗？停用后外部 AI 将无法继续使用它。')) return;

        try {
            const response = await fetch(API_KEYS_REVOKE_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ id })
            });
            const payload = await response.json().catch(() => ({}));
            if (!response.ok) throw new Error(payload.error || 'Failed to revoke API key.');
            await loadExternalApiKeys();
            setStatus('API Key 已停用');
        } catch (error) {
            console.error(error);
            setStatus('API Key 停用失败', 'error');
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

    window.handleAdminLogin = async function(event) {
        event.preventDefault();
        if (window.location.protocol === 'file:') {
            setAuthError('请通过本地服务或线上地址打开，中台登录需要后端支持。');
            return;
        }

        const username = document.getElementById('adminUsername')?.value?.trim() || '';
        const password = document.getElementById('adminPassword')?.value || '';
        if (!username || !password) {
            setAuthError('请输入管理员账号和密码。');
            return;
        }

        setAuthLoading(true);
        setAuthError('');
        try {
            const response = await fetch(API_AUTH_LOGIN_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });
            const payload = await response.json().catch(() => ({}));
            if (!response.ok) throw new Error(payload.error || '登录失败');

            document.getElementById('adminPassword').value = '';
            await startAuthenticatedApp();
        } catch (error) {
            console.error(error);
            setAuthError(error.message || '登录失败，请重新输入。');
        } finally {
            setAuthLoading(false);
        }
    };

    window.onload = async function() {
        document.title = 'DECAGROWTH中台';
        showAuthGate();
        await resetAuthOnRefresh();
    };
