import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:image_picker/image_picker.dart';
import 'package:dio/dio.dart';
import '../../core/services/api_service.dart';
import '../../core/theme/app_theme.dart';
import '../../shared/widgets/shared_widgets.dart';

class NewApplicationWizard extends StatefulWidget {
  final VoidCallback onSuccess;

  const NewApplicationWizard({super.key, required this.onSuccess});

  @override
  State<NewApplicationWizard> createState() => _NewApplicationWizardState();
}

class _NewApplicationWizardState extends State<NewApplicationWizard> {
  final _api = ApiService();
  final _pageCtrl = PageController();
  int _step = 0;
  bool _loading = false;
  int? _createdAppId;

  // Step 1 data
  String _sector = 'Commerce';
  double _amount = 500000;
  int _duration = 12;
  final _descCtrl = TextEditingController();

  // Antenne & Structure Kafo Jiginew
  String _country = 'Mali';
  String _city = 'Bamako';
  String _branchCode = '701';
  String _accountType = 'INDIVIDUAL';

  final List<String> _countries = ['Mali', 'Sénégal', 'Côte d\'Ivoire'];
  final List<String> _maliCities = ['Bamako', 'Sikasso', 'Ségou', 'Mopti', 'Kayes'];
  final Map<String, List<Map<String, String>>> _branchesByCity = {
    'Bamako': [
      {'code': '701', 'name': '701 - Agence Centrale Bamako (Hamdallaye ACI)'},
      {'code': '702', 'name': '702 - Caisse Urbaine Médina-Coura'},
    ],
    'Sikasso': [
      {'code': '801', 'name': '801 - Antenne Régionale Sikasso (Wayerma)'},
      {'code': '802', 'name': '802 - Caisse Rurale Koutiala'},
    ],
    'Ségou': [
      {'code': '901', 'name': '901 - Antenne Régionale Ségou (Pelengana)'},
    ],
    'Mopti': [
      {'code': '902', 'name': '902 - Antenne Mopti (Sévaré)'},
    ],
    'Kayes': [
      {'code': '903', 'name': '903 - Antenne Kayes (Légal Ségou)'},
    ],
  };

  // Step 2 - document
  XFile? _docFile;
  bool _extracting = false;
  String? _extractStatus;
  bool _extractSuccess = false;

  // Step 3 - voice query
  final _voiceCtrl = TextEditingController();
  String? _voiceResponse;
  List<String> _suggestions = [];

  final List<String> _sectors = ['Commerce', 'Agriculture', 'Artisanat', 'TPE', 'Autre'];
  final Map<String, IconData> _sectorIcons = {
    'Commerce': Icons.storefront_rounded,
    'Agriculture': Icons.agriculture_rounded,
    'Artisanat': Icons.handyman_rounded,
    'TPE': Icons.business_center_rounded,
    'Autre': Icons.category_rounded,
  };
  final Map<String, String> _sectorSubs = {
    'Commerce': 'Grand Marché / Détaillant',
    'Agriculture': 'Maraîchage Baguinéda',
    'Artisanat': 'Couture & Forge',
    'TPE': 'PME Locale',
    'Autre': 'Activités diverses',
  };

  @override
  void dispose() {
    _pageCtrl.dispose();
    _descCtrl.dispose();
    _voiceCtrl.dispose();
    super.dispose();
  }

  void _next() {
    if (_step < 3) {
      _pageCtrl.nextPage(duration: 300.ms, curve: Curves.easeInOutCubic);
      setState(() => _step++);
    }
  }

  void _prev() {
    if (_step > 0) {
      _pageCtrl.previousPage(duration: 300.ms, curve: Curves.easeInOutCubic);
      setState(() => _step--);
    } else {
      Navigator.pop(context);
    }
  }

  Future<void> _submitProfile() async {
    setState(() => _loading = true);
    try {
      final result = await _api.createApplication({
        'activity_sector': _sector,
        'requested_amount': _amount,
        'requested_duration_months': _duration,
        'business_description': _descCtrl.text.trim().isEmpty
            ? '$_sector – Activité déclarée via mobile'
            : _descCtrl.text.trim(),
        'branch_code': _branchCode,
        'application_type': _accountType,
      });
      _createdAppId = result['id'];
      _next();
    } catch (e) {
      _showError('Erreur lors de la création du dossier');
    }
    setState(() => _loading = false);
  }

