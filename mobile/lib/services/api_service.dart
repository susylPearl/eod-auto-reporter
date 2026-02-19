import 'dart:convert';
import 'package:http/http.dart' as http;

class ApiService {
  final String baseUrl;

  ApiService({required this.baseUrl});

  bool get isConfigured => baseUrl.isNotEmpty;

  Uri _uri(String path) => Uri.parse('$baseUrl$path');

  Future<Map<String, dynamic>> getHealth() async {
    final res = await http.get(_uri('/health')).timeout(
      const Duration(seconds: 10),
    );
    if (res.statusCode == 200) return jsonDecode(res.body);
    throw Exception('Health check failed: ${res.statusCode}');
  }

  Future<Map<String, dynamic>> getStats() async {
    final res = await http.get(_uri('/api/stats')).timeout(
      const Duration(seconds: 15),
    );
    if (res.statusCode == 200) return jsonDecode(res.body);
    throw Exception('Stats fetch failed: ${res.statusCode}');
  }

  Future<Map<String, dynamic>> getActivity() async {
    final res = await http.get(_uri('/api/activity')).timeout(
      const Duration(seconds: 20),
    );
    if (res.statusCode == 200) return jsonDecode(res.body);
    throw Exception('Activity fetch failed: ${res.statusCode}');
  }

  Future<Map<String, dynamic>> getSchedulerStatus() async {
    final res = await http.get(_uri('/api/scheduler')).timeout(
      const Duration(seconds: 10),
    );
    if (res.statusCode == 200) return jsonDecode(res.body);
    throw Exception('Scheduler status failed: ${res.statusCode}');
  }

  Future<Map<String, dynamic>> triggerEod() async {
    final res = await http.post(_uri('/trigger-eod')).timeout(
      const Duration(seconds: 10),
    );
    if (res.statusCode == 200) return jsonDecode(res.body);
    throw Exception('Trigger failed: ${res.statusCode}');
  }
}
