import discord
from discord.ext import commands
import json
import os

TOKEN = os.getenv("TOKEN")  # Bot token comes from Railway/hosting env variables
DATA_FILE = "rosters.json"

intents = discord.Intents.default()
intents.members = True
intents.guilds = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Load saved roster data
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        rosters = json.load(f)
else:
    rosters = {}  # {guild_id: [{channel_id, message_id, role_ids: []}]}

async def build_roster_embed(guild: discord.Guild, role_ids: list[int]):
    embed = discord.Embed(title="Role Roster", color=discord.Color.blue())
    for rid in role_ids:
        role = guild.get_role(rid)
        if role:
            members = [m.mention for m in role.members]
            member_list = "\n".join(members) if members else "*No members*"
            embed.add_field(name=role.name, value=member_list, inline=False)
    return embed

async def update_rosters(guild: discord.Guild):
    if str(guild.id) not in rosters:
        return
    for entry in rosters[str(guild.id)]:
        channel = guild.get_channel(entry["channel_id"])
        try:
            msg = await channel.fetch_message(entry["message_id"])
            embed = await build_roster_embed(guild, entry["role_ids"])
            await msg.edit(embed=embed)
        except Exception as e:
            print(f"Error updating roster: {e}")

def save_rosters():
    with open(DATA_FILE, "w") as f:
        json.dump(rosters, f, indent=4)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Slash commands synced: {len(synced)}")
    except Exception as e:
        print(f"Error syncing commands: {e}")

@bot.tree.command(name="role", description="Create a roster embed for one role")
async def role_command(interaction: discord.Interaction, role: discord.Role):
    embed = await build_roster_embed(interaction.guild, [role.id])
    msg = await interaction.channel.send(embed=embed)

    guild_id = str(interaction.guild.id)
    if guild_id not in rosters:
        rosters[guild_id] = []
    rosters[guild_id].append({
        "channel_id": interaction.channel.id,
        "message_id": msg.id,
        "role_ids": [role.id]
    })
    save_rosters()
    await interaction.response.send_message(f"Roster created for {role.mention}", ephemeral=True)

@bot.tree.command(name="rolelist", description="Create a roster embed for multiple roles")
async def rolelist_command(interaction: discord.Interaction, *roles: discord.Role):
    if not roles:
        await interaction.response.send_message("You must mention at least one role.", ephemeral=True)
        return
    role_ids = [r.id for r in roles]
    embed = await build_roster_embed(interaction.guild, role_ids)
    msg = await interaction.channel.send(embed=embed)

    guild_id = str(interaction.guild.id)
    if guild_id not in rosters:
        rosters[guild_id] = []
    rosters[guild_id].append({
        "channel_id": interaction.channel.id,
        "message_id": msg.id,
        "role_ids": role_ids
    })
    save_rosters()
    await interaction.response.send_message("Multi-role roster created!", ephemeral=True)

@bot.event
async def on_member_update(before, after):
    await update_rosters(after.guild)

@bot.event
async def on_member_remove(member):
    await update_rosters(member.guild)

bot.run(TOKEN)
