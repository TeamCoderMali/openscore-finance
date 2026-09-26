import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:provider/provider.dart';
import '../../core/services/api_service.dart';
import '../../core/services/auth_service.dart';
import '../../core/theme/app_theme.dart';
import '../../shared/widgets/shared_widgets.dart';

class SimulatorScreen extends StatefulWidget {
  const SimulatorScreen({super.key});

  @override
  State<SimulatorScreen> createState() => _SimulatorScreenState();
}

class _SimulatorScreenState extends State<SimulatorScreen> {
  final _api = ApiService();

  // Basic loan params
  double _amount = 1000000;
  double _duration = 12;
  String _sector = 'Commerce';

  // Financial inputs
  double _revenue = 500000;
  double _secondaryRevenue = 0;
  double _expenses = 200000;
  int _regularityMonths = 12;
  double _yearsInBusiness = 3;

  // Multiple Collaterals / Guarantees
  final List<Map<String, dynamic>> _guarantees = [];
  String _tempGuaranteeType = 'terrain';
  final _tempGuaranteeDescCtrl = TextEditingController(text: 'Parcelle Bamako');
  final _tempGuaranteeValCtrl = TextEditingController(text: '1500000');

  // Multiple Debts
  final List<Map<String, dynamic>> _debts = [];
  final _tempDebtCreditorCtrl = TextEditingController(text: 'Tontine / Banque');
  final _tempDebtMonthlyCtrl = TextEditingController(text: '30000');

  // Scoring Simulation Result (Base 100)
  bool _calculating = false;
  Map<String, dynamic>? _simResult;

  static const double _rate = 0.015; // 1.5% mensuel dégressif BCEAO

  double get _totalDebtsMonthly {
    return _debts.fold(0.0, (sum, d) => sum + (d['monthly_payment'] as num).toDouble());
  }

  double get _totalGuaranteesVal {
    return _guarantees.fold(0.0, (sum, g) => sum + (g['estimated_value'] as num).toDouble());
  }

  double get _monthlyPayment {
    if (_duration <= 0 || _amount <= 0) return 0;
    return (_amount / _duration) + (_amount * _rate);
  }

  double get _disposableIncome {
    return (_revenue + _secondaryRevenue) - (_expenses + _totalDebtsMonthly);
  }

  double get _debtEffortRate {
    final totalRev = _revenue + _secondaryRevenue;
    if (totalRev <= 0) return 0;
    final totalMonthlyCharges = _monthlyPayment + _totalDebtsMonthly;
    return (totalMonthlyCharges / totalRev * 100).clamp(0, 100);
  }

  @override
  void dispose() {
    _tempGuaranteeDescCtrl.dispose();
    _tempGuaranteeValCtrl.dispose();
    _tempDebtCreditorCtrl.dispose();
    _tempDebtMonthlyCtrl.dispose();
    super.dispose();
  }

  Future<void> _calculateScoring() async {
    setState(() => _calculating = true);
    try {
      final res = await _api.simulateScoring({
        'monthly_revenue': _revenue,
        'secondary_revenue': _secondaryRevenue,
        'monthly_expenses': _expenses,
        'other_recurring_expenses': 0,
        'revenue_regularity_months': _regularityMonths,
        'years_in_business': _yearsInBusiness,
        'requested_amount': _amount,
        'requested_duration_months': _duration.toInt(),
        'activity_sector': _sector,
        'guarantees': _guarantees,
        'debts': _debts,
      });
      setState(() => _simResult = res);
    } catch (e) {
      // Offline fallback heuristic scoring on base 100
      final net = _disposableIncome;
      final ratio = _debtEffortRate / 100.0;
      int baseScore = 60;
      if (ratio <= 0.30) {
        baseScore += 20;
      } else if (ratio <= 0.40) {
        baseScore += 10;
      } else {
        baseScore -= 20;
      }

      if (net >= 100000) baseScore += 10;
      if (_totalGuaranteesVal >= _amount) baseScore += 10;
      final clamped = baseScore.clamp(20, 95);

      setState(() {
        _simResult = {
          'score': clamped,
          'risk_level': clamped >= 75 ? 'low' : (clamped >= 60 ? 'medium' : 'high'),
          'decision': clamped >= 75 ? 'approved' : (clamped >= 60 ? 'adjusted' : 'rejected'),
          'disposable_income': net,
          'debt_ratio': ratio,
          'guarantee_coverage_ratio': _amount > 0 ? (_totalGuaranteesVal / _amount) : 0,
        };
      });
    } finally {
      setState(() => _calculating = false);
    }
  }