  Future<void> _pickDocument() async {
    final picker = ImagePicker();
    final file = await picker.pickImage(
      source: ImageSource.gallery,
      imageQuality: 85,
    );
    if (file != null) setState(() => _docFile = file);
  }

  Future<void> _extractDocument() async {
    if (_docFile == null || _createdAppId == null) return;
    setState(() {
      _extracting = true;
      _extractStatus = 'Analyse IA Gemini en cours...';
    });

    try {
      final formData = FormData.fromMap({
        'file': await MultipartFile.fromFile(
          _docFile!.path,
          filename: _docFile!.name,
        ),
      });
      await _api.extractDocs(_createdAppId!, formData);
      setState(() {
        _extractStatus = 'Document extrait avec succès par IA';
        _extractSuccess = true;
      });
    } catch (e) {
      setState(() {
        _extractStatus = 'Document ignoré — vous pouvez continuer';
        _extractSuccess = false;
      });
    }
    setState(() => _extracting = false);
  }

  Future<void> _sendVoiceQuery() async {
    final query = _voiceCtrl.text.trim();
    if (query.isEmpty) return;
    setState(() => _loading = true);
    try {
      final data = await _api.voiceQuery(query);
      setState(() {
        _voiceResponse = data['response_text'];
        _suggestions = List<String>.from(data['suggestions'] ?? []);
      });
    } catch (_) {
      setState(() => _voiceResponse = 'Assistant temporairement indisponible.');
    }
    setState(() => _loading = false);
  }

  void _showError(String msg) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(msg),
        backgroundColor: AppTheme.rose,
        behavior: SnackBarBehavior.floating,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      height: MediaQuery.of(context).size.height * 0.9,
      decoration: BoxDecoration(
        color: Theme.of(context).scaffoldBackgroundColor,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
      ),
      child: Column(
        children: [
          // Handle bar
          Container(
            width: 40,
            height: 4,
            margin: const EdgeInsets.only(top: 12),
            decoration: BoxDecoration(
              color: AppTheme.slate200,
              borderRadius: BorderRadius.circular(2),
            ),
          ),

          // Header
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 16, 20, 0),
            child: Column(
              children: [
                Row(
                  children: [
                    IconButton(
                      icon: const Icon(Icons.arrow_back),
                      onPressed: _prev,
                      padding: EdgeInsets.zero,
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            _stepTitles[_step],
                            style: const TextStyle(
                                fontWeight: FontWeight.w800, fontSize: 16),
                          ),
                          Text(
                            'Étape ${_step + 1} / 4',
                            style: TextStyle(
                                color: AppTheme.slate400, fontSize: 12),
                          ),
                        ],
                      ),
                    ),
                    IconButton(
                      icon: Icon(Icons.close, color: AppTheme.slate400),
                      onPressed: () => Navigator.pop(context),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                // Progress bar
                Row(
                  children: List.generate(4, (i) {
                    return Expanded(
                      child: Container(
                        height: 4,
                        margin: EdgeInsets.only(right: i < 3 ? 4 : 0),
                        decoration: BoxDecoration(
                          color: i <= _step
                              ? AppTheme.primaryBlue
                              : AppTheme.slate200,
                          borderRadius: BorderRadius.circular(2),
                        ),
                      ),
                    );
                  }),
                ),
              ],
            ),
          ),

