# AVOCarbon SharePoint MCP

Serveur MCP Python pour gérer SharePoint et OneDrive avec Microsoft Graph.

## Actions incluses

- Profil, sites et bibliothèques
- Navigation dans les dossiers
- Recherche et lecture de fichiers
- Création de dossiers
- Upload simple et upload par blocs
- Mise à jour, copie, déplacement, renommage et suppression
- Liens de partage, invitations et permissions
- Liste et restauration des versions

## Configuration

Copier le modèle :

```bash
cp .env.example .env
```

Renseigner un **nouveau** secret Azure :

```env
AZURE_TENANT_ID=4e99b5ff-dd77-418a-8b69-1d684e911168
AZURE_CLIENT_ID=653f4fbf-ba11-406c-98ea-e61d637d79d0
AZURE_CLIENT_SECRET=your-new-secret
```

Le fichier `.env` est exclu de Git par `.gitignore`.

## Permissions Microsoft Graph

Pour un premier test avec des permissions d'application :

- `Sites.ReadWrite.All`
- `Files.ReadWrite.All`

Accorder ensuite le consentement administrateur. Pour la production, préférer `Sites.Selected` afin de limiter l'accès aux sites requis.

## Démarrage local

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
python server.py
```

Endpoint MCP :

```text
http://localhost:8000/mcp
```

## Docker

```bash
docker build -t avocarbon-sharepoint-mcp .
docker run --rm -p 8000:8000 --env-file .env avocarbon-sharepoint-mcp
```

## Azure App Service

Ajouter les paramètres d'application suivants :

```text
AZURE_TENANT_ID
AZURE_CLIENT_ID
AZURE_CLIENT_SECRET
HOST=0.0.0.0
PORT=8000
MCP_TRANSPORT=streamable-http
```

Commande de démarrage :

```text
python server.py
```

URL publique habituelle :

```text
https://YOUR-APP.azurewebsites.net/mcp
```

## Exemple AVOCarbon SharePoint

Pour `https://avocarbongroup.sharepoint.com/sites/pdc/...` :

1. `get_site(hostname="avocarbongroup.sharepoint.com", site_path="/sites/pdc")`
2. `list_site_drives(site_id=...)`
3. `list_folder_items(drive_id=..., folder_path=...)`
4. `upload_file(drive_id=..., parent_item_id=..., file_name=..., content_base64=...)`

## Sécurité

Ne jamais mettre un client secret réel dans GitHub, même dans un dépôt privé. Utiliser les variables d'environnement Azure App Service ou GitHub Actions Secrets.
