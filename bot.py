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

# 🕛 anti double message quotidien
last_daily = None


async def monitor():
    global last_players, channel, last_daily

    await client.wait_until_ready()
    channel = await client.fetch_channel(CHANNEL_ID)

    while not client.is_closed():
        try:
            status = server.status()

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

            # 🕛 MESSAGE QUOTIDIEN À 12H
            now = datetime.now()

            if now.hour == 12 and (last_daily is None or last_daily != now.date()):
                await channel.send("🟢 Bot toujours actif (check quotidien)")
                last_daily = now.date()

        except Exception as e:
            print("Erreur :", e)

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
