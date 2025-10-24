# Pourquoi uv ?

Ce projet utilise [uv](https://github.com/astral-sh/uv) comme gestionnaire de paquets Python recommandé.

## 🚀 Avantages

### Vitesse
uv est écrit en Rust et est **10-100x plus rapide** que pip :

| Tâche | pip | uv |
|-------|-----|-----|
| Installation complète | ~60s | ~5s |
| Réinstallation (avec cache) | ~30s | ~0.5s |
| Résolution de dépendances | ~10s | ~0.1s |

### Dans GitHub Actions

Pour ce projet spécifiquement :
- ⏱️ **Réduction du temps d'installation** : de 2min à 10-20s
- 💰 **Économie de coûts** GitHub Actions
- 🔄 **Cache intelligent** entre les runs
- ✅ **Compatible avec requirements.txt**

### Installation locale

Sur votre machine de développement :
```bash
# Installer uv (une seule fois)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Utiliser uv
uv pip install --system -r requirements.txt
```

### Compilation native optimisée

uv gère mieux la compilation de paquets comme `lxml` :
- Détection automatique des bibliothèques système
- Utilisation de wheels pré-compilés quand disponibles
- Fallback intelligent sur la compilation source

## 📦 Compatibilité

uv est **100% compatible** avec pip :
- Utilise le même format `requirements.txt`
- Installe dans le même environnement Python
- Commandes similaires : `uv pip install` = `pip install`

## 🔄 Migration pip → uv

Pour les développeurs habitués à pip :

| pip | uv |
|-----|-----|
| `pip install package` | `uv pip install package` |
| `pip install -r requirements.txt` | `uv pip install -r requirements.txt` |
| `pip freeze > requirements.txt` | `uv pip freeze > requirements.txt` |
| `pip list` | `uv pip list` |

## 🛠️ Installation

### Linux / macOS / WSL
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Windows (PowerShell)
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Via pip (si vous n'avez que pip)
```bash
pip install uv
```

## 📊 Impact sur ce projet

### GitHub Actions

**Avant (avec pip)** :
```
Install dependencies: 2m 15s
```

**Après (avec uv)** :
```
Install uv: 2s
Install Python dependencies with uv: 8s
Total: 10s
```

**Gain** : ~2 minutes par run, soit :
- ~1h par mois économisée (scraping quotidien)
- ~30% de réduction du temps total du workflow

### Développement local

**Premier install** : 60s → 5s (12x plus rapide)
**Réinstall après changement** : 30s → 0.5s (60x plus rapide)

## 🔗 Ressources

- [Documentation uv](https://github.com/astral-sh/uv)
- [Comparaison de performances](https://astral.sh/blog/uv)
- [Migration depuis pip](https://github.com/astral-sh/uv#compatibility-with-pip)

## 💡 Note

Si vous préférez utiliser pip, c'est toujours possible ! Le projet reste 100% compatible :
```bash
pip install -r requirements.txt
```

Mais nous recommandons fortement uv pour l'expérience développeur améliorée.
