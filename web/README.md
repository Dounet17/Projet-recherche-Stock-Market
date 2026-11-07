# Interface web

Première version de l'interface : une page sans étape de compilation, qui présente les résultats déjà calculés.

```bash
venv/bin/python reports/build_web_data.py   # environ 1 minute, écrit web/site_data.js
```

Le script ne lance aucun test de stratégie et s'arrête si une courbe ne retombe pas sur le capital du journal. Rien n'y est lu après le 31/12/2024, sauf les chiffres de la validation 2025-2026 déjà publiés, recopiés à la main.

`index.html` suit le format des artefacts : il ne contient ni `<!doctype>`, ni `<html>`, ni `<body>`, ajoutés à la publication. Le choix du cadre pour le site définitif reste à faire.

Orbes de chargement : `thinking-orbs` 0.3.2 (licence MIT), moteur chargé depuis unpkg. La page reste complète si le chargement échoue.
