import os
import discord
import asyncio
import aiohttp
from datetime import datetime
from mcstatus import JavaServer
from PIL import Image, ImageDraw
from io import BytesIO

TOKEN = os.getenv("TOKEN")

CHANNEL_ID = 1495136829228322928      # monitoring
MAP_CHANNEL_ID = 1495415786997678282   # map
GUILD_ID = 1495136828364292246    

server = JavaServer.lookup("confdesenclumes.ddns.net:25565")

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(client)

last_players = set()
channel = None

last_daily = None
server_offline = False
monitoring = False

map_message = None

# =========================
# 🔥 SQUAREMAP CONFIG
# =========================
BASE_URL = "http://confdesenclumes.ddns.net:3001/tiles/minecraft_overworld/0"

TILES = {
    "0_0": (1, 0),
    "0_-1": (1, 1),
    "-1_0": (0, 0),
    "-1_-1": (0, 1),
}

TILE_SIZE = 128  # dépend Squaremap (souvent 128 ou 256)


# =========================
# 🗺️ LOAD TILE
# =========================
async def load_tile(session, name):
    url = f"{BASE_URL}/{name}.png"
    async with session.get(url) as resp:
        data = await resp.read()
        return Image.open(BytesIO(data)).convert("RGBA")


# =========================
# 🗺️ BUILD MAP
# =========================
async def build_map(players):
    async with aiohttp.ClientSession() as session:
        tiles = {}

        for name in TILES:
            tiles[name] = await load_tile(session, name)

        base = Image.new("RGBA", (TILE_SIZE * 2, TILE_SIZE * 2))

        for name, (x, y) in TILES.items():
            base.paste(tiles[name], (x * TILE_SIZE, y * TILE_SIZE))

        draw = ImageDraw.Draw(base)

        # =========================
        # 🔴 PLAYERS OVERLAY
        # =========================
        for p in players:
            x = p.get("x", 0)
            z = p.get("z", 0)

            # ⚠️ SCALE À AJUSTER selon ton serveur
            scale = 0.1

            px = int(TILE_SIZE + x * scale)
            pz = int(TILE_SIZE + z * scale)

            draw.ellipse((px-3, pz-3, px+3, pz+3), fill="red")

        return base


# =========================
# 👥 MONITOR MC SERVER
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

            if status.players.sample:
                current_players = {p.name for p in status.players.sample}
            else:
                current_players = set()

            current_count = len(current_players)

            joined = current_players - last_players
            left = last_players - current_players

            if joined:
                await channel.send(
                    f"🟢 Connecté(s): {', '.join(joined)}\n👥 {current_count} joueurs"
                )

            if left:
                await channel.send(
                    f"🔴 Déconnecté(s): {', '.join(left)}\n👥 {current_count} joueurs"
                )

            last_players = current_players

        except Exception as e:
            if not server_offline:
                await channel.send("🔴 Serveur Minecraft inaccessible")
                server_offline = True
            print("MC ERROR:", e)

        await asyncio.sleep(10)


# =========================
# 🗺️ MONITOR MAP
# =========================
map_message = None

SQUAREMAP_PLAYERS_URL = "http://confdesenclumes.ddns.net:3001/tiles/players.json"


async def monitor_map():
    global map_message, monitoring

    await client.wait_until_ready()
    map_channel = await client.fetch_channel(MAP_CHANNEL_ID)

    while monitoring:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(SQUAREMAP_PLAYERS_URL) as resp:
                    data = await resp.json()

            players = data.get("players", [])

            # 📝 TEXTE (tu voulais le garder)
            content = "📡 **Joueurs (Squaremap)**\n\n"

            if not players:
                content += "Aucun joueur"
            else:
                for p in players:
                    content += (
                        f"🧑 {p['name']}\n"
                        f"📍 {p['x']} / {p['y']} / {p['z']}\n"
                        f"❤️ {p['health']} | 🛡 {p['armor']}\n\n"
                    )

            # 🗺️ IMAGE SIMPLE (pas les tiles pour l’instant → plus stable)
            img = Image.new("RGB", (500, 500), (30, 30, 30))
            draw = ImageDraw.Draw(img)

            for p in players:
                x = p["x"]
                z = p["z"]

                # ⚠️ scale simplifié
                scale = 0.05

                px = int(250 + x * scale)
                pz = int(250 + z * scale)

                draw.ellipse((px-5, pz-5, px+5, pz+5), fill="red")

                draw.text((px+6, pz), p["name"], fill="white")

            buffer = BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)

            file = discord.File(buffer, filename="map.png")

            if map_message is None:
                map_message = await map_channel.send(content=content, file=file)
            else:
                await map_message.edit(content=content, attachments=[file])

        except Exception as e:
            print("❌ MAP ERROR:", e)

        await asyncio.sleep(10)


# =========================
# /start
# =========================
@tree.command(name="start")
async def start(interaction: discord.Interaction):
    global monitoring

    if monitoring:
        await interaction.response.send_message("⚠️ déjà actif", ephemeral=True)
        return

    monitoring = True
    client.loop.create_task(monitor())
    client.loop.create_task(monitor_map())

    await interaction.response.send_message("🟢 monitoring ON")


# =========================
# /stop
# =========================
@tree.command(name="stop")
async def stop(interaction: discord.Interaction):
    global monitoring
    monitoring = False
    await interaction.response.send_message("🔴 monitoring OFF")


# =========================
# /test
# =========================
@tree.command(name="test")
async def test(interaction: discord.Interaction):
    try:
        status = server.status()
        await interaction.response.send_message(
            f"🟢 OK\n👥 {status.players.online} joueurs"
        )
    except:
        await interaction.response.send_message("🔴 serveur offline")


# =========================
# ON READY
# =========================
@client.event
async def on_ready():
    print(f"Bot connecté {client.user}")

    guild = discord.Object(id=GUILD_ID)
    tree.copy_global_to(guild=guild)
    await tree.sync(guild=guild)

    print("commands synced")


client.run(TOKEN)
