# Guide de contribution

Merci de votre intérêt pour contribuer à ce projet !

## 🐛 Signaler un bug

Ouvrez une issue en décrivant :
- Le comportement attendu
- Le comportement observé
- Les étapes pour reproduire
- Les logs pertinents

## 💡 Proposer une amélioration

Ouvrez une issue ou une pull request avec :
- La description de l'amélioration
- La justification (pourquoi c'est utile)
- L'implémentation proposée

## 🔧 Développement

### Configuration de l'environnement

```bash
# Cloner le repo
git clone https://github.com/VOTRE_USERNAME/scrapearretesparis.git
cd scrapearretesparis

# Installer uv (recommandé pour la vitesse)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Installer les dépendances système (Linux)
sudo apt-get install -y libxml2-dev libxslt-dev

# Installer les dépendances Python avec uv (ou pip)
uv pip install --system -r requirements.txt
playwright install chromium

# Créer un fichier .env pour les tests
cp .env.example .env
```

### Tester vos changements

```bash
# Mode DRY_RUN pour tester sans S3
export DRY_RUN=true
export MAX_PAGES_TO_SCRAPE=1
cd src
python scraper.py
```

### Structure du code

- `src/scraper.py` : Logique principale du scraping
- `src/s3_uploader.py` : Gestion de l'upload S3
- `src/config.py` : Configuration et variables d'environnement

### Bonnes pratiques

1. **Code quality** :
   - Suivre PEP 8
   - Ajouter des docstrings
   - Logger les informations importantes

2. **Commits** :
   - Messages clairs et descriptifs
   - Un commit par fonctionnalité

3. **Pull Requests** :
   - Tester avant de soumettre
   - Décrire clairement les changements
   - Référencer les issues liées

## 📝 Améliorations possibles

- [ ] Ajouter des tests unitaires
- [ ] Supporter d'autres catégories d'arrêtés
- [ ] Notifications par email lors de nouveaux arrêtés
- [ ] API REST pour accéder aux données
- [ ] Dashboard de visualisation
- [ ] Retry automatique en cas d'erreur
- [ ] Monitoring et alerting

## 🤝 Code de conduite

Soyez respectueux et constructif dans vos interactions.
