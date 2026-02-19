import 'package:flutter/material.dart';
import '../services/api_service.dart';

class DashboardScreen extends StatefulWidget {
  final ApiService api;
  const DashboardScreen({super.key, required this.api});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  bool _loading = false;
  bool _sending = false;
  Map<String, dynamic>? _stats;
  Map<String, dynamic>? _scheduler;
  String? _error;

  @override
  void initState() {
    super.initState();
    _refresh();
  }

  @override
  void didUpdateWidget(DashboardScreen old) {
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
      final results = await Future.wait([
        widget.api.getStats(),
        widget.api.getSchedulerStatus(),
      ]);
      setState(() {
        _stats = results[0];
        _scheduler = results[1];
        _loading = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  Future<void> _sendEod() async {
    setState(() => _sending = true);
    try {
      await widget.api.triggerEod();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('EOD pipeline triggered successfully'),
            backgroundColor: Color(0xFF1B873B),
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: $e'), backgroundColor: Colors.red),
        );
      }
    }
    setState(() => _sending = false);
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Scaffold(
      appBar: AppBar(
        title: const Text('Dashboard'),
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
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            // Send EOD button
            FilledButton.icon(
              onPressed: (_sending || !widget.api.isConfigured) ? null : _sendEod,
              icon: _sending
                  ? const SizedBox(
                      width: 18, height: 18,
                      child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                    )
                  : const Icon(Icons.send),
              label: Text(_sending ? 'Sending...' : 'Send EOD'),
              style: FilledButton.styleFrom(
                minimumSize: const Size.fromHeight(52),
                textStyle: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
              ),
            ),

            const SizedBox(height: 20),

            // Error state
            if (_error != null)
              Card(
                color: cs.errorContainer,
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Row(
                    children: [
                      Icon(Icons.error_outline, color: cs.error),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Text(
                          _error!,
                          style: TextStyle(color: cs.onErrorContainer),
                        ),
                      ),
                    ],
                  ),
                ),
              ),

            // Scheduler card
            if (_scheduler != null) ...[
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Container(
                            width: 12, height: 12,
                            decoration: BoxDecoration(
                              shape: BoxShape.circle,
                              color: _scheduler!['running'] == true
                                  ? const Color(0xFF1B873B)
                                  : Colors.red,
                            ),
                          ),
                          const SizedBox(width: 10),
                          Text(
                            _scheduler!['running'] == true
                                ? 'Scheduler Running'
                                : 'Scheduler Paused',
                            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      _infoRow('Schedule', '${_scheduler!['schedule_time']} ${_scheduler!['timezone']}'),
                      if (_scheduler!['next_run'] != null)
                        _infoRow('Next run', _formatDateTime(_scheduler!['next_run'])),
                      if (_scheduler!['last_run'] != null)
                        _infoRow('Last run', _formatDateTime(_scheduler!['last_run'])),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),
            ],

            // Stats grid
            if (_stats != null)
              GridView.count(
                crossAxisCount: 2,
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                mainAxisSpacing: 12,
                crossAxisSpacing: 12,
                childAspectRatio: 1.4,
                children: [
                  _statCard(context, 'Commits', _stats!['commits'] ?? 0, Icons.commit, cs.primary),
                  _statCard(context, 'PRs', _stats!['prs'] ?? 0, Icons.merge, cs.tertiary),
                  _statCard(context, 'Completed', _stats!['completed'] ?? 0, Icons.check_circle, const Color(0xFF1B873B)),
                  _statCard(context, 'In Progress', _stats!['in_progress'] ?? 0, Icons.pending, const Color(0xFF9A6700)),
                ],
              ),
          ],
        ),
      ),
    );
  }

  Widget _infoRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 4),
      child: Row(
        children: [
          SizedBox(
            width: 80,
            child: Text(label, style: TextStyle(color: Colors.grey.shade600, fontSize: 13)),
          ),
          Expanded(child: Text(value, style: const TextStyle(fontSize: 13))),
        ],
      ),
    );
  }

  Widget _statCard(BuildContext context, String label, int value, IconData icon, Color color) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, color: color, size: 28),
            const SizedBox(height: 8),
            Text(
              '$value',
              style: TextStyle(fontSize: 28, fontWeight: FontWeight.bold, color: color),
            ),
            Text(label, style: TextStyle(color: Colors.grey.shade600, fontSize: 12)),
          ],
        ),
      ),
    );
  }

  String _formatDateTime(String iso) {
    try {
      final dt = DateTime.parse(iso).toLocal();
      final now = DateTime.now();
      final dayStr = dt.day == now.day && dt.month == now.month
          ? 'Today'
          : '${dt.month}/${dt.day}';
      return '$dayStr ${dt.hour.toString().padLeft(2, '0')}:${dt.minute.toString().padLeft(2, '0')}';
    } catch (_) {
      return iso;
    }
  }
}
