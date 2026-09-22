import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';
import '../../core/services/auth_service.dart';
import '../../core/theme/app_theme.dart';
import '../../shared/widgets/shared_widgets.dart';

class RegisterScreen extends StatefulWidget {
  const RegisterScreen({super.key});

  @override
  State<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends State<RegisterScreen> {
  final _formKey = GlobalKey<FormState>();
  final _pageCtrl = PageController();
  int _currentPage = 0;

  // ── Step 1 : Informations personnelles ───────────────────────
  final _nameCtrl = TextEditingController();
  final _emailCtrl = TextEditingController();
  final _phoneCtrl = TextEditingController();
  final _passCtrl = TextEditingController();
  bool _obscure = true;

  // ── Step 2 : Profil financier ─────────────────────────────────
  String _sector = 'Commerce';
  double _revenue = 350000;
  double _expenses = 120000;
  double _amount = 500000;
  final _descCtrl = TextEditingController();

  // ── Step 3 : Documents obligatoires ──────────────────────────
  // Pièce d'identité (obligatoire pour tous)
  String _idType = 'NINA';
  final _ninaCtrl = TextEditingController();
  XFile? _idCardFile; // photo / scan de la pièce

  // TPE / PME uniquement
  final _nifCtrl = TextEditingController();
  final _rccmCtrl = TextEditingController();
  XFile? _nifFile;
  XFile? _rccmFile;

  // Attestation d'activité (Commerce, Agriculture, Artisanat)
  XFile? _attestationFile;

  // ── Static data ───────────────────────────────────────────────
  final List<String> _sectors = ['Commerce', 'Agriculture', 'Artisanat', 'TPE'];
  final Map<String, String> _sectorSubs = {
    'Commerce': 'Grand Marché / Détaillant',
    'Agriculture': 'Maraîchage / cultivateur',
    'Artisanat': 'Couture & Forge',
    'TPE': 'PME Locale',
  };
  final Map<String, IconData> _sectorIcons = {
    'Commerce': Icons.storefront_rounded,
    'Agriculture': Icons.agriculture_rounded,
    'Artisanat': Icons.handyman_rounded,
    'TPE': Icons.business_center_rounded,
  };

  bool get _isTpe => _sector == 'TPE';

  @override
  void dispose() {
    _nameCtrl.dispose();
    _emailCtrl.dispose();
    _phoneCtrl.dispose();
    _passCtrl.dispose();
    _descCtrl.dispose();
    _ninaCtrl.dispose();
    _nifCtrl.dispose();
    _rccmCtrl.dispose();
    _pageCtrl.dispose();
    super.dispose();
  }

  // ── Navigation ────────────────────────────────────────────────
  void _goNext() {
    if (!_formKey.currentState!.validate()) return;
    _pageCtrl.nextPage(duration: 300.ms, curve: Curves.easeInOutCubic);
    setState(() => _currentPage++);
  }

  void _goPrev() {
    if (_currentPage > 0) {
      _pageCtrl.previousPage(duration: 300.ms, curve: Curves.easeInOutCubic);
      setState(() => _currentPage--);
    } else {
      context.read<AuthService>().clearError();
      if (context.canPop()) {
        context.pop();
      } else {
        context.go('/welcome');
      }
    }
  }

  // ── Documents validation ──────────────────────────────────────
  bool _validateDocs() {
    // Numéro NINA/CNI obligatoire
    if (_ninaCtrl.text.trim().isEmpty) {
      _showDocError(
          'Le numéro ${_idType == "NIF" ? "NIF" : _idType} est obligatoire.');
      return false;
    }
    // Fichier pièce d'identité obligatoire
    if (_idCardFile == null) {
      _showDocError('Veuillez scanner ou photographier votre $_idType.');
      return false;
    }
    // Pour TPE : NIF + RCCM obligatoires
    if (_isTpe) {
      if (_nifCtrl.text.trim().isEmpty) {
        _showDocError('Le numéro NIF est obligatoire pour les PME.');
        return false;
      }
      if (_nifFile == null) {
        _showDocError('Le document NIF (attestation fiscale) est obligatoire.');
        return false;
      }
      if (_rccmCtrl.text.trim().isEmpty) {
        _showDocError('Le numéro RCCM est obligatoire pour les PME.');
        return false;
      }
    }
    return true;
  }

  void _showDocError(String msg) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Row(
          children: [
            const Icon(Icons.warning_amber_rounded,
                color: Colors.white, size: 18),
            const SizedBox(width: 8),
            Expanded(child: Text(msg)),
          ],
        ),
        backgroundColor: AppTheme.rose,
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
      ),
    );
  }

  // ── Image picker ──────────────────────────────────────────────
  Future<XFile?> _pickFile() async {
    final picker = ImagePicker();
    final choice = await showModalBottomSheet<String>(
      context: context,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
      ),
      builder: (ctx) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 40,
              height: 4,
              margin: const EdgeInsets.only(top: 12, bottom: 16),
              decoration: BoxDecoration(
                color: AppTheme.slate200,
                borderRadius: BorderRadius.circular(2),
              ),
            ),
            ListTile(
              leading: Container(
                width: 40,
                height: 40,
                decoration: BoxDecoration(
                  color: AppTheme.primaryBlue.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Icon(Icons.camera_alt_outlined,
                    color: AppTheme.primaryBlue),
              ),
              title: const Text('Prendre une photo',
                  style: TextStyle(fontWeight: FontWeight.w600)),
              subtitle: const Text('Appareil photo de votre téléphone'),
              onTap: () => Navigator.pop(ctx, 'camera'),
            ),
            ListTile(
              leading: Container(
                width: 40,
                height: 40,
                decoration: BoxDecoration(
                  color: AppTheme.emerald.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(10),
                ),
                child:
                    Icon(Icons.photo_library_outlined, color: AppTheme.emerald),
              ),
              title: const Text('Choisir dans la galerie',
                  style: TextStyle(fontWeight: FontWeight.w600)),
              subtitle: const Text('Sélectionner un fichier existant'),
              onTap: () => Navigator.pop(ctx, 'gallery'),
            ),
            const SizedBox(height: 12),
          ],
        ),
      ),
    );
    if (choice == null) return null;
    final src = choice == 'camera' ? ImageSource.camera : ImageSource.gallery;
    return picker.pickImage(source: src, imageQuality: 90);
  }

  // ── Submit ────────────────────────────────────────────────────
  Future<void> _submit() async {
    if (!_validateDocs()) return;
    final auth = context.read<AuthService>();
    final ok = await auth.register({
      'full_name': _nameCtrl.text.trim(),
      'email': _emailCtrl.text.trim(),
      'phone': _phoneCtrl.text.trim(),
      'password': _passCtrl.text.trim(),
      'activity_sector': _sector,
      'monthly_revenue': _revenue,
      'monthly_expenses': _expenses,
      'requested_amount': _amount,
      'business_description': _descCtrl.text.trim(),
      'id_number': _isTpe && _nifCtrl.text.trim().isNotEmpty
          ? 'NIF-${_nifCtrl.text.trim()}'
          : _ninaCtrl.text.trim(),
      'id_type': _isTpe ? 'NIF' : _idType,
    });
    if (ok && mounted) context.go('/home');
  }

  // ── UI ────────────────────────────────────────────────────────
  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthService>();
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      backgroundColor: isDark ? AppTheme.darkBg : AppTheme.canvas,
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: _goPrev,
        ),
        title: const OsfLogo(size: 32, showText: false),
        centerTitle: true,
        actions: [
          const LiquidGlassThemeToggle(),
          const SizedBox(width: 8),
          Padding(
            padding: const EdgeInsets.only(right: 16),
            child: Center(
              child: Text(
                '${_currentPage + 1}/3',
                style: TextStyle(
                  color: isDark ? const Color(0xFF94A3B8) : AppTheme.slate500,
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                  fontFamily: 'monospace',
                ),
              ),
            ),
          ),
        ],
      ),
      body: Column(
        children: [
          // ── Step progress bar ─────────────────────────────
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 12, 20, 4),
            child: Column(
              children: [
                Row(
                  children: List.generate(3, (i) {
                    final active = i <= _currentPage;
                    return Expanded(
                      child: Row(
                        children: [
                          Expanded(
                            child: AnimatedContainer(
                              duration: 300.ms,
                              height: 5,
                              decoration: BoxDecoration(
                                color: active
                                    ? AppTheme.primaryBlue
                                    : AppTheme.slate200,
                                borderRadius: BorderRadius.circular(3),
                              ),
                            ),
                          ),
                          if (i < 2) const SizedBox(width: 4),
                        ],
                      ),
                    );
                  }),
                ),
                const SizedBox(height: 8),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    _stepLabel('Identité', 0),
                    _stepLabel('Profil Fin.', 1),
                    _stepLabel('Documents', 2),
                  ],
                ),
              ],
            ),
          ),

          // ── Error banner ──────────────────────────────────
          if (auth.error != null)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 6),
              child: Container(
                width: double.infinity,
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: AppTheme.roseLight,
                  borderRadius: BorderRadius.circular(10),
                  border:
                      Border.all(color: AppTheme.rose.withValues(alpha: 0.4)),
                ),
                child: Row(
                  children: [
                    Icon(Icons.error_outline, color: AppTheme.rose, size: 16),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(auth.error!,
                          style: TextStyle(color: AppTheme.rose, fontSize: 13)),
                    ),
                  ],
                ),
              ).animate().shakeX(),
            ),

          // ── Pages ─────────────────────────────────────────
          Expanded(
            child: Form(
              key: _formKey,
              child: PageView(
                controller: _pageCtrl,
                physics: const NeverScrollableScrollPhysics(),
                children: [
                  _buildStep1(),
                  _buildStep2(),
                  _buildStep3(auth),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _stepLabel(String label, int step) {
    final active = step <= _currentPage;
    final current = step == _currentPage;
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        AnimatedContainer(
          duration: 250.ms,
          width: 18,
          height: 18,
          decoration: BoxDecoration(
            color: active ? AppTheme.primaryBlue : AppTheme.slate200,
            borderRadius: BorderRadius.circular(9),
          ),
          child: Center(
            child: step < _currentPage
                ? const Icon(Icons.check, size: 10, color: Colors.white)
                : Text(
                    '${step + 1}',
                    style: TextStyle(
                      color: active ? Colors.white : AppTheme.slate400,
                      fontSize: 9,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
          ),
        ),
        const SizedBox(width: 4),
        Text(
          label,
          style: TextStyle(
            fontSize: 10,
            fontWeight: current ? FontWeight.w700 : FontWeight.normal,
            color: active ? AppTheme.primaryBlue : AppTheme.slate400,
          ),
        ),
      ],
    );
  }

  // ════════════════════════════════════════════════════════════
  // STEP 1 — Informations personnelles
  // ════════════════════════════════════════════════════════════
  Widget _buildStep1() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Créez votre compte emprunteur',
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  fontWeight: FontWeight.w800,
                ),
          ).animate().fadeIn(duration: 400.ms),
          const SizedBox(height: 4),
          Text(
            'Espace Microfinance Mali • Sécurisé BCEAO',
            style: Theme.of(context).textTheme.bodySmall,
          ).animate().fadeIn(delay: 100.ms),
          const SizedBox(height: 24),
          TextFormField(
            controller: _nameCtrl,
            textCapitalization: TextCapitalization.words,
            decoration: const InputDecoration(
              labelText: 'Nom complet *',
              hintText: 'Ex: Ibrahim Sory Diallo',
              prefixIcon: Icon(Icons.person_outline),
            ),
            validator: (v) => v == null || v.isEmpty ? 'Nom requis' : null,
          ).animate().fadeIn(delay: 200.ms),
          const SizedBox(height: 14),
          TextFormField(
            controller: _emailCtrl,
            keyboardType: TextInputType.emailAddress,
            decoration: const InputDecoration(
              labelText: 'Email *',
              hintText: 'votre@email.ml',
              prefixIcon: Icon(Icons.email_outlined),
            ),
            validator: (v) {
              if (v == null || v.isEmpty) return 'Email requis';
              if (!v.contains('@')) return 'Email invalide';
              return null;
            },
          ).animate().fadeIn(delay: 250.ms),
          const SizedBox(height: 14),
          TextFormField(
            controller: _phoneCtrl,
            keyboardType: TextInputType.phone,
            decoration: const InputDecoration(
              labelText: 'Téléphone *',
              hintText: '+223 70 00 00 00',
              prefixIcon: Icon(Icons.phone_outlined),
            ),
            validator: (v) =>
                v == null || v.isEmpty ? 'Téléphone requis' : null,
          ).animate().fadeIn(delay: 300.ms),
          const SizedBox(height: 14),
          TextFormField(
            controller: _passCtrl,
            obscureText: _obscure,
            decoration: InputDecoration(
              labelText: 'Mot de passe *',
              hintText: 'Minimum 6 caractères',
              prefixIcon: const Icon(Icons.lock_outline),
              suffixIcon: IconButton(
                icon: Icon(_obscure
                    ? Icons.visibility_outlined
                    : Icons.visibility_off_outlined),
                onPressed: () => setState(() => _obscure = !_obscure),
              ),
            ),
            validator: (v) {
              if (v == null || v.length < 6) return 'Minimum 6 caractères';
              return null;
            },
          ).animate().fadeIn(delay: 350.ms),
          const SizedBox(height: 28),
          PrimaryButton(
            label: 'Continuer → Profil financier',
            onPressed: _goNext,
            icon: Icons.arrow_forward,
            width: double.infinity,
          ).animate().fadeIn(delay: 400.ms),
        ],
      ),
    );
  }

  // ════════════════════════════════════════════════════════════
  // STEP 2 — Profil financier
  // ════════════════════════════════════════════════════════════
  Widget _buildStep2() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Votre profil financier',
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  fontWeight: FontWeight.w800,
                ),
          ).animate().fadeIn(duration: 400.ms),
          const SizedBox(height: 4),
          Text(
            "Ces informations servent à calculer votre score d'éligibilité",
            style: Theme.of(context).textTheme.bodySmall,
          ).animate().fadeIn(delay: 100.ms),
          const SizedBox(height: 24),

          // Sector
          const _SLabel(text: "SECTEUR D'ACTIVITÉ *"),
          const SizedBox(height: 8),
          GridView.count(
            crossAxisCount: 2,
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            crossAxisSpacing: 8,
            mainAxisSpacing: 8,
            childAspectRatio: 2.5,
            children: _sectors.map((s) {
              final sel = _sector == s;
              return GestureDetector(
                onTap: () => setState(() => _sector = s),
                child: AnimatedContainer(
                  duration: 200.ms,
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: sel
                        ? AppTheme.primaryBlue.withValues(alpha: 0.08)
                        : Colors.white,
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
                            Text(
                              s,
                              style: TextStyle(
                                inherit: true,
                                fontWeight: FontWeight.w700,
                                fontSize: 12,
                                color: sel
                                    ? AppTheme.primaryBlue
                                    : AppTheme.slate800,
                              ),
                            ),
                            Text(
                              _sectorSubs[s] ?? '',
                              style: const TextStyle(
                                inherit: true,
                                fontSize: 9,
                                color: AppTheme.slate500,
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
          ).animate().fadeIn(delay: 200.ms),
          const SizedBox(height: 20),

          EditableAmountSlider(
            label: 'Revenus Mensuels',
            value: _revenue,
            min: 50000,
            max: 2000000,
            divisions: 39,
            presets: const [50000, 100000, 250000, 500000, 1000000, 2000000],
            onChanged: (v) => setState(() => _revenue = v),
          ),
          const SizedBox(height: 16),

          EditableAmountSlider(
            label: 'Dépenses Mensuelles',
            value: _expenses,
            min: 20000,
            max: 1000000,
            divisions: 49,
            presets: const [20000, 50000, 100000, 250000, 500000, 1000000],
            onChanged: (v) => setState(() => _expenses = v),
          ),
          const SizedBox(height: 16),

          EditableAmountSlider(
            label: 'Montant Souhaité',
            value: _amount,
            min: 100000,
            max: 3000000,
            divisions: 58,
            color: AppTheme.emerald,
            presets: const [250000, 500000, 1000000, 2000000, 3000000, 5000000],
            onChanged: (v) => setState(() => _amount = v),
          ),
          const SizedBox(height: 16),

          TextFormField(
            controller: _descCtrl,
            maxLines: 2,
            decoration: const InputDecoration(
              labelText: "Description de l'activité (optionnel)",
              hintText:
                  'Ex: Vente de tissu Bazin, Stand n°142, Grand Marché...',
              prefixIcon: Icon(Icons.business_outlined),
              alignLabelWithHint: true,
            ),
          ).animate().fadeIn(delay: 350.ms),
          const SizedBox(height: 28),

          PrimaryButton(
            label: 'Continuer → Documents obligatoires',
            onPressed: _goNext,
            icon: Icons.folder_outlined,
            width: double.infinity,
          ).animate().fadeIn(delay: 400.ms),
          const SizedBox(height: 16),
        ],
      ),
    );
  }

  // ════════════════════════════════════════════════════════════
  // STEP 3 — Documents obligatoires
  // ════════════════════════════════════════════════════════════
  Widget _buildStep3(AuthService auth) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Documents obligatoires',
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  fontWeight: FontWeight.w800,
                ),
          ).animate().fadeIn(),
          const SizedBox(height: 4),
          Text(
            'Ces documents sont exigés par la réglementation BCEAO/UEMOA pour toute demande de microcrédit au Mali.',
            style: Theme.of(context).textTheme.bodySmall,
          ).animate().fadeIn(delay: 100.ms),
          const SizedBox(height: 16),

          // ── Info banner ─────────────────────────────────
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: AppTheme.primaryBlue.withValues(alpha: 0.06),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(
                  color: AppTheme.primaryBlue.withValues(alpha: 0.2)),
            ),
            child: Row(
              children: [
                Icon(Icons.security_outlined,
                    color: AppTheme.primaryBlue, size: 18),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    'Vos données sont chiffrées et traitées conformément aux directives BCEAO n°01/2023. Aucun document n\'est partagé à des tiers.',
                    style: TextStyle(color: AppTheme.primaryBlue, fontSize: 11),
                  ),
                ),
              ],
            ),
          ).animate().fadeIn(delay: 120.ms),
          const SizedBox(height: 20),

          // ════════════════════════════════════════════════
          // Section A — Pièce d'identité (TOUS)
          // ════════════════════════════════════════════════
          _sectionHeader(
            icon: Icons.badge_outlined,
            color: AppTheme.primaryBlue,
            title: 'A. Pièce d\'identité',
            badge: 'OBLIGATOIRE',
            badgeColor: AppTheme.rose,
          ),
          const SizedBox(height: 12),

          // ID type selector
          const _SLabel(text: 'TYPE DE DOCUMENT *'),
          const SizedBox(height: 8),
          Row(
            children: ['NINA', 'CNI', 'Passeport'].map((t) {
              final sel = _idType == t;
              return Expanded(
                child: GestureDetector(
                  onTap: () => setState(() => _idType = t),
                  child: AnimatedContainer(
                    duration: 200.ms,
                    margin: const EdgeInsets.only(right: 6),
                    padding: const EdgeInsets.symmetric(vertical: 10),
                    decoration: BoxDecoration(
                      color: sel ? AppTheme.primaryBlue : Colors.transparent,
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(
                        color: sel ? AppTheme.primaryBlue : AppTheme.slate200,
                      ),
                    ),
                    child: Column(
                      children: [
                        Icon(
                          t == 'NINA'
                              ? Icons.fingerprint
                              : t == 'CNI'
                                  ? Icons.credit_card
                                  : Icons.book_outlined,
                          size: 16,
                          color: sel ? Colors.white : AppTheme.slate500,
                        ),
                        const SizedBox(height: 2),
                        Text(
                          t,
                          style: TextStyle(
                            fontSize: 11,
                            fontWeight: FontWeight.w700,
                            color: sel ? Colors.white : AppTheme.slate600,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              );
            }).toList(),
          ),
          const SizedBox(height: 14),

          // ID number input
          TextFormField(
            controller: _ninaCtrl,
            textCapitalization: TextCapitalization.characters,
            decoration: InputDecoration(
              labelText: 'Numéro $_idType *',
              hintText: _idType == 'NINA'
                  ? 'Ex: 12345678901234'
                  : _idType == 'CNI'
                      ? 'Ex: CNI-123456'
                      : 'Ex: PASS-ML-123456',
              prefixIcon: const Icon(Icons.tag),
              suffixIcon: _ninaCtrl.text.isNotEmpty
                  ? const Icon(Icons.check_circle, color: AppTheme.emerald)
                  : null,
            ),
            onChanged: (_) => setState(() {}),
          ).animate().fadeIn(delay: 200.ms),
          const SizedBox(height: 14),

          // ID Card file upload
          _docUploadZone(
            label: 'Photo / Scan de la $_idType *',
            description: 'Recto-verso, lisible, sans reflet • JPG, PNG ou PDF',
            file: _idCardFile,
            required: true,
            icon: Icons.credit_card,
            onPick: () async {
              final f = await _pickFile();
              if (f != null) setState(() => _idCardFile = f);
            },
            onRemove: () => setState(() => _idCardFile = null),
          ),

          const SizedBox(height: 24),

          // ════════════════════════════════════════════════
          // Section B — Documents secteur spécifique
          // ════════════════════════════════════════════════
          if (_isTpe) ...[
            _sectionHeader(
              icon: Icons.business_center_outlined,
              color: AppTheme.purple,
              title: 'B. Documents PME / TPE',
              badge: 'OBLIGATOIRE',
              badgeColor: AppTheme.rose,
            ),
            const SizedBox(height: 12),

            // NIF
            _subHeader(
                'NIF — Numéro d\'Identification Fiscale', AppTheme.purple),
            const SizedBox(height: 8),
            TextFormField(
              controller: _nifCtrl,
              textCapitalization: TextCapitalization.characters,
              keyboardType: TextInputType.text,
              decoration: const InputDecoration(
                labelText: 'Numéro NIF *',
                hintText: 'Ex: 123456789M',
                prefixIcon: Icon(Icons.receipt_long_outlined),
              ),
              onChanged: (_) => setState(() {}),
            ).animate().fadeIn(delay: 100.ms),
            const SizedBox(height: 10),
            _docUploadZone(
              label: 'Attestation NIF (DGI Mali) *',
              description:
                  'Délivrée par la Direction Générale des Impôts (DGI) • PDF ou image',
              file: _nifFile,
              required: true,
              icon: Icons.receipt_outlined,
              iconColor: AppTheme.purple,
              onPick: () async {
                final f = await _pickFile();
                if (f != null) setState(() => _nifFile = f);
              },
              onRemove: () => setState(() => _nifFile = null),
            ),

            const SizedBox(height: 18),

            // RCCM
            _subHeader('RCCM — Registre du Commerce et du Crédit Mobilier',
                AppTheme.amber),
            const SizedBox(height: 8),
            TextFormField(
              controller: _rccmCtrl,
              textCapitalization: TextCapitalization.characters,
              decoration: const InputDecoration(
                labelText: 'Numéro RCCM *',
                hintText: 'Ex: BKO/2023/B/12345',
                prefixIcon: Icon(Icons.store_outlined),
              ),
              onChanged: (_) => setState(() {}),
            ).animate().fadeIn(delay: 150.ms),
            const SizedBox(height: 10),
            _docUploadZone(
              label: 'Extrait RCCM *',
              description:
                  'Extrait du Registre du Commerce (Tribunal de Commerce de Bamako)',
              file: _rccmFile,
              required: true,
              icon: Icons.gavel_outlined,
              iconColor: AppTheme.amber,
              onPick: () async {
                final f = await _pickFile();
                if (f != null) setState(() => _rccmFile = f);
              },
              onRemove: () => setState(() => _rccmFile = null),
            ),

            const SizedBox(height: 18),

            // Attestation locale optionnelle
            _sectionHeader(
              icon: Icons.assignment_outlined,
              color: AppTheme.slate500,
              title: 'C. Document complémentaire (optionnel)',
              badge: 'OPTIONNEL',
              badgeColor: AppTheme.slate400,
            ),
            const SizedBox(height: 10),
            _docUploadZone(
              label: 'Bilan comptable ou déclaration fiscale',
              description: 'Dernier exercice fiscal • PDF recommandé',
              file: _attestationFile,
              required: false,
              icon: Icons.bar_chart_outlined,
              iconColor: AppTheme.slate500,
              onPick: () async {
                final f = await _pickFile();
                if (f != null) setState(() => _attestationFile = f);
              },
              onRemove: () => setState(() => _attestationFile = null),
            ),
          ] else ...[
            // Non-TPE sectors: optional attestation
            _sectionHeader(
              icon: Icons.assignment_outlined,
              color: AppTheme.amber,
              title: 'B. Attestation d\'activité',
              badge: 'RECOMMANDÉ',
              badgeColor: AppTheme.amber,
            ),
            const SizedBox(height: 10),
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: AppTheme.amberLight,
                borderRadius: BorderRadius.circular(10),
                border:
                    Border.all(color: AppTheme.amber.withValues(alpha: 0.3)),
              ),
              child: Row(
                children: [
                  Icon(Icons.info_outline, color: AppTheme.amber, size: 16),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      _sector == 'Commerce'
                          ? 'Carte de commerçant (Mairie) ou registre de reçus de vente'
                          : _sector == 'Agriculture'
                              ? 'Attestation d\'exploitation agricole ou titre de concession rurale'
                              : 'Carte d\'artisan (APIM) ou attestation de l\'association de métier',
                      style: TextStyle(
                          color: AppTheme.amber,
                          fontSize: 11,
                          fontWeight: FontWeight.w500),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 10),
            _docUploadZone(
              label: _sector == 'Commerce'
                  ? 'Carte de commerçant / Registre de reçus'
                  : _sector == 'Agriculture'
                      ? 'Attestation d\'exploitation agricole'
                      : 'Carte d\'artisan APIM',
              description: 'Document non obligatoire mais améliore votre score',
              file: _attestationFile,
              required: false,
              icon: Icons.assignment_outlined,
              iconColor: AppTheme.amber,
              onPick: () async {
                final f = await _pickFile();
                if (f != null) setState(() => _attestationFile = f);
              },
              onRemove: () => setState(() => _attestationFile = null),
            ),
          ],

          const SizedBox(height: 24),

          // ── Required docs checklist ─────────────────────
          _buildDocChecklist(),

          const SizedBox(height: 24),

          // ── Submit ──────────────────────────────────────
          PrimaryButton(
            label: 'Créer mon compte',
            onPressed: _submit,
            isLoading: auth.isLoading,
            icon: Icons.check_circle_outline,
            width: double.infinity,
          ).animate().fadeIn(delay: 200.ms),
          const SizedBox(height: 8),
          Center(
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: const [
                Icon(Icons.lock_outline_rounded, size: 12, color: AppTheme.slate400),
                SizedBox(width: 4),
                Text(
                  'Vos données sont protégées par chiffrement AES-256',
                  style: TextStyle(inherit: true, color: AppTheme.slate400, fontSize: 10),
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),
        ],
      ),
    );
  }

  // ── Doc checklist widget ─────────────────────────────────────
  Widget _buildDocChecklist() {
    final items = <_CheckItem>[
      _CheckItem(
        label: 'Numéro $_idType renseigné',
        ok: _ninaCtrl.text.trim().isNotEmpty,
        required: true,
      ),
      _CheckItem(
        label: 'Photo/Scan $_idType ajoutée',
        ok: _idCardFile != null,
        required: true,
      ),
      if (_isTpe) ...[
        _CheckItem(
          label: 'Numéro NIF renseigné',
          ok: _nifCtrl.text.trim().isNotEmpty,
          required: true,
        ),
        _CheckItem(
          label: 'Attestation NIF ajoutée',
          ok: _nifFile != null,
          required: true,
        ),
        _CheckItem(
          label: 'Numéro RCCM renseigné',
          ok: _rccmCtrl.text.trim().isNotEmpty,
          required: true,
        ),
      ],
      _CheckItem(
        label: 'Document complémentaire',
        ok: _attestationFile != null,
        required: false,
      ),
    ];

    final allRequired = items.where((i) => i.required).every((i) => i.ok);

    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: allRequired ? AppTheme.emeraldLight : AppTheme.slate50,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: allRequired
              ? AppTheme.emerald.withValues(alpha: 0.4)
              : AppTheme.slate200,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                allRequired ? Icons.check_circle : Icons.checklist,
                color: allRequired ? AppTheme.emerald : AppTheme.slate500,
                size: 16,
              ),
              const SizedBox(width: 8),
              Text(
                allRequired
                    ? 'Tous les documents obligatoires sont fournis'
                    : 'Récapitulatif des documents',
                style: TextStyle(
                  fontWeight: FontWeight.w700,
                  fontSize: 12,
                  color: allRequired ? AppTheme.emerald : AppTheme.slate700,
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          ...items.map(
            (item) => Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: Row(
                children: [
                  Container(
                    width: 18,
                    height: 18,
                    decoration: BoxDecoration(
                      color: item.ok
                          ? AppTheme.emerald
                          : item.required
                              ? AppTheme.rose.withValues(alpha: 0.15)
                              : AppTheme.slate200,
                      borderRadius: BorderRadius.circular(9),
                      border: item.ok
                          ? null
                          : Border.all(
                              color: item.required
                                  ? AppTheme.rose.withValues(alpha: 0.5)
                                  : AppTheme.slate300,
                            ),
                    ),
                    child: item.ok
                        ? const Icon(Icons.check, size: 11, color: Colors.white)
                        : null,
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      item.label,
                      style: TextStyle(
                        fontSize: 12,
                        color: item.ok
                            ? AppTheme.slate700
                            : item.required
                                ? AppTheme.rose
                                : AppTheme.slate500,
                        fontWeight: item.required && !item.ok
                            ? FontWeight.w600
                            : FontWeight.normal,
                      ),
                    ),
                  ),
                  if (!item.required)
                    Text(
                      'optionnel',
                      style: TextStyle(
                          color: AppTheme.slate400,
                          fontSize: 9,
                          fontStyle: FontStyle.italic),
                    ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  // ── Doc upload zone widget ───────────────────────────────────
  Widget _docUploadZone({
    required String label,
    required String description,
    required XFile? file,
    required bool required,
    required IconData icon,
    required VoidCallback onPick,
    required VoidCallback onRemove,
    Color? iconColor,
  }) {
    final color = iconColor ?? AppTheme.primaryBlue;
    final uploaded = file != null;

    return GestureDetector(
      onTap: uploaded ? null : onPick,
      child: AnimatedContainer(
        duration: 250.ms,
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color:
              uploaded ? AppTheme.emeraldLight : color.withValues(alpha: 0.04),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: uploaded
                ? AppTheme.emerald.withValues(alpha: 0.5)
                : required
                    ? color.withValues(alpha: 0.3)
                    : AppTheme.slate200,
            width: 1.5,
            style: uploaded ? BorderStyle.solid : BorderStyle.solid,
          ),
        ),
        child: Row(
          children: [
            Container(
              width: 44,
              height: 44,
              decoration: BoxDecoration(
                color: uploaded
                    ? AppTheme.emerald.withValues(alpha: 0.15)
                    : color.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Icon(
                uploaded ? Icons.check_circle_outline : icon,
                color: uploaded ? AppTheme.emerald : color,
                size: 22,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          uploaded ? file.name : label,
                          style: TextStyle(
                            fontWeight: FontWeight.w700,
                            fontSize: 12,
                            color:
                                uploaded ? AppTheme.emerald : AppTheme.slate800,
                          ),
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                      if (required && !uploaded)
                        Container(
                          margin: const EdgeInsets.only(left: 6),
                          padding: const EdgeInsets.symmetric(
                              horizontal: 5, vertical: 1),
                          decoration: BoxDecoration(
                            color: AppTheme.rose.withValues(alpha: 0.12),
                            borderRadius: BorderRadius.circular(4),
                            border: Border.all(
                                color: AppTheme.rose.withValues(alpha: 0.3)),
                          ),
                          child: Text(
                            'requis',
                            style: TextStyle(
                                color: AppTheme.rose,
                                fontSize: 8,
                                fontWeight: FontWeight.w700),
                          ),
                        ),
                    ],
                  ),
                  Text(
                    uploaded
                        ? 'Document ajouté • Appuyez sur × pour retirer'
                        : description,
                    style: TextStyle(
                      color: uploaded ? AppTheme.emerald : AppTheme.slate400,
                      fontSize: 10,
                    ),
                  ),
                ],
              ),
            ),
            if (uploaded)
              IconButton(
                icon: Icon(Icons.close, color: AppTheme.rose, size: 18),
                onPressed: onRemove,
                padding: EdgeInsets.zero,
                constraints: const BoxConstraints(minWidth: 28, minHeight: 28),
              )
            else
              Icon(Icons.upload_outlined, color: color, size: 20),
          ],
        ),
      ),
    );
  }

  // ── Helpers ───────────────────────────────────────────────────
  Widget _sectionHeader({
    required IconData icon,
    required Color color,
    required String title,
    required String badge,
    required Color badgeColor,
  }) {
    return Row(
      children: [
        Container(
          width: 32,
          height: 32,
          decoration: BoxDecoration(
            color: color.withValues(alpha: 0.12),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Icon(icon, color: color, size: 16),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: Text(
            title,
            style: TextStyle(
                fontWeight: FontWeight.w700,
                fontSize: 13,
                color: AppTheme.slate800),
          ),
        ),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
          decoration: BoxDecoration(
            color: badgeColor.withValues(alpha: 0.12),
            borderRadius: BorderRadius.circular(6),
            border: Border.all(color: badgeColor.withValues(alpha: 0.35)),
          ),
          child: Text(
            badge,
            style: TextStyle(
              color: badgeColor,
              fontSize: 8,
              fontWeight: FontWeight.w800,
              letterSpacing: 0.4,
            ),
          ),
        ),
      ],
    );
  }

  Widget _subHeader(String text, Color color) {
    return Text(
      text,
      style: TextStyle(
        fontSize: 11,
        fontWeight: FontWeight.w700,
        color: color,
      ),
    );
  }
}

// ── Utility widgets ─────────────────────────────────────────────
class _SLabel extends StatelessWidget {
  final String text;
  const _SLabel({required this.text});

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

class _CheckItem {
  final String label;
  final bool ok;
  final bool required;
  const _CheckItem(
      {required this.label, required this.ok, required this.required});
}
