# ADR 0003 — Abstraction multi-provider pour les LLM

## Statut
Accepté

## Contexte
La plateforme doit pouvoir basculer entre Claude, OpenAI, Mistral et Ollama
sans changer la logique métier (§7.5), et rester testable sans dépendre
d'appels réseau réels (§13).

## Décision
Interface commune `BaseLLMProvider` (§7.5) avec une factory
`get_provider()` résolvant le provider/modèle actif depuis
`AppConfiguration` (singleton, §6.8). `FakeProvider` déterministe utilisé
systématiquement en tests (`config/settings/test.py`).

## Conséquences
Chaque provider gère son propre retry (`tenacity`) et son propre calcul de
coût (`price_per_1k`) ; les sorties sont toujours validées par des schémas
Pydantic (§7.5 `schemas.py`) avant écriture en base.
