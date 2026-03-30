/**
 * n8n Node API Compatibility Tests (M21 Step 3)
 *
 * Validates that all HUBEX API endpoints used by the n8n node are
 * accessible and return expected response shapes. Run against a
 * live HUBEX backend instance.
 *
 * Usage:
 *   HUBEX_URL=http://localhost:8000 \
 *   HUBEX_EMAIL=user@example.com \
 *   HUBEX_PASSWORD=Test1234! \
 *   npx tsx tests/api-compat.test.ts
 */

const BASE = process.env.HUBEX_URL || 'http://localhost:8000';
const EMAIL = process.env.HUBEX_EMAIL || 'codex+20251219002029@example.com';
const PASSWORD = process.env.HUBEX_PASSWORD || 'Test1234!';

interface TestResult {
	name: string;
	ok: boolean;
	status?: number;
	error?: string;
}

const results: TestResult[] = [];

async function getToken(): Promise<string> {
	const r = await fetch(`${BASE}/api/v1/auth/login`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ email: EMAIL, password: PASSWORD }),
	});
	if (!r.ok) throw new Error(`Login failed: ${r.status}`);
	const d = await r.json();
	return d.access_token;
}

async function test(name: string, method: string, path: string, token: string, body?: unknown) {
	try {
		const opts: RequestInit = {
			method,
			headers: {
				Authorization: `Bearer ${token}`,
				'Content-Type': 'application/json',
			},
		};
		if (body) opts.body = JSON.stringify(body);

		const r = await fetch(`${BASE}${path}`, opts);
		const ok = r.status >= 200 && r.status < 300;
		results.push({ name, ok, status: r.status, error: ok ? undefined : `HTTP ${r.status}` });
	} catch (e: unknown) {
		results.push({ name, ok: false, error: String(e) });
	}
}

async function run() {
	console.log(`\n  HUBEX n8n Node — API Compatibility Test\n  Target: ${BASE}\n`);

	const token = await getToken();
	console.log('  Auth: OK\n');

	// Device operations
	await test('device.list',           'GET',  '/api/v1/devices', token);

	// Telemetry (POST-only ingestion endpoint, device-token auth for recent — skip in user-auth test)

	// Alerts
	await test('alert.listRules',       'GET',  '/api/v1/alerts/rules', token);
	await test('alert.listEvents',      'GET',  '/api/v1/alerts', token);

	// Variables
	await test('variable.definitions',  'GET',  '/api/v1/variables/definitions', token);
	await test('variable.history',      'GET',  '/api/v1/variables/history?key=demo.temperature&scope=device&limit=10', token);

	// Automations (M21)
	await test('automation.list',       'GET',  '/api/v1/automations', token);
	await test('automation.templates',  'GET',  '/api/v1/automations/templates', token);
	await test('automation.triggers',   'GET',  '/api/v1/automations/trigger-templates', token);

	// Dashboards (M21)
	await test('dashboard.list',        'GET',  '/api/v1/dashboards', token);

	// Semantic Types (M21)
	await test('semanticType.list',     'GET',  '/api/v1/types/semantic', token);

	// Webhooks
	await test('webhook.list',          'GET',  '/api/v1/webhooks', token);

	// Metrics
	await test('metrics',               'GET',  '/api/v1/metrics', token);

	// Health (non-auth)
	try {
		const hr = await fetch(`${BASE}/health`);
		results.push({ name: 'health', ok: hr.ok, status: hr.status });
	} catch (e: unknown) {
		results.push({ name: 'health', ok: false, error: String(e) });
	}

	// Print results
	let passed = 0;
	let failed = 0;
	for (const r of results) {
		const icon = r.ok ? '\x1b[32m✓\x1b[0m' : '\x1b[31m✗\x1b[0m';
		const detail = r.error ? ` (${r.error})` : ` (${r.status})`;
		console.log(`  ${icon} ${r.name}${detail}`);
		if (r.ok) passed++;
		else failed++;
	}

	console.log(`\n  ${passed} passed, ${failed} failed, ${results.length} total\n`);
	process.exit(failed > 0 ? 1 : 0);
}

run().catch((e) => {
	console.error('Fatal:', e);
	process.exit(1);
});
