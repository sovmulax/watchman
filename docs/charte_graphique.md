# Charte Graphique — Plateforme de Veille Technologique

*Direction artistique : épuré, minimaliste, apaisant. Optimisé pour la lecture prolongée (long-form reading). Thèmes clair et sombre.*

---

## 1. Philosophie de design

L'application est un outil de **lecture**. L'utilisateur y passe de longues sessions à parcourir des synthèses, des articles, des digests. Chaque choix visuel découle donc d'un seul principe directeur : **réduire la fatigue oculaire et le bruit visuel** pour que le contenu reste au centre.

Trois règles non négociables :

1. **Aucun contraste agressif.** Jamais de noir pur (`#000000`) sur blanc pur (`#FFFFFF`) — cette combinaison crée un halo et fatigue l'œil sur la durée. On utilise des neutres légèrement teintés de chaud (tons "papier").
2. **Saturation basse partout.** Les couleurs sont désaturées, sourdes, naturelles. La couleur ne sert qu'à guider (accent, statut), jamais à décorer.
3. **De l'espace, du silence.** Beaucoup de blanc (négatif), une seule couleur d'accent, une hiérarchie typographique claire. Le minimalisme n'est pas une esthétique ici, c'est une fonction : moins d'éléments = moins de charge cognitive.

Référence d'inspiration : les liseuses (Kindle, iA Writer, Readwise Reader), qui privilégient le fond « papier » et le texte « encre », pas les interfaces SaaS saturées.

---

## 2. Palette de couleurs

