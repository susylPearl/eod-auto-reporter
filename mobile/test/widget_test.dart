import 'package:flutter_test/flutter_test.dart';
import 'package:eod_reporter/main.dart';

void main() {
  testWidgets('App launches', (WidgetTester tester) async {
    await tester.pumpWidget(const EODReporterApp());
    expect(find.text('Dashboard'), findsWidgets);
  });
}
