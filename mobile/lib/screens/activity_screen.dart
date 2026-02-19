import 'package:flutter/material.dart';
import '../services/api_service.dart';

class ActivityScreen extends StatefulWidget {
  final ApiService api;
  const ActivityScreen({super.key, required this.api});

  @override
  State<ActivityScreen> createState() => _ActivityScreenState();
}

class _ActivityScreenState extends State<ActivityScreen> {
  bool _loading = false;
  Map<String, dynamic>? _data;
  String? _error;

  @override
  void initState() {
    super.initState();
    _refresh();
  }

  @override
  void didUpdateWidget(ActivityScreen old) {
    super.didUpdateWidget(old);
    if (old.api.baseUrl != widget.api.baseUrl) _refresh();
  }

  Future<void> _refresh() async {
    if (!widget.api.isConfigured) {
      setState(() => _error = 'Set your server URL in Settings first');
      return;
    }
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final data = await widget.api.getActivity();
      setState(() {
        _data = data;
        _loading = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Scaffold(
      appBar: AppBar(
        title: const Text("Today's Activity"),
        actions: [
          IconButton(
            onPressed: _loading ? null : _refresh,
            icon: _loading
                ? const SizedBox(
                    width: 20, height: 20,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.refresh),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _refresh,
        child: _buildBody(cs),
      ),
    );
  }

  Widget _buildBody(ColorScheme cs) {
    if (_error != null) {
      return ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            color: cs.errorContainer,
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Text(_error!, style: TextStyle(color: cs.onErrorContainer)),
            ),
          ),
        ],
      );
    }

    if (_data == null) {
      return const Center(child: CircularProgressIndicator());
    }

    final github = _data!['github'] as Map<String, dynamic>?;
    final clickup = _data!['clickup'] as Map<String, dynamic>?;
    final errors = (_data!['errors'] as List?)?.cast<String>() ?? [];

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        if (errors.isNotEmpty)
          Card(
            color: cs.errorContainer,
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Text(errors.join('\n'), style: TextStyle(color: cs.onErrorContainer, fontSize: 12)),
            ),
          ),

        // GitHub Section
        if (github != null) _buildGitHubSection(github, cs),

        // ClickUp Section
        if (clickup != null) _buildClickUpSection(clickup, cs),

        if (github == null && clickup == null)
          const Padding(
            padding: EdgeInsets.only(top: 60),
            child: Center(
              child: Text('No activity data yet', style: TextStyle(color: Colors.grey)),
            ),
          ),
      ],
    );
  }

  Widget _buildGitHubSection(Map<String, dynamic> gh, ColorScheme cs) {
    final commits = (gh['commits'] as List?) ?? [];
    final prsOpened = (gh['prs_opened'] as List?) ?? [];
    final prsMerged = (gh['prs_merged'] as List?) ?? [];
    final hasData = commits.isNotEmpty || prsOpened.isNotEmpty || prsMerged.isNotEmpty;

    if (!hasData) return const SizedBox.shrink();

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.code, color: cs.primary, size: 20),
                const SizedBox(width: 8),
                Text('GitHub', style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
              ],
            ),
            const Divider(height: 20),

            if (commits.isNotEmpty) ...[
              _sectionLabel('Commits (${commits.length})', const Color(0xFF0969DA)),
              ...commits.take(10).map((c) => _commitTile(c)),
              const SizedBox(height: 8),
            ],

            if (prsOpened.isNotEmpty) ...[
              _sectionLabel('PRs Opened (${prsOpened.length})', cs.primary),
              ...prsOpened.map((pr) => _prTile(pr)),
              const SizedBox(height: 8),
            ],

            if (prsMerged.isNotEmpty) ...[
              _sectionLabel('PRs Merged (${prsMerged.length})', const Color(0xFF1B873B)),
              ...prsMerged.map((pr) => _prTile(pr)),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildClickUpSection(Map<String, dynamic> cu, ColorScheme cs) {
    final completed = (cu['tasks_completed'] as List?) ?? [];
    final inProgress = (cu['status_changes'] as List?) ?? [];
    final hasData = completed.isNotEmpty || inProgress.isNotEmpty;

    if (!hasData) return const SizedBox.shrink();

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.task_alt, color: Color(0xFF7B68EE), size: 20),
                const SizedBox(width: 8),
                Text('ClickUp', style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
              ],
            ),
            const Divider(height: 20),

            if (completed.isNotEmpty) ...[
              _sectionLabel('Completed (${completed.length})', const Color(0xFF1B873B)),
              ...completed.take(15).map((t) => _taskTile(t, true)),
              const SizedBox(height: 8),
            ],

            if (inProgress.isNotEmpty) ...[
              _sectionLabel('In Progress (${inProgress.length})', const Color(0xFF9A6700)),
              ...inProgress.take(15).map((t) => _taskTile(t, false)),
            ],
          ],
        ),
      ),
    );
  }

  Widget _sectionLabel(String text, Color color) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Text(text, style: TextStyle(color: color, fontWeight: FontWeight.w600, fontSize: 13)),
    );
  }

  Widget _commitTile(dynamic c) {
    final repo = (c['repo'] ?? '').toString().split('/').last;
    final msg = c['message'] ?? '';
    final sha = (c['sha'] ?? '').toString().substring(0, 7);
    return Padding(
      padding: const EdgeInsets.only(bottom: 4, left: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('• ', style: TextStyle(fontSize: 13)),
          Expanded(
            child: Text.rich(
              TextSpan(children: [
                TextSpan(text: '$sha ', style: TextStyle(color: Colors.grey.shade500, fontSize: 12, fontFamily: 'monospace')),
                TextSpan(text: msg, style: const TextStyle(fontSize: 13)),
                TextSpan(text: '  ($repo)', style: TextStyle(color: Colors.grey.shade500, fontSize: 12)),
              ]),
            ),
          ),
        ],
      ),
    );
  }

  Widget _prTile(dynamic pr) {
    final repo = (pr['repo'] ?? '').toString().split('/').last;
    final title = pr['title'] ?? '';
    final number = pr['number'] ?? '';
    return Padding(
      padding: const EdgeInsets.only(bottom: 4, left: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('• ', style: TextStyle(fontSize: 13)),
          Expanded(
            child: Text.rich(
              TextSpan(children: [
                TextSpan(text: '#$number ', style: TextStyle(color: Colors.grey.shade500, fontSize: 12)),
                TextSpan(text: title, style: const TextStyle(fontSize: 13)),
                TextSpan(text: '  ($repo)', style: TextStyle(color: Colors.grey.shade500, fontSize: 12)),
              ]),
            ),
          ),
        ],
      ),
    );
  }

  Widget _taskTile(dynamic t, bool completed) {
    final name = t['name'] ?? '';
    final status = t['status'] ?? '';
    return Padding(
      padding: const EdgeInsets.only(bottom: 4, left: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(
            completed ? Icons.check_circle : Icons.pending,
            size: 14,
            color: completed ? const Color(0xFF1B873B) : const Color(0xFF9A6700),
          ),
          const SizedBox(width: 6),
          Expanded(
            child: Text.rich(
              TextSpan(children: [
                TextSpan(text: name, style: const TextStyle(fontSize: 13)),
                TextSpan(text: '  [$status]', style: TextStyle(color: Colors.grey.shade500, fontSize: 12)),
              ]),
            ),
          ),
        ],
      ),
    );
  }
}
