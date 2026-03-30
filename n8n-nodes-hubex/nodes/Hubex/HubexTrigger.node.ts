import type {
	IHookFunctions,
	IWebhookFunctions,
	INodeType,
	INodeTypeDescription,
	IWebhookResponseData,
} from 'n8n-workflow';

// ---------------------------------------------------------------------------
// Trigger node — registers HUBEX webhook subscription on activate
// ---------------------------------------------------------------------------

export class HubexTrigger implements INodeType {
	description: INodeTypeDescription = {
		displayName: 'HUBEX Trigger',
		name: 'hubexTrigger',
		icon: 'file:hubex.svg',
		group: ['trigger'],
		version: 2,
		description: 'Receive HUBEX events in real-time via webhook subscription',
		defaults: { name: 'HUBEX Trigger' },
		inputs: [],
		outputs: ['main'],
		credentials: [{ name: 'hubexApi', required: true }],
		webhooks: [
			{
				name: 'default',
				httpMethod: 'POST',
				responseMode: 'onReceived',
				path: 'hubex-trigger',
			},
		],
		properties: [
			{
				displayName: 'Event Types',
				name: 'eventTypes',
				type: 'multiOptions',
				options: [
					{ name: 'Device Paired', value: 'device.paired' },
					{ name: 'Device Online', value: 'device.online' },
					{ name: 'Device Offline', value: 'device.offline' },
					{ name: 'Telemetry Received', value: 'telemetry.received' },
					{ name: 'Alert Fired', value: 'alert.fired' },
					{ name: 'Alert Resolved', value: 'alert.resolved' },
					{ name: 'Task Completed', value: 'task.completed' },
					{ name: 'Variable Auto-Discovered', value: 'variable.auto_discovered' },
					{ name: 'Variable Changed', value: 'variable.changed' },
					{ name: 'Automation Fired', value: 'automation.fired' },
					{ name: 'Automation Failed', value: 'automation.failed' },
					{ name: 'All Events', value: '*' },
				],
				default: ['device.offline', 'alert.fired'],
				description: 'Which HUBEX event types to subscribe to',
			},
		],
	};

	webhookMethods = {
		default: {
			async checkExists(this: IHookFunctions): Promise<boolean> {
				const webhookData = this.getWorkflowStaticData('node');
				if (!webhookData.subscriptionId) return false;

				const credentials = await this.getCredentials('hubexApi');
				const serverUrl = (credentials.serverUrl as string).replace(/\/$/, '');
				const email = credentials.email as string;
				const password = credentials.password as string;

				try {
					const loginResp = await this.helpers.httpRequest({
						method: 'POST',
						url: `${serverUrl}/api/v1/auth/login`,
						body: { email, password },
						json: true,
					});
					const jwt = loginResp.access_token as string;

					const resp = await this.helpers.httpRequest({
						method: 'GET',
						url: `${serverUrl}/api/v1/webhooks/${webhookData.subscriptionId}`,
						headers: { Authorization: `Bearer ${jwt}` },
						json: true,
					});
					return !!resp.id;
				} catch {
					return false;
				}
			},

			async create(this: IHookFunctions): Promise<boolean> {
				const webhookUrl = this.getNodeWebhookUrl('default') as string;
				const eventTypes = this.getNodeParameter('eventTypes') as string[];

				const credentials = await this.getCredentials('hubexApi');
				const serverUrl = (credentials.serverUrl as string).replace(/\/$/, '');
				const email = credentials.email as string;
				const password = credentials.password as string;

				const loginResp = await this.helpers.httpRequest({
					method: 'POST',
					url: `${serverUrl}/api/v1/auth/login`,
					body: { email, password },
					json: true,
				});
				const jwt = loginResp.access_token as string;

				const resp = await this.helpers.httpRequest({
					method: 'POST',
					url: `${serverUrl}/api/v1/webhooks`,
					headers: { Authorization: `Bearer ${jwt}` },
					body: {
						url: webhookUrl,
						event_types: eventTypes,
						description: `n8n workflow: ${this.getWorkflow().name}`,
					},
					json: true,
				});

				const webhookData = this.getWorkflowStaticData('node');
				webhookData.subscriptionId = resp.id;
				return true;
			},

			async delete(this: IHookFunctions): Promise<boolean> {
				const webhookData = this.getWorkflowStaticData('node');
				if (!webhookData.subscriptionId) return true;

				const credentials = await this.getCredentials('hubexApi');
				const serverUrl = (credentials.serverUrl as string).replace(/\/$/, '');
				const email = credentials.email as string;
				const password = credentials.password as string;

				try {
					const loginResp = await this.helpers.httpRequest({
						method: 'POST',
						url: `${serverUrl}/api/v1/auth/login`,
						body: { email, password },
						json: true,
					});
					const jwt = loginResp.access_token as string;

					await this.helpers.httpRequest({
						method: 'DELETE',
						url: `${serverUrl}/api/v1/webhooks/${webhookData.subscriptionId}`,
						headers: { Authorization: `Bearer ${jwt}` },
						json: true,
					});
				} catch {
					// Ignore errors on delete — subscription may already be gone
				}

				delete webhookData.subscriptionId;
				return true;
			},
		},
	};

	async webhook(this: IWebhookFunctions): Promise<IWebhookResponseData> {
		const body = this.getBodyData();

		// Enrich with semantic type info if present in payload
		const enriched = { ...(body as object) };

		return {
			workflowData: [[{ json: enriched }]],
		};
	}
}
