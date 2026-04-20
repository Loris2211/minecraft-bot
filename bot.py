import os
import discord
import asyncio
import aiohttp
import traceback
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

# =========================
# VARIABLES
# =========================
last_players = set()
channel = None

last_daily = None
server_offline = False
monitoring = False
tasks_started = False

track_message = None
player_history = {}


# =========================
# 📡 GET PLAYERS DATA (SAFE)
# =========================
async def get_players():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(SQUAREMAP_URL) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
                return data.get("players", [])
    except:
        return []


# =========================
# 🌍 WORLD NAME
# =========================
def get_world_name(world):
    if world == "minecraft_overworld":
        return "🌍 Overworld"
    elif world == "minecraft_the_nether":
        return "🔥 Nether"
    elif world == "minecraft_the_end":
        return "🌌 End"
    else:
        return f"❓ {world}"


# =========================
# 👥 MONITOR SERVER
# =========================
async def monitor():
    global last_players, channel, last_daily, server_offline, monitoring

    await client.wait_until_ready()
    channel = await client.fetch_channel(CHANNEL_ID)

    while monitoring:
        try:
            status = server.status()

            # 🟢 serveur revient
            if server_offline:
                await channel.send("@everyone 🟢 Serveur Minecraft de nouveau en ligne")
                server_offline = False

            current_players = {p.name for p in (status.players.sample or [])}
            current_count = len(current_players)

            joined = current_players - last_players
            left = last_players - current_players

            # 🟢 JOIN
            if joined:
                await channel.send(
                    f"@everyone 🟢 **Connecté(s)** : {', '.join(joined)}\n"
                    f"👥 Joueurs : {current_count}"
                )

            # 🔴 LEAVE
            if left:
                await channel.send(
                    f"@everyone 🔴 **Déconnecté(s)** : {', '.join(left)}\n"
                    f"👥 Joueurs : {current_count}"
                )

            last_players = current_players

            # 🕛 daily check
            now = datetime.now()
            if now.hour == 12 and (last_daily is None or last_daily != now.date()):
                await channel.send("@here 🟢 Bot toujours actif (check quotidien)")
                last_daily = now.date()

        except Exception as e:
            print("Erreur serveur Minecraft :", e)

            if not server_offline:
                await channel.send("@everyone 🔴 Serveur Minecraft inaccessible ou hors ligne")
                server_offline = True

        await asyncio.sleep(10)


# =========================
# 📍 TRACK POSITIONS
# =========================
async def monitor_positions():
    global monitoring

    await client.wait_until_ready()
    track_channel = await client.fetch_channel(TRACK_CHANNEL_ID)

    while monitoring:
        try:
            players = await get_players()
            current_names = set()

            if players:
                for p in players:
                    name = p.get("name")
                    current_names.add(name)

                    x = p.get("x")
                    y = p.get("y")
                    z = p.get("z")
                    health = p.get("health", "?")
                    armor = p.get("armor", "?")
                    world = get_world_name(p.get("world", "unknown"))

                    # 🔥 historique
                    if name not in player_history:
                        player_history[name] = []

                    player_history[name].append((x, z, datetime.now()))

                    if len(player_history[name]) > 50:
                        player_history[name].pop(0)

                    # 📏 distance
                    distance = 0
                    hist = player_history[name]

                    for i in range(len(hist) - 1):
                        x1, z1, _ = hist[i]
                        x2, z2, _ = hist[i + 1]
                        distance += ((x2 - x1) ** 2 + (z2 - z1) ** 2) ** 0.5

                    content = (
                        f"🧑 **{name}**\n"
                        f"🌍 Monde : {world}\n"
                        f"📍 {x} / {y} / {z}\n"
                        f"❤️ {health} | 🛡 {armor}\n"
                        f"📏 Distance : {int(distance)} blocs\n"
                        f"🕒 Points : {len(hist)}"
                    )

                    # 🔥 créer ou update message joueur
                    if name not in player_messages:
                        msg = await track_channel.send(content)
                        player_messages[name] = msg
                    else:
                        try:
                            await player_messages[name].edit(content=content)
                        except:
                            msg = await track_channel.send(content)
                            player_messages[name] = msg

            # 🔴 SUPPRIMER messages des joueurs déco
            to_remove = [name for name in player_messages if name not in current_names]

            for name in to_remove:
                try:
                    await player_messages[name].delete()
                except:
                    pass

                del player_messages[name]

                # reset historique si tu veux (optionnel)
                if name in player_history:
                    del player_history[name]

        except Exception:
            traceback.print_exc()

        await asyncio.sleep(10)


# =========================
# 🔥 COMMANDES
# =========================
@tree.command(name="start", description="Démarrer le monitoring")
async def start(interaction: discord.Interaction):
    global monitoring, tasks_started

    if monitoring:
        await interaction.response.send_message("⚠️ Déjà actif", ephemeral=True)
        return

    monitoring = True

    if not tasks_started:
        client.loop.create_task(monitor())
        client.loop.create_task(monitor_positions())
        tasks_started = True

    await interaction.response.send_message("🟢 Monitoring ON")


@tree.command(name="stop", description="Arrêter le monitoring")
async def stop(interaction: discord.Interaction):
    global monitoring

    monitoring = False
    await interaction.response.send_message("🔴 Monitoring OFF")


@tree.command(name="test", description="Tester le bot")
async def test(interaction: discord.Interaction):
    global monitoring

    try:
        status = server.status()

        await interaction.response.send_message(
            f"🟢 Bot OK\n"
            f"🌐 Serveur OK\n"
            f"👥 Joueurs : {status.players.online}\n"
            f"📡 Monitoring : {'ON' if monitoring else 'OFF'}"
        )

    except:
        await interaction.response.send_message(
            f"🟢 Bot OK\n"
            f"🔴 Serveur OFF\n"
            f"📡 Monitoring : {'ON' if monitoring else 'OFF'}"
        )


# =========================
# 🚀 READY
# =========================
@client.event
async def on_ready():
    print(f"Bot connecté : {client.user}")

    guild = discord.Object(id=GUILD_ID)
    tree.copy_global_to(guild=guild)
    await tree.sync(guild=guild)

    print("Commandes synchronisées")

    ch = await client.fetch_channel(CHANNEL_ID)
    await ch.send("✅ Bot online")


client.run(TOKEN)
