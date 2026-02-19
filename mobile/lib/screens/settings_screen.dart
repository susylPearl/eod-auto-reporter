import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../services/api_service.dart';

class SettingsScreen extends StatefulWidget {
  final String currentUrl;
  final ValueChanged<String> onUrlChanged;

  const SettingsScreen({
    super.key,
    required this.currentUrl,
    required this.onUrlChanged,
  });

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  late TextEditingController _urlController;
  bool _testing = false;
  String? _testResult;
  bool? _testOk;

  @override
  void initState() {
    super.initState();
    _urlController = TextEditingController(text: widget.currentUrl);
  }

  @override
  void dispose() {
    _urlController.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    final url = _urlController.text.trim().replaceAll(RegExp(r'/+$'), '');
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('base_url', url);
    widget.onUrlChanged(url);
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Server URL saved'), backgroundColor: Color(0xFF1B873B)),
      );
    }
  }

  Future<void> _test() async {
    final url = _urlController.text.trim().replaceAll(RegExp(r'/+$'), '');
    if (url.isEmpty) {
      setState(() {
        _testResult = 'Please enter a URL first';
        _testOk = false;
      });
      return;
    }
    setState(() {
      _testing = true;
      _testResult = null;
    });
    try {
      final api = ApiService(baseUrl: url);
      final health = await api.getHealth();
      setState(() {
        _testResult = 'Connected! Version ${health['version']}';
        _testOk = true;
        _testing = false;
      });
    } catch (e) {
      setState(() {
        _testResult = 'Connection failed: ${e.toString().substring(0, (e.toString().length).clamp(0, 100))}';
        _testOk = false;
        _testing = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Scaffold(
      appBar: AppBar(title: const Text('Settings')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // Server URL
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Icon(Icons.dns, color: cs.primary, size: 20),
                      const SizedBox(width: 8),
                      Text('Server Connection',
                        style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
                    ],
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'Enter the URL of your EOD Reporter backend (deployed on Render or running locally).',
                    style: TextStyle(color: Colors.grey.shade600, fontSize: 13),
                  ),
                  const SizedBox(height: 16),
                  TextField(
                    controller: _urlController,
                    decoration: InputDecoration(
                      labelText: 'Server URL',
                      hintText: 'https://eod-auto-reporter.onrender.com',
                      border: const OutlineInputBorder(),
                      prefixIcon: const Icon(Icons.link),
                      suffixIcon: IconButton(
                        icon: const Icon(Icons.clear),
                        onPressed: () => _urlController.clear(),
                      ),
                    ),
                    keyboardType: TextInputType.url,
                    autocorrect: false,
                  ),
                  const SizedBox(height: 16),
                  Row(
                    children: [
                      Expanded(
                        child: FilledButton.tonalIcon(
                          onPressed: _testing ? null : _test,
                          icon: _testing
                              ? const SizedBox(
                                  width: 16, height: 16,
                                  child: CircularProgressIndicator(strokeWidth: 2),
                                )
                              : const Icon(Icons.wifi_find),
                          label: Text(_testing ? 'Testing...' : 'Test Connection'),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: FilledButton.icon(
                          onPressed: _save,
                          icon: const Icon(Icons.save),
                          label: const Text('Save'),
                        ),
                      ),
                    ],
                  ),
                  if (_testResult != null) ...[
                    const SizedBox(height: 12),
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: _testOk == true
                            ? const Color(0xFF1B873B).withOpacity(0.1)
                            : Colors.red.withOpacity(0.1),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Row(
                        children: [
                          Icon(
                            _testOk == true ? Icons.check_circle : Icons.error,
                            color: _testOk == true ? const Color(0xFF1B873B) : Colors.red,
                            size: 18,
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              _testResult!,
                              style: TextStyle(
                                color: _testOk == true ? const Color(0xFF1B873B) : Colors.red,
                                fontSize: 13,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ),

          const SizedBox(height: 16),

          // Info card
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Icon(Icons.info_outline, color: cs.primary, size: 20),
                      const SizedBox(width: 8),
                      Text('How it works',
                        style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
                    ],
                  ),
                  const SizedBox(height: 12),
                  _bulletPoint('Your tokens and API keys are configured on the server (Render environment variables)'),
                  _bulletPoint('This mobile app connects to your server to view activity and trigger EOD reports'),
                  _bulletPoint('The scheduler runs on the server — no need to keep this app open'),
                  _bulletPoint('All data is fetched in real-time from GitHub, ClickUp, and Slack'),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _bulletPoint(String text) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Padding(
            padding: EdgeInsets.only(top: 6),
            child: Icon(Icons.circle, size: 6, color: Colors.grey),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(text, style: TextStyle(color: Colors.grey.shade700, fontSize: 13)),
          ),
        ],
      ),
    );
  }
}
