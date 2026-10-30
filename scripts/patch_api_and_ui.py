"""
Patches API and UI for:
1. Dataset transactions browser in /api/v1/datasets/transactions
2. Labeled transactions endpoint in /api/v1/feedback/labeled-feed
3. Removing Detection Rules tab from front end
4. Displaying every transaction data directly in Dataset Management
5. Displaying Dataset 2's labeled transactions (Scam vs Legit) in Feedback & Learning tab
"""

import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# -------------------------------------------------------------
# 1. Patch backend/app/api/v1/datasets.py
# -------------------------------------------------------------
datasets_file = os.path.join(BASE_DIR, "backend", "app", "api", "v1", "datasets.py")
with open(datasets_file, "r", encoding="utf-8") as f:
    ds_code = f.read().replace("\r\n", "\n")

TRANSACTIONS_ENDPOINT = """
@router.get("/transactions", summary="Browse and explore all transaction data across datasets")
def browse_dataset_transactions(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    dataset_source: Optional[str] = None,
    currency: Optional[str] = None,
    search: Optional[str] = None,
    conn=Depends(get_db)
):
    offset = (page - 1) * page_size
    query = \"\"\"
        SELECT id, event_id, source_account_id, destination_account_id,
               amount, currency, transaction_type, payment_channel, status,
               risk_score, risk_band, dataset_source, created_at
        FROM transactions
        WHERE 1=1
    \"\"\"
    params = []
    if dataset_source and dataset_source.upper() != "ALL":
        query += " AND dataset_source = ?"
        params.append(dataset_source.upper())
    if currency and currency.upper() != "ALL":
        query += " AND currency = ?"
        params.append(currency.upper())
    if search:
        query += " AND (id LIKE ? OR source_account_id LIKE ? OR destination_account_id LIKE ?)"
        term = f"%{search}%"
        params.extend([term, term, term])

    count_query = f"SELECT COUNT(*) FROM ({query})"
    cursor = conn.cursor()
    cursor.execute(count_query, params)
    total = cursor.fetchone()[0]

    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.extend([page_size, offset])
    cursor.execute(query, params)
    rows = [dict(r) for r in cursor.fetchall()]

    return {
        "items": rows,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if page_size > 0 else 1
    }
"""

if "/transactions" not in ds_code:
    target_pos = ds_code.find("@router.get(\"\", summary=\"List all registered datasets and their status\")")
    if target_pos != -1:
        insert_idx = ds_code.find("def list_datasets():", target_pos)
        end_def = ds_code.find("return DatasetRegistry.get_all_registered_datasets()", insert_idx)
        end_def = ds_code.find("\n", end_def)
        ds_code = ds_code[:end_def] + "\n" + TRANSACTIONS_ENDPOINT + ds_code[end_def:]
        with open(datasets_file, "w", encoding="utf-8") as f:
            f.write(ds_code)
        print("datasets.py patched with /transactions endpoint.")

# -------------------------------------------------------------
# 2. Patch backend/app/api/v1/feedback.py
# -------------------------------------------------------------
feedback_file = os.path.join(BASE_DIR, "backend", "app", "api", "v1", "feedback.py")
with open(feedback_file, "r", encoding="utf-8") as f:
    fb_code = f.read().replace("\r\n", "\n")

LABELED_ENDPOINT = """
@router.get("/labeled-transactions", summary="Fetch Dataset 2 labeled transactions for feedback learning")
def get_labeled_transactions(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    label_filter: Optional[str] = None, # SCAM, LEGIT, or ALL
    db: sqlite3.Connection = Depends(get_db)
):
    offset = (page - 1) * page_size
    query = \"\"\"
        SELECT f.id, f.investigation_id, f.disposition, f.rationale,
               f.is_eligible_for_training, f.training_label, f.created_at,
               i.case_number, i.title, i.priority
        FROM analyst_feedback f
        LEFT JOIN investigations i ON f.investigation_id = i.id
        WHERE 1=1
    \"\"\"
    params = []
    if label_filter == "SCAM":
        query += " AND f.training_label = 1"
    elif label_filter == "LEGIT":
        query += " AND f.training_label = 0"

    cursor = db.cursor()
    cursor.execute(f"SELECT COUNT(*) FROM ({query})", params)
    total = cursor.fetchone()[0]

    query += " ORDER BY f.created_at DESC LIMIT ? OFFSET ?"
    params.extend([page_size, offset])
    cursor.execute(query, params)
    rows = [dict(r) for r in cursor.fetchall()]

    return {
        "items": rows,
        "total": total,
        "page": page,
        "page_size": page_size
    }
"""

