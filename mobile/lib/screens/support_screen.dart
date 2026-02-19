import 'package:flutter/material.dart';

class SupportScreen extends StatelessWidget {
  const SupportScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Scaffold(
      appBar: AppBar(title: const Text('Support')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          _helpCard(
            context,
            icon: Icons.rocket_launch,
            title: 'Getting Started',
            items: [
              'Deploy the backend to Render (or run locally)',
              'Enter your server URL in the Settings tab',
              'Tap "Test Connection" to verify',
              'View your activity on the Dashboard and Activity tabs',
            ],
          ),

          _helpCard(
            context,
            icon: Icons.dns,
            title: 'Server Setup',
            items: [
              'Push the repo to GitHub',
              'Create a Web Service on render.com',
              'Connect your GitHub repo',
              'Add environment variables (tokens, IDs) in Render dashboard',
              'Set start command: uvicorn app.main:app --host 0.0.0.0 --port \$PORT',
            ],
          ),

          _helpCard(
            context,
            icon: Icons.key,
            title: 'Required Environment Variables',
            items: [
              'GITHUB_TOKEN — Personal Access Token',
              'GITHUB_USERNAME — Your GitHub login',
              'CLICKUP_API_TOKEN — ClickUp API token',
              'CLICKUP_TEAM_ID — Workspace team ID',
              'CLICKUP_USER_ID — Your numeric user ID',
              'SLACK_BOT_TOKEN — Bot OAuth Token (xoxb-...)',
              'SLACK_CHANNEL — Channel ID or name',
              'SLACK_USER_ID — Your Slack user ID',
              'REPORT_HOUR / REPORT_MINUTE — Schedule time',
              'TIMEZONE — e.g. Asia/Kathmandu',
            ],
          ),

          _helpCard(
            context,
            icon: Icons.info_outline,
            title: 'About',
            items: [
              'EOD Auto Reporter v1.0.0',
              'Fetches GitHub commits, PRs, ClickUp tasks',
              'Posts formatted EOD reports to Slack',
              'Scheduler runs Mon–Fri at your configured time',
            ],
          ),
        ],
      ),
    );
  }

  Widget _helpCard(BuildContext context, {
    required IconData icon,
    required String title,
    required List<String> items,
  }) {
    final cs = Theme.of(context).colorScheme;
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(icon, color: cs.primary, size: 20),
                const SizedBox(width: 8),
                Text(title, style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
              ],
            ),
            const SizedBox(height: 12),
            ...items.asMap().entries.map((e) => Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  SizedBox(
                    width: 20,
                    child: Text(
                      '${e.key + 1}',
                      style: TextStyle(color: cs.primary, fontWeight: FontWeight.w600, fontSize: 13),
                    ),
                  ),
                  Expanded(
                    child: Text(e.value, style: const TextStyle(fontSize: 13)),
                  ),
                ],
              ),
            )),
          ],
        ),
      ),
    );
  }
}
