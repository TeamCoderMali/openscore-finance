import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../../core/services/api_service.dart';
import '../../core/services/auth_service.dart';
import '../../core/theme/app_theme.dart';
import '../../shared/widgets/shared_widgets.dart';

class VoiceAssistantScreen extends StatefulWidget {
  const VoiceAssistantScreen({super.key});

  @override
  State<VoiceAssistantScreen> createState() => _VoiceAssistantScreenState();
}

class _VoiceAssistantScreenState extends State<VoiceAssistantScreen>
    with TickerProviderStateMixin {
  final _api = ApiService();
  final _queryCtrl = TextEditingController();
  final _scrollCtrl = ScrollController();

  bool _loading = false;
  bool _isListening = false;
  int? _speakingMessageIndex;
  String _selectedLanguage = 'fr'; // 'fr' or 'bm'

  // Diagnostic Mode Interactif Pas-à-Pas
  int _diagnosticStep = 0; // 0 = standard chat, 1 = revenue, 2 = expenses, 3 = debts, 4 = guarantees
  double _diagRevenue = 350000;
  double _diagExpenses = 120000;
  double _diagDebts = 0;

  late final AnimationController _waveCtrl;

  final List<_ChatMessage> _messages = [
    _ChatMessage(
      text:
          "Bonjour ! Je suis votre Assistant IA OpenScore Finance propulsé par Google Gemini.\n\n"
          "Je vous conseille sur le calcul de votre score de solvabilité (/100), l'enregistrement de vos garanties (terrains, motos, stocks), "
          "la maîtrise de votre ratio d'endettement (règle des 40%) et vos remboursements par Mobile Money (Orange Money, Wave). "
          "Posez-moi n'importe quelle question, même spécifique ou imprévue !",
      isBot: true,
      timestamp: DateTime.now(),
      suggestions: [
        "Comment est calculé mon score /100 ?",
        "Quelles garanties puis-je enregistrer ?",
        "Comment rembourser par Orange Money ou Wave ?",
        "Quelle est la règle des 40% d'endettement ?",
      ],
      intent: "GENERAL_ASSIST",
    ),
  ];

  final List<_TopicChip> _topicChips = const [
    _TopicChip(
      icon: Icons.speed_rounded,
      label: "Score /100",
      query: "Comment est calculé mon score de solvabilité sur 100 points ?",
      color: AppTheme.primaryBlue,
    ),
    _TopicChip(
      icon: Icons.shield_outlined,
      label: "Garanties & Biens",
      query: "Quelles garanties (terrains, motos, matériel) sont acceptées ?",
      color: AppTheme.emerald,
    ),
    _TopicChip(
      icon: Icons.account_balance_wallet_outlined,
      label: "Dettes & Seuil 40%",
      query: "Comment déclarer mes dettes et quelle est la règle des 40% ?",
      color: AppTheme.amber,
    ),
    _TopicChip(
      icon: Icons.phone_android_rounded,
      label: "Orange / Wave",
      query: "Comment effectuer les remboursements par Orange Money ou Wave ?",
      color: AppTheme.primaryBlue,
    ),
    _TopicChip(
      icon: Icons.timelapse_rounded,
      label: "Délais & Comité",
      query: "Combien de temps faut-il pour avoir la décision du comité de crédit ?",
      color: AppTheme.slate700,
    ),
    _TopicChip(
      icon: Icons.percent_rounded,
      label: "Taux & Frais",
      query: "Quel est le taux d'intérêt et y a-t-il des frais de dossier ?",
      color: AppTheme.rose,
    ),
    _TopicChip(
      icon: Icons.storefront_rounded,
      label: "Sugu (Commerce)",
      query: "Je veux un crédit pour mon commerce au Grand Marché",
      color: AppTheme.amber,
    ),
    _TopicChip(
      icon: Icons.agriculture_rounded,
      label: "Sɛnɛ (Agriculture)",
      query: "Sɛnɛ — Crédit pour maraîchage avec différé de récolte",
      color: AppTheme.emerald,
    ),
    _TopicChip(
      icon: Icons.translate_rounded,
      label: "Bamanankan",
      query: "I ni ce ! N b'a fɛ ka juru ta sugu baara kama",
      color: AppTheme.primaryBlue,
    ),
  ];

  @override
  void initState() {
    super.initState();
    _waveCtrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 650),
    );
  }

  @override
  void dispose() {
    _queryCtrl.dispose();
    _scrollCtrl.dispose();
    _waveCtrl.dispose();
    super.dispose();
  }

  void _startDiagnostic() {
    setState(() {
      _diagnosticStep = 1;
      _messages.add(
        _ChatMessage(
          text: "🚀 Diagnostic de Solvabilité Pas-à-Pas (IA)\n\n"
              "Étape 1/4 : Quel est votre revenu mensuel moyen (chiffre d'affaires net ou salaire) ?",
          isBot: true,
          timestamp: DateTime.now(),
          suggestions: [
            "200 000 FCFA / mois",
            "350 000 FCFA / mois",
            "600 000 FCFA / mois",
            "1 000 000 FCFA / mois",
          ],
          intent: "DIAG_STEP_1",
        ),
      );
    });
    _scrollToBottom();
  }

  Future<void> _send(String query) async {
    final clean = query.trim();
    if (clean.isEmpty) return;

    if (clean.toLowerCase().contains("recommencer le diagnostic") ||
        clean.toLowerCase().contains("démarrer le diagnostic")) {
      _queryCtrl.clear();
      _startDiagnostic();
      return;
    }

    if (_diagnosticStep > 0) {
      _queryCtrl.clear();
      setState(() {
        _isListening = false;
        _waveCtrl.stop();
        _messages.add(_ChatMessage(
          text: clean,
          isBot: false,
          timestamp: DateTime.now(),
        ));
      });

      if (_diagnosticStep == 1) {
        final numMatch = RegExp(r'\d[\d\s]*').firstMatch(clean);
        if (numMatch != null) {
          _diagRevenue = double.tryParse(numMatch.group(0)!.replaceAll(' ', '')) ?? 350000;
        }
        _diagnosticStep = 2;
        setState(() {
          _messages.add(_ChatMessage(
            text: "Étape 2/4 : Quelles sont vos charges et dépenses mensuelles moyennes (loyer, alimentation, factures, intrants) ?",
            isBot: true,
            timestamp: DateTime.now(),
            suggestions: [
              "60 000 FCFA",
              "120 000 FCFA",
              "200 000 FCFA",
              "350 000 FCFA",
            ],
            intent: "DIAG_STEP_2",
          ));
        });
      } else if (_diagnosticStep == 2) {
        final numMatch = RegExp(r'\d[\d\s]*').firstMatch(clean);
        if (numMatch != null) {
          _diagExpenses = double.tryParse(numMatch.group(0)!.replaceAll(' ', '')) ?? 120000;
        }
        _diagnosticStep = 3;
        setState(() {
          _messages.add(_ChatMessage(
            text: "Étape 3/4 : Avez-vous des prêts ou mensualités en cours (banques, microfinance ou tontines) ?",
            isBot: true,
            timestamp: DateTime.now(),
            suggestions: [
              "Aucune dette en cours (0 FCFA)",
              "Dette de 50 000 FCFA",
              "Dette de 150 000 FCFA",
            ],
            intent: "DIAG_STEP_3",
          ));
        });
      } else if (_diagnosticStep == 3) {
        final numMatch = RegExp(r'\d[\d\s]*').firstMatch(clean);
        if (numMatch != null && !clean.toLowerCase().contains('aucun')) {
          _diagDebts = double.tryParse(numMatch.group(0)!.replaceAll(' ', '')) ?? 0;
        } else {
          _diagDebts = 0;
        }
        _diagnosticStep = 4;
        setState(() {
          _messages.add(_ChatMessage(
            text: "Étape 4/4 : De quelles garanties disposez-vous pour consolider votre dossier ?",
            isBot: true,
            timestamp: DateTime.now(),
            suggestions: [
              "Moto / Véhicule avec carte grise",
              "Titre de propriété / Lettre d'attribution",
              "Caution solidaire / Avaliste certifié",
              "Dépôt de garantie épargne nantie (DGA)",
            ],
            intent: "DIAG_STEP_4",
          ));
        });
      } else if (_diagnosticStep == 4) {
        _diagnosticStep = 0;
        final netIncome = math.max(0.0, _diagRevenue - _diagExpenses);
        final debtRatio = _diagRevenue > 0 ? ((_diagDebts + (_diagRevenue * 0.15)) / _diagRevenue) * 100 : 25.0;
        int score = 75;
        if (debtRatio <= 30) {
          score += 12;
        } else if (debtRatio <= 40) {
          score += 5;
        } else {
          score -= 15;
        }

        if (netIncome > 200000) {
          score += 8;
        }
        if (clean.toLowerCase().contains('titre') || clean.toLowerCase().contains('épargne') || clean.toLowerCase().contains('dga')) {
          score += 7;
        }
        score = score.clamp(35, 96);

        final risk = score >= 80 ? 'Faible (Favorable)' : (score >= 60 ? 'Modéré (Acceptable)' : 'Élevé (Renforcer garanties)');
        final maxCapacity = (netIncome * 0.40 * 12).round();

        setState(() {
          _messages.add(_ChatMessage(
            text: "📊 RÉSULTAT DE VOTRE DIAGNOSTIC SOLVABILITÉ :\n\n"
                "• Score estimé : $score / 100\n"
                "• Niveau de risque : $risk\n"
                "• Reste à vivre mensuel : ${formatFCFA(netIncome)}\n"
                "• Ratio d'endettement : ${debtRatio.toStringAsFixed(1)}% (Plafond prudentiel BCEAO : 40%)\n"
                "• Capacité d'emprunt indicative : ${formatFCFA(maxCapacity.toDouble())} sur 12 mois\n\n"
                "💡 Recommandation de l'IA : Votre profil présente une bonne assise financière. Vous pouvez soumettre votre dossier directement auprès de votre antenne Kafo Jiginew.",
            isBot: true,
            timestamp: DateTime.now(),
            suggestions: [
              "Comment faire certifier mes garanties ?",
              "Recommencer le diagnostic",
            ],
            intent: "DIAG_RESULT",
          ));
        });
      }
      _scrollToBottom();
      return;
    }

    _queryCtrl.clear();
    setState(() {
      _isListening = false;
      _waveCtrl.stop();
      _messages.add(_ChatMessage(
        text: clean,
        isBot: false,
        timestamp: DateTime.now(),
      ));
      _loading = true;
    });
    _scrollToBottom();

    try {
      final data = await _api.voiceQuery(
        clean,
        language: _selectedLanguage,
      );

      final responseText = data['response_text'] ??
          "Je reste à votre entière disposition pour tout renseignement.";
      final suggestions = List<String>.from(data['suggestions'] ?? []);
      final intent = data['detected_intent'];

      if (mounted) {
        setState(() {
          _messages.add(_ChatMessage(
            text: responseText,
            isBot: true,
            timestamp: DateTime.now(),
            suggestions: suggestions,
            intent: intent,
          ));
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() {
          _messages.add(_ChatMessage(
            text:
                "Je suis temporairement indisponible pour cause de connexion. "
                "Veuillez vérifier votre réseau et réessayez dans un instant.",
            isBot: true,
            timestamp: DateTime.now(),
            suggestions: [
              "Comment est calculé mon score /100 ?",
              "Quelles garanties puis-je enregistrer ?",
            ],
            intent: "OFFLINE",
          ));
        });
      }
    } finally {
      if (mounted) {
        setState(() => _loading = false);
        _scrollToBottom();
      }
    }
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollCtrl.hasClients) {
        _scrollCtrl.animateTo(
          _scrollCtrl.position.maxScrollExtent + 120,
          duration: const Duration(milliseconds: 350),
          curve: Curves.easeOutCubic,
        );
      }
    });
  }

  void _toggleListening() {
    setState(() {
      _isListening = !_isListening;
      if (_isListening) {
        _waveCtrl.repeat(reverse: true);
      } else {
        _waveCtrl.stop();
      }
    });
  }

  void _toggleSpeaking(int index) {
    setState(() {
      if (_speakingMessageIndex == index) {
        _speakingMessageIndex = null;
      } else {
        _speakingMessageIndex = index;
        // Auto-stop speech simulation after 6 seconds
        Future.delayed(const Duration(seconds: 6), () {
          if (mounted && _speakingMessageIndex == index) {
            setState(() => _speakingMessageIndex = null);
          }
        });
      }
    });
  }

  void _clearChat() {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text("Effacer la conversation ?"),
        content: const Text(
          "Voulez-vous réinitialiser le fil de discussion avec l'Assistant ?",
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text("Annuler"),
          ),
          ElevatedButton(
            onPressed: () {
              Navigator.pop(ctx);
              setState(() {
                _messages.clear();
                _messages.add(
                  _ChatMessage(
                    text:
                        "Conversation réinitialisée. Posez votre question en français ou en bambara.",
                    isBot: true,
                    timestamp: DateTime.now(),
                    suggestions: [
                      "Comment calculer mon score /100 ?",
                      "Quelles garanties ajouter ?",
                      "Comment rembourser par Wave ?",
                    ],
                  ),
                );
              });
            },
            child: const Text("Effacer"),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final auth = context.watch<AuthService>();
    final userName = auth.currentUser?.fullName.split(' ').first;

    return Scaffold(
      backgroundColor: isDark ? AppTheme.darkBg : const Color(0xFFF8FAFC),
      body: SafeArea(
        child: Column(
          children: [
            // ── TOP HEADER (Solid Brand Blue Chart — Zero Overflow) ───
            _buildCleanHeader(isDark),

            // ── TOPIC CHIPS BAR ───────────────────────────────────────
            _buildTopicChipsBar(isDark),

            // ── CHAT STREAM ───────────────────────────────────────────
            Expanded(
              child: _messages.length == 1
                  ? _buildWelcomeExperience(isDark, userName)
                  : _buildMessagesList(isDark),
            ),

            // ── ACTIVE VOICE WAVEFORM PANEL ───────────────────────────
            if (_isListening) _buildVoiceListeningPanel(isDark),

            // ── BOTTOM INPUT BAR (Clean Solid Primary Dock) ───────────
            _buildInputDock(isDark),
          ],
        ),
      ),
    );
  }

  // ── 1. Clean Header (Solid Brand Blue, No Gradients, No Overflow) ─────────
  Widget _buildCleanHeader(bool isDark) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: isDark ? AppTheme.darkSurface : Colors.white,
        border: Border(
          bottom: BorderSide(
            color: isDark ? AppTheme.darkBorder : AppTheme.slate200,
          ),
        ),
      ),
      child: Row(
        children: [
          // Solid Brand Avatar (No Gradient, Professional Support Icon)
          Container(
            width: 38,
            height: 38,
            decoration: BoxDecoration(
              color: AppTheme.primaryBlue,
              borderRadius: BorderRadius.circular(10),
            ),
            child: const Icon(
              Icons.support_agent_rounded,
              color: Colors.white,
              size: 22,
            ),
          ),
          const SizedBox(width: 10),

          // Title & Status (Flexible to avoid any RenderFlex overflow)
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Flexible(
                      child: Text(
                        "Assistant Vocal IA",
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.w800,
                          color: isDark ? Colors.white : AppTheme.slate900,
                        ),
                      ),
                    ),
                    const SizedBox(width: 4),
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 5, vertical: 1.5),
                      decoration: BoxDecoration(
                        color: AppTheme.primaryBlue.withValues(alpha: 0.1),
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: const Text(
                        "Gemini",
                        style: TextStyle(
                          fontSize: 9,
                          fontWeight: FontWeight.w800,
                          color: AppTheme.primaryBlue,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 2),
                Row(
                  children: [
                    Container(
                      width: 6,
                      height: 6,
                      decoration: const BoxDecoration(
                        color: Color(0xFF10B981),
                        shape: BoxShape.circle,
                      ),
                    ),
                    const SizedBox(width: 4),
                    Expanded(
                      child: Text(
                        _selectedLanguage == 'fr'
                            ? "En direct • Bilingue"
                            : "Bamanankan • Dɛmɛ",
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          fontSize: 11,
                          color: isDark ? AppTheme.slate400 : AppTheme.slate500,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),

          const SizedBox(width: 4),

          // Compact Language Pill
          GestureDetector(
            onTap: () {
              setState(() {
                _selectedLanguage = _selectedLanguage == 'fr' ? 'bm' : 'fr';
              });
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(
                  content: Text(
                    _selectedLanguage == 'fr'
                        ? "Langue : Français activé"
                        : "Kan : Bamanankan kɔnɔna",
                  ),
                  duration: const Duration(seconds: 1),
                  behavior: SnackBarBehavior.floating,
                ),
              );
            },
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: BoxDecoration(
                color: isDark ? AppTheme.darkCard : AppTheme.slate100,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(
                  color: isDark ? AppTheme.darkBorder : AppTheme.slate300,
                ),
              ),
              child: Text(
                _selectedLanguage == 'fr' ? "FR" : "BM",
                style: const TextStyle(
                  fontSize: 10,
                  fontWeight: FontWeight.w800,
                  color: AppTheme.primaryBlue,
                ),
              ),
            ),
          ),

          // Reset Button
          IconButton(
            padding: EdgeInsets.zero,
            constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
            icon: Icon(
              Icons.refresh_rounded,
              size: 18,
              color: isDark ? AppTheme.slate400 : AppTheme.slate600,
            ),
            tooltip: "Réinitialiser",
            onPressed: _clearChat,
          ),
        ],
      ),
    );
  }

  // ── 2. Topic Chips Bar ───────────────────────────────────────────────────
  Widget _buildTopicChipsBar(bool isDark) {
    return Container(
      height: 46,
      decoration: BoxDecoration(
        color: isDark ? AppTheme.darkSurface : Colors.white,
        border: Border(
          bottom: BorderSide(
            color: isDark ? AppTheme.darkBorder : AppTheme.slate200,
          ),
        ),
      ),
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        itemCount: _topicChips.length,
        separatorBuilder: (_, __) => const SizedBox(width: 8),
        itemBuilder: (ctx, i) {
          final t = _topicChips[i];
          return GestureDetector(
            onTap: () => _send(t.query),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 3),
              decoration: BoxDecoration(
                color: t.color.withValues(alpha: isDark ? 0.15 : 0.08),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(
                  color: t.color.withValues(alpha: isDark ? 0.35 : 0.25),
                ),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(t.icon, size: 13, color: t.color),
                  const SizedBox(width: 5),
                  Text(
                    t.label,
                    style: TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.w700,
                      color: t.color,
                    ),
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }

  // ── 3. Welcome Experience (Solid Brand Blue, No Gradients, No Stickers) ──
  Widget _buildWelcomeExperience(bool isDark, String? userName) {
    return SingleChildScrollView(
      controller: _scrollCtrl,
      padding: const EdgeInsets.all(20),
      child: Column(
        children: [
          const SizedBox(height: 12),

          // Solid Brand Blue Centerpiece (No Radial, No Gradients, Clean Icon)
          Container(
            width: 68,
            height: 68,
            decoration: const BoxDecoration(
              color: AppTheme.primaryBlue,
              shape: BoxShape.circle,
            ),
            child: const Icon(
              Icons.support_agent_rounded,
              color: Colors.white,
              size: 36,
            ),
          ),

          const SizedBox(height: 14),

          // Greeting Text
          Text(
            userName != null
                ? "Bonjour $userName !"
                : "Bienvenue sur OpenScore AI",
            textAlign: TextAlign.center,
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.w800,
              color: isDark ? Colors.white : AppTheme.slate900,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            "Votre conseiller financier bilingue (Français & Bambara). "
            "Posez toutes vos questions sur votre dossier de crédit, le score /100 et les garanties.",
            textAlign: TextAlign.center,
            style: TextStyle(
              fontSize: 12,
              color: isDark ? AppTheme.slate400 : AppTheme.slate600,
              height: 1.4,
            ),
          ),

          const SizedBox(height: 18),

          // ── Diagnostic Express Pas-à-Pas (IA) ─────────────────────────
          GestureDetector(
            onTap: _startDiagnostic,
            child: Container(
              width: double.infinity,
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: AppTheme.primaryBlue,
                borderRadius: BorderRadius.circular(12),
                boxShadow: [
                  BoxShadow(
                    color: AppTheme.primaryBlue.withValues(alpha: 0.25),
                    blurRadius: 10,
                    offset: const Offset(0, 4),
                  ),
                ],
              ),
              child: Row(
                children: [
                  Container(
                    width: 38,
                    height: 38,
                    decoration: BoxDecoration(
                      color: Colors.white.withValues(alpha: 0.2),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: const Icon(Icons.flash_on_rounded, color: Colors.white, size: 22),
                  ),
                  const SizedBox(width: 12),
                  const Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          "Diagnostic Express du Score /100",
                          style: TextStyle(
                            fontSize: 13,
                            fontWeight: FontWeight.w800,
                            color: Colors.white,
                          ),
                        ),
                        SizedBox(height: 2),
                        Text(
                          "Simulez votre éligibilité en 4 questions interactives",
                          style: TextStyle(
                            fontSize: 11,
                            color: Colors.white70,
                          ),
                        ),
                      ],
                    ),
                  ),
                  const Icon(Icons.arrow_forward_ios_rounded, color: Colors.white70, size: 14),
                ],
              ),
            ),
          ),

          const SizedBox(height: 20),

          // 4 Action Cards in Grid (Solid Brand Chart Colors)
          Text(
            "SUGGESTIONS FRÉQUENTES",
            style: TextStyle(
              fontSize: 10,
              fontWeight: FontWeight.w800,
              letterSpacing: 1.0,
              color: isDark ? AppTheme.slate400 : AppTheme.slate500,
            ),
          ),
          const SizedBox(height: 10),

          GridView.count(
            crossAxisCount: 2,
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            crossAxisSpacing: 10,
            mainAxisSpacing: 10,
            childAspectRatio: 1.3,
            children: [
              _buildFeatureCard(
                isDark: isDark,
                icon: Icons.speed_rounded,
                color: AppTheme.primaryBlue,
                title: "Score /100",
                desc: "Comprendre le calcul et les 5 critères",
                onTap: () => _send("Comment est calculé mon score /100 ?"),
              ),
              _buildFeatureCard(
                isDark: isDark,
                icon: Icons.shield_rounded,
                color: AppTheme.emerald,
                title: "Garanties",
                desc: "Titres, motos et stocks marchands",
                onTap: () => _send("Quelles garanties puis-je enregistrer ?"),
              ),
              _buildFeatureCard(
                isDark: isDark,
                icon: Icons.payment_rounded,
                color: AppTheme.primaryBlue,
                title: "Wave & Orange",
                desc: "Remboursements mobiles et reçus",
                onTap: () => _send("Comment rembourser par Orange Money ou Wave ?"),
              ),
              _buildFeatureCard(
                isDark: isDark,
                icon: Icons.pie_chart_outline_rounded,
                color: AppTheme.amber,
                title: "Règle des 40%",
                desc: "Seuil d'endettement maximal",
                onTap: () => _send("Quelle est la règle des 40% d'endettement ?"),
              ),
            ],
          ),

          const SizedBox(height: 20),

          // First Message from Bot
          _buildMessageBubble(_messages.first, 0, isDark),
        ],
      ),
    );
  }

  Widget _buildFeatureCard({
    required bool isDark,
    required IconData icon,
    required Color color,
    required String title,
    required String desc,
    required VoidCallback onTap,
  }) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(12),
      child: Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: isDark ? AppTheme.darkCard : Colors.white,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: isDark ? AppTheme.darkBorder : AppTheme.slate200,
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              padding: const EdgeInsets.all(6),
              decoration: BoxDecoration(
                color: color.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Icon(icon, color: color, size: 16),
            ),
            const SizedBox(height: 6),
            Text(
              title,
              style: TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w800,
                color: isDark ? Colors.white : AppTheme.slate900,
              ),
            ),
            const SizedBox(height: 2),
            Text(
              desc,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                fontSize: 10,
                color: isDark ? AppTheme.slate400 : AppTheme.slate500,
                height: 1.25,
              ),
            ),
          ],
        ),
      ),
    );
  }

  // ── 4. Chat Messages List ────────────────────────────────────────────────
  Widget _buildMessagesList(bool isDark) {
    return ListView.builder(
      controller: _scrollCtrl,
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 16),
      itemCount: _messages.length + (_loading ? 1 : 0),
      itemBuilder: (ctx, i) {
        if (i == _messages.length) {
          return _buildThinkingIndicator(isDark);
        }
        return _buildMessageBubble(_messages[i], i, isDark);
      },
    );
  }

  // ── 5. Message Bubble (Solid Brand Blue, No Gradients, Clean Cards) ───────
  Widget _buildMessageBubble(_ChatMessage message, int index, bool isDark) {
    final isBot = message.isBot;
    final isSpeaking = _speakingMessageIndex == index;

    return Padding(
      padding: const EdgeInsets.only(bottom: 14),
      child: Column(
        crossAxisAlignment:
            isBot ? CrossAxisAlignment.start : CrossAxisAlignment.end,
        children: [
          Row(
            mainAxisAlignment:
                isBot ? MainAxisAlignment.start : MainAxisAlignment.end,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Bot Avatar (Solid Brand Blue)
              if (isBot) ...[
                Container(
                  width: 30,
                  height: 30,
                  margin: const EdgeInsets.only(right: 8, top: 2),
                  decoration: BoxDecoration(
                    color: AppTheme.primaryBlue,
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: const Icon(
                    Icons.support_agent_rounded,
                    color: Colors.white,
                    size: 16,
                  ),
                ),
              ],

              // Bubble Container
              Flexible(
                child: Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: isBot
                        ? (isDark ? AppTheme.darkCard : Colors.white)
                        : AppTheme.primaryBlue,
                    borderRadius: BorderRadius.only(
                      topLeft: const Radius.circular(14),
                      topRight: const Radius.circular(14),
                      bottomLeft: Radius.circular(isBot ? 3 : 14),
                      bottomRight: Radius.circular(isBot ? 14 : 3),
                    ),
                    border: isBot
                        ? Border.all(
                            color: isDark
                                ? AppTheme.darkBorder
                                : AppTheme.slate200,
                          )
                        : null,
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Header inside Bot card
                      if (isBot) ...[
                        Row(
                          children: [
                            const Text(
                              "OpenScore Assistant",
                              style: TextStyle(
                                fontSize: 11,
                                fontWeight: FontWeight.w800,
                                color: AppTheme.primaryBlue,
                              ),
                            ),
                            if (message.intent != null) ...[
                              const SizedBox(width: 6),
                              Container(
                                padding: const EdgeInsets.symmetric(
                                    horizontal: 5, vertical: 1),
                                decoration: BoxDecoration(
                                  color: AppTheme.emeraldLight,
                                  borderRadius: BorderRadius.circular(3),
                                ),
                                child: Text(
                                  message.intent!,
                                  style: const TextStyle(
                                    fontSize: 8,
                                    fontWeight: FontWeight.w700,
                                    color: AppTheme.emerald,
                                  ),
                                ),
                              ),
                            ],
                            const Spacer(),
                            Text(
                              DateFormat('HH:mm').format(message.timestamp),
                              style: TextStyle(
                                fontSize: 9,
                                color: isDark
                                    ? AppTheme.slate400
                                    : AppTheme.slate500,
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 6),
                      ],

                      // Message Body Text
                      Text(
                        message.text,
                        style: TextStyle(
                          fontSize: 13,
                          height: 1.5,
                          color: isBot
                              ? (isDark ? Colors.white : AppTheme.slate900)
                              : Colors.white,
                          fontWeight: isBot ? FontWeight.w400 : FontWeight.w500,
                        ),
                      ),

                      // User Message Time Tag
                      if (!isBot) ...[
                        const SizedBox(height: 3),
                        Align(
                          alignment: Alignment.bottomRight,
                          child: Text(
                            DateFormat('HH:mm').format(message.timestamp),
                            style: TextStyle(
                              fontSize: 9,
                              color: Colors.white.withValues(alpha: 0.7),
                            ),
                          ),
                        ),
                      ],

                      // Action Bar for Bot Messages (Copy & Speak)
                      if (isBot) ...[
                        const SizedBox(height: 8),
                        Divider(
                          height: 1,
                          color: isDark ? AppTheme.darkBorder : AppTheme.slate200,
                        ),
                        const SizedBox(height: 6),
                        Row(
                          mainAxisAlignment: MainAxisAlignment.end,
                          children: [
                            // Speak Button
                            InkWell(
                              onTap: () => _toggleSpeaking(index),
                              borderRadius: BorderRadius.circular(4),
                              child: Padding(
                                padding: const EdgeInsets.symmetric(
                                    horizontal: 6, vertical: 3),
                                child: Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    Icon(
                                      isSpeaking
                                          ? Icons.volume_up_rounded
                                          : Icons.volume_mute_rounded,
                                      size: 14,
                                      color: isSpeaking
                                          ? AppTheme.primaryBlue
                                          : (isDark
                                              ? AppTheme.slate400
                                              : AppTheme.slate500),
                                    ),
                                    const SizedBox(width: 4),
                                    Text(
                                      isSpeaking ? "Lecture..." : "Écouter",
                                      style: TextStyle(
                                        fontSize: 10,
                                        fontWeight: FontWeight.w600,
                                        color: isSpeaking
                                            ? AppTheme.primaryBlue
                                            : (isDark
                                                ? AppTheme.slate400
                                                : AppTheme.slate600),
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            ),
                            const SizedBox(width: 6),

                            // Copy Button
                            InkWell(
                              onTap: () {
                                Clipboard.setData(
                                    ClipboardData(text: message.text));
                                ScaffoldMessenger.of(context).showSnackBar(
                                  const SnackBar(
                                    content:
                                        Text("Réponse copiée dans le presse-papier"),
                                    duration: Duration(seconds: 1),
                                    behavior: SnackBarBehavior.floating,
                                  ),
                                );
                              },
                              borderRadius: BorderRadius.circular(4),
                              child: Padding(
                                padding: const EdgeInsets.symmetric(
                                    horizontal: 6, vertical: 3),
                                child: Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    Icon(
                                      Icons.copy_rounded,
                                      size: 12,
                                      color: isDark
                                          ? AppTheme.slate400
                                          : AppTheme.slate500,
                                    ),
                                    const SizedBox(width: 4),
                                    Text(
                                      "Copier",
                                      style: TextStyle(
                                        fontSize: 10,
                                        fontWeight: FontWeight.w600,
                                        color: isDark
                                            ? AppTheme.slate400
                                            : AppTheme.slate600,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            ),
                          ],
                        ),
                      ],
                    ],
                  ),
                ),
              ),
            ],
          ),

          // Follow-Up Interactive Suggestion Pills
          if (isBot && message.suggestions.isNotEmpty) ...[
            const SizedBox(height: 6),
            Padding(
              padding: const EdgeInsets.only(left: 38),
              child: Wrap(
                spacing: 6,
                runSpacing: 6,
                children: message.suggestions.map((s) {
                  return GestureDetector(
                    onTap: () => _send(s),
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 10, vertical: 4),
                      decoration: BoxDecoration(
                        color: isDark
                            ? AppTheme.darkCard
                            : const Color(0xFFEFF6FF),
                        borderRadius: BorderRadius.circular(14),
                        border: Border.all(
                          color: AppTheme.primaryBlue.withValues(alpha: 0.3),
                        ),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Flexible(
                            child: Text(
                              s,
                              style: const TextStyle(
                                fontSize: 11,
                                fontWeight: FontWeight.w600,
                                color: AppTheme.primaryBlue,
                              ),
                            ),
                          ),
                          const SizedBox(width: 4),
                          const Icon(
                            Icons.arrow_forward_rounded,
                            size: 11,
                            color: AppTheme.primaryBlue,
                          ),
                        ],
                      ),
                    ),
                  );
                }).toList(),
              ),
            ),
          ],
        ],
      ),
    );
  }

  // ── 6. Thinking Indicator ────────────────────────────────────────────────
  Widget _buildThinkingIndicator(bool isDark) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 14),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 30,
            height: 30,
            margin: const EdgeInsets.only(right: 8, top: 2),
            decoration: BoxDecoration(
              color: AppTheme.primaryBlue,
              borderRadius: BorderRadius.circular(8),
            ),
            child: const Icon(
              Icons.support_agent_rounded,
              color: Colors.white,
              size: 16,
            ),
          ),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
            decoration: BoxDecoration(
              color: isDark ? AppTheme.darkCard : Colors.white,
              borderRadius: const BorderRadius.only(
                topLeft: Radius.circular(14),
                topRight: Radius.circular(14),
                bottomRight: Radius.circular(14),
                bottomLeft: Radius.circular(3),
              ),
              border: Border.all(
                color: isDark ? AppTheme.darkBorder : AppTheme.slate200,
              ),
            ),
            child: const Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  "Analyse en cours...",
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                    color: AppTheme.primaryBlue,
                  ),
                ),
                SizedBox(width: 8),
                SizedBox(
                  width: 12,
                  height: 12,
                  child: CircularProgressIndicator(
                    strokeWidth: 2,
                    valueColor:
                        AlwaysStoppedAnimation<Color>(AppTheme.primaryBlue),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  // ── 7. Voice Listening Waveform Panel ────────────────────────────────────
  Widget _buildVoiceListeningPanel(bool isDark) {
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.fromLTRB(16, 0, 16, 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: isDark ? AppTheme.darkCard : const Color(0xFFEFF6FF),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: AppTheme.primaryBlue.withValues(alpha: 0.3),
        ),
      ),
      child: Column(
        children: [
          Row(
            children: [
              Container(
                width: 8,
                height: 8,
                decoration: const BoxDecoration(
                  color: Color(0xFFEF4444),
                  shape: BoxShape.circle,
                ),
              ),
              const SizedBox(width: 6),
              const Text(
                "Écoute active en cours...",
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w800,
                  color: AppTheme.primaryBlue,
                ),
              ),
              const Spacer(),
              GestureDetector(
                onTap: _toggleListening,
                child: const Icon(
                  Icons.close_rounded,
                  size: 16,
                  color: AppTheme.primaryBlue,
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),

          // Solid Audio Waveform (No Gradients)
          AnimatedBuilder(
            animation: _waveCtrl,
            builder: (ctx, _) {
              return SizedBox(
                height: 30,
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: List.generate(11, (idx) {
                    final factor = math.sin((_waveCtrl.value * math.pi * 2) +
                        (idx * 0.6));
                    final height = 6 + (factor.abs() * 22);
                    return Container(
                      width: 3.5,
                      height: height,
                      margin: const EdgeInsets.symmetric(horizontal: 2),
                      decoration: BoxDecoration(
                        color: AppTheme.primaryBlue,
                        borderRadius: BorderRadius.circular(3),
                      ),
                    );
                  }),
                ),
              );
            },
          ),
          const SizedBox(height: 8),

          Text(
            "Ou touchez pour formuler vocalement :",
            style: TextStyle(
              fontSize: 10,
              color: isDark ? AppTheme.slate400 : AppTheme.slate600,
            ),
          ),
          const SizedBox(height: 6),
          Wrap(
            spacing: 6,
            runSpacing: 6,
            alignment: WrapAlignment.center,
            children: [
              _buildVoiceQuickPreset(
                "Taux d'intérêt",
                () => _send("Quel est le taux d'intérêt et les frais ?"),
              ),
              _buildVoiceQuickPreset(
                "Paiement Wave",
                () => _send("Comment payer mon échéance avec Wave ?"),
              ),
              _buildVoiceQuickPreset(
                "Garantie Moto",
                () => _send("Comment enregistrer ma moto comme garantie ?"),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildVoiceQuickPreset(String label, VoidCallback onTap) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(
            color: AppTheme.primaryBlue.withValues(alpha: 0.3),
          ),
        ),
        child: Text(
          label,
          style: const TextStyle(
            fontSize: 10,
            fontWeight: FontWeight.w700,
            color: AppTheme.primaryBlue,
          ),
        ),
      ),
    );
  }

  // ── 8. Clean Input Dock (Solid Brand Colors, No Gradients) ────────────────
  Widget _buildInputDock(bool isDark) {
    final bottomInset = MediaQuery.of(context).viewInsets.bottom;

    return Container(
      padding: EdgeInsets.fromLTRB(14, 8, 14, bottomInset + 10),
      decoration: BoxDecoration(
        color: isDark ? AppTheme.darkSurface : Colors.white,
        border: Border(
          top: BorderSide(
            color: isDark ? AppTheme.darkBorder : AppTheme.slate200,
          ),
        ),
      ),
      child: Row(
        children: [
          // Solid Brand Mic Button (No Gradient)
          GestureDetector(
            onTap: _toggleListening,
            child: Container(
              width: 42,
              height: 42,
              decoration: BoxDecoration(
                color: _isListening
                    ? const Color(0xFFEF4444)
                    : AppTheme.primaryBlue,
                shape: BoxShape.circle,
              ),
              child: Icon(
                _isListening ? Icons.mic_rounded : Icons.mic_none_rounded,
                color: Colors.white,
                size: 20,
              ),
            ),
          ),
          const SizedBox(width: 8),

          // Text Field
          Expanded(
            child: Container(
              decoration: BoxDecoration(
                color: isDark ? AppTheme.darkCard : const Color(0xFFF1F5F9),
                borderRadius: BorderRadius.circular(20),
                border: Border.all(
                  color: isDark ? AppTheme.darkBorder : AppTheme.slate200,
                ),
              ),
              child: TextField(
                controller: _queryCtrl,
                style: TextStyle(
                  fontSize: 13,
                  color: isDark ? Colors.white : AppTheme.slate900,
                ),
                decoration: InputDecoration(
                  hintText: _selectedLanguage == 'fr'
                      ? "Posez votre question à l'Assistant..."
                      : "I ka nyininkali cɛ...",
                  hintStyle: TextStyle(
                    fontSize: 12,
                    color: isDark ? AppTheme.slate400 : AppTheme.slate500,
                  ),
                  contentPadding: const EdgeInsets.symmetric(
                    horizontal: 14,
                    vertical: 10,
                  ),
                  border: InputBorder.none,
                  suffixIcon: _queryCtrl.text.isNotEmpty
                      ? IconButton(
                          icon: const Icon(Icons.clear, size: 16),
                          onPressed: () {
                            _queryCtrl.clear();
                            setState(() {});
                          },
                        )
                      : null,
                ),
                onChanged: (_) => setState(() {}),
                onSubmitted: _send,
              ),
            ),
          ),
          const SizedBox(width: 8),

          // Solid Brand Send Button (No Gradient)
          GestureDetector(
            onTap: _loading ? null : () => _send(_queryCtrl.text),
            child: Container(
              width: 42,
              height: 42,
              decoration: BoxDecoration(
                color: _loading || _queryCtrl.text.trim().isEmpty
                    ? (isDark ? AppTheme.darkCard : AppTheme.slate200)
                    : AppTheme.primaryBlue,
                shape: BoxShape.circle,
              ),
              child: _loading
                  ? const Center(
                      child: SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          valueColor:
                              AlwaysStoppedAnimation<Color>(Colors.white),
                        ),
                      ),
                    )
                  : Icon(
                      Icons.arrow_upward_rounded,
                      color: _queryCtrl.text.trim().isEmpty
                          ? (isDark ? AppTheme.slate500 : AppTheme.slate400)
                          : Colors.white,
                      size: 20,
                    ),
            ),
          ),
        ],
      ),
    );
  }
}

// ── Data Models ─────────────────────────────────────────────────────────────
class _ChatMessage {
  final String text;
  final bool isBot;
  final DateTime timestamp;
  final List<String> suggestions;
  final String? intent;

  _ChatMessage({
    required this.text,
    required this.isBot,
    required this.timestamp,
    this.suggestions = const [],
    this.intent,
  });
}

class _TopicChip {
  final IconData icon;
  final String label;
  final String query;
  final Color color;

  const _TopicChip({
    required this.icon,
    required this.label,
    required this.query,
    required this.color,
  });
}
