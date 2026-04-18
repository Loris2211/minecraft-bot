import os
import discord
import asyncio
from mcstatus import JavaServer

TOKEN = os.getenv("TOKEN")
CHANNEL_ID = 1495136829228322928

server = JavaServer.lookup("confdesenclumes.ddns.net:25565")

intents = discord.Intents.default()
client = discord.Client(intents=intents)

last = None
channel = None

async def monitor():
    global last, channel

    await client.wait_until_ready()

    # 🔥 récupère UNE FOIS le channel (stable)
    channel = await client.fetch_channel(CHANNEL_ID)

    while not client.is_closed():
        try:
            # 🧠 sécurité si le serveur répond mal
            try:
                status = server.status()
                current = status.players.online
            except:
                current = -1

            if last is not None and current != last:
                await channel.send(f"🔔 Discord : {last} → {current}")

            last = current

        except Exception as e:
            print("Erreur monitor :", e)

        await asyncio.sleep(30)

@client.event
async def on_ready():
    print(f"Bot connecté : {client.user}")

    client.loop.create_task(monitor())

    # 🔥 safe send (évite crash si channel pas prêt)
    try:
        ch = await client.fetch_channel(CHANNEL_ID)
        await ch.send("✅ bot online")
    except Exception as e:
        print("Erreur on_ready :", e)

client.run(TOKEN)
