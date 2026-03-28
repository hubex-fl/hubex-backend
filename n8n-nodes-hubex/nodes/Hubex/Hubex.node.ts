import type {
	IExecuteFunctions,
	INodeExecutionData,
	INodeType,
	INodeTypeDescription,
} from 'n8n-workflow';
import { NodeOperationError } from 'n8n-workflow';

// ---------------------------------------------------------------------------
// JWT helper — login once per execution
// ---------------------------------------------------------------------------

async function getJwt(
	context: IExecuteFunctions,
	serverUrl: string,
	email: string,
	password: string,
): Promise<string> {
	const response = await context.helpers.httpRequest({
		method: 'POST',
		url: `${serverUrl}/api/v1/auth/login`,
		body: { email, password },
		json: true,
	});
	if (!response.access_token) {
		throw new NodeOperationError(context.getNode(), 'HUBEX login failed — check credentials');
	}
	return response.access_token as string;
}

// ---------------------------------------------------------------------------
// Node definition
// ---------------------------------------------------------------------------

export class Hubex implements INodeType {
	description: INodeTypeDescription = {
		displayName: 'HUBEX',
		name: 'hubex',
		icon: 'file:hubex.svg',
		group: ['transform'],
		version: 1,
		subtitle: '={{ $parameter["resource"] + ": " + $parameter["operation"] }}',
		description: 'Interact with HUBEX IoT platform — devices, telemetry, alerts, variables, variable streams',
		defaults: { name: 'HUBEX' },
		inputs: ['main'],
		outputs: ['main'],
		credentials: [{ name: 'hubexApi', required: true }],
		properties: [
			// ------------------------------------------------------------------
			// Resource selector
			// ------------------------------------------------------------------
			{
				displayName: 'Resource',
				name: 'resource',
				type: 'options',
				noDataExpression: true,
				options: [
					{ name: 'Device', value: 'device' },
					{ name: 'Telemetry', value: 'telemetry' },
					{ name: 'Alert', value: 'alert' },
					{ name: 'Variable', value: 'variable' },
					{ name: 'Variable Stream', value: 'variableStream' },
				],
				default: 'device',
			},

			// ------------------------------------------------------------------
			// Device operations
			// ------------------------------------------------------------------
			{
				displayName: 'Operation',
				name: 'operation',
				type: 'options',
				noDataExpression: true,
				displayOptions: { show: { resource: ['device'] } },
				options: [
					{ name: 'List Devices', value: 'list', action: 'List all devices', description: 'Get a paginated list of devices' },
					{ name: 'Get Device', value: 'get', action: 'Get a device', description: 'Get a single device by UID' },
				],
				default: 'list',
			},
			{
				displayName: 'Device UID',
				name: 'deviceUid',
				type: 'string',
				default: '',
				required: true,
				displayOptions: { show: { resource: ['device'], operation: ['get'] } },
				description: 'The unique identifier of the device',
			},
			{
				displayName: 'Health Filter',
				name: 'healthFilter',
				type: 'options',
				options: [
					{ name: 'All', value: '' },
					{ name: 'OK', value: 'ok' },
					{ name: 'Stale', value: 'stale' },
					{ name: 'Dead', value: 'dead' },
				],
				default: '',
				displayOptions: { show: { resource: ['device'], operation: ['list'] } },
			},
			{
				displayName: 'Limit',
				name: 'limit',
				type: 'number',
				typeOptions: { minValue: 1, maxValue: 200 },
				default: 50,
				displayOptions: { show: { resource: ['device'], operation: ['list'] } },
			},

			// ------------------------------------------------------------------
			// Telemetry operations
			// ------------------------------------------------------------------
			{
				displayName: 'Operation',
				name: 'operation',
				type: 'options',
				noDataExpression: true,
				displayOptions: { show: { resource: ['telemetry'] } },
				options: [
					{ name: 'List', value: 'list', action: 'List telemetry', description: 'Get recent telemetry entries' },
					{ name: 'Get Latest', value: 'latest', action: 'Get latest telemetry', description: 'Get most recent entry for a device' },
				],
				default: 'list',
			},
			{
				displayName: 'Device UID',
				name: 'deviceUid',
				type: 'string',
				default: '',
				required: true,
				displayOptions: { show: { resource: ['telemetry'] } },
			},
			{
				displayName: 'Limit',
				name: 'limit',
				type: 'number',
				typeOptions: { minValue: 1, maxValue: 200 },
				default: 20,
				displayOptions: { show: { resource: ['telemetry'], operation: ['list'] } },
			},

			// ------------------------------------------------------------------
			// Alert operations
			// ------------------------------------------------------------------
			{
				displayName: 'Operation',
				name: 'operation',
				type: 'options',
				noDataExpression: true,
				displayOptions: { show: { resource: ['alert'] } },
				options: [
					{ name: 'List Rules', value: 'listRules', action: 'List alert rules' },
					{ name: 'List Events', value: 'listEvents', action: 'List alert events' },
					{ name: 'Acknowledge Event', value: 'ackEvent', action: 'Acknowledge an alert event' },
				],
				default: 'listRules',
			},
			{
				displayName: 'Event ID',
				name: 'eventId',
				type: 'string',
				default: '',
				required: true,
				displayOptions: { show: { resource: ['alert'], operation: ['ackEvent'] } },
			},
			{
				displayName: 'Device UID Filter',
				name: 'deviceUid',
				type: 'string',
				default: '',
				displayOptions: { show: { resource: ['alert'], operation: ['listEvents'] } },
				description: 'Filter events by device UID (optional)',
			},

			// ------------------------------------------------------------------
			// Variable operations
			// ------------------------------------------------------------------
			{
				displayName: 'Operation',
				name: 'operation',
				type: 'options',
				noDataExpression: true,
				displayOptions: { show: { resource: ['variable'] } },
				options: [
					{ name: 'List Variables', value: 'list', action: 'List device variables' },
					{ name: 'Set Variable', value: 'set', action: 'Set a device variable' },
					{ name: 'Delete Variable', value: 'delete', action: 'Delete a device variable' },
				],
				default: 'list',
			},
			{
				displayName: 'Device UID',
				name: 'deviceUid',
				type: 'string',
				default: '',
				required: true,
				displayOptions: { show: { resource: ['variable'] } },
			},
			{
				displayName: 'Variable Key',
				name: 'variableKey',
				type: 'string',
				default: '',
				required: true,
				displayOptions: { show: { resource: ['variable'], operation: ['set', 'delete'] } },
			},
			{
				displayName: 'Value',
				name: 'variableValue',
				type: 'string',
				default: '',
				required: true,
				displayOptions: { show: { resource: ['variable'], operation: ['set'] } },
			},

			// ------------------------------------------------------------------
			// Variable Stream operations
			// ------------------------------------------------------------------
			{
				displayName: 'Operation',
				name: 'operation',
				type: 'options',
				noDataExpression: true,
				displayOptions: { show: { resource: ['variableStream'] } },
				options: [
					{ name: 'Get History', value: 'getHistory', action: 'Get variable history', description: 'Get time-series data for a variable' },
					{ name: 'Get Snapshot', value: 'getSnapshot', action: 'Get variable snapshot', description: 'Get current values of all variables for a scope/device' },
					{ name: 'Get Definitions', value: 'getDefinitions', action: 'List variable definitions', description: 'List all variable definitions' },
					{ name: 'Bulk Set', value: 'bulkSet', action: 'Bulk set variables', description: 'Set multiple variables at once' },
				],
				default: 'getHistory',
			},
			// --- getHistory params ---
			{
				displayName: 'Variable Key',
				name: 'variableKey',
				type: 'string',
				default: '',
				required: true,
				displayOptions: { show: { resource: ['variableStream'], operation: ['getHistory'] } },
				description: 'The variable key to retrieve history for',
			},
			{
				displayName: 'Scope',
				name: 'scope',
				type: 'options',
				options: [
					{ name: 'Device', value: 'device' },
					{ name: 'Org', value: 'org' },
					{ name: 'Global', value: 'global' },
				],
				default: 'device',
				displayOptions: { show: { resource: ['variableStream'], operation: ['getHistory', 'getSnapshot'] } },
				description: 'The variable scope',
			},
			{
				displayName: 'Device UID',
				name: 'deviceUid',
				type: 'string',
				default: '',
				displayOptions: { show: { resource: ['variableStream'], operation: ['getHistory', 'getSnapshot'] } },
				description: 'Device UID (required for device scope)',
			},
			{
				displayName: 'From (ISO)',
				name: 'fromDate',
				type: 'string',
				default: '',
				displayOptions: { show: { resource: ['variableStream'], operation: ['getHistory'] } },
				description: 'Start of time range (ISO 8601, e.g. 2024-01-01T00:00:00Z). Optional.',
			},
			{
				displayName: 'To (ISO)',
				name: 'toDate',
				type: 'string',
				default: '',
				displayOptions: { show: { resource: ['variableStream'], operation: ['getHistory'] } },
				description: 'End of time range (ISO 8601). Optional.',
			},
			{
				displayName: 'Limit',
				name: 'limit',
				type: 'number',
				typeOptions: { minValue: 1, maxValue: 10000 },
				default: 500,
				displayOptions: { show: { resource: ['variableStream'], operation: ['getHistory'] } },
			},
			// --- bulkSet params ---
			{
				displayName: 'Variables (JSON)',
				name: 'bulkVariables',
				type: 'json',
				default: '[\n  { "key": "temperature", "value": "23.5", "scope": "device", "device_uid": "my-device" }\n]',
				required: true,
				displayOptions: { show: { resource: ['variableStream'], operation: ['bulkSet'] } },
				description: 'JSON array of variables to set. Each item needs: key, value, scope, and optionally device_uid.',
			},
			{
				displayName: 'Allow Partial',
				name: 'allowPartial',
				type: 'boolean',
				default: true,
				displayOptions: { show: { resource: ['variableStream'], operation: ['bulkSet'] } },
				description: 'If true, continue setting variables even if some fail',
			},
		],
	};

