import os
import discord
import asyncio
from mcstatus import JavaServer

# 🔐 TOKEN sécurisé via Railway
TOKEN = os.getenv("TOKEN")

# 🎮 ID du salon Discord
CHANNEL_ID = 1495136829228322928

# 🌍 Serveur Minecraft
server = JavaServer.lookup("confdesenclumes.ddns.net:25565")

intents = discord.Intents.default()
client = discord.Client(intents=intents)

last = None
async def monitor():
    global last
    await client.wait_until_ready()

    while not client.is_closed():
        try:
            channel = await client.fetch_channel(CHANNEL_ID)

            status = server.status()
            current = status.players.online

            if last is not None and current != last:
                await channel.send(f"🔔 Discord : {last} → {current}")

            last = current

        except Exception as e:
            print("Erreur :", e)

        await asyncio.sleep(30)

@client.event
async def on_ready():
    print(f"Bot connecté : {client.user}")
    client.loop.create_task(monitor())

client.run(TOKEN)
