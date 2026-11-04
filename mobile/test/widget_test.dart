import 'package:flutter_test/flutter_test.dart';
import 'package:notes_mobile/main.dart';

void main() {
  testWidgets('NotesApp renders', (WidgetTester tester) async {
    await tester.pumpWidget(const NotesApp());
    expect(find.text('Заметки'), findsOneWidget);
  });
}
