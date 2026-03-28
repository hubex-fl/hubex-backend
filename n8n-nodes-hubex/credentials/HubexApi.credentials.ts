import type {
	IAuthenticateGeneric,
	ICredentialTestRequest,
	ICredentialType,
	INodeProperties,
} from 'n8n-workflow';

export class HubexApi implements ICredentialType {
	name = 'hubexApi';
	displayName = 'HUBEX API';
	documentationUrl = 'https://github.com/your-org/hubex';

	properties: INodeProperties[] = [
		{
			displayName: 'Server URL',
			name: 'serverUrl',
			type: 'string',
			default: 'http://localhost:8000',
			placeholder: 'https://hubex.example.com',
			description: 'Base URL of your HUBEX server',
		},
		{
			displayName: 'Email',
			name: 'email',
			type: 'string',
			typeOptions: { email: true },
			default: '',
			placeholder: 'user@example.com',
		},
		{
			displayName: 'Password',
			name: 'password',
			type: 'string',
			typeOptions: { password: true },
			default: '',
		},
	];

	// n8n uses this to inject the auth token — we handle auth manually in the node
	// to support the JWT login flow, so we use a "noAuth" placeholder here.
	authenticate: IAuthenticateGeneric = {
		type: 'generic',
		properties: {},
	};

	test: ICredentialTestRequest = {
		request: {
			baseURL: '={{ $credentials.serverUrl }}',
			url: '/api/v1/auth/login',
			method: 'POST',
			body: {
				email: '={{ $credentials.email }}',
				password: '={{ $credentials.password }}',
			},
			headers: {
				'Content-Type': 'application/json',
			},
		},
		rules: [
			{
				type: 'responseSuccessBody',
				properties: {
					key: 'access_token',
					value: '',
					message: 'Login failed — check email/password and server URL',
				},
			},
		],
	};
}
