import discord
from discord.ext import commands
from discord import app_commands
import datetime
import random
import re

# =========================
# CONFIG
# =========================
TOKEN = 'MTUyNzI0NzQ3NzI0MDEwMjk1Mg.GA-1we.96j_eY9BkHpDQZ4J-pyNa5niEnpl6JB9vKZMWw' # ← RESET THIS IMMEDIATELY!
STAFF_ROLE_ID = 1527246278839500800
LOG_CHANNEL_ID = 1510034826860691509
TICKET_CATEGORY_ID = 1527042580771111040
WELCOME_CHANNEL_ID = 1527042580771111035
AUTO_ROLE_ID = 1527042580334907562
BOSS_ROLE_ID = 1527042580326514851 # ← Replace with the boss role ID

intents = discord.Intents.all()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# =========================
# WEAPON DATABASE
# =========================
wapen_database = {
    "pistol": {"naam": "Pistol", "voorraad": 15},
    "assaultrifle": {"naam": "Assault Rifle", "voorraad": 8},
    "shotgun": {"naam": "Shotgun", "voorraad": 5},
    # Add more here
}
embed_bericht_id = None
embed_kanaal_id = None
BAD_WORDS = ["kanker", "kkr", "tyfus", "hoer", "aids", "fuck you"]
link_pattern = re.compile(r"(https?://|www\.|discord\.gg/|discordapp\.com/invite/)")

# =========================
# HELPERS
# =========================
def bepaal_status(voorraad):
    if voorraad == 0: return "❌ Uitverkocht"
    elif voorraad <= 5: return "⚠️ Beperkt"
    elif voorraad <= 10: return "⚠️ Laag"
    return "✅ In Voorraad"

def maak_wapen_embed():
    embed = discord.Embed(
        title="⚙️ [LEGACY RP] Wapenvoorraad Systeem",
        description="📋 **Officiële Wapenlijst**\n\n",
        color=discord.Color.purple()
    )
  
    tabel = "```\n| Wapen (Code) | Naam | Voorraad | Status |\n"
    tabel += "|------------------|---------------------|----------|----------------|\n"
    for code, info in wapen_database.items():
        status = bepaal_status(info['voorraad'])
        tabel += f"| {code:<16} | {info['naam']:<19} | {info['voorraad']:<8} | {status:<14} |\n"
    tabel += "```"
    embed.description += tabel
  
    embed.add_field(name="🛠️ Beheerders Commando's", value="`/setwapen <code> <aantal>`\n`/addstock <code> <aantal>`", inline=False)
    embed.set_footer(text="Gebruik exacte code uit de tabel!")
    return embed

async def update_embed_bericht(interaction: discord.Interaction = None):
    global embed_bericht_id, embed_kanaal_id
    nieuw_embed = maak_wapen_embed()
  
    kanaal_id = embed_kanaal_id or (interaction.channel_id if interaction else None)
    if not kanaal_id: return
    kanaal = client.get_channel(kanaal_id)
    if not kanaal: return
    if embed_bericht_id:
        try:
            msg = await kanaal.fetch_message(embed_bericht_id)
            await msg.edit(embed=nieuw_embed)
            return
        except:
            pass
    msg = await kanaal.send(embed=nieuw_embed)
    embed_bericht_id = msg.id
    embed_kanaal_id = kanaal.id

