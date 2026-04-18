import discord
import time
import threading
from mcstatus import JavaServer

TOKEN = "MTQ5NTEzOTQ0NzQ3NjU4NDU1OQ.GwF1Of.YVOW6hMVAaAgEb5M8mt_L4lc7NHbDGmQ9xCzTQ"
CHANNEL_ID = 1495136829228322928  # remplace par l'ID de ton salon

server = JavaServer.lookup("confdesenclumes.ddns.net:25565")

intents = discord.Intents.default()
client = discord.Client(intents=intents)

last = None

def monitor():
    global last
    while True:
        try:
            status = server.status()
            current = status.players.online

            if last is not None and current != last:
                channel = client.get_channel(CHANNEL_ID)
                if channel:
                    client.loop.create_task(
                        channel.send(f"🔔 Minecraft : {last} → {current}")
                    )

            last = current

        except Exception as e:
            print("Erreur :", e)

        time.sleep(30)

@client.event
async def on_ready():
    print("Bot connecté")
    threading.Thread(target=monitor).start()

client.run(TOKEN)