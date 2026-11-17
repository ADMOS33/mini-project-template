L’objectif est de choisir un projet d’implémentation de votre choix (petite application, petit jeu, …) a faire en groupe (2, ou 3). Ce projet doit être:

- **Petit, mais non trivial**. Ce ne doit pas être quelque chose de faisable en une poignée de prompts (vous avez 2 semaines pour le faire). L’idée est d’avoir un retour d’expérience avec un projet qui commence à passer à l’échelle. Disons au moins une vingtaine de fichiers de code et une cinquantaine de commits (ça peut paraître gros! mais vous allez voir, ça passe très vite).
- **Visible sur Git**. Pour pouvoir jeter un oeil sur le code et le développement, le code doit être visible (pour moi, vous pouvez le garder privé), ainsi que des informations basiques de développement. Pour ce faire, j’ai crée un “hook” (comme présenté en classe par Tristan!)  qui devrait se charger automatiquement sur Vibe (testé avec 3.1.2). Le hook ne fait qu’enregistrer des informations. On pourra s’en servir pour analyser des données de développement. Vous devez commencer par forker le repo template: https://github.com/rrobbes/mini-project-template/ , quand vous lancez l’agent dans le repo 
- **Utilisable par un agent**. Un petit côté experimental: votre application doit être au moins partiellement (c’est pas forcément évident pour toutes les scénarios) utilisable par un agent. Ça peut être soit par une interface en ligne de commande (en parallèle à une interface web/graphique), soit par un serveur MCP. Si vous avez des difficultés à imaginer quoi faire dans votre cas, envoyez-moi un mail et on en parle. Si vous voulez, vous pouvez même faire un “skill” (comme présenté en classe par Paul!) afin d’enseigner à votre agent comment utiliser l’application.
- **Utilisez Vibe**. Certains d’entre vous utilisent Claude, Codex, … le hook ne marchera pas avec ces agents.

Dans le cas ou vous avez déjà commencé dans la demi-heure, je pense que ça ne vous prendra pas trop de temps de “recommencer” avec le template du repo.  

Timeline:
- D’ici **mercredi 18** maximum: 
	- un membre du groupe doit forker le projet (clicker sur un bouton): https://github.com/rrobbes/mini-project-template/ 
	- inviter votre binôme.
	- m’inviter en tant que membre du projet (rrobbes sur GitHub). 
	- lancer Vibe une fois dans le repo, “truster” la configuration, et vérifier que des événements s’enregistrent dans le dossier events. 
- D'ici **vendredi 20**: 
	- faire au moins un premier commit d’un README.md avec un plan initial du projet. 
	- m’envoyer un mail si vous avez des difficultés à envisager comment faire que votre application soit utilisable par un agent.
- Jusqu’a **lundi 30**:
  - travail sur le mini-projet.
  - ajouter un fichier "report.md" ou vous faîtes une (brève) réflexion sur votre processus de travail, les facilités, les difficultés.