La palette repose sur des **neutres chauds** (base de l'interface) et **une seule couleur d'accent** : un **vert sauge / eucalyptus** désaturé, reconnu pour son effet apaisant et son excellent confort en lecture longue. Les couleurs sémantiques sont volontairement adoucies pour ne pas rompre le calme général.

### 2.1 Thème clair — « Papier »

| Rôle | Hex | Usage |
|---|---|---|
| `bg-base` | `#F6F4EF` | Fond principal de l'application (blanc cassé chaud, effet papier) |
| `bg-subtle` | `#EFEDE7` | Zones en léger retrait (barres latérales, sections) |
| `surface` | `#FCFBF8` | Cartes, panneaux, conteneurs de contenu |
| `border` | `#E3DFD6` | Séparateurs, contours discrets |
| `text-primary` | `#2E2C28` | Texte de lecture principal (encre chaude, jamais noir pur) |
| `text-secondary` | `#6B665E` | Métadonnées, sous-titres, légendes |
| `text-muted` | `#9C968C` | Texte tertiaire, placeholders, états désactivés |

### 2.2 Thème sombre — « Encre »

| Rôle | Hex | Usage |
|---|---|---|
| `bg-base` | `#16181C` | Fond principal (bleu-charbon profond, jamais noir pur) |
| `bg-subtle` | `#1B1E23` | Zones en léger retrait |
| `surface` | `#21252B` | Cartes, panneaux, conteneurs |
| `border` | `#2E333A` | Séparateurs discrets |
| `text-primary` | `#E6E3DC` | Texte de lecture (blanc cassé chaud, jamais blanc pur) |
| `text-secondary` | `#A8A49B` | Métadonnées, sous-titres |
| `text-muted` | `#726E66` | Texte tertiaire, désactivé |

### 2.3 Couleur d'accent — Vert sauge

| Rôle | Clair | Sombre | Usage |
|---|---|---|---|
| `accent` | `#4F7A5E` | `#7FA98B` | Liens, boutons primaires, éléments actifs, focus |
| `accent-hover` | `#446B52` | `#93B99D` | État survol / actif |
| `accent-subtle` | `#E8EFE9` | `#232D26` | Fonds d'accent légers (badge actif, surbrillance) |

> En thème clair, l'accent `#4F7A5E` est assez foncé pour porter du texte blanc sur un bouton plein (contraste ≥ 4.5:1). En thème sombre, on éclaircit l'accent (`#7FA98B`) pour qu'il ressorte sur fond charbon.

### 2.4 Couleurs sémantiques (désaturées)

Volontairement sourdes pour préserver le calme — pas de rouge criard ni de vert fluo.

| Rôle | Clair | Sombre | Usage |
|---|---|---|---|
| `success` | `#4F7A5E` | `#7FA98B` | Succès (aligné sur l'accent sauge) |
| `info` | `#5B7C99` | `#89A9C4` | Information, statut neutre (bleu ardoise) |
| `warning` | `#B08637` | `#D4A85E` | Avertissement (ocre/ambre doux) |
| `error` | `#A85D4A` | `#C98572` | Erreur (terracotta désaturé, non agressif) |

Chaque sémantique dispose d'une variante « subtle » (fond léger) pour les bandeaux d'état : même teinte, très haute clarté en thème clair / très basse en thème sombre.

---

## 3. Typographie

Séparation classique et efficace : **une serif humaniste pour le contenu long** (confort de lecture supérieur sur de longs paragraphes), **une sans-serif neutre pour l'interface** (labels, boutons, navigation).

| Usage | Police | Fallback |
|---|---|---|
| Contenu de lecture (synthèses, articles) | **Source Serif 4** (ou Lora / Charter) | `Georgia, serif` |
| Interface (UI, navigation, boutons) | **Inter** (ou IBM Plex Sans) | `system-ui, sans-serif` |
| Code / extraits techniques | **JetBrains Mono** (ou IBM Plex Mono) | `ui-monospace, monospace` |

### 3.1 Échelle typographique (base 16px, ratio ~1.25)

| Token | Taille | Line-height | Usage |
|---|---|---|---|
| `text-xs` | 12px | 1.5 | Métadonnées, timestamps |
| `text-sm` | 14px | 1.55 | Labels UI, légendes |
| `text-base` | 16px | **1.7** | Corps UI, texte courant |
| `text-reading` | 18px | **1.75** | **Corps de lecture long-form** (confort maximal) |
| `text-lg` | 20px | 1.5 | Sous-titres |
| `text-xl` | 24px | 1.4 | Titres de section |
| `text-2xl` | 30px | 1.3 | Titres de page |
| `text-3xl` | 36px | 1.25 | Titre principal / hero |

### 3.2 Règles de lecture (essentielles pour le long-form)

- **Largeur de ligne limitée** : le corps de lecture ne dépasse jamais **65–75 caractères** (~`680px` max), pour un retour à la ligne confortable.
- **Interlignage généreux** : `1.7` à `1.75` sur le contenu, jamais moins de `1.6`.
- **Graisses limitées** : Regular (400) pour le corps, Medium (500) pour les labels, Semibold (600) pour les titres. Pas de Bold agressif, pas d'italique décoratif.
- **Espacement des paragraphes** : marge inférieure de `1em` à `1.25em` entre paragraphes, pas d'indentation.

---

## 4. Espacement & mise en page

Grille de base **8px** (échelle 4/8/12/16/24/32/48/64). L'espace négatif est un élément de design à part entière.

| Token | Valeur | Usage |
|---|---|---|
| `space-1` | 4px | Micro-espacements (icône/label) |
| `space-2` | 8px | Espacement serré |
| `space-3` | 12px | Espacement de base |
| `space-4` | 16px | Padding standard de composant |
| `space-6` | 24px | Espacement entre blocs |
| `space-8` | 32px | Séparation de sections |
| `space-12` | 48px | Respiration de page |
| `space-16` | 64px | Grandes marges verticales |

**Layout général :** navigation latérale discrète et étroite, zone de contenu centrée avec marges généreuses, largeur de lecture contrainte. Pas de contenu « bord à bord » sur grand écran.

---

## 5. Formes, élévation & mouvement

### 5.1 Rayons de bordure (doux, jamais anguleux)

| Token | Valeur | Usage |
|---|---|---|
| `radius-sm` | 6px | Badges, tags, inputs |
| `radius-md` | 10px | Boutons, cartes |
| `radius-lg` | 16px | Panneaux, modales |
| `radius-full` | 9999px | Avatars, pastilles de statut |

### 5.2 Ombres (subtiles, diffuses)

Ombres très douces et peu opaques — elles suggèrent l'élévation sans créer de contraste dur. En thème sombre, l'élévation passe surtout par la **couleur de surface** (surfaces plus claires = plus élevées) plutôt que par l'ombre.

- `shadow-sm` : `0 1px 2px rgba(45, 42, 38, 0.04)`
- `shadow-md` : `0 4px 12px rgba(45, 42, 38, 0.06)`
- `shadow-lg` : `0 12px 32px rgba(45, 42, 38, 0.08)`

### 5.3 Mouvement

- Transitions courtes et douces : **150–200ms**, courbe `ease-out`.
- Pas d'animation gratuite. Le mouvement sert uniquement le feedback (survol, apparition de panneau, changement d'état).
- Respect de `prefers-reduced-motion` : désactivation des transitions non essentielles.

---

## 6. Accessibilité (non négociable)

- **Contraste** : texte principal ≥ 7:1 (AAA), texte secondaire et éléments d'interface ≥ 4.5:1 (AA). Vérifié pour les deux thèmes.
- **Focus visible** : anneau de focus systématique en couleur d'accent (`outline` de 2px + décalage), jamais supprimé.
- **Thème** : bascule clair/sombre explicite + respect de `prefers-color-scheme` par défaut. La couleur seule ne porte jamais une information (les statuts ont aussi une icône/un label).
- **Taille de cible tactile** : minimum 44×44px pour les éléments interactifs.
- **Zoom** : la mise en page reste fonctionnelle jusqu'à 200% de zoom.

---

## 7. Implémentation technique (design tokens)

Tous les tokens ci-dessus sont exposés en **variables CSS** sous `:root` (thème clair) et surchargés sous `[data-theme="dark"]`. Cela permet une bascule de thème instantanée sans rechargement et un point de vérité unique.

```css
:root {
  /* Couleurs — thème clair */
  --bg-base: #F6F4EF;
  --bg-subtle: #EFEDE7;
  --surface: #FCFBF8;
  --border: #E3DFD6;
  --text-primary: #2E2C28;
  --text-secondary: #6B665E;
  --text-muted: #9C968C;
  --accent: #4F7A5E;
  --accent-hover: #446B52;
  --accent-subtle: #E8EFE9;
  --info: #5B7C99;
  --warning: #B08637;
  --error: #A85D4A;

  /* Typographie */
  --font-reading: "Source Serif 4", Georgia, serif;
  --font-ui: "Inter", system-ui, sans-serif;
  --font-mono: "JetBrains Mono", ui-monospace, monospace;

  /* Rayons & espacements — voir tableaux ci-dessus */
  --radius-md: 10px;
  --reading-max-width: 680px;
}

[data-theme="dark"] {
  --bg-base: #16181C;
  --bg-subtle: #1B1E23;
  --surface: #21252B;
  --border: #2E333A;
  --text-primary: #E6E3DC;
  --text-secondary: #A8A49B;
  --text-muted: #726E66;
  --accent: #7FA98B;
  --accent-hover: #93B99D;
  --accent-subtle: #232D26;
  --info: #89A9C4;
  --warning: #D4A85E;
  --error: #C98572;
}
```

> Si le frontend part sur **Tailwind CSS**, ces tokens se mappent directement dans `tailwind.config.js` (`theme.extend.colors`, `fontFamily`, `borderRadius`) et le mode sombre s'active via la stratégie `class` / `[data-theme]`. Cohérent avec l'option « templates Django + HTMX » de la roadmap comme avec un frontend React/Vue.

---

## 8. Récapitulatif de l'identité

Une interface qui ressemble à **une page de livre bien imprimée** plutôt qu'à un tableau de bord : fond papier chaud, encre douce, une seule touche de vert sauge pour guider, beaucoup d'air, une typographie de lecture soignée. L'utilisateur doit pouvoir lire une heure sans y penser — c'est la réussite du design.
