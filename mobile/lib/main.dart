import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'screens/dashboard_screen.dart';
import 'screens/activity_screen.dart';
import 'screens/settings_screen.dart';
import 'screens/support_screen.dart';
import 'services/api_service.dart';

void main() {
  runApp(const EODReporterApp());
}

class EODReporterApp extends StatelessWidget {
  const EODReporterApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'EOD Reporter',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        useMaterial3: true,
        colorSchemeSeed: const Color(0xFF6750A4),
        brightness: Brightness.light,
      ),
      darkTheme: ThemeData(
        useMaterial3: true,
        colorSchemeSeed: const Color(0xFF6750A4),
        brightness: Brightness.dark,
      ),
      themeMode: ThemeMode.system,
      home: const MainShell(),
    );
  }
}

class MainShell extends StatefulWidget {
  const MainShell({super.key});

  @override
  State<MainShell> createState() => _MainShellState();
}

class _MainShellState extends State<MainShell> {
  int _currentIndex = 0;
  String _baseUrl = '';

  @override
  void initState() {
    super.initState();
    _loadBaseUrl();
  }

  Future<void> _loadBaseUrl() async {
    final prefs = await SharedPreferences.getInstance();
    setState(() {
      _baseUrl = prefs.getString('base_url') ?? '';
    });
  }

  void _onBaseUrlChanged(String url) {
    setState(() => _baseUrl = url);
  }

  @override
  Widget build(BuildContext context) {
    final api = ApiService(baseUrl: _baseUrl);
    final screens = [
      DashboardScreen(api: api),
      ActivityScreen(api: api),
      SettingsScreen(
        currentUrl: _baseUrl,
        onUrlChanged: _onBaseUrlChanged,
      ),
      const SupportScreen(),
    ];

    return Scaffold(
      body: IndexedStack(index: _currentIndex, children: screens),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _currentIndex,
        onDestinationSelected: (i) => setState(() => _currentIndex = i),
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.dashboard_outlined),
            selectedIcon: Icon(Icons.dashboard),
            label: 'Dashboard',
          ),
          NavigationDestination(
            icon: Icon(Icons.list_alt_outlined),
            selectedIcon: Icon(Icons.list_alt),
            label: 'Activity',
          ),
          NavigationDestination(
            icon: Icon(Icons.settings_outlined),
            selectedIcon: Icon(Icons.settings),
            label: 'Settings',
          ),
          NavigationDestination(
            icon: Icon(Icons.help_outline),
            selectedIcon: Icon(Icons.help),
            label: 'Support',
          ),
        ],
      ),
    );
  }
}
