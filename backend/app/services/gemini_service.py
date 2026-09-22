"""
OpenScore Finance — Centralized Gemini AI & Contextual Assistant Service
Provides conversational and voice-driven guidance for microfinance clients and credit officers.
Directly interfaces with Google Gemini (server-side only, client keys never exposed)
with an advanced contextual reasoning engine for non-predefined and complex queries.
"""

from __future__ import annotations

import os
import re
import logging
import json
from typing import Optional, Dict, Any, List

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

ASSISTANT_SYSTEM_PROMPT = """Tu es l'Assistant Virtuel officiel d'OpenScore Finance, expert en microfinance et inclusion financière en Afrique de l'Ouest (Mali et espace UEMOA).
Tu communiques avec clarté, bienveillance et professionnalisme en Français et comprends parfaitement les expressions en Bambara (Bamanankan) relatives aux activités économiques locales (Sugu/Marché, Sɛnɛ/Agriculture, Numuya/Artisanat, Wari/Argent, Tontine/Musow ka tontine, Juru/Dette, etc.).

RÈGLES D'OR :
1. Tu n'inventes JAMAIS de décision d'octroi ou de score imaginaire. Si le contexte du dossier ou du scoring est fourni, appuie-toi RIGOUREUSEMENT dessus pour expliquer les facteurs déterminants (garanties solides, endettement bas, régularité des revenus) et les points d'amélioration (charges lourdes, endettement supérieur à 40%).
2. Si le client n'a pas encore de compte microfinance officiel (CMF/Nyèsigiso/Kafo Jiginew), explique-lui avec clarté les 4 étapes simples pour en ouvrir un et les pièces requises (NINA/CNI, justificatif de domicile, versement initial).
3. Les scores sont TOUJOURS exprimés sur une BASE STRICTE DE 100 (ex: 78/100). Ne mentionne JAMAIS de score sur 1000.
4. Réponds toujours avec précision, pédagogie et encouragement.
5. Propose systématiquement 2 à 4 suggestions de questions suivantes courtes et pertinentes.

Format de sortie attendu (JSON strict valide) :
{
  "response_text": "Ta réponse claire et utile en français ou bilingue selon la question",
  "suggestions": ["Question suivante 1", "Question suivante 2", "Question suivante 3"],
  "detected_intent": "SECTOR_INFO | SCORE_EXPLANATION | GUARANTEE_INQUIRY | DEBT_INQUIRY | ACCOUNT_OPENING | REPAYMENT_TERMS | INTEREST_RATES | DISBURSEMENT_TIME | GENERAL_ASSIST",
  "suggested_field": {"field": "field_name_optionnel", "value": "valeur_optionnelle"}
}
"""


