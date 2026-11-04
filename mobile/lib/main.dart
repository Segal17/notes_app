import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:package_info_plus/package_info_plus.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:speech_to_text/speech_to_text.dart' as stt;
import 'package:speech_to_text/speech_recognition_result.dart';

void main() {
  runApp(const NotesApp());
}

class NotesApp extends StatelessWidget {
  const NotesApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Notes Mobile',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.teal),
        useMaterial3: true,
      ),
      home: const NotesScreen(),
    );
  }
}

class NotesScreen extends StatefulWidget {
  const NotesScreen({super.key});

  @override
  State<NotesScreen> createState() => _NotesScreenState();
}

class _NotesScreenState extends State<NotesScreen> {
  static const _prefsKeyServerUrl = 'server_url';
  static const _defaultServerUrl =
      'http://10.0.2.2:8000'; // эмулятор; на телефоне — http://<ip>:8000

  final TextEditingController _controller = TextEditingController();
  final TextEditingController _cultureController = TextEditingController();
  String _serverUrl = _defaultServerUrl;
  bool _sending = false;
  String _appVersion = '?';

  final stt.SpeechToText _speech = stt.SpeechToText();
  bool _speechAvailable = false;
  bool _listening = false;

  @override
  void initState() {
    super.initState();
    _loadServerUrl();
    _loadAppVersion();
  }

  Future<void> _loadAppVersion() async {
    try {
      final info = await PackageInfo.fromPlatform();
      if (mounted) setState(() => _appVersion = '${info.version}+${info.buildNumber}');
    } catch (e) {
      debugPrint('package info error: $e');
    }
  }

  Future<void> _loadServerUrl() async {
    final prefs = await SharedPreferences.getInstance();
    setState(() {
      _serverUrl = prefs.getString(_prefsKeyServerUrl) ?? _defaultServerUrl;
    });
  }

  Future<void> _saveServerUrl(String url) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_prefsKeyServerUrl, url);
    setState(() => _serverUrl = url);
  }

  void _showTopSnack(String msg) {
    final top = MediaQuery.of(context).padding.top + kToolbarHeight + 8;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(msg),
        behavior: SnackBarBehavior.floating,
        margin: EdgeInsets.only(top: top, left: 16, right: 16),
      ),
    );
  }

  Future<void> _openSettings() async {
    final ctrl = TextEditingController(text: _serverUrl);
    final result = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Настройки'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Версия приложения: $_appVersion',
                style: Theme.of(ctx).textTheme.bodySmall),
            const SizedBox(height: 12),
            TextField(
              controller: ctrl,
              keyboardType: TextInputType.url,
              decoration: const InputDecoration(
                labelText: 'URL сервера',
                hintText: 'http://192.168.1.10:8000',
              ),
            ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Отмена')),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, ctrl.text.trim()),
            child: const Text('Сохранить'),
          ),
        ],
      ),
    );
    if (result != null && result.isNotEmpty) {
      await _saveServerUrl(result);
      if (mounted) _showTopSnack('URL сохранён: $result');
    }
  }

  Future<void> _initSpeech() async {
    _speechAvailable = await _speech.initialize(
      onError: (e) => debugPrint('speech error: $e'),
      onStatus: (s) => debugPrint('speech status: $s'),
    );
    if (mounted) setState(() {});
  }

  Future<void> _onMicPressed() async {
    if (!_speechAvailable) {
      await _initSpeech();
      if (!_speechAvailable) {
        if (mounted) {
          _showTopSnack('Голос недоступен (нет разрешения/движка)');
        }
        return;
      }
    }
    if (_listening) {
      await _speech.stop();
      if (mounted) setState(() => _listening = false);
      return;
    }
    setState(() => _listening = true);
    await _speech.listen(
      onResult: (SpeechRecognitionResult r) {
        if (r.finalResult) {
          final text = r.recognizedWords.trim();
          if (text.isNotEmpty) {
            final cur = _controller.text;
            _controller.text = cur.isEmpty ? text : '$cur $text';
            _controller.selection =
                TextSelection.collapsed(offset: _controller.text.length);
          }
        }
      },
      listenOptions: stt.SpeechListenOptions(localeId: 'ru_RU'),
    );
  }

  Future<void> _onSendPressed() async {
    final description = _controller.text.trim();
    final cultureRaw = _cultureController.text.trim();
    final String? culture = cultureRaw.isEmpty ? null : cultureRaw;
    if (description.isEmpty) {
      _showTopSnack('Пустая заметка');
      return;
    }
    setState(() => _sending = true);
    try {
      final uri = Uri.parse('$_serverUrl/api/notes');
      final resp = await http
          .post(
            uri,
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode({'description': description, 'culture': culture}),
          )
          .timeout(const Duration(seconds: 15));
      if (resp.statusCode >= 200 && resp.statusCode < 300) {
        _controller.clear();
        _cultureController.clear();
        if (mounted) _showTopSnack('Отправлено (${resp.statusCode})');
      } else {
        if (mounted) _showTopSnack('Ошибка ${resp.statusCode}: ${resp.body}');
      }
    } catch (e) {
      if (mounted) _showTopSnack('Сеть/ошибка: $e');
    } finally {
      if (mounted) setState(() => _sending = false);
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    _cultureController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Заметки'),
        actions: [
          IconButton(
            tooltip: 'Настройки',
            icon: const Icon(Icons.settings),
            onPressed: _openSettings,
          ),
        ],
      ),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              'Сервер: $_serverUrl',
              style: Theme.of(context).textTheme.bodySmall,
            ),
            const SizedBox(height: 8),
            Expanded(
              child: TextField(
                controller: _controller,
                maxLines: null,
                expands: true,
                textAlignVertical: TextAlignVertical.top,
                decoration: const InputDecoration(
                  border: OutlineInputBorder(),
                  hintText: 'Текст заметки…',
                ),
              ),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _cultureController,
              decoration: const InputDecoration(
                border: OutlineInputBorder(),
                labelText: 'Культура (необязательно)',
                hintText: 'например: пшеница',
              ),
              textInputAction: TextInputAction.done,
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                IconButton.filledTonal(
                  onPressed: _onMicPressed,
                  icon: Icon(_listening ? Icons.stop : Icons.mic),
                  tooltip: _listening ? 'Стоп' : 'Голос',
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: FilledButton.icon(
                    onPressed: _sending ? null : _onSendPressed,
                    icon: const Icon(Icons.send),
                    label: _sending
                        ? const SizedBox(
                            width: 16, height: 16,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Text('Отправить'),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