if "/labeled-transactions" not in fb_code:
    fb_code += "\n" + LABELED_ENDPOINT
    with open(feedback_file, "w", encoding="utf-8") as f:
        f.write(fb_code)
    print("feedback.py patched with /labeled-transactions endpoint.")

# -------------------------------------------------------------
# 3. Patch backend/app/static/index.html
# -------------------------------------------------------------
index_file = os.path.join(BASE_DIR, "backend", "app", "static", "index.html")
with open(index_file, "r", encoding="utf-8") as f:
    html = f.read().replace("\r\n", "\n")

# A. Remove Detection Rules button from sidebar
RULES_BTN = """                <button onclick="switchView('rules')" id="nav-rules" class="w-full text-left text-text-secondary hover:text-text-primary hover:bg-surface-variant font-mono text-xs px-3 py-2.5 rounded flex items-center gap-2.5 transition-colors group">
                    <span class="material-symbols-outlined text-[18px] group-hover:text-primary">tune</span>
                    <span>Detection Rules</span>
                </button>"""
html = html.replace(RULES_BTN, "")

# B. Remove <div id="view-rules">...</div>
start_rules = html.find('id="view-rules"')
if start_rules != -1:
    div_start = html.rfind('<div', 0, start_rules)
    # Find matching closing div or next section
    next_sec = html.find('id="view-audit"', start_rules)
    if next_sec != -1:
        sec_div = html.rfind('<div', 0, next_sec)
        html = html[:div_start] + html[sec_div:]
        print("view-rules section removed from index.html.")

# C. Update switchView list
html = html.replace("'rules', ", "")
html = html.replace(", 'rules'", "")