class GeminiService:
    """Production-grade AI Assistant service with Google Gemini API & intelligent microfinance engine."""

    def __init__(self):
        self.model_name = settings.GEMINI_MODEL or "gemini-1.5-flash"

    def _get_api_key(self) -> str:
        """Dynamically fetch Gemini API key from environment or settings."""
        return (
            os.environ.get("GEMINI_API_KEY")
            or os.environ.get("GOOGLE_API_KEY")
            or settings.GEMINI_API_KEY
            or ""
        ).strip()

    async def query_assistant(
        self,
        query_text: str,
        language: str = "fr",
        context: Optional[Dict[str, Any]] = None,
        application_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Process user query with full context awareness (score, collateral, debts, account status).
        Calls live Google Gemini API if configured, otherwise leverages our advanced contextual fallback engine.
        """
        clean_query = query_text.strip()
        if not clean_query:
            return {
                "response_text": "Bonjour ! Je suis l'assistant intelligent OpenScore Finance. Comment puis-je vous guider aujourd'hui dans votre projet de crédit ?",
                "suggestions": [
                    "Combien puis-je emprunter ?",
                    "Quelles garanties fournir ?",
                    "Comment est calculé mon score /100 ?",
                    "Comment ouvrir un compte microfinance ?",
                ],
                "detected_intent": "GENERAL_ASSIST",
                "suggested_field": None,
            }

        # Build detailed context string
        context_str = ""
        if application_data:
            context_str += "\n[CONTEXTE DOSSIER ACTUEL]\n"
            if "reference" in application_data:
                context_str += f"- Référence dossier: {application_data.get('reference')}\n"
            if "score" in application_data and application_data.get("score") is not None:
                context_str += f"- Score calculé: {application_data.get('score')}/100\n"
            if "risk_level" in application_data:
                context_str += f"- Niveau de risque: {application_data.get('risk_level')}\n"
            if "requested_amount" in application_data:
                context_str += f"- Montant sollicité: {application_data.get('requested_amount'):,.0f} FCFA\n"
            if "activity_sector" in application_data:
                context_str += f"- Secteur: {application_data.get('activity_sector')}\n"
            if "guarantees" in application_data:
                guarantees = application_data.get("guarantees", [])
                tot_val = sum(g.get("estimated_value", 0) for g in guarantees)
                context_str += f"- Garanties déclarées: {len(guarantees)} bien(s), valeur cumulée: {tot_val:,.0f} FCFA\n"
            if "debts" in application_data:
                debts = application_data.get("debts", [])
                tot_monthly = sum(d.get("monthly_payment", 0) for d in debts)
                context_str += f"- Dettes en cours: {len(debts)} engagement(s), mensualités cumulées: {tot_monthly:,.0f} FCFA/mois\n"

        if context:
            context_str += f"\n[INFOS COMPLÉMENTAIRES]: {json.dumps(context, ensure_ascii=False)}\n"

        api_key = self._get_api_key()

        # Attempt call to live Gemini API if key is set
        if api_key:
            try:
                from google import genai
                from google.genai import types

                client = genai.Client(api_key=api_key)
                prompt_content = (
                    f"{ASSISTANT_SYSTEM_PROMPT}\n\n"
                    f"Langue demandée: {language}\n"
                    f"{context_str}\n\n"
                    f"Question de l'utilisateur : {clean_query}"
                )

                response = client.models.generate_content(
                    model=self.model_name,
                    contents=prompt_content,
                    config=types.GenerateContentConfig(
                        temperature=0.3,
                        response_mime_type="application/json",
                        max_output_tokens=1024,
                    ),
                )

                raw_text = response.text.strip() if response.text else "{}"
                # Handle possible markdown backticks in response
                if raw_text.startswith("```"):
                    raw_text = re.sub(r"^```(?:json)?\n?", "", raw_text)
                    raw_text = re.sub(r"\n?```$", "", raw_text).strip()

                parsed = json.loads(raw_text)
                return {
                    "response_text": parsed.get("response_text", "Je reste à votre entière disposition pour tout renseignement."),
                    "suggestions": parsed.get("suggestions", [
                        "Comment améliorer mon score /100 ?",
                        "Quelles garanties puis-je enregistrer ?",
                    ]),
                    "detected_intent": parsed.get("detected_intent", "GENERAL_ASSIST"),
                    "suggested_field": parsed.get("suggested_field"),
                }
            except Exception as e:
                logger.warning(f"Google Gemini API error, falling back to local contextual reasoning: {e}")

        # Intelligent contextual fallback covering predefined and non-predefined questions
        return self._contextual_fallback(clean_query, application_data)

    def _contextual_fallback(
        self,
        query: str,
        application_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        High-precision microfinance NLP reasoning engine.
        Handles both standard and non-predefined questions (debts, rates, mobile money,
        collateral, approval times, grace periods, Bambara terms, etc.).
        """
        q = query.lower()

        # ── 1. Taux d'intérêt & Frais (Interest rates / TEG) ────────────────
        if any(k in q for k in ["taux", "interet", "intérêt", "teg", "cout", "coût", "frais", "pourcentage", "agios"]):
            return {
                "response_text": (
                    "Dans les institutions de microfinance partenaires au Mali (régies par les règles BCEAO), "
                    "les taux d'intérêt sont plafonnés par la loi sur l'usure (généralement entre 1% et 2% par mois selon le produit). "
                    "Les frais de dossier sont transparents (1% à 2.5% du montant accordé) et il n'y a aucun frais caché. "
                    "Vous recevez un échéancier complet avant tout déblocage."
                ),
                "suggestions": [
                    "Quel est le délai de remboursement ?",
                    "Peut-on rembourser par Orange Money ou Wave ?",
                    "Combien puis-je emprunter ?",
                ],
                "detected_intent": "INTEREST_RATES",
                "suggested_field": None,
            }

        # ── 2. Délais & Comité de crédit (Disbursement & Approval Time) ──────
        if any(k in q for k in ["delai", "délai", "temps", "combien de temps", "quand", "comite", "comité", "deblocage", "déblocage", "decision"]):
            return {
                "response_text": (
                    "Grâce au scoring automatisé OpenScore Finance, l'analyse initiale est instantanée ! "
                    "La décision finale du Comité de Crédit intervient généralement sous 24h à 48h ouvrées. "
                    "Dès validation, les fonds sont débloqués directement sur votre compte microfinance ou via votre compte Mobile Money."
                ),
                "suggestions": [
                    "Comment suivre l'avancement de mon dossier ?",
                    "Quels documents manquent à mon dossier ?",
                    "Puis-je modifier ma demande après soumission ?",
                ],
                "detected_intent": "DISBURSEMENT_TIME",
                "suggested_field": None,
            }

        # ── 3. Moyens de remboursement & Mobile Money ─────────────────────────
        if any(k in q for k in ["rembourser", "remboursement", "orange", "wave", "moov", "wari", "mensualite", "mensualité", "echeance", "échéance"]):
            return {
                "response_text": (
                    "Le remboursement s'effectue facilement selon votre convenance : \n"
                    "• Par Mobile Money (Orange Money, Wave, Moov Money) sans vous déplacer ;\n"
                    "• Par prélèvement direct sur votre compte épargne IMF ;\n"
                    "• En agence auprès d'un guichet partenaire.\n"
                    "Un reçu numérique horodaté vous est immédiatement délivré après chaque versement."
                ),
                "suggestions": [
                    "Que se passe-t-il si je rembourse en avance ?",
                    "Puis-je avoir un différé de paiement ?",
                    "Comment déclarer mes dettes actuelles ?",
                ],
                "detected_intent": "REPAYMENT_TERMS",
                "suggested_field": None,
            }

        # ── 4. Remboursement anticipé & Différé ───────────────────────────────
        if any(k in q for k in ["avance", "anticipe", "anticipé", "differe", "différé", "grace", "grâce", "pause"]):
            return {
                "response_text": (
                    "Oui, vous avez le droit de solder votre crédit par anticipation à tout moment ! "
                    "Ce remboursement anticipé réduit les intérêts restants et améliore immédiatement votre historique de crédit. "
                    "Pour les activités saisonnières (agricoles ou commandes marchandes), un différé d'amortissement de 1 à 3 mois "
                    "peut également être accordé lors de la signature."
                ),
                "suggestions": [
                    "Comment fonctionne le différé pour l'agriculture ?",
                    "Quel est l'impact sur mon score /100 ?",
                ],
                "detected_intent": "REPAYMENT_TERMS",
                "suggested_field": None,
            }

        # ── 5. Score & Solvabilité ──────────────────────────────────────────
        if any(k in q for k in ["score", "solvabilite", "solvabilité", "pourquoi", "facteur", "note", "calcul", "points"]):
            if application_data and application_data.get("score") is not None:
                score = application_data.get("score")
                risk = application_data.get("risk_level", "Modéré")
                return {
                    "response_text": (
                        f"Votre score de solvabilité actuel est de {score}/100 (Niveau de risque : {risk}). "
                        f"Il est calculé en pondérant 5 critères majeurs : votre ratio d'endettement (30%), "
                        f"votre reste à vivre mensuel (20%), la valeur de vos garanties (20%), la régularité "
                        f"de vos revenus (15%) et votre ancienneté d'activité (15%). "
                        f"L'enregistrement de garanties supplémentaires ou l'allègement de vos charges mensuelles "
                        f"permettra d'augmenter votre note vers la zone verte (> 75/100)."
                    ),
                    "suggestions": [
                        "Comment passer au-dessus de 75/100 ?",
                        "Quelles garanties ajouter pour monter mon score ?",
                        "Quel montant puis-je espérer obtenir ?",
                    ],
                    "detected_intent": "SCORE_EXPLANATION",
                }
            return {
                "response_text": (
                    "Le Score de Solvabilité OpenScore est calibré sur une échelle stricte de 0 à 100 points :\n"
                    "• 75 à 100 : Risque Faible — Accord direct recommandé par le système ;\n"
                    "• 60 à 74 : Risque Modéré — Éligible avec offre ajustable ou garanties ;\n"
                    "• 40 à 59 : Risque Élevé — Nécessite une caution solidaire ou un apport ;\n"
                    "• Moins de 40 : Risque Très Élevé — Risque de surendettement.\n"
                    "Ce barème garantit une analyse objective, équitable et explicable."
                ),
                "suggestions": [
                    "Quelles garanties sont acceptées ?",
                    "Comment calculer mon reste à vivre ?",
                    "Quelle est la limite d'endettement ?",
                ],
                "detected_intent": "SCORE_EXPLANATION",
            }

        # ── 6. Garanties & Biens ─────────────────────────────────────────────
        if any(k in q for k in ["garantie", "bien", "terrain", "maison", "titre", "lettre", "moto", "vehicule", "véhicule", "gage", "materiel", "matériel", "caution"]):
            return {
                "response_text": (
                    "Les institutions de microfinance partenaires acceptent un large éventail de sûretés et garanties :\n"
                    "1. Biens immobiliers : Titre Foncier (TF), Permis d'occuper, Lettre d'attribution, Concession rurale ;\n"
                    "2. Véhicules & Engins : Motos (Djakarta, TVS), Tricycles, Voitures et Camionnettes ;\n"
                    "3. Équipements pros : Machines de couture, motopompes, moulins, outillage ;\n"
                    "4. Stocks marchands et Cautions solidaires (groupes de caution mutuelle / Tontines).\n"
                    "Chaque garantie ajoutée réduit le risque de perte et bonifie directement votre score /100."
                ),
                "suggestions": [
                    "Combien de biens puis-je déclarer ?",
                    "Comment estimer la valeur de ma moto ou de mon stock ?",
                    "Faut-il obligatoirement un Titre Foncier ?",
                ],
                "detected_intent": "GUARANTEE_INQUIRY",
            }

        # ── 7. Dettes & Ratio d'endettement 40% ──────────────────────────────
        if any(k in q for k in ["dette", "tontine", "impaye", "impayé", "credit en cours", "crédit en cours", "40%", "surendettement", "autre banque"]):
            return {
                "response_text": (
                    "La réglementation prudentielle BCEAO et la politique de crédit OpenScore fixent un plafond d'endettement "
                    "de 40% de vos revenus nets. Cela signifie que la somme de vos mensualités (nouveau crédit + dettes existantes + tontines) "
                    "ne doit pas absorber plus de 40% de ce que vous gagnez chaque mois. "
                    "Déclarer sincèrement vos engagements protège votre activité contre les défauts de paiement."
                ),
                "suggestions": [
                    "Que faire si je dépasse 40% d'endettement ?",
                    "Puis-je regrouper ou consolider mes dettes ?",
                    "Comment calculer mon reste à vivre ?",
                ],
                "detected_intent": "DEBT_INQUIRY",
            }

        # ── 8. Ouverture de compte & Adhésion ────────────────────────────────
        if any(k in q for k in ["compte", "ouvrir", "inscription", "adhesion", "adhésion", "livret", "cmf", "piece", "pièce", "document"]):
            return {
                "response_text": (
                    "Pour adhérer et ouvrir votre livret d'épargne officiel chez une IMF partenaire :\n"
                    "1. Choisissez l'agence de proximité la plus proche (Kafo Jiginew, Nyèsigiso, CMF...) ;\n"
                    "2. Présentez votre pièce d'identité (NINA, CNI biométrique ou Passeport) ;\n"
                    "3. Fournissez 2 photos d'identité et un justificatif de domicile (facture EDM/SOMAGEP ou attestation de quartier) ;\n"
                    "4. Versez le dépôt initial d'ouverture (10 000 à 25 000 FCFA selon l'institution).\n"
                    "Une fois votre numéro de compte obtenu (ex: CMF-2026-XXXXXX), vous pouvez soumettre votre dossier de crédit !"
                ),
                "suggestions": [
                    "Combien de temps après l'ouverture puis-je demander un crédit ?",
                    "Comment rattacher mon compte sur l'application ?",
                    "Quels sont les avantages d'un compte IMF ?",
                ],
                "detected_intent": "ACCOUNT_OPENING",
            }

        # ── 9. Secteur Commerce / Sugu ───────────────────────────────────────
        if any(k in q for k in ["sugu", "marche", "marché", "commerce", "tissu", "bazin", "boutiki", "boutique", "vente"]):
            return {
                "response_text": (
                    "Pour les commerçants (marchés de Bamako, boutiques de quartier, vente de bazin ou denrées) :\n"
                    "• Montants disponibles : de 100 000 FCFA à 5 000 000 FCFA selon le chiffre d'affaires ;\n"
                    "• Durées de prêt : 6 à 24 mois avec échéances mensuelles constantes ;\n"
                    "• Justificatifs : carnet de vente, photos de boutique ou déclaration de stock.\n"
                    "Votre régularité commerciale est un atout majeur pour votre score."
                ),
                "suggestions": [
                    "Puis-je mettre mon stock de marchandises en garantie ?",
                    "Comment déclarer mes ventes journalières ?",
                    "Quel est le taux pour le commerce ?",
                ],
                "detected_intent": "SECTOR_INFO",
                "suggested_field": {"field": "activity_sector", "value": "Commerce"},
            }

        # ── 10. Secteur Agriculture & Maraîchage / Sɛnɛ ─────────────────────
        if any(k in q for k in ["sɛnɛ", "sene", "foro", "champ", "champs", "culture", "tomate", "maraicher", "maraîcher", "baguineda", "baguinéda", "recolte", "récolte", "semence"]):
            return {
                "response_text": (
                    "Pour les producteurs et maraîchers (Sɛnɛkɛlaw à Baguinéda, Sikasso, etc.) :\n"
                    "• Financements adaptés au calendrier des cultures (semences, engrais, irrigation, motopompes) ;\n"
                    "• Possibilité d'obtenir un différé de remboursement calqué sur la période des récoltes ;\n"
                    "• Vos équipements agricoles et parcelles peuvent être valorisés comme garanties."
                ),
                "suggestions": [
                    "Comment fonctionne le différé de remboursement ?",
                    "Quelles pièces fournir pour une activité maraîchère ?",
                    "Quel montant pour l'achat d'une motopompe ?",
                ],
                "detected_intent": "SECTOR_INFO",
                "suggested_field": {"field": "activity_sector", "value": "Agriculture"},
            }

        # ── 11. Secteur Artisanat / Numuya & Transport ──────────────────────
        if any(k in q for k in ["numuya", "artisan", "artisanat", "couture", "couturier", "menuisier", "mecanicien", "mécanicien", "garage", "transport", "taxi", "moto-taxi"]):
            return {
                "response_text": (
                    "Pour les artisans (Numuyaw, ateliers de couture, menuiserie, mécanique) et transporteurs :\n"
                    "• Financement d'équipements de travail (machines à coudre industrielles, outillage, pièces détachées) ;\n"
                    "• Vos machines et véhicules peuvent être nantis comme garantie sans immobiliser votre travail quotidien ;\n"
                    "• Un carnet de commandes ou des contrats clients renforcent considérablement votre profil de solvabilité."
                ),
                "suggestions": [
                    "Puis-je gager ma machine de travail ?",
                    "Quelle ancienneté d'atelier est requise ?",
                    "Combien puis-je solliciter pour équiper mon atelier ?",
                ],
                "detected_intent": "SECTOR_INFO",
                "suggested_field": {"field": "activity_sector", "value": "Artisanat"},
            }

        # ── 12. Termes Bambara / Bamanankan ─────────────────────────────────
        if any(k in q for k in ["wari", "an be", "musow", "baara", "kafo", "nyesigiso", "juru", "tɔgɔ", "kɛnɛ"]):
            return {
                "response_text": (
                    "I ni ce ! OpenScore Finance dɛmɛbaga b'i dɛmɛ wari taali la IMF la (Kafo Jiginew, Nyèsigiso, CMF). "
                    "An bɛ se ka i ka dɔnniya lase juru taacogo, sɛnɛbaara ani sugu lajɛlen kan. "
                    "I b'a fɛ ka hakɛ jume lajɛ bi ?"
                ),
                "suggestions": [
                    "Sugu wari — Crédit commerce",
                    "Sɛnɛ wari — Crédit agriculture",
                    "Juru hakɛ — Solvabilité score",
                ],
                "detected_intent": "GENERAL_ASSIST",
            }

        # ── 13. Questions ouvertes / imprévues non-prédéfinies ───────────────
        # When a question is completely unique or unforeseen, formulate an intelligent,
        # structured microfinance response tailored to their words.
        clean_terms = re.findall(r"\w+", q)
        highlight_subject = "votre démarche de crédit"
        if len(clean_terms) >= 2:
            meaningful_terms = [t for t in clean_terms if len(t) > 3 and t not in ["comment", "faire", "avec", "dans", "pour", "peut", "veut", "cette", "vous"]]
            if meaningful_terms:
                highlight_subject = f"votre question relative à « {' '.join(meaningful_terms[:3])} »"

        app_context_info = ""
        if application_data and application_data.get("requested_amount"):
            app_context_info = (
                f" En tenant compte de votre demande en cours ({application_data.get('requested_amount'):,.0f} FCFA), "
                f"un conseiller de crédit peut personnaliser ces paramètres lors de l'instruction."
            )

        return {
            "response_text": (
                f"Concernant {highlight_subject} : OpenScore Finance accompagne chaque porteur de projet "
                f"selon les normes de l'inclusion financière UEMOA. "
                f"Que votre projet porte sur l'extension d'une activité existante, un besoin de fonds de roulement ou une caution d'engagement, "
                f"l'évaluation repose sur la viabilité de votre trésorerie, la maîtrise de votre endettement (max 40%) et la qualité de vos garanties.{app_context_info} "
                f"N'hésitez pas à préciser un montant ou un secteur pour une simulation sur-mesure."
            ),
            "suggestions": [
                "Comment simuler mon crédit en détail ?",
                "Quelles garanties puis-je renseigner ?",
                "Quels sont les plafonds d'emprunt ?",
                "Comment fonctionne le comité de crédit ?",
            ],
            "detected_intent": "GENERAL_ASSIST",
            "suggested_field": None,
        }


gemini_service = GeminiService()
