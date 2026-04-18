import os
import discord
import asyncio
from datetime import datetime
from mcstatus import JavaServer

TOKEN = os.getenv("TOKEN")
CHANNEL_ID = 1495136829228322928

server = JavaServer.lookup("confdesenclumes.ddns.net:25565")

intents = discord.Intents.default()
client = discord.Client(intents=intents)

last_players = set()
channel = None

last_daily = None
server_offline = False  # 🧠 état du serveur


async def monitor():
    global last_players, channel, last_daily, server_offline

    await client.wait_until_ready()
    channel = await client.fetch_channel(CHANNEL_ID)

    while not client.is_closed():
        try:
            status = server.status()

            # 🟢 serveur de nouveau en ligne
            if server_offline:
                await channel.send("🟢 Serveur Minecraft de nouveau en ligne")
                server_offline = False

            # 👥 joueurs actuels
            if status.players.sample:
                current_players = {p.name for p in status.players.sample}
            else:
                current_players = set()

            current_count = len(current_players)

            print("Joueurs actuels =", current_players)

            joined = current_players - last_players
            left = last_players - current_players

            # 🟢 JOINS
            if joined:
                await channel.send(
                    f"🟢 **Joueur(s) connecté(s)** : {', '.join(joined)}\n"
                    f"👥 Joueurs actuellement : {current_count}"
                )

            # 🔴 LEAVES
            if left:
                await channel.send(
                    f"🔴 **Joueur(s) déconnecté(s)** : {', '.join(left)}\n"
                    f"👥 Joueurs actuellement : {current_count}"
                )

            last_players = current_players

            # 🕛 MESSAGE QUOTIDIEN
            now = datetime.now()

            if now.hour == 12 and (last_daily is None or last_daily != now.date()):
                await channel.send("🟢 Bot toujours actif (check quotidien)")
                last_daily = now.date()

        except Exception as e:
            print("Erreur serveur Minecraft :", e)

            # 🚨 serveur OFFLINE (1 seul message)
            if not server_offline:
                await channel.send("🔴 Serveur Minecraft inaccessible ou hors ligne")
                server_offline = True

        await asyncio.sleep(30)


@client.event
async def on_ready():
    print(f"Bot connecté : {client.user}")
    client.loop.create_task(monitor())

    try:
        ch = await client.fetch_channel(CHANNEL_ID)
        await ch.send("✅ bot online")
    except Exception as e:
        print("Erreur on_ready :", e)


client.run(TOKEN)