# =========================
# VIEWS
# =========================
class SneakPeekView(discord.ui.View):
    def __init__(self, embed, log_channel, author):
        super().__init__(timeout=60)
        self.embed = embed
        self.log_channel = log_channel
        self.author = author
    @discord.ui.button(label="✅ Plaatsen", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        final = self.embed.copy()
        if final.title.startswith(": "):
            final.title = final.title.replace("👀 ganghuis: ", "📢 ganghuis: ")
      
        await interaction.channel.send(embed=final)
        if self.log_channel:
            await self.log_channel.send(f"📢 ganghuis geplaatst door {self.author.mention}", embed=final)
        await interaction.response.edit_message(content="✅ ganghuis geplaatst!", view=None)
    @discord.ui.button(label="❌ Annuleren", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="❌ Geannuleerd", view=None)

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="📩 Maak Ticket", style=discord.ButtonStyle.blurple, custom_id="create_ticket")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        member = interaction.user
        for ch in guild.channels:
            if ch.name.startswith("ticket-") and str(member.id) in (getattr(ch, 'topic', '') or ""):
                return await interaction.response.send_message("Je hebt al een open ticket!", ephemeral=True)
        category = discord.utils.get(guild.categories, id=TICKET_CATEGORY_ID)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            member: discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True),
        }
        if staff_role := guild.get_role(STAFF_ROLE_ID):
            overwrites[staff_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
        ticket = await guild.create_text_channel(name=f"ticket-{member.name}", category=category, topic=f"Ticket van {member} ({member.id})", overwrites=overwrites)
        await interaction.response.send_message(f"✅ Ticket aangemaakt → {ticket.mention}", ephemeral=True)
        await ticket.send(embed=discord.Embed(title="🎟️ Nieuw Support Ticket", description=f"Hallo {member.mention}!\n\nEen stafflid komt eraan.", color=discord.Color.blurple()), view=CloseView())

class CloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="🔒 Sluit Ticket", style=discord.ButtonStyle.red)
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        transcript = [f"{msg.created_at.strftime('%H:%M')} | {msg.author}: {msg.content}" async for msg in interaction.channel.history(limit=200)]
        if log := interaction.guild.get_channel(LOG_CHANNEL_ID):
            await log.send(f"**Ticket gesloten:** {interaction.channel.name}\n**Door:** {interaction.user.mention}",
                           file=discord.File(fp=discord.utils.BytesIO("\n".join(reversed(transcript)).encode()), filename=f"{interaction.channel.name}-transcript.txt"))
        await interaction.channel.delete()

# =========================
# EVENTS
# =========================
@client.event
async def on_ready():
    await tree.sync()
    print(f"✅ Bot online als {client.user}")

@client.event
async def on_member_join(member):
    # Auto role addition
    if role := member.guild.get_role(AUTO_ROLE_ID):
        try:
            await member.add_roles(role)
            print(f"Auto-role assigned to {member}")
        except Exception as e:
            print(f"Failed to assign auto-role: {e}")
   
    if ch := client.get_channel(WELCOME_CHANNEL_ID):
        embed = discord.Embed(title=f"👋 Welkom bij {member.guild.name}!", color=discord.Color.from_rgb(47, 49, 54))
        embed.description = f"Hallo {member.mention}!\nWe zijn nu **{member.guild.member_count}** members!"
        embed.set_thumbnail(url=member.display_avatar.url)
        await ch.send(f"Welkom {member.mention}!", embed=embed)

@client.event
async def on_message(message: discord.Message):
    if message.author.bot: return
    content = message.content.lower()
    
    # Boss role tag warning
    if message.role_mentions and any(role.id == BOSS_ROLE_ID for role in message.role_mentions):
        try:
            warning = f"⚠️ **Waarschuwing:** {message.author.mention}, tagging the boss role is not allowed without permission!"
            await message.channel.send(warning, delete_after=10)
            if log := message.guild.get_channel(LOG_CHANNEL_ID):
                await log.send(f"⚠️ Boss role tag detected by {message.author.mention} in {message.channel.mention}")
        except:
            pass
    
    if link_pattern.search(content) or any(word in content for word in BAD_WORDS):
        try:
            await message.delete()
            await message.channel.send(f"🚫 {message.author.mention} dit is niet toegestaan.", delete_after=5)
        except: pass

# =========================
# COMMANDS
# =========================
@tree.command(name="ping", description="Ping de bot")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"Pong! 🏓 {round(client.latency * 1000)}ms")

