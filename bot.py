import os
import discord
import asyncio
import aiohttp
from datetime import datetime
from mcstatus import JavaServer

TOKEN = os.getenv("TOKEN")

CHANNEL_ID = 1495136829228322928      # monitoring
MAP_CHANNEL_ID = 1495415786997678282   # 🔥 A REMPLACER (nouveau salon)
GUILD_ID = 1495136828364292246    

server = JavaServer.lookup("confdesenclumes.ddns.net:25565")

SQUAREMAP_URL = "http://confdesenclumes.ddns.net:3001/tiles/players.json"

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(client)

last_players = set()
channel = None

last_daily = None
server_offline = False
monitoring = False


# 🔥 Récup données Squaremap
async def get_squaremap_players():
    async with aiohttp.ClientSession() as session:
        async with session.get(SQUAREMAP_URL) as resp:
            data = await resp.json()
            return data.get("players", [])


# 🔥 MONITOR SERVEUR (inchangé)
async def monitor():
    global last_players, channel, last_daily, server_offline, monitoring

    await client.wait_until_ready()
    channel = await client.fetch_channel(CHANNEL_ID)

    while monitoring:
        try:
            status = server.status()

            if server_offline:
                await channel.send("🟢 Serveur Minecraft de nouveau en ligne")
                server_offline = False

            if status.players.sample:
                current_players = {p.name for p in status.players.sample}
            else:
                current_players = set()

            current_count = len(current_players)

            joined = current_players - last_players
            left = last_players - current_players

            if joined:
                await channel.send(
                    f"🟢 **Joueur(s) connecté(s)** : {', '.join(joined)}\n"
                    f"👥 Joueurs actuellement : {current_count}"
                )

            if left:
                await channel.send(
                    f"🔴 **Joueur(s) déconnecté(s)** : {', '.join(left)}\n"
                    f"👥 Joueurs actuellement : {current_count}"
                )

            last_players = current_players

            now = datetime.now()
            if now.hour == 12 and (last_daily is None or last_daily != now.date()):
                await channel.send("🟢 Bot toujours actif (check quotidien)")
                last_daily = now.date()

        except Exception as e:
            print("Erreur serveur Minecraft :", e)

            if not server_offline:
                await channel.send("🔴 Serveur Minecraft inaccessible ou hors ligne")
                server_offline = True

        await asyncio.sleep(10)


# 🔥 MONITOR MAP (NOUVEAU)
async def monitor_map():
    global map_message, monitoring

    await client.wait_until_ready()
    map_channel = await client.fetch_channel(MAP_CHANNEL_ID)

    map_message = None  # 🔥 reset propre au démarrage de la boucle

    while monitoring:
        try:
            players = await get_squaremap_players()

            if not players:
                content = "📡 Aucun joueur détecté"
            else:
                content = "📡 **Joueurs en ligne**\n\n"

                for p in players:
                    name = p.get("name")
                    x = p.get("x")
                    y = p.get("y")
                    z = p.get("z")
                    health = p.get("health")
                    armor = p.get("armor")

                    content += (
                        f"🧑 **{name}**\n"
                        f"📍 {x}/{y}/{z}\n"
                        f"❤️ {health} | 🛡 {armor}\n\n"
                    )

            # 🔥 créer le message si besoin
            if map_message is None:
                map_message = await map_channel.send(content)
            else:
                await map_message.edit(content=content)

        except Exception as e:
            print("❌ ERREUR MAP =", e)

            # 🔥 important : éviter blocage silencieux
            if map_message:
                try:
                    await map_message.edit(content=f"⚠️ Erreur Squaremap : {e}")
                except:
                    pass

        await asyncio.sleep(10)

# 🔥 /start
@tree.command(name="start", description="Démarrer le monitoring Minecraft")
async def start(interaction: discord.Interaction):
    global monitoring

    if monitoring:
        await interaction.response.send_message("⚠️ Monitoring déjà actif", ephemeral=True)
        return

    monitoring = True
    client.loop.create_task(monitor())
    client.loop.create_task(monitor_map())  # 🔥 ajouté

    await interaction.response.send_message("🟢 Monitoring démarré")


# 🔥 /stop
@tree.command(name="stop", description="Arrêter le monitoring Minecraft")
async def stop(interaction: discord.Interaction):
    global monitoring

    if not monitoring:
        await interaction.response.send_message("⚠️ Monitoring déjà arrêté", ephemeral=True)
        return

    monitoring = False
    await interaction.response.send_message("🔴 Monitoring arrêté")


# 🔥 /test (inchangé)
@tree.command(name="test", description="Tester le bot, le serveur et le monitoring")
async def test(interaction: discord.Interaction):
    global monitoring

    try:
        status = server.status()

        if status.players.sample:
            players = [p.name for p in status.players.sample]
        else:
            players = []

        await interaction.response.send_message(
            f"🟢 Bot OK\n"
            f"🌐 Serveur OK\n"
            f"👥 Joueurs : {status.players.online}\n"
            f"📋 Liste : {', '.join(players) if players else 'aucun'}\n"
            f"📡 Monitoring : {'🟢 ON' if monitoring else '🔴 OFF'}"
        )

    except Exception:
        await interaction.response.send_message(
            f"🟢 Bot OK\n"
            f"🔴 Serveur Minecraft inaccessible\n"
            f"📡 Monitoring : {'🟢 ON' if monitoring else '🔴 OFF'}"
        )


@client.event
async def on_ready():
    print(f"Bot connecté : {client.user}")

    guild = discord.Object(id=GUILD_ID)
    tree.copy_global_to(guild=guild)
    await tree.sync(guild=guild)

    print("Commandes synchronisées")

    try:
        ch = await client.fetch_channel(CHANNEL_ID)
        await ch.send("✅ bot online (commands ready)")
    except Exception as e:
        print("Erreur on_ready :", e)


client.run(TOKEN)
