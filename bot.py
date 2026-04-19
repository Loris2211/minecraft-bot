import os
import discord
import asyncio
import aiohttp
from datetime import datetime, date
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

track_message = None

# 🔥 historique positions + distance journalière
player_history = {}
player_daily_distance = {}
current_day = date.today()


# =========================
# 📡 GET SQUAREMAP DATA
# =========================
async def get_players():
    async with aiohttp.ClientSession() as session:
        async with session.get(SQUAREMAP_URL) as resp:
            data = await resp.json()
            return data.get("players", [])


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
    return f"❓ {world}"


# =========================
# ⏰ RESET JOURNALIER
# =========================
def reset_daily():
    global player_history, player_daily_distance
    player_history = {}
    player_daily_distance = {}


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

            now = datetime.now()
            if now.hour == 12 and (last_daily is None or last_daily != now.date()):
                await channel.send("🟢 Bot toujours actif (check quotidien)")
                last_daily = now.date()

        except Exception as e:
            print("Erreur serveur Minecraft :", e)
            if not server_offline:
                await channel.send("🔴 Serveur Minecraft inaccessible")
                server_offline = True

        await asyncio.sleep(10)


# =========================
# 📍 TRACK POSITIONS + DISTANCE JOURNALIÈRE
# =========================
async def monitor_positions():
    global track_message, monitoring, current_day

    await client.wait_until_ready()
    track_channel = await client.fetch_channel(TRACK_CHANNEL_ID)

    while monitoring:
        try:
            # 🔥 reset jour
            if date.today() != current_day:
                current_day = date.today()
                reset_daily()

            players = await get_players()

            content = "📍 **Tracking joueurs (jour)**\n\n"

            if not players:
                content += "Aucun joueur"
            else:
                for p in players:
                    name = p["name"]
                    x, y, z = p["x"], p["y"], p["z"]
                    health = p.get("health", "?")
                    armor = p.get("armor", "?")
                    world = get_world_name(p.get("world", "unknown"))

                    # init
                    if name not in player_history:
                        player_history[name] = []
                        player_daily_distance[name] = 0

                    hist = player_history[name]

                    # ajouter point
                    hist.append((x, z))

                    if len(hist) > 100:
                        hist.pop(0)

                    # calcul distance (incremental propre)
                    if len(hist) >= 2:
                        x1, z1 = hist[-2]
                        x2, z2 = hist[-1]
                        player_daily_distance[name] += ((x2 - x1)**2 + (z2 - z1)**2) ** 0.5

                    content += (
                        f"🧑 **{name}**\n"
                        f"🌍 {world}\n"
                        f"📍 {x} / {y} / {z}\n"
                        f"❤️ {health} | 🛡 {armor}\n"
                        f"📏 Distance jour : {int(player_daily_distance[name])} blocs\n\n"
                    )

            if track_message is None:
                track_message = await track_channel.send(content)
            else:
                await track_message.edit(content=content)

        except Exception as e:
            print("Erreur tracking :", e)

        await asyncio.sleep(10)


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