# D. Update view-datasets section with Transaction Data Explorer
NEW_DATASETS_VIEW = """            <!-- SECTION 10: DATASET MANAGEMENT & TRANSACTION BROWSER -->
            <div id="view-datasets" class="space-y-5 hidden">
                <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-surface-border">
                    <div>
                        <h1 class="text-2xl font-bold text-text-primary tracking-tight">Dataset Management & Transaction Explorer</h1>
                        <p class="text-xs text-text-secondary mt-0.5">Explore ingested transactions across SAML-D and NFPC with multi-currency routing and strict label isolation.</p>
                    </div>
                    <div class="flex items-center gap-3">
                        <button onclick="loadDatasetTransactions()" class="px-3 py-1.5 bg-primary text-surface-base font-mono text-xs font-bold rounded hover:bg-primary/90 transition shadow-sm flex items-center gap-1.5">
                            <span class="material-symbols-outlined text-[15px]">refresh</span>
                            <span>Refresh Data</span>
                        </button>
                    </div>
                </div>

                <!-- Dataset Status Summary Cards -->
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div class="bg-surface-card rounded-xl border border-surface-border p-4 flex items-center justify-between">
                        <div class="space-y-1">
                            <span class="px-2 py-0.5 text-[10px] font-mono bg-primary/10 text-primary border border-primary/20 rounded font-bold">DATASET 1: SAML-D</span>
                            <h3 class="text-sm font-bold text-text-primary">Synthetic AML Monitoring Dataset</h3>
                            <p class="text-[11px] text-text-secondary font-mono">Role: Unsupervised Development & Detection Stream (USD, EUR, GBP, AED, INR, SGD)</p>
                        </div>
                        <div class="text-right">
                            <span class="text-xl font-bold font-mono text-primary" id="saml-count-badge">400</span>
                            <span class="text-[10px] font-mono text-text-muted block">Active Records</span>
                        </div>
                    </div>
                    <div class="bg-surface-card rounded-xl border border-surface-border p-4 flex items-center justify-between">
                        <div class="space-y-1">
                            <span class="px-2 py-0.5 text-[10px] font-mono bg-status-warning/10 text-status-warning border border-status-warning/20 rounded font-bold">DATASET 2: NFPC MULE</span>
                            <h3 class="text-sm font-bold text-text-primary">Mule Account Labeled Dataset</h3>
                            <p class="text-[11px] text-text-secondary font-mono">Role: Governed Feedback & Continuous Learning (Ground Truth: Scam vs Legit)</p>
                        </div>
                        <div class="text-right">
                            <span class="text-xl font-bold font-mono text-status-warning" id="nfpc-count-badge">50</span>
                            <span class="text-[10px] font-mono text-text-muted block">Labeled Records</span>
                        </div>
                    </div>
                </div>

                <!-- Transaction Browser Table -->
                <div class="bg-surface-card rounded-xl border border-surface-border overflow-hidden">
                    <!-- Filters & Search Toolbar -->
                    <div class="p-4 border-b border-surface-border flex flex-col md:flex-row items-center justify-between gap-3 bg-surface-base/50">
                        <div class="flex items-center gap-2 w-full md:w-auto">
                            <div class="relative w-full md:w-64">
                                <span class="material-symbols-outlined absolute left-2.5 top-2 text-[16px] text-text-muted">search</span>
                                <input id="ds-search-input" type="text" placeholder="Search by Txn ID or Account..." onkeyup="if(event.key==='Enter') loadDatasetTransactions()" class="w-full pl-8 pr-3 py-1.5 bg-surface-base border border-surface-border rounded text-xs font-mono text-text-primary focus:outline-none focus:border-primary">
                            </div>
                            <button onclick="loadDatasetTransactions()" class="px-3 py-1.5 bg-surface-variant hover:bg-surface-elevated text-text-primary font-mono text-xs rounded border border-surface-border">
                                Filter
                            </button>
                        </div>

                        <div class="flex items-center gap-2 self-end">
                            <select id="ds-filter-source" onchange="loadDatasetTransactions()" class="bg-surface-base border border-surface-border text-text-primary text-xs font-mono rounded px-2.5 py-1.5 focus:outline-none">
                                <option value="ALL">All Datasets</option>
                                <option value="SAML_D" selected>Dataset 1: SAML-D</option>
                                <option value="NFPC_MULE">Dataset 2: NFPC</option>
                            </select>
                            <select id="ds-filter-curr" onchange="loadDatasetTransactions()" class="bg-surface-base border border-surface-border text-text-primary text-xs font-mono rounded px-2.5 py-1.5 focus:outline-none">
                                <option value="ALL">All Currencies</option>
                                <option value="USD">USD</option>
                                <option value="EUR">EUR</option>
                                <option value="GBP">GBP</option>
                                <option value="AED">AED</option>
                                <option value="INR">INR</option>
                                <option value="SGD">SGD</option>
                            </select>
                        </div>
                    </div>

                    <!-- Live Transactions Data Table -->
                    <div class="overflow-x-auto">
                        <table class="w-full text-left text-xs border-collapse">
                            <thead class="bg-surface-base text-[11px] font-mono text-text-muted tracking-wider border-b border-surface-border">
                                <tr>
                                    <th class="px-4 py-3">Transaction ID</th>
                                    <th class="px-4 py-3">Source Account</th>
                                    <th class="px-4 py-3">Destination Account</th>
                                    <th class="px-4 py-3">Amount & Currency</th>
                                    <th class="px-4 py-3">Channel / Type</th>
                                    <th class="px-4 py-3">Risk Band</th>
                                    <th class="px-4 py-3">Dataset</th>
                                    <th class="px-4 py-3">Timestamp</th>
                                </tr>
                            </thead>
                            <tbody id="ds-transactions-tbody" class="divide-y divide-surface-border text-text-secondary font-mono text-[11px]">
                                <tr><td colspan="8" class="px-4 py-8 text-center text-text-muted">Loading dataset transactions...</td></tr>
                            </tbody>
                        </table>
                    </div>

                    <!-- Pagination Footer -->
                    <div class="p-3 bg-surface-base/80 border-t border-surface-border flex items-center justify-between text-xs font-mono text-text-muted">
                        <span id="ds-pagination-info">Showing records 1 - 50</span>
                        <div class="flex items-center gap-2">
                            <button id="ds-prev-btn" onclick="changeDsPage(-1)" class="px-2.5 py-1 bg-surface-card hover:bg-surface-variant rounded border border-surface-border disabled:opacity-50" disabled>Previous</button>
                            <span id="ds-current-page" class="font-bold text-text-primary px-2">Page 1</span>
                            <button id="ds-next-btn" onclick="changeDsPage(1)" class="px-2.5 py-1 bg-surface-card hover:bg-surface-variant rounded border border-surface-border disabled:opacity-50">Next</button>
                        </div>
                    </div>
                </div>
            </div>"""

