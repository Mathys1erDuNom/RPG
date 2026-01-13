import discord
from discord.ui import View, Button, Select
import json
import os

def load_json(file):
    with open(file, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

class ShopView(View):
    def __init__(self, joueur, on_shop_close):
        super().__init__(timeout=300)  # 5 minutes timeout
        self.joueur = joueur
        self.on_shop_close = on_shop_close
        
        # Charger les objets disponibles
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.objets = load_json(os.path.join(script_dir, "json/shop_items.json"))
        
        # Initialiser l'inventaire si nécessaire
        if "inventaire" not in self.joueur:
            self.joueur["inventaire"] = []
        if "gold" not in self.joueur:
            self.joueur["gold"] = 100
        
        # Créer les boutons
        self.setup_ui()
    
    def setup_ui(self):
        # Select pour acheter des objets
        options = []
        for obj in self.objets:
            emoji = "⚔️" if obj["type"] == "arme" else "🛡️" if obj["type"] == "armure" else "💊"
            options.append(
                discord.SelectOption(
                    label=f"{obj['nom']} - {obj['prix']}G",
                    description=obj["description"][:100],
                    value=obj["id"],
                    emoji=emoji
                )
            )
        
        self.select_acheter = Select(
            placeholder="💰 Acheter un objet",
            options=options[:25]  # Discord limite à 25 options
        )
        self.select_acheter.callback = self.acheter_objet
        self.add_item(self.select_acheter)
        
        # Select pour utiliser des objets de l'inventaire
        if self.joueur["inventaire"]:
            inv_options = []
            for item_id in self.joueur["inventaire"]:
                obj = next((o for o in self.objets if o["id"] == item_id), None)
                if obj:
                    emoji = "⚔️" if obj["type"] == "arme" else "🛡️" if obj["type"] == "armure" else "💊"
                    inv_options.append(
                        discord.SelectOption(
                            label=obj["nom"],
                            description=f"Utiliser: {obj['description'][:80]}",
                            value=obj["id"],
                            emoji=emoji
                        )
                    )
            
            if inv_options:
                self.select_utiliser = Select(
                    placeholder="🎒 Utiliser un objet",
                    options=inv_options[:25]
                )
                self.select_utiliser.callback = self.utiliser_objet
                self.add_item(self.select_utiliser)
        
        # Bouton pour quitter le shop
        btn_quitter = Button(label="Continuer l'aventure", style=discord.ButtonStyle.success, emoji="➡️")
        btn_quitter.callback = self.quitter_shop
        self.add_item(btn_quitter)
    
    def get_shop_content(self):
        """Génère le contenu du message du shop."""
        content = "🏪 **BOUTIQUE DU VOYAGEUR** 🏪\n\n"
        content += f"💰 **Or disponible : {self.joueur['gold']} G**\n"
        content += f"🎒 **Inventaire : {len(self.joueur['inventaire'])} objets**\n\n"
        
        # Stats actuelles
        content += "📊 **Vos stats actuelles :**\n"
        content += f"❤️ PV: {self.joueur['pv']}/{self.joueur['pv_max']} | "
        content += f"⚔️ Force: {self.joueur['force']} | "
        content += f"✨ Magie: {self.joueur['magie']}\n"
        content += f"🛡️ Armure: {self.joueur['armure']}% | "
        content += f"🔮 Armure Magique: {self.joueur['armure_magique']}%\n\n"
        
        # Inventaire
        if self.joueur["inventaire"]:
            content += "🎒 **Votre inventaire :**\n"
            for item_id in self.joueur["inventaire"]:
                obj = next((o for o in self.objets if o["id"] == item_id), None)
                if obj:
                    emoji = "⚔️" if obj["type"] == "arme" else "🛡️" if obj["type"] == "armure" else "💊"
                    content += f"{emoji} {obj['nom']}\n"
        
        return content
    
    async def acheter_objet(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        item_id = self.select_acheter.values[0]
        obj = next((o for o in self.objets if o["id"] == item_id), None)
        
        if not obj:
            await interaction.followup.send("❌ Objet introuvable !", ephemeral=True)
            return
        
        # Vérifier si le joueur a assez d'or
        if self.joueur["gold"] < obj["prix"]:
            await interaction.followup.send(
                f"❌ Pas assez d'or ! Il vous faut {obj['prix']}G mais vous n'avez que {self.joueur['gold']}G.",
                ephemeral=True
            )
            return
        
        # Acheter l'objet
        self.joueur["gold"] -= obj["prix"]
        self.joueur["inventaire"].append(item_id)
        
        # Sauvegarder
        save_json("json/personnage.json", self.joueur)
        
        # Recréer l'UI avec le nouvel inventaire
        self.clear_items()
        self.setup_ui()
        
        await interaction.message.edit(
            content=self.get_shop_content() + f"\n✅ **{obj['nom']} acheté pour {obj['prix']}G !**",
            view=self
        )
    
    async def utiliser_objet(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        item_id = self.select_utiliser.values[0]
        obj = next((o for o in self.objets if o["id"] == item_id), None)
        
        if not obj:
            await interaction.followup.send("❌ Objet introuvable !", ephemeral=True)
            return
        
        # Appliquer les effets
        message_effet = f"✨ **{obj['nom']} utilisé !**\n"
        
        for effet, valeur in obj["effets"].items():
            if effet == "heal":
                old_pv = self.joueur["pv"]
                self.joueur["pv"] = min(self.joueur["pv"] + valeur, self.joueur["pv_max"])
                heal = self.joueur["pv"] - old_pv
                message_effet += f"❤️ +{heal} PV restaurés\n"
            
            elif effet == "pv_max":
                self.joueur["pv_max"] += valeur
                self.joueur["pv"] += valeur
                message_effet += f"❤️ PV Max +{valeur}\n"
            
            elif effet == "force":
                self.joueur["force"] += valeur
                message_effet += f"⚔️ Force +{valeur}\n"
            
            elif effet == "magie":
                self.joueur["magie"] += valeur
                message_effet += f"✨ Magie +{valeur}\n"
            
            elif effet == "armure":
                self.joueur["armure"] += valeur
                message_effet += f"🛡️ Armure +{valeur}%\n"
            
            elif effet == "armure_magique":
                self.joueur["armure_magique"] += valeur
                message_effet += f"🔮 Armure Magique +{valeur}%\n"
            
            elif effet == "vitesse":
                self.joueur["vitesse"] += valeur
                message_effet += f"⚡ Vitesse +{valeur}\n"
            
            elif effet == "nouvelle_attaque":
                # Ajouter une nouvelle attaque
                if valeur not in [a["nom"] for a in self.joueur["attaques"]]:
                    # Charger la bibliothèque d'attaques
                    script_dir = os.path.dirname(os.path.abspath(__file__))
                    try:
                        attaques_dispo = load_json(os.path.join(script_dir, "json/attaques.json"))
                        nouvelle_attaque = next((a for a in attaques_dispo if a["nom"] == valeur), None)
                        if nouvelle_attaque:
                            self.joueur["attaques"].append(nouvelle_attaque)
                            message_effet += f"⚔️ Nouvelle attaque débloquée : {valeur} !\n"
                        else:
                            message_effet += f"⚠️ Attaque '{valeur}' introuvable dans la bibliothèque\n"
                    except FileNotFoundError:
                        message_effet += f"⚠️ Fichier attaques.json introuvable\n"
                else:
                    message_effet += f"ℹ️ Vous possédez déjà l'attaque {valeur}\n"
        
        # Retirer l'objet de l'inventaire si c'est un consommable
        if obj.get("consommable", True):
            self.joueur["inventaire"].remove(item_id)
        
        # Sauvegarder
        save_json("json/personnage.json", self.joueur)
        
        # Recréer l'UI
        self.clear_items()
        self.setup_ui()
        
        await interaction.message.edit(
            content=self.get_shop_content() + f"\n{message_effet}",
            view=self
        )
    
    async def quitter_shop(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        # Sauvegarder une dernière fois
        save_json("json/personnage.json", self.joueur)
        
        # Appeler le callback pour continuer le combat
        await self.on_shop_close(interaction)