@tree.command(name="message", description="Stuur bericht/embed naar kanaal")
@app_commands.choices(stijl=[app_commands.Choice(name="Normaal", value="normal"), app_commands.Choice(name="Embed", value="embed")])
async def message_cmd(interaction: discord.Interaction, kanaal: discord.TextChannel, bericht: str, stijl: app_commands.Choice[str]):
    if not any(r.id == STAFF_ROLE_ID for r in interaction.user.roles):
        return await interaction.response.send_message("❌ Geen permissie.", ephemeral=True)
  
    try:
        if stijl.value == "embed":
            embed = discord.Embed(description=bericht, color=discord.Color.dark_grey(), timestamp=datetime.datetime.now())
            if interaction.guild.icon:
                embed.set_author(name=interaction.guild.name, icon_url=interaction.guild.icon.url)
            embed.set_footer(text=f"Verstuurd door {interaction.user}")
            await kanaal.send(embed=embed)
        else:
            await kanaal.send(bericht)
        await interaction.response.send_message(f"✅ Bericht verstuurd naar {kanaal.mention}", ephemeral=True)
    except:
        await interaction.response.send_message("❌ Geen rechten om in dat kanaal te sturen.", ephemeral=True)

@tree.command(name="sneakpeaks", description="Maak sneak peek met ganghuis")
async def sneakpeaks(interaction: discord.Interaction, titel: str, beschrijving: str, afbeelding: discord.Attachment):
    if not any(r.id == STAFF_ROLE_ID for r in interaction.user.roles):
        return await interaction.response.send_message("❌ Geen permissie.", ephemeral=True)
    if not afbeelding.content_type or not afbeelding.content_type.startswith("image/"):
        return await interaction.response.send_message("❌ Alleen afbeeldingen toegestaan.", ephemeral=True)
    embed = discord.Embed(title=f": {titel}", description=beschrijving, color=discord.Color.orange())
    embed.set_image(url=afbeelding.url)
    embed.set_footer(text=f" door {interaction.user}")
    view = SneakPeekView(embed, interaction.guild.get_channel(LOG_CHANNEL_ID), interaction.user)
    await interaction.response.send_message(":", embed=embed, view=view, ephemeral=True)

@tree.command(name="ticketpanel", description="Plaats ticket knop")
@app_commands.default_permissions(administrator=True)
async def ticketpanel(interaction: discord.Interaction):
    embed = discord.Embed(title="Support Tickets", description="Klik hieronder om een ticket aan te maken.", color=discord.Color.blurple())
    await interaction.channel.send(embed=embed, view=TicketView())
    await interaction.response.send_message("✅ Ticket paneel geplaatst!", ephemeral=True)

@tree.command(name="setwapen", description="Zet voorraad wapen")
@app_commands.default_permissions(administrator=True)
async def setwapen(interaction: discord.Interaction, code: str, hoeveelheid: int):
    code = code.lower()
    if code not in wapen_database:
        return await interaction.response.send_message("❌ Onbekend wapen!", ephemeral=True)
    wapen_database[code]["voorraad"] = max(0, hoeveelheid)
    await update_embed_bericht(interaction)
    await interaction.response.send_message(f"✅ {code} voorraad gezet op **{hoeveelheid}**", ephemeral=True)

@tree.command(name="addstock", description="Voeg voorraad toe")
@app_commands.default_permissions(administrator=True)
async def addstock(interaction: discord.Interaction, code: str, hoeveelheid: int):
    code = code.lower()
    if code not in wapen_database:
        return await interaction.response.send_message("❌ Onbekend wapen!", ephemeral=True)
    wapen_database[code]["voorraad"] = max(0, wapen_database[code]["voorraad"] + hoeveelheid)
    await update_embed_bericht(interaction)
    await interaction.response.send_message(f"✅ +{hoeveelheid} aan {code} (Nieuw: {wapen_database[code]['voorraad']})", ephemeral=True)

# =========================
# RUN
# =========================
client.run(TOKEN)