  void _showAddGuaranteeDialog() {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Ajouter une Garantie / Gage', style: TextStyle(fontSize: 15, fontWeight: FontWeight.w800)),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            DropdownButtonFormField<String>(
              initialValue: _tempGuaranteeType,
              decoration: const InputDecoration(labelText: 'Type de bien'),
              items: const [
                DropdownMenuItem(value: 'terrain', child: Text('Terrain / Titre foncier')),
                DropdownMenuItem(value: 'maison', child: Text('Maison / Bâtiment')),
                DropdownMenuItem(value: 'vehicule', child: Text('Véhicule / Moto')),
                DropdownMenuItem(value: 'equipement', child: Text('Matériel professionnel')),
                DropdownMenuItem(value: 'stock', child: Text('Stock marchandises')),
                DropdownMenuItem(value: 'caution', child: Text('Caution tontine')),
              ],
              onChanged: (v) => _tempGuaranteeType = v ?? 'terrain',
            ),
            const SizedBox(height: 8),
            TextField(
              controller: _tempGuaranteeDescCtrl,
              decoration: const InputDecoration(labelText: 'Description'),
            ),
            const SizedBox(height: 8),
            TextField(
              controller: _tempGuaranteeValCtrl,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(labelText: 'Valeur estimée (FCFA)'),
            ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Annuler')),
          ElevatedButton(
            onPressed: () {
              final val = double.tryParse(_tempGuaranteeValCtrl.text.replaceAll(' ', '')) ?? 0;
              if (val > 0) {
                setState(() {
                  _guarantees.add({
                    'guarantee_type': _tempGuaranteeType,
                    'description': _tempGuaranteeDescCtrl.text.trim(),
                    'estimated_value': val,
                    'retained_value': val * 0.7,
                  });
                });
                Navigator.pop(ctx);
              }
            },
            child: const Text('Ajouter'),
          ),
        ],
      ),
    );
  }

  void _showAddDebtDialog() {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Ajouter une Dette en cours', style: TextStyle(fontSize: 15, fontWeight: FontWeight.w800)),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: _tempDebtCreditorCtrl,
              decoration: const InputDecoration(labelText: 'Créancier (Banque, IMF, Tontine)'),
            ),
            const SizedBox(height: 8),
            TextField(
              controller: _tempDebtMonthlyCtrl,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(labelText: 'Mensualité payée (FCFA)'),
            ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Annuler')),
          ElevatedButton(
            onPressed: () {
              final val = double.tryParse(_tempDebtMonthlyCtrl.text.replaceAll(' ', '')) ?? 0;
              if (val > 0) {
                setState(() {
                  _debts.add({
                    'creditor_name': _tempDebtCreditorCtrl.text.trim(),
                    'monthly_payment': val,
                    'remaining_amount': val * 6,
                  });
                });
                Navigator.pop(ctx);
              }
            },
            child: const Text('Ajouter'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final auth = context.watch<AuthService>();

    return Scaffold(
      appBar: AppBar(
        title: const Text('Simulateur de Solvabilité', style: TextStyle(fontSize: 15, fontWeight: FontWeight.w800)),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header
            Text(
              'Simulateur & Éligibilité Prudentielle',
              style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w900),
            ),
            const SizedBox(height: 4),
            Text(
              'Calculez votre score d\'éligibilité sur base 100 en intégrant vos garanties et dettes.',
              style: TextStyle(fontSize: 12, color: AppTheme.slate500),
            ),
            const SizedBox(height: 20),

            // ── HERO SCORING RESULT (BASE 100) ─────────────────────────
            if (_simResult != null) ...[
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                  color: _simResult!['score'] >= 75
                      ? AppTheme.emeraldLight
                      : (_simResult!['score'] >= 60 ? const Color(0xFFdbeafe) : AppTheme.roseLight),
                  border: Border.all(
                    color: _simResult!['score'] >= 75
                        ? AppTheme.emerald
                        : (_simResult!['score'] >= 60 ? AppTheme.primaryBlue : AppTheme.rose),
                    width: 1.5,
                  ),
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Column(
                  children: [
                    const Text('SCORE ESTIMÉ DE SOLVABILITÉ', style: TextStyle(fontSize: 10, fontWeight: FontWeight.w800, letterSpacing: 0.8)),
                    const SizedBox(height: 6),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      crossAxisAlignment: CrossAxisAlignment.baseline,
                      textBaseline: TextBaseline.alphabetic,
                      children: [
                        Text(
                          '${_simResult!['score']}',
                          style: TextStyle(
                            fontSize: 48,
                            fontWeight: FontWeight.w900,
                            fontFamily: 'monospace',
                            color: _simResult!['score'] >= 75
                                ? AppTheme.emerald
                                : (_simResult!['score'] >= 60 ? AppTheme.primaryBlue : AppTheme.rose),
                          ),
                        ),
                        const Text(' / 100', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800, color: AppTheme.slate500)),
                      ],
                    ),
                    const SizedBox(height: 6),
                    Text(
                      _simResult!['score'] >= 75
                          ? 'Avis Favorable : Capacité d\'emprunt optimale'
                          : (_simResult!['score'] >= 60 ? 'Avis Ajusté : Réduction de montant conseillée' : 'Risque Élevé : Garanties supplémentaires requises'),
                      style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 12),
                    ),
                  ],
                ),
              ).animate().scale(duration: 300.ms),
              const SizedBox(height: 20),
            ],

            // ── LOAN PARAMETERS ────────────────────────────────────────
            OSFCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('CONDITIONS DU PRÊT SOUHAITÉ', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w800, color: AppTheme.slate500)),
                  const SizedBox(height: 14),

                  // Amount
                  EditableAmountSlider(
                    label: 'Montant Demandé',
                    value: _amount,
                    min: 100000,
                    max: 5000000,
                    divisions: 49,
                    color: AppTheme.primaryBlue,
                    presets: const [250000, 500000, 1000000, 2000000, 3000000],
                    onChanged: (v) => setState(() => _amount = v),
                  ),

                  const SizedBox(height: 16),

                  // Duration
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text('Durée de remboursement', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600)),
                      Text('${_duration.toInt()} mois', style: const TextStyle(fontFamily: 'monospace', fontWeight: FontWeight.w800, fontSize: 13, color: AppTheme.purple)),
                    ],
                  ),
                  Slider(
                    value: _duration,
                    min: 3,
                    max: 36,
                    divisions: 33,
                    activeColor: AppTheme.purple,
                    onChanged: (v) => setState(() => _duration = v),
                  ),

                  const SizedBox(height: 8),

                  // Sector
                  DropdownButtonFormField<String>(
                    initialValue: _sector,
                    decoration: const InputDecoration(labelText: 'Secteur d\'activité'),
                    items: const [
                      DropdownMenuItem(value: 'Commerce', child: Text('Commerce de détail / Grossiste')),
                      DropdownMenuItem(value: 'Agriculture', child: Text('Agriculture & Maraîchage')),
                      DropdownMenuItem(value: 'Artisanat', child: Text('Artisanat & Métiers')),
                      DropdownMenuItem(value: 'TPE', child: Text('Très Petite Entreprise / Services')),
                      DropdownMenuItem(value: 'Autre', child: Text('Autre secteur d\'activité')),
                    ],
                    onChanged: (v) => setState(() => _sector = v ?? 'Commerce'),
                  ),
                ],
              ),
            ),

            const SizedBox(height: 16),

            // ── FINANCIAL HEALTH & ACTIVITY ────────────────────────────
            OSFCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('SITUATION FINANCIÈRE & ACTIVITÉ', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w800, color: AppTheme.slate500)),
                  const SizedBox(height: 14),

                  EditableAmountSlider(
                    label: 'Revenus Mensuels Principaux',
                    value: _revenue,
                    min: 50000,
                    max: 3000000,
                    divisions: 59,
                    color: AppTheme.emerald,
                    onChanged: (v) => setState(() => _revenue = v),
                  ),

                  const SizedBox(height: 14),

                  EditableAmountSlider(
                    label: 'Revenus Secondaires',
                    value: _secondaryRevenue,
                    min: 0,
                    max: 1500000,
                    divisions: 30,
                    color: AppTheme.emerald,
                    onChanged: (v) => setState(() => _secondaryRevenue = v),
                  ),

                  const SizedBox(height: 14),

                  EditableAmountSlider(
                    label: 'Charges & Dépenses Mensuelles',
                    value: _expenses,
                    min: 20000,
                    max: 2000000,
                    divisions: 40,
                    color: AppTheme.rose,
                    onChanged: (v) => setState(() => _expenses = v),
                  ),

                  const SizedBox(height: 16),

                  Row(
                    children: [
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text('Régularité (Mois)', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700)),
                            Slider(
                              value: _regularityMonths.toDouble(),
                              min: 1,
                              max: 12,
                              divisions: 11,
                              activeColor: AppTheme.primaryBlue,
                              onChanged: (v) => setState(() => _regularityMonths = v.toInt()),
                            ),
                            Center(child: Text('$_regularityMonths / 12 mois', style: const TextStyle(fontFamily: 'monospace', fontSize: 11, fontWeight: FontWeight.w700))),
                          ],
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text('Ancienneté d\'activité', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700)),
                            Slider(
                              value: _yearsInBusiness,
                              min: 0.5,
                              max: 10,
                              divisions: 19,
                              activeColor: AppTheme.primaryBlue,
                              onChanged: (v) => setState(() => _yearsInBusiness = v),
                            ),
                            Center(child: Text('${_yearsInBusiness.toStringAsFixed(1)} ans', style: const TextStyle(fontFamily: 'monospace', fontSize: 11, fontWeight: FontWeight.w700))),
                          ],
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),

            const SizedBox(height: 16),

            // ── MULTI-GUARANTEES SECTION ───────────────────────────────
            OSFCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text('GARANTIES & BIENS EN GAGE', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w800, color: AppTheme.slate500)),
                      TextButton.icon(
                        onPressed: _showAddGuaranteeDialog,
                        icon: const Icon(Icons.add, size: 16),
                        label: const Text('Ajouter', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700)),
                      ),
                    ],
                  ),
                  if (_guarantees.isEmpty)
                    Text('Aucun bien en garantie ajouté. L\'ajout de garanties augmente significativement votre score.', style: TextStyle(fontSize: 11, color: AppTheme.slate400))
                  else ...[
                    ..._guarantees.map((g) => ListTile(
                          dense: true,
                          contentPadding: EdgeInsets.zero,
                          title: Text(g['description'], style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700)),
                          subtitle: Text('Type : ${g['guarantee_type']}', style: const TextStyle(fontSize: 10)),
                          trailing: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Text(formatFCFA((g['estimated_value'] as num).toDouble()), style: const TextStyle(fontFamily: 'monospace', fontWeight: FontWeight.w700, fontSize: 12)),
                              IconButton(
                                icon: const Icon(Icons.close, size: 16, color: AppTheme.rose),
                                onPressed: () => setState(() => _guarantees.remove(g)),
                              ),
                            ],
                          ),
                        )),
                    const Divider(),
                    Text('Total Garanties : ${formatFCFA(_totalGuaranteesVal)} (${(_totalGuaranteesVal / _amount * 100).toStringAsFixed(0)}% du prêt)',
                        style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w800, color: AppTheme.emerald)),
                  ],
                ],
              ),
            ),

            const SizedBox(height: 16),

            // ── MULTI-DEBTS SECTION ────────────────────────────────────
            OSFCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text('DETTES & ENGAGEMENTS EN COURS', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w800, color: AppTheme.slate500)),
                      TextButton.icon(
                        onPressed: _showAddDebtDialog,
                        icon: const Icon(Icons.add, size: 16),
                        label: const Text('Ajouter', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700)),
                      ),
                    ],
                  ),
                  if (_debts.isEmpty)
                    Text('Aucune dette en cours déclarée.', style: TextStyle(fontSize: 11, color: AppTheme.slate400))
                  else ...[
                    ..._debts.map((d) => ListTile(
                          dense: true,
                          contentPadding: EdgeInsets.zero,
                          title: Text(d['creditor_name'], style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700)),
                          trailing: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Text('${formatFCFA((d['monthly_payment'] as num).toDouble())} / mois',
                                  style: const TextStyle(fontFamily: 'monospace', fontWeight: FontWeight.w700, fontSize: 11, color: AppTheme.rose)),
                              IconButton(
                                icon: const Icon(Icons.close, size: 16, color: AppTheme.rose),
                                onPressed: () => setState(() => _debts.remove(d)),
                              ),
                            ],
                          ),
                        )),
                    const Divider(),
                    Text('Mensualités des dettes : ${formatFCFA(_totalDebtsMonthly)} / mois',
                        style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w800, color: AppTheme.rose)),
                  ],
                ],
              ),
            ),

            const SizedBox(height: 20),

            // ── CALCULATE SCORE BUTTON ─────────────────────────────────
            SizedBox(
              width: double.infinity,
              child: ElevatedButton.icon(
                onPressed: _calculating ? null : _calculateScoring,
                icon: _calculating
                    ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                    : const Icon(Icons.auto_awesome_rounded),
                label: Text(
                  _calculating ? 'Calcul ML & SHAP en cours...' : 'Calculer mon Score de Solvabilité (/100)',
                  style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w800),
                ),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppTheme.primaryBlue,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                ),
              ),
            ),

            if (!auth.isAuthenticated) ...[
              const SizedBox(height: 28),

              // ── GUIDE PÉDAGOGIQUE POUR LES NON-ADHÉRENTS ───────────────
              Container(
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                  color: isDark ? AppTheme.darkCard : Colors.white,
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(color: AppTheme.primaryBlue.withValues(alpha: 0.3)),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withValues(alpha: 0.04),
                      blurRadius: 10,
                      offset: const Offset(0, 4),
                    ),
                  ],
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.all(8),
                          decoration: BoxDecoration(
                            color: AppTheme.primaryBlue.withValues(alpha: 0.1),
                            shape: BoxShape.circle,
                          ),
                          child: const Icon(Icons.menu_book_rounded, color: AppTheme.primaryBlue, size: 22),
                        ),
                        const SizedBox(width: 12),
                        const Expanded(
                          child: Text(
                            'Comment ouvrir un compte chez une IMF partenaire ?',
                            style: TextStyle(fontWeight: FontWeight.w800, fontSize: 14),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    const Text(
                      'Pour recevoir votre crédit et débloquer les fonds en toute sécurité, un compte d\'épargne ou livret IMF officiel est requis selon les règles BCEAO.',
                      style: TextStyle(fontSize: 12, height: 1.4),
                    ),
                    const SizedBox(height: 16),

                    _buildGuideStep(
                      number: '1',
                      title: 'Choisir votre agence de proximité',
                      desc: 'Rendez-vous dans une agence ou guichet de nos IMF partenaires (Kafo Jiginew, Nyèsigiso, CMF, etc.).',
                    ),
                    const SizedBox(height: 12),
                    _buildGuideStep(
                      number: '2',
                      title: 'Fournir les pièces requises',
                      desc: '• 1 Copie de votre carte NINA, CNI biométrique ou passeport\n• 2 Photos d\'identité récentes\n• Justificatif de domicile (facture EDM/SOMAGEP ou certificat)',
                    ),
                    const SizedBox(height: 12),
                    _buildGuideStep(
                      number: '3',
                      title: 'Effectuer le versement initial d\'adhésion',
                      desc: 'Dépôt symbolique d\'ouverture de livret (généralement 10 000 à 25 000 FCFA selon l\'institution).',
                    ),
                    const SizedBox(height: 12),
                    _buildGuideStep(
                      number: '4',
                      title: 'Obtenir votre identifiant de compte CMF',
                      desc: 'Votre numéro officiel (ex: CMF-2026-XXXXXX) vous permet de soumettre directement votre demande de crédit sur OpenScore Finance !',
                    ),
                  ],
                ),
              ),
            ],

            const SizedBox(height: 60),
          ],
        ),
      ),
    );
  }

  Widget _buildGuideStep({required String number, required String title, required String desc}) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          width: 24,
          height: 24,
          decoration: const BoxDecoration(
            color: AppTheme.primaryBlue,
            shape: BoxShape.circle,
          ),
          alignment: Alignment.center,
          child: Text(
            number,
            style: const TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.w800),
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(title, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12)),
              const SizedBox(height: 2),
              Text(desc, style: TextStyle(fontSize: 11, color: AppTheme.slate500, height: 1.35)),
            ],
          ),
        ),
      ],
    );
  }
}