          // Pages
          Expanded(
            child: PageView(
              controller: _pageCtrl,
              physics: const NeverScrollableScrollPhysics(),
              children: [
                _buildStep1(),
                _buildStep2(),
                _buildStep3(),
                _buildStep4(),
              ],
            ),
          ),
        ],
      ),
    );
  }

  final List<String> _stepTitles = [
    'Paramètres du Microcrédit',
    'Justificatifs & IA Extraction',
    'Assistant Vocal Bilingue',
    'Suivi & Décision',
  ];

  // ── Step 1: Profile ────────────────────────────────────────────
  Widget _buildStep1() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Sector grid
          const _Label(text: "SECTEUR D'ACTIVITÉ"),
          const SizedBox(height: 8),
          GridView.count(
            crossAxisCount: 2,
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            crossAxisSpacing: 8,
            mainAxisSpacing: 8,
            childAspectRatio: 2.2,
            children: _sectors.map((s) {
              final sel = _sector == s;
              return GestureDetector(
                onTap: () => setState(() => _sector = s),
                child: AnimatedContainer(
                  duration: 200.ms,
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  decoration: BoxDecoration(
                    color: sel
                        ? AppTheme.primaryBlue.withValues(alpha: 0.08)
                        : Colors.transparent,
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(
                      color: sel ? AppTheme.primaryBlue : AppTheme.slate200,
                      width: sel ? 2 : 1,
                    ),
                  ),
                  child: Row(
                    children: [
                      Icon(
                        _sectorIcons[s] ?? Icons.description_rounded,
                        size: 20,
                        color: sel ? AppTheme.primaryBlue : AppTheme.slate500,
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Text(s,
                                style: TextStyle(
                                  fontWeight: FontWeight.w700,
                                  fontSize: 12,
                                  color: sel
                                      ? AppTheme.primaryBlue
                                      : AppTheme.slate800,
                                )),
                            Text(
                              _sectorSubs[s] ?? '',
                              style: TextStyle(
                                fontSize: 9,
                                color: AppTheme.slate400,
                              ),
                              overflow: TextOverflow.ellipsis,
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              );
            }).toList(),
          ),
          const SizedBox(height: 20),

          // Amount
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const _Label(text: 'MONTANT SOLLICITÉ (FCFA)'),
              TextButton.icon(
                onPressed: () => showCustomAmountBottomSheet(
                  context: context,
                  title: 'Montant Sollicité',
                  currentValue: _amount,
                  onSubmitted: (v) => setState(() => _amount = v),
                  presets: const [250000, 500000, 1000000, 1500000, 2000000, 3000000, 5000000],
                ),
                icon: const Icon(Icons.edit_note_rounded, size: 16),
                label: const Text('Saisie libre', style: TextStyle(inherit: true, fontSize: 12)),
              ),
            ],
          ),
          const SizedBox(height: 4),
          GestureDetector(
            onTap: () => showCustomAmountBottomSheet(
              context: context,
              title: 'Montant Sollicité',
              currentValue: _amount,
              onSubmitted: (v) => setState(() => _amount = v),
              presets: const [250000, 500000, 1000000, 1500000, 2000000, 3000000, 5000000],
            ),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
              decoration: BoxDecoration(
                color: AppTheme.primaryBlue.withValues(alpha: 0.08),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(
                  color: AppTheme.primaryBlue.withValues(alpha: 0.25),
                  width: 1,
                ),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    formatFCFA(_amount),
                    style: const TextStyle(
                      inherit: true,
                      fontFamily: 'monospace',
                      fontWeight: FontWeight.w800,
                      fontSize: 20,
                      color: AppTheme.primaryBlue,
                    ),
                  ),
                  const SizedBox(width: 8),
                  const Icon(Icons.edit_rounded, size: 16, color: AppTheme.primaryBlue),
                ],
              ),
            ),
          ),
          if (_amount > 3000000 || _amount < 100000)
            Padding(
              padding: const EdgeInsets.only(top: 6),
              child: Text(
                _amount > 3000000
                    ? 'Montant personnalisé : ${formatFCFA(_amount)} (supérieur au curseur standard)'
                    : 'Montant personnalisé : ${formatFCFA(_amount)} (inférieur à 100 000 FCFA)',
                style: const TextStyle(
                  inherit: true,
                  fontSize: 11,
                  fontWeight: FontWeight.w600,
                  color: AppTheme.amber,
                ),
              ),
            ),
          Slider(
            value: _amount.clamp(100000, 3000000),
            min: 100000,
            max: 3000000,
            divisions: 58,
            activeColor: AppTheme.primaryBlue,
            inactiveColor: AppTheme.slate200,
            onChanged: (v) => setState(() => _amount = v),
          ),

          // Quick chips
          Wrap(
            spacing: 6,
            runSpacing: 6,
            children: [
              ...[250000, 500000, 1000000, 1500000, 2000000].map((amt) {
                final sel = (_amount - amt).abs() < 1;
                return GestureDetector(
                  onTap: () => setState(() => _amount = amt.toDouble()),
                  child: AnimatedContainer(
                    duration: 150.ms,
                    padding:
                        const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                    decoration: BoxDecoration(
                      color: sel ? AppTheme.primaryBlue : Colors.transparent,
                      borderRadius: BorderRadius.circular(20),
                      border: Border.all(
                        color: sel ? AppTheme.primaryBlue : AppTheme.slate200,
                      ),
                    ),
                    child: Text(
                      amt >= 1000000
                          ? '${(amt / 1000000).toStringAsFixed(0)}M FCFA'
                          : '${(amt / 1000).toStringAsFixed(0)}k FCFA',
                      style: TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.w600,
                        fontFamily: 'monospace',
                        color: sel ? Colors.white : AppTheme.slate600,
                      ),
                    ),
                  ),
                );
              }),
              GestureDetector(
                onTap: () => showCustomAmountBottomSheet(
                  context: context,
                  title: 'Montant Sollicité',
                  currentValue: _amount,
                  onSubmitted: (v) => setState(() => _amount = v),
                  presets: const [250000, 500000, 1000000, 1500000, 2000000, 3000000, 5000000],
                ),
                child: AnimatedContainer(
                  duration: 150.ms,
                  padding:
                      const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                  decoration: BoxDecoration(
                    color: Colors.transparent,
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(
                      color: AppTheme.primaryBlue,
                    ),
                  ),
                  child: const Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.edit_rounded, size: 12, color: AppTheme.primaryBlue),
                      SizedBox(width: 4),
                      Text(
                        'Autre',
                        style: TextStyle(
                          inherit: true,
                          fontSize: 11,
                          fontWeight: FontWeight.w600,
                          fontFamily: 'monospace',
                          color: AppTheme.primaryBlue,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 20),

          // Duration
          const _Label(text: 'DURÉE DE REMBOURSEMENT'),
          const SizedBox(height: 8),
          Row(
            children: [6, 12, 18, 24].map((d) {
              final sel = _duration == d;
              return Expanded(
                child: GestureDetector(
                  onTap: () => setState(() => _duration = d),
                  child: AnimatedContainer(
                    duration: 150.ms,
                    margin: const EdgeInsets.only(right: 6),
                    padding: const EdgeInsets.symmetric(vertical: 10),
                    decoration: BoxDecoration(
                      color: sel
                          ? AppTheme.primaryBlue
                          : Colors.transparent,
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(
                        color: sel ? AppTheme.primaryBlue : AppTheme.slate200,
                      ),
                    ),
                    child: Column(
                      children: [
                        Text(
                          '$d',
                          style: TextStyle(
                            fontWeight: FontWeight.w800,
                            fontSize: 16,
                            color: sel ? Colors.white : AppTheme.slate700,
                          ),
                        ),
                        Text(
                          'mois',
                          style: TextStyle(
                            fontSize: 9,
                            color: sel
                                ? Colors.white.withValues(alpha: 0.8)
                                : AppTheme.slate400,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              );
            }).toList(),
          ),
          const SizedBox(height: 16),

          // Description
          TextField(
            controller: _descCtrl,
            maxLines: 2,
            decoration: const InputDecoration(
              labelText: "Description de l'activité",
              hintText:
                  'Ex: Vente de tissus Bazin au Grand Marché, Stand n°142...',
              prefixIcon: Icon(Icons.business_outlined),
              alignLabelWithHint: true,
            ),
          ),

          // ── Sélection de l'Antenne Régionale ───────────────────────────
          const SizedBox(height: 16),
          Builder(
            builder: (context) {
              final isDark = Theme.of(context).brightness == Brightness.dark;
              return Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: isDark ? const Color(0xFF1E293B) : const Color(0xFFF1F5F9),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(
                    color: isDark ? AppTheme.darkBorder : AppTheme.slate200,
                  ),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        const Icon(Icons.account_balance_rounded, size: 16, color: AppTheme.primaryBlue),
                        const SizedBox(width: 8),
                        Text(
                          'Antenne Régionale de Rattachement',
                          style: TextStyle(
                            fontWeight: FontWeight.w700,
                            fontSize: 12,
                            color: isDark ? Colors.white : AppTheme.slate900,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 10),

                    // Type de dossier (Particulier / Salarié vs PME)
                    Row(
                      children: [
                        Expanded(
                          child: GestureDetector(
                            onTap: () => setState(() => _accountType = 'INDIVIDUAL'),
                            child: Container(
                              padding: const EdgeInsets.symmetric(vertical: 7),
                              decoration: BoxDecoration(
                                color: _accountType == 'INDIVIDUAL'
                                    ? AppTheme.primaryBlue.withValues(alpha: 0.12)
                                    : Colors.transparent,
                                borderRadius: BorderRadius.circular(8),
                                border: Border.all(
                                  color: _accountType == 'INDIVIDUAL' ? AppTheme.primaryBlue : AppTheme.slate300,
                                  width: _accountType == 'INDIVIDUAL' ? 2 : 1,
                                ),
                              ),
                              child: Text(
                                'Particulier',
                                textAlign: TextAlign.center,
                                style: TextStyle(
                                  fontSize: 11,
                                  fontWeight: FontWeight.bold,
                                  color: _accountType == 'INDIVIDUAL' ? AppTheme.primaryBlue : AppTheme.slate600,
                                ),
                              ),
                            ),
                          ),
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: GestureDetector(
                            onTap: () => setState(() => _accountType = 'BUSINESS'),
                            child: Container(
                              padding: const EdgeInsets.symmetric(vertical: 7),
                              decoration: BoxDecoration(
                                color: _accountType == 'BUSINESS'
                                    ? AppTheme.primaryBlue.withValues(alpha: 0.12)
                                    : Colors.transparent,
                                borderRadius: BorderRadius.circular(8),
                                border: Border.all(
                                  color: _accountType == 'BUSINESS' ? AppTheme.primaryBlue : AppTheme.slate300,
                                  width: _accountType == 'BUSINESS' ? 2 : 1,
                                ),
                              ),
                              child: Text(
                                'Entreprise / PME',
                                textAlign: TextAlign.center,
                                style: TextStyle(
                                  fontSize: 11,
                                  fontWeight: FontWeight.bold,
                                  color: _accountType == 'BUSINESS' ? AppTheme.primaryBlue : AppTheme.slate600,
                                ),
                              ),
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 10),

                    // Cascading: Pays & Ville
                    Row(
                      children: [
                        Expanded(
                          flex: 4,
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text('Pays', style: TextStyle(fontSize: 10, color: AppTheme.slate500)),
                              const SizedBox(height: 2),
                              DropdownButtonFormField<String>(
                                initialValue: _country,
                                isExpanded: true,
                                decoration: const InputDecoration(
                                  contentPadding: EdgeInsets.symmetric(horizontal: 8, vertical: 6),
                                ),
                                items: _countries.map((c) => DropdownMenuItem(value: c, child: Text(c, style: TextStyle(fontSize: 11, color: isDark ? Colors.white : Colors.black)))).toList(),
                                onChanged: (val) {
                                  if (val != null) setState(() => _country = val);
                                },
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          flex: 6,
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text('Ville', style: TextStyle(fontSize: 10, color: AppTheme.slate500)),
                              const SizedBox(height: 2),
                              DropdownButtonFormField<String>(
                                initialValue: _city,
                                isExpanded: true,
                                decoration: const InputDecoration(
                                  contentPadding: EdgeInsets.symmetric(horizontal: 8, vertical: 6),
                                ),
                                items: _maliCities.map((ct) => DropdownMenuItem(value: ct, child: Text(ct, style: TextStyle(fontSize: 11, color: isDark ? Colors.white : Colors.black)))).toList(),
                                onChanged: (val) {
                                  if (val != null) {
                                    setState(() {
                                      _city = val;
                                      final branches = _branchesByCity[val];
                                      if (branches != null && branches.isNotEmpty) {
                                        _branchCode = branches.first['code']!;
                                      }
                                    });
                                  }
                                },
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),

                    // Antenne / Caisse
                    Text('Antenne / Caisse', style: TextStyle(fontSize: 10, color: AppTheme.slate500)),
                    const SizedBox(height: 2),
                    DropdownButtonFormField<String>(
                      initialValue: _branchCode,
                      isExpanded: true,
                      decoration: const InputDecoration(
                        contentPadding: EdgeInsets.symmetric(horizontal: 8, vertical: 6),
                      ),
                      items: (_branchesByCity[_city] ?? [
                        {'code': '701', 'name': '701 - Agence Centrale Bamako (Hamdallaye ACI)'}
                      ]).map((b) => DropdownMenuItem(
                        value: b['code'],
                        child: Text(
                          b['name']!,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(fontSize: 11, color: isDark ? Colors.white : Colors.black),
                        ),
                      )).toList(),
                      onChanged: (val) {
                        if (val != null) setState(() => _branchCode = val);
                      },
                    ),
                  ],
                ),
              );
            },
          ),
          const SizedBox(height: 24),

          PrimaryButton(
            label: 'Enregistrer & Continuer',
            onPressed: _submitProfile,
            isLoading: _loading,
            icon: Icons.arrow_forward,
            width: double.infinity,
          ),
        ],
      ),
    );
  }

  // ── Step 2: Documents ──────────────────────────────────────────
  Widget _buildStep2() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          OSFCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(Icons.info_outline,
                        color: AppTheme.primaryBlue, size: 18),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        'Documents acceptés : NINA, CNI, Carnet de reçus',
                        style: TextStyle(
                            color: AppTheme.primaryBlue,
                            fontSize: 12,
                            fontWeight: FontWeight.w600),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 4),
                Text(
                  'Les données sont analysées par IA Gemini et supprimées après extraction.',
                  style: TextStyle(color: AppTheme.slate400, fontSize: 11),
                ),
              ],
            ),
          ).animate().fadeIn(),
          const SizedBox(height: 20),

          // Upload zone
          GestureDetector(
            onTap: _pickDocument,
            child: AnimatedContainer(
              duration: 200.ms,
              width: double.infinity,
              padding: const EdgeInsets.all(32),
              decoration: BoxDecoration(
                color: _docFile != null
                    ? AppTheme.emeraldLight
                    : AppTheme.primaryBlue.withValues(alpha: 0.04),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(
                  color: _docFile != null
                      ? AppTheme.emerald
                      : AppTheme.primaryBlue.withValues(alpha: 0.3),
                  width: 1.5,
                  style: BorderStyle.solid,
                ),
              ),
              child: Column(
                children: [
                  Icon(
                    _docFile != null
                        ? Icons.check_circle_outline
                        : Icons.cloud_upload_outlined,
                    size: 48,
                    color: _docFile != null
                        ? AppTheme.emerald
                        : AppTheme.primaryBlue,
                  ),
                  const SizedBox(height: 12),
                  Text(
                    _docFile != null
                        ? _docFile!.name
                        : 'Appuyer pour choisir un fichier',
                    style: TextStyle(
                      fontWeight: FontWeight.w700,
                      color: _docFile != null
                          ? AppTheme.emerald
                          : AppTheme.primaryBlue,
                      fontSize: 14,
                    ),
                    textAlign: TextAlign.center,
                  ),
                  if (_docFile == null)
                    Text(
                      'JPG, PNG ou PDF',
                      style: TextStyle(color: AppTheme.slate400, fontSize: 12),
                    ),
                ],
              ),
            ),
          ).animate().fadeIn(delay: 100.ms),

          if (_docFile != null) ...[
            const SizedBox(height: 16),
            if (_extractStatus != null)
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: _extractSuccess
                      ? AppTheme.emeraldLight
                      : AppTheme.amberLight,
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Row(
                  children: [
                    Icon(
                      _extractSuccess
                          ? Icons.check_circle_rounded
                          : Icons.info_outline_rounded,
                      size: 16,
                      color: _extractSuccess
                          ? AppTheme.emerald
                          : AppTheme.amber,
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                        child: Text(_extractStatus!,
                            style: const TextStyle(fontSize: 12))),
                  ],
                ),
              ).animate().fadeIn(),
            const SizedBox(height: 12),
            PrimaryButton(
              label: _extracting
                  ? 'Extraction IA en cours...'
                  : 'Lancer l\'Extraction Gemini',
              onPressed: _extracting ? null : _extractDocument,
              isLoading: _extracting,
              icon: Icons.auto_awesome,
              width: double.infinity,
            ),
          ],
          const SizedBox(height: 16),
          OutlinedButton.icon(
            onPressed: _next,
            icon: const Icon(Icons.skip_next, size: 16),
            label: const Text('Passer cette étape'),
            style: OutlinedButton.styleFrom(
                minimumSize: const Size(double.infinity, 48)),
          ),
        ],
      ),
    );
  }

  // ── Step 3: Voice Assistant ────────────────────────────────────
  Widget _buildStep3() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [
                  AppTheme.primaryBlue.withValues(alpha: 0.08),
                  AppTheme.purple.withValues(alpha: 0.06),
                ],
              ),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(
                  color: AppTheme.primaryBlue.withValues(alpha: 0.2)),
            ),
            child: Row(
              children: [
                Container(
                  width: 44,
                  height: 44,
                  decoration: BoxDecoration(
                    color: AppTheme.primaryBlue,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: const Icon(Icons.mic, color: Colors.white, size: 24),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Assistant Vocal Bilingue',
                        style: TextStyle(
                            fontWeight: FontWeight.w700, fontSize: 14),
                      ),
                      Text(
                        'Posez vos questions en Français ou Bambara',
                        style: TextStyle(
                            color: AppTheme.slate500, fontSize: 11),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ).animate().fadeIn(),
          const SizedBox(height: 20),

          // Quick suggestions
          const _Label(text: 'QUESTIONS FRÉQUENTES'),
          const SizedBox(height: 8),
          Wrap(
            spacing: 6,
            runSpacing: 6,
            children: [
              'Quels documents fournir ?',
              'Combien puis-je emprunter ?',
              'Je veux un crédit Sugu',
              'Sɛnɛ — Crédit agricole',
            ].map((q) => GestureDetector(
              onTap: () {
                _voiceCtrl.text = q;
                _sendVoiceQuery();
              },
              child: Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                decoration: BoxDecoration(
                  color: AppTheme.primaryBlue.withValues(alpha: 0.08),
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(
                      color: AppTheme.primaryBlue.withValues(alpha: 0.25)),
                ),
                child: Text(q,
                    style: TextStyle(
                        fontSize: 11, color: AppTheme.primaryBlue)),
              ),
            )).toList(),
          ),
          const SizedBox(height: 20),

          // Input
          Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _voiceCtrl,
                  decoration: const InputDecoration(
                    hintText: 'Votre question (fr ou Bambara)...',
                    prefixIcon: Icon(Icons.chat_outlined),
                  ),
                  onSubmitted: (_) => _sendVoiceQuery(),
                ),
              ),
              const SizedBox(width: 8),
              ElevatedButton(
                onPressed: _loading ? null : _sendVoiceQuery,
                style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.all(14),
                  minimumSize: const Size(52, 52),
                ),
                child: _loading
                    ? const SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          valueColor:
                              AlwaysStoppedAnimation<Color>(Colors.white),
                        ),
                      )
                    : const Icon(Icons.send),
              ),
            ],
          ),

          if (_voiceResponse != null) ...[
            const SizedBox(height: 16),
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: AppTheme.primaryBlue.withValues(alpha: 0.06),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(
                    color: AppTheme.primaryBlue.withValues(alpha: 0.2)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Icon(Icons.smart_toy_outlined,
                          color: AppTheme.primaryBlue, size: 16),
                      const SizedBox(width: 6),
                      Text(
                        'Assistant OpenScore',
                        style: TextStyle(
                            color: AppTheme.primaryBlue,
                            fontWeight: FontWeight.w700,
                            fontSize: 12),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Text(_voiceResponse!,
                      style: const TextStyle(fontSize: 13, height: 1.5)),
                  if (_suggestions.isNotEmpty) ...[
                    const SizedBox(height: 10),
                    Wrap(
                      spacing: 6,
                      runSpacing: 6,
                      children: _suggestions
                          .map((s) => GestureDetector(
                                onTap: () {
                                  _voiceCtrl.text = s;
                                  _sendVoiceQuery();
                                },
                                child: Container(
                                  padding: const EdgeInsets.symmetric(
                                      horizontal: 10, vertical: 5),
                                  decoration: BoxDecoration(
                                    color:
                                        AppTheme.primaryBlue.withValues(alpha: 0.1),
                                    borderRadius: BorderRadius.circular(16),
                                  ),
                                  child: Text(s,
                                      style: TextStyle(
                                          fontSize: 10,
                                          color: AppTheme.primaryBlue)),
                                ),
                              ))
                          .toList(),
                    ),
                  ],
                ],
              ),
            ).animate().fadeIn(),
          ],
          const SizedBox(height: 20),
          PrimaryButton(
            label: 'Passer au suivi du dossier',
            onPressed: _next,
            icon: Icons.arrow_forward,
            width: double.infinity,
          ),
        ],
      ),
    );
  }

  // ── Step 4: Decision summary ───────────────────────────────────
  Widget _buildStep4() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Success icon
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(24),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [
                  AppTheme.emerald.withValues(alpha: 0.1),
                  AppTheme.primaryBlue.withValues(alpha: 0.05),
                ],
              ),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(
                  color: AppTheme.emerald.withValues(alpha: 0.3)),
            ),
            child: Column(
              children: [
                const Icon(Icons.check_circle,
                    color: AppTheme.emerald, size: 56),
                const SizedBox(height: 12),
                const Text(
                  'Dossier soumis avec succès !',
                  style: TextStyle(
                      fontWeight: FontWeight.w800, fontSize: 18),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 6),
                Text(
                  'Votre demande est en cours de traitement par notre équipe.',
                  textAlign: TextAlign.center,
                  style: TextStyle(color: AppTheme.slate500, fontSize: 13),
                ),
              ],
            ),
          ).animate().scale(begin: const Offset(0.8, 0.8)).fadeIn(),
          const SizedBox(height: 24),

          // Summary card
          const _Label(text: 'RÉCAPITULATIF DE LA DEMANDE'),
          const SizedBox(height: 8),
          OSFCard(
            child: Column(
              children: [
                _summaryRow('Secteur d\'activité', _sector),
                const Divider(height: 16),
                _summaryRow('Montant demandé', formatFCFA(_amount)),
                const Divider(height: 16),
                _summaryRow('Durée', '$_duration mois'),
                if (_createdAppId != null) ...[
                  const Divider(height: 16),
                  _summaryRow('Réf. dossier', 'ID #$_createdAppId'),
                ],
              ],
            ),
          ).animate().fadeIn(delay: 200.ms),
          const SizedBox(height: 20),

          // Next steps
          OSFCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Prochaines étapes',
                  style: TextStyle(
                      fontWeight: FontWeight.w700, fontSize: 13),
                ),
                const SizedBox(height: 12),
                _step4Item('1', 'Un agent vérifie vos données sous 24–48h',
                    AppTheme.primaryBlue),
                _step4Item('2', 'Évaluation du score d\'éligibilité par IA',
                    AppTheme.purple),
                _step4Item('3', 'Décision officielle envoyée par SMS',
                    AppTheme.emerald),
              ],
            ),
          ).animate().fadeIn(delay: 300.ms),
          const SizedBox(height: 24),

          PrimaryButton(
            label: 'Retourner à mes dossiers',
            onPressed: () {
              widget.onSuccess();
              Navigator.pop(context);
            },
            icon: Icons.folder_outlined,
            width: double.infinity,
          ),
        ],
      ),
    );
  }

  Widget _summaryRow(String label, String value) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(label, style: TextStyle(color: AppTheme.slate500, fontSize: 13)),
        Text(value,
            style: const TextStyle(
                fontWeight: FontWeight.w700,
                fontSize: 13,
                fontFamily: 'monospace')),
      ],
    );
  }

  Widget _step4Item(String num, String text, Color color) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(
        children: [
          Container(
            width: 24,
            height: 24,
            decoration: BoxDecoration(
              color: color,
              borderRadius: BorderRadius.circular(12),
            ),
            child: Center(
              child: Text(
                num,
                style: const TextStyle(
                    color: Colors.white,
                    fontSize: 11,
                    fontWeight: FontWeight.w700),
              ),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
              child: Text(text, style: const TextStyle(fontSize: 13))),
        ],
      ),
    );
  }
}

class _Label extends StatelessWidget {
  final String text;
  const _Label({required this.text});

  @override
  Widget build(BuildContext context) {
    return Text(
      text,
      style: const TextStyle(
        fontSize: 10,
        fontWeight: FontWeight.w700,
        color: AppTheme.slate500,
        letterSpacing: 0.8,
      ),
    );
  }
}
