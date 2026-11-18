# Board Skills & Agents

Inventaire automatique des skills et agents des 7 dépôts, rangés par but.

- `config.json` : les dépôts et dossiers lus (ajoute un dépôt ici pour qu'il entre dans le board).
- `build_board.py` : recense, classe par mots-clés, fusionne les doublons, repère les nouveautés.
- `board.json` : inventaire complet (sert aussi de mémoire pour détecter les nouveaux).
- `items.json`, `repos.json` : les fichiers envoyés au board.
- `index.html` : la page du board.

Board : https://claude.ai/artifact/TSsQCRkzw1BLGKZ8bbSeQs (privé tant qu'il n'est pas partagé).

```bash
python3 board/build_board.py --root ..   # dossier qui contient les 7 dépôts
```

Une tâche planifiée quotidienne relance le script, publie les nouveaux fichiers dans le board et commite `board.json` ici.