	async execute(this: IExecuteFunctions): Promise<INodeExecutionData[][]> {
		const credentials = await this.getCredentials('hubexApi');
		const serverUrl = (credentials.serverUrl as string).replace(/\/$/, '');
		const email = credentials.email as string;
		const password = credentials.password as string;

		const resource = this.getNodeParameter('resource', 0) as string;
		const operation = this.getNodeParameter('operation', 0) as string;

		// Login once
		const jwt = await getJwt(this, serverUrl, email, password);
		const authHeader = { Authorization: `Bearer ${jwt}` };

		let responseData: unknown;

		if (resource === 'device') {
			if (operation === 'list') {
				const limit = this.getNodeParameter('limit', 0) as number;
				const health = this.getNodeParameter('healthFilter', 0) as string;
				const params = new URLSearchParams({ limit: String(limit) });
				if (health) params.set('health', health);
				responseData = await this.helpers.httpRequest({
					method: 'GET',
					url: `${serverUrl}/api/v1/devices?${params}`,
					headers: authHeader,
					json: true,
				});
			} else if (operation === 'get') {
				const uid = this.getNodeParameter('deviceUid', 0) as string;
				responseData = await this.helpers.httpRequest({
					method: 'GET',
					url: `${serverUrl}/api/v1/devices/${encodeURIComponent(uid)}`,
					headers: authHeader,
					json: true,
				});
			}
		} else if (resource === 'telemetry') {
			const uid = this.getNodeParameter('deviceUid', 0) as string;
			if (operation === 'list') {
				const limit = this.getNodeParameter('limit', 0) as number;
				responseData = await this.helpers.httpRequest({
					method: 'GET',
					url: `${serverUrl}/api/v1/telemetry?device_uid=${encodeURIComponent(uid)}&limit=${limit}`,
					headers: authHeader,
					json: true,
				});
			} else if (operation === 'latest') {
				responseData = await this.helpers.httpRequest({
					method: 'GET',
					url: `${serverUrl}/api/v1/telemetry/latest/${encodeURIComponent(uid)}`,
					headers: authHeader,
					json: true,
				});
			}
		} else if (resource === 'alert') {
			if (operation === 'listRules') {
				responseData = await this.helpers.httpRequest({
					method: 'GET',
					url: `${serverUrl}/api/v1/alerts/rules`,
					headers: authHeader,
					json: true,
				});
			} else if (operation === 'listEvents') {
				const uid = this.getNodeParameter('deviceUid', 0) as string;
				const params = new URLSearchParams();
				if (uid) params.set('device_uid', uid);
				responseData = await this.helpers.httpRequest({
					method: 'GET',
					url: `${serverUrl}/api/v1/alerts/events?${params}`,
					headers: authHeader,
					json: true,
				});
			} else if (operation === 'ackEvent') {
				const eventId = this.getNodeParameter('eventId', 0) as string;
				responseData = await this.helpers.httpRequest({
					method: 'POST',
					url: `${serverUrl}/api/v1/alerts/events/${encodeURIComponent(eventId)}/ack`,
					headers: authHeader,
					json: true,
				});
			}
		} else if (resource === 'variable') {
			const uid = this.getNodeParameter('deviceUid', 0) as string;
			if (operation === 'list') {
				responseData = await this.helpers.httpRequest({
					method: 'GET',
					url: `${serverUrl}/api/v1/devices/${encodeURIComponent(uid)}/variables`,
					headers: authHeader,
					json: true,
				});
			} else if (operation === 'set') {
				const key = this.getNodeParameter('variableKey', 0) as string;
				const value = this.getNodeParameter('variableValue', 0) as string;
				responseData = await this.helpers.httpRequest({
					method: 'PUT',
					url: `${serverUrl}/api/v1/devices/${encodeURIComponent(uid)}/variables/${encodeURIComponent(key)}`,
					headers: authHeader,
					body: { value },
					json: true,
				});
			} else if (operation === 'delete') {
				const key = this.getNodeParameter('variableKey', 0) as string;
				responseData = await this.helpers.httpRequest({
					method: 'DELETE',
					url: `${serverUrl}/api/v1/devices/${encodeURIComponent(uid)}/variables/${encodeURIComponent(key)}`,
					headers: authHeader,
					json: true,
				});
			}
		} else if (resource === 'variableStream') {
			if (operation === 'getHistory') {
				const key = this.getNodeParameter('variableKey', 0) as string;
				const scope = this.getNodeParameter('scope', 0) as string;
				const deviceUid = this.getNodeParameter('deviceUid', 0) as string;
				const fromDate = this.getNodeParameter('fromDate', 0) as string;
				const toDate = this.getNodeParameter('toDate', 0) as string;
				const limit = this.getNodeParameter('limit', 0) as number;

				const params = new URLSearchParams({ key, scope, limit: String(limit) });
				if (deviceUid) params.set('device_uid', deviceUid);
				if (fromDate) params.set('from', fromDate);
				if (toDate) params.set('to', toDate);

				responseData = await this.helpers.httpRequest({
					method: 'GET',
					url: `${serverUrl}/api/v1/variables/history?${params}`,
					headers: authHeader,
					json: true,
				});
			} else if (operation === 'getSnapshot') {
				const scope = this.getNodeParameter('scope', 0) as string;
				const deviceUid = this.getNodeParameter('deviceUid', 0) as string;

				const params = new URLSearchParams({ scope });
				if (deviceUid) params.set('device_uid', deviceUid);

				responseData = await this.helpers.httpRequest({
					method: 'GET',
					url: `${serverUrl}/api/v1/variables/snapshot?${params}`,
					headers: authHeader,
					json: true,
				});
			} else if (operation === 'getDefinitions') {
				responseData = await this.helpers.httpRequest({
					method: 'GET',
					url: `${serverUrl}/api/v1/variables/definitions`,
					headers: authHeader,
					json: true,
				});
			} else if (operation === 'bulkSet') {
				const bulkVars = this.getNodeParameter('bulkVariables', 0) as string;
				const allowPartial = this.getNodeParameter('allowPartial', 0) as boolean;

				let items: unknown[];
				try {
					items = typeof bulkVars === 'string' ? JSON.parse(bulkVars) : bulkVars;
				} catch {
					throw new NodeOperationError(this.getNode(), 'Invalid JSON in "Variables (JSON)" field');
				}

				responseData = await this.helpers.httpRequest({
					method: 'POST',
					url: `${serverUrl}/api/v1/variables/bulk-set`,
					headers: authHeader,
					body: { items, allow_partial: allowPartial },
					json: true,
				});
			}
		}

		// Wrap array or single object into n8n items
		const items = Array.isArray(responseData)
			? (responseData as object[]).map((item) => ({ json: item }))
			: [{ json: responseData as object }];

		return [items];
	}
}