# Replace view-datasets with the new transaction explorer
start_ds = html.find('id="view-datasets"')
if start_ds != -1:
    div_start = html.rfind('<div', 0, start_ds)
    next_sec = html.find('id="view-fundflow"', start_ds)
    if next_sec != -1:
        sec_div = html.rfind('<div', 0, next_sec)
        html = html[:div_start] + NEW_DATASETS_VIEW + "\n\n" + html[sec_div:]
        print("view-datasets replaced with Transaction Explorer.")

# E. Update view-learning section to show Dataset 2's Labeled Feed (Scam vs Legit)
LABELED_FEED_TABLE = """                <!-- DATASET 2: LABELED GROUND TRUTH (SCAM VS LEGIT) -->
                <div class="bg-surface-card rounded-xl border border-surface-border p-5 space-y-4">
                    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-surface-border pb-3">
                        <div>
                            <div class="flex items-center gap-2">
                                <span class="px-2 py-0.5 text-[10px] font-mono bg-status-warning/10 text-status-warning border border-status-warning/30 rounded font-bold">DATASET 2: NFPC MULE GROUND TRUTH</span>
                                <h3 class="text-sm font-bold text-text-primary">Human-Verified Training Corpus (Scam vs Legit)</h3>
                            </div>
                            <p class="text-xs text-text-secondary mt-0.5">Transactions from Dataset 2 with definitive labels (1 = Scam / Confirmed Fraud, 0 = Legit / False Positive) powering continuous learning.</p>
                        </div>
                        <div class="flex items-center gap-2">
                            <button onclick="loadLabeledFeed('ALL')" class="px-2.5 py-1 bg-surface-base hover:bg-surface-elevated text-xs font-mono rounded border border-surface-border text-text-primary font-semibold">All</button>
                            <button onclick="loadLabeledFeed('SCAM')" class="px-2.5 py-1 bg-status-critical/10 hover:bg-status-critical/20 text-xs font-mono rounded border border-status-critical/30 text-status-critical font-bold">Scam (1)</button>
                            <button onclick="loadLabeledFeed('LEGIT')" class="px-2.5 py-1 bg-status-success/10 hover:bg-status-success/20 text-xs font-mono rounded border border-status-success/30 text-status-success font-bold">Legit (0)</button>
                        </div>
                    </div>

                    <!-- Labeled Table -->
                    <div class="overflow-x-auto border border-surface-border rounded-lg">
                        <table class="w-full text-left text-xs border-collapse">
                            <thead class="bg-surface-base text-[11px] font-mono text-text-muted border-b border-surface-border">
                                <tr>
                                    <th class="px-4 py-2.5">Feedback ID</th>
                                    <th class="px-4 py-2.5">Case Reference</th>
                                    <th class="px-4 py-2.5">Ground-Truth Verdict</th>
                                    <th class="px-4 py-2.5">Label (ML Target)</th>
                                    <th class="px-4 py-2.5">Investigative Rationale</th>
                                    <th class="px-4 py-2.5">Training Status</th>
                                    <th class="px-4 py-2.5">Disposed At</th>
                                </tr>
                            </thead>
                            <tbody id="labeled-feed-tbody" class="divide-y divide-surface-border text-text-secondary font-mono text-[11px]">
                                <tr><td colspan="7" class="px-4 py-6 text-center text-text-muted">Loading labeled training samples...</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>"""

