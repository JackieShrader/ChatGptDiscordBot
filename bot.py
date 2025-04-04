import discord
from openai import OpenAI
import os
import aiohttp
import pdfplumber
from discord.ext import commands
from dotenv import load_dotenv

# Load API keys from .env file
load_dotenv()
client = OpenAI()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Initialize OpenAI API
OpenAI.api_key = OPENAI_API_KEY

# Set up Discord bot
intents = discord.Intents.all()
intents.messages = True
bot = commands.Bot(command_prefix="!", intents=intents)

# reaction to show user their message has been read by bot
confirm = '\N{THUMBS UP SIGN}'

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    await bot.process_commands(message)  # Ensure command processing

@bot.command(help="Responds with 'Pong!'")
async def ping(ctx):
    await ctx.send('Pong!')
    
@bot.command(help="Sends prompt to chatgpt4 and responds with answer")
async def ask(ctx, *, question: str):
    try:
        await ctx.message.add_reaction(confirm)
        reply = await sendGPTRequest(question, None, "gpt-4")
        await ctx.send(reply)
    except Exception as e:
        print(f"Error occurred: {e}")  # Log the error
        await ctx.send("Error: An issue occurred while processing your question.")

#TODO: add ability to read more file types
@bot.command(help="Summarizes content of the attached pdf file")
async def sumcontent(ctx):
    try:
        if ctx.message.attachments:
            await ctx.message.add_reaction(confirm)
            text = await readPDF(ctx)
            if text:
                # check which model to use based on text size
                model = whichModel(text)
                summary = await sendGPTRequest("Summarize the following text concisely:", text, model)

                await ctx.send(f"📄 **PDF Summary using {model}:**\n```{summary}```")

    except Exception as e:
        print(f"Error occurred: {e}")  # Log the error
        await ctx.send("Error: An issue occurred while processing your question.")


#TODO: add ability to read more file types
@bot.command(help="Answers questions about the attached pdf file")
async def askaboutcontent(ctx, *, question: str):
    try:
        if ctx.message.attachments:
            await ctx.message.add_reaction(confirm)
            text = await readPDF(ctx)
            if text:
                # check which model to use based on text size
                model = whichModel(text)
                summary = await sendGPTRequest(question, text, model)

                await ctx.send(f"📄 **Response using {model}:**\n```{summary}```")

    except Exception as e:
        print(f"Error occurred: {e}")  # Log the error
        await ctx.send("Error: An issue occurred while processing your question.")


async def readPDF(ctx):
    if ctx.message.attachments:
        await ctx.message.add_reaction(confirm)
        attachment = ctx.message.attachments[0]  # Get the first attached file
        if attachment.filename.endswith(".pdf"):  # Ensure it's a PDF
            async with aiohttp.ClientSession() as session:
                async with session.get(attachment.url) as resp:
                    if resp.status == 200:
                        file_path = f"./{attachment.filename}"
                        with open(file_path, "wb") as f:
                            f.write(await resp.read())

                        # Extract text from PDF
                        with pdfplumber.open(file_path) as pdf:
                            text = "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())

                        os.remove(file_path)  # Clean up the file

                        if not text:
                            await ctx.send("⚠️ No readable text found in the PDF!")
                            return
                        
                        #return the text of the file
                        return text
        else:
            await ctx.send("⚠️ Please upload a `.pdf` file.")
    else:
        await ctx.send("⚠️ No file attached!")

async def sendGPTRequest(question, text, model):
    try:
        # check if we have text to send as well or just a question
        if text is None:
            messages=[
                {"role": "system", "content": question},
            ]
        else:
            messages=[
                {"role": "system", "content": question},
                {"role": "user", "content": text}
            ]
                        
        response = client.chat.completions.create(
            model=model,
            messages=messages
        )
        response = response.choices[0].message.content
        return response

    except Exception as e:
        print(f"Error occurred: {e}")  # Log the error
        return("Error: An issue occurred while processing your question.")

def whichModel(text):
    model = "gpt-4"
    wordCount = text.split()

    if(len(wordCount)>8000):
        model = "gpt-4-turbo"
    return model

# Run bot
bot.run(DISCORD_TOKEN)
