import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:patient_app/core/providers/auth_provider.dart';
import 'package:patient_app/core/providers/patient_provider.dart';
import 'package:patient_app/core/providers/localization_provider.dart';
import 'package:patient_app/main.dart';

void main() {
  testWidgets('App loads smoke test', (WidgetTester tester) async {
    final locProvider = LocalizationProvider();
    await locProvider.init();

    final authProvider = AuthProvider();

    await tester.pumpWidget(
      MultiProvider(
        providers: [
          ChangeNotifierProvider.value(value: authProvider),
          ChangeNotifierProvider(create: (_) => PatientProvider()),
          ChangeNotifierProvider.value(value: locProvider),
        ],
        child: const CogniCompanionPatientApp(),
      ),
    );

    await tester.pump();

    // Verify header brand renders
    expect(find.textContaining('CogniCompanion'), findsWidgets);
  });
}