# Insert LABELED_FEED_TABLE into view-learning before the end of view-learning
pos_learning = html.find('id="view-learning"')
if pos_learning != -1:
    pos_policy = html.find('Platform Label Policy (Responsible AI Safeguard)', pos_learning)
    if pos_policy != -1:
        # Find the closing div of the policy container
        policy_card_start = html.rfind('<div class="bg-surface-card p-6', 0, pos_policy)
        html = html[:policy_card_start] + LABELED_FEED_TABLE + "\n\n                " + html[policy_card_start:]
        print("view-learning updated with Labeled Ground Truth Feed.")

# F. Add JavaScript handlers for Dataset Explorer and Labeled Feed
JS_ADDITIONS = """
        // ================= DATASET TRANSACTIONS BROWSER LOGIC =================
        let dsCurrentPage = 1;

        async function loadDatasetManagement() {
            loadDatasetTransactions();
        }

        async function loadDatasetTransactions() {
            const tbody = document.getElementById('ds-transactions-tbody');
            tbody.innerHTML = `<tr><td colspan="8" class="px-4 py-6 text-center text-text-muted font-mono text-xs animate-pulse">Loading transaction records...</td></tr>`;
            try {
                const search = document.getElementById('ds-search-input') ? document.getElementById('ds-search-input').value : '';
                const source = document.getElementById('ds-filter-source') ? document.getElementById('ds-filter-source').value : 'ALL';
                const curr = document.getElementById('ds-filter-curr') ? document.getElementById('ds-filter-curr').value : 'ALL';

                const url = `${API_BASE}/datasets/transactions?page=${dsCurrentPage}&page_size=50&dataset_source=${source}&currency=${curr}&search=${encodeURIComponent(search)}`;
                const res = await fetch(url);
                const data = await res.json();

                if (!data.items || data.items.length === 0) {
                    tbody.innerHTML = `<tr><td colspan="8" class="px-4 py-6 text-center text-text-muted font-mono text-xs">No transactions match the selected criteria.</td></tr>`;
                    return;
                }

                tbody.innerHTML = data.items.map(t => {
                    const bandColor = t.risk_band === 'HIGH' ? 'bg-status-critical/10 text-status-critical border border-status-critical/30' :
                                      t.risk_band === 'ELEVATED' ? 'bg-status-warning/10 text-status-warning border border-status-warning/30' :
                                      'bg-surface-variant text-text-muted border border-surface-border';
                    return `
                        <tr class="hover:bg-surface-elevated/40 transition">
                            <td class="px-4 py-2.5 font-bold text-text-primary">${t.id}</td>
                            <td class="px-4 py-2.5 text-primary">${t.source_account_id}</td>
                            <td class="px-4 py-2.5">${t.destination_account_id || '--'}</td>
                            <td class="px-4 py-2.5 font-bold text-text-primary">${t.currency} ${Number(t.amount).toLocaleString()}</td>
                            <td class="px-4 py-2.5 text-text-muted">${t.payment_channel || 'TRANSFER'}</td>
                            <td class="px-4 py-2.5"><span class="px-2 py-0.5 rounded text-[10px] font-bold ${bandColor}">${t.risk_band} (${t.risk_score})</span></td>
                            <td class="px-4 py-2.5"><span class="px-1.5 py-0.5 rounded text-[10px] font-bold bg-primary/10 text-primary border border-primary/20">${t.dataset_source}</span></td>
                            <td class="px-4 py-2.5 text-text-muted">${(t.created_at || '').replace('T', ' ').slice(0, 19)}</td>
                        </tr>
                    `;
                }).join('');

                document.getElementById('ds-pagination-info').innerText = `Showing records ${(dsCurrentPage - 1) * 50 + 1} - ${Math.min(dsCurrentPage * 50, data.total)} of ${data.total} total`;
                document.getElementById('ds-current-page').innerText = `Page ${data.page} of ${data.total_pages}`;
                document.getElementById('ds-prev-btn').disabled = data.page <= 1;
                document.getElementById('ds-next-btn').disabled = data.page >= data.total_pages;

                if (document.getElementById('saml-count-badge')) {
                    document.getElementById('saml-count-badge').innerText = data.total;
                }
            } catch(e) {
                tbody.innerHTML = `<tr><td colspan="8" class="px-4 py-6 text-center text-status-critical font-mono text-xs">Error loading transactions: ${e}</td></tr>`;
            }
        }

        function changeDsPage(delta) {
            dsCurrentPage = Math.max(1, dsCurrentPage + delta);
            loadDatasetTransactions();
        }

        // ================= LABELED FEED (DATASET 2) LOGIC =================
        async function loadLabeledFeed(filter = 'ALL') {
            const tbody = document.getElementById('labeled-feed-tbody');
            if (!tbody) return;
            tbody.innerHTML = `<tr><td colspan="7" class="px-4 py-6 text-center text-text-muted font-mono text-xs animate-pulse">Loading Dataset 2 labeled records...</td></tr>`;
            try {
                const res = await fetch(`${API_BASE}/feedback/labeled-transactions?label_filter=${filter}`);
                const data = await res.json();
                if (!data.items || data.items.length === 0) {
                    tbody.innerHTML = `<tr><td colspan="7" class="px-4 py-6 text-center text-text-muted font-mono text-xs">No labeled records found.</td></tr>`;
                    return;
                }

                tbody.innerHTML = data.items.map(r => {
                    const isScam = r.training_label === 1;
                    const labelBadge = isScam
                        ? `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-status-critical/10 text-status-critical border border-status-critical/30">SCAM [1]</span>`
                        : `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-status-success/10 text-status-success border border-status-success/30">LEGIT [0]</span>`;

                    return `
                        <tr class="hover:bg-surface-elevated/40 transition">
                            <td class="px-4 py-2.5 font-bold text-text-primary">${r.id}</td>
                            <td class="px-4 py-2.5 text-primary">${r.case_number || r.investigation_id}</td>
                            <td class="px-4 py-2.5 font-bold text-text-primary">${r.disposition.replace('_', ' ')}</td>
                            <td class="px-4 py-2.5">${labelBadge}</td>
                            <td class="px-4 py-2.5 text-text-secondary max-w-[280px] truncate" title="${r.rationale}">${r.rationale}</td>
                            <td class="px-4 py-2.5"><span class="px-1.5 py-0.5 rounded text-[10px] font-bold bg-status-success/10 text-status-success">ELIGIBLE</span></td>
                            <td class="px-4 py-2.5 text-text-muted">${(r.created_at || '').replace('T', ' ').slice(0, 19)}</td>
                        </tr>
                    `;
                }).join('');
            } catch(e) {
                tbody.innerHTML = `<tr><td colspan="7" class="px-4 py-6 text-center text-status-critical font-mono text-xs">Error: ${e}</td></tr>`;
            }
        }
"""

# Replace loadLearningStatus to also trigger loadLabeledFeed
html = html.replace("loadLearningStatus();", "loadLearningStatus(); loadLabeledFeed();")
html = html.replace("async function loadLearningStatus()", JS_ADDITIONS + "\n        async function loadLearningStatus()")

with open(index_file, "w", encoding="utf-8") as f:
    f.write(html)

print("index.html successfully updated.")
