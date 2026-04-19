import os
import discord
import asyncio
import aiohttp
from datetime import datetime
from mcstatus import JavaServer

TOKEN = os.getenv("TOKEN")

CHANNEL_ID = 1495136829228322928
TRACK_CHANNEL_ID = 1495415786997678282
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

# 👇 SYSTEME PAR JOUEUR
player_messages = {}
player_history = {}
player_last_data = {}


# =========================
# 📡 GET SQUAREMAP DATA
# =========================
async def get_players():
    async with aiohttp.ClientSession() as session:
        async with session.get(SQUAREMAP_URL) as resp:
            data = await resp.json()
            return data.get("players", [])


# =========================
# 🌍 WORLD
# =========================
def get_world_name(world):
    if world == "minecraft_overworld":
        return "🌍 Overworld"
    elif world == "minecraft_the_nether":
        return "🔥 Nether"
    elif world == "minecraft_the_end":
        return "🌌 End"
    return f"❓ {world}"


# =========================
# 👥 MONITOR SERVEUR
# =========================
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

            current_players = {p.name for p in (status.players.sample or [])}
            current_count = len(current_players)

            joined = current_players - last_players
            left = last_players - current_players

            if joined:
                await channel.send(f"🟢 Connecté(s) : {', '.join(joined)}")
            if left:
                await channel.send(f"🔴 Déconnecté(s) : {', '.join(left)}")

            last_players = current_players

        except Exception as e:
            print("Erreur serveur :", e)
            if not server_offline:
                await channel.send("🔴 Serveur Minecraft inaccessible")
                server_offline = True

        await asyncio.sleep(10)


# =========================
# 📍 TRACK PAR JOUEUR (AMÉLIORÉ)
# =========================
async def monitor_positions():
    global monitoring

    await client.wait_until_ready()
    track_channel = await client.fetch_channel(TRACK_CHANNEL_ID)

    while monitoring:
        try:
            players = await get_players()
            active_names = set()

            for p in players:
                name = p["name"]
                active_names.add(name)

                x, y, z = p["x"], p["y"], p["z"]
                health = p.get("health", "?")
                armor = p.get("armor", "?")
                world = get_world_name(p.get("world", "unknown"))

                # init
                if name not in player_history:
                    player_history[name] = []

                hist = player_history[name]

                # ajout position
                hist.append((x, z))

                if len(hist) > 100:
                    hist.pop(0)

                # distance journalière simple
                distance = 0
                for i in range(len(hist)-1):
                    x1, z1 = hist[i]
                    x2, z2 = hist[i+1]
                    distance += ((x2-x1)**2 + (z2-z1)**2) ** 0.5

                content = (
                    f"🧑 **{name}**\n"
                    f"🌍 {world}\n"
                    f"📍 {x} / {y} / {z}\n"
                    f"❤️ {health} | 🛡 {armor}\n"
                    f"📏 Distance : {int(distance)} blocs"
                )

                # CREATE OR UPDATE MESSAGE
                if name not in player_messages:
                    msg = await track_channel.send(content)
                    player_messages[name] = msg
                    player_last_data[name] = content
                else:
                    if player_last_data[name] != content:
                        await player_messages[name].edit(content=content)
                        player_last_data[name] = content

            # suppression joueurs offline
            for name in list(player_messages.keys()):
                if name not in active_names:
                    try:
                        await player_messages[name].edit(
                            content=f"🔴 **{name} hors ligne**"
                        )
                    except:
                        pass

                    del player_messages[name]
                    del player_last_data[name]

        except Exception as e:
            print("Erreur tracking :", e)

        await asyncio.sleep(5)


# =========================
# COMMANDES
# =========================
@tree.command(name="start", description="Démarrer monitoring")
async def start(interaction: discord.Interaction):
    global monitoring

    if monitoring:
        await interaction.response.send_message("⚠️ Déjà actif", ephemeral=True)
        return

    monitoring = True
    client.loop.create_task(monitor())
    client.loop.create_task(monitor_positions())

    await interaction.response.send_message("🟢 Monitoring ON")


@tree.command(name="stop", description="Arrêter monitoring")
async def stop(interaction: discord.Interaction):
    global monitoring
    monitoring = False
    await interaction.response.send_message("🔴 Monitoring OFF")


@tree.command(name="test", description="Tester bot")
async def test(interaction: discord.Interaction):
    try:
        status = server.status()
        await interaction.response.send_message(
            f"🟢 OK\n🌐 Serveur OK\n👥 Joueurs : {status.players.online}\n📡 Monitoring : {'ON' if monitoring else 'OFF'}"
        )
    except:
        await interaction.response.send_message(
            f"🟢 Bot OK\n🔴 Serveur OFF\n📡 Monitoring : {'ON' if monitoring else 'OFF'}"
        )


# =========================
# READY
# =========================
@client.event
async def on_ready():
    print(f"Bot connecté : {client.user}")

    guild = discord.Object(id=GUILD_ID)
    tree.copy_global_to(guild=guild)
    await tree.sync(guild=guild)

    ch = await client.fetch_channel(CHANNEL_ID)
    await ch.send("✅ Bot online")


client.run(TOKEN)
