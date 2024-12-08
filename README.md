# Connectivity Guard

## Comment ça marche ?
Le système surveille en permanence le serveur via une connexion WebSocket. Si le serveur ne répond plus, il va :
1. Essayer de se reconnecter plusieurs fois (on sait jamais, ça peut être juste un petit lag)
2. Si ça marche toujours pas, il change l'IP dans Cloudflare pour pointer vers le serveur de backup
3. Envoie un message sur Discord avec le webhook pour prévenir
4. Continue de surveiller pour rebasculer sur le serveur principal quand il remarche

## 
- Python (version 3.8+)


```bash
pip install -r requirements.txt
```
---

```bash
python src/main.py
```



## Configuration

Dans le fichier `config.yaml`, tu peux régler :
- Le temps entre chaque vérification
- Combien de fois il essaie de se reconnecter avant de basculer
- Si tu veux qu'il revienne automatiquement sur le serveur principal
- Les temps d'attente entre les changements DNS

## Logs

Le système garde une trace de tout ce qui se passe dans le dossier `logs/`. Tu peux y voir :
- Quand il y a eu des pannes
- Les changements d'IP
- Les erreurs
- Le temps de dispo du serveur


