import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    API_ID = int(os.environ.get("API_ID", "39193426"))
    API_HASH = os.environ.get("API_HASH", "dec352035203bc35933ca952e19e5b1d")
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "8552560424:AAFJpVqHLb_AyYYkK6WOhrywCenqJjGrP3E")
    
    _owner_raw = os.environ.get("OWNER_ID", "7010804219").replace(",", " ")
    OWNER_ID = [int(x) for x in _owner_raw.split() if x.strip().isdigit()]
    
    MONGO_URI = os.environ.get("MONGO_URI", "mongodb+srv://a:a@loude.0uy8em5.mongodb.net/?appName=LOUDE")
    BIN_CHANNEL = int(os.environ.get("BIN_CHANNEL", "-1003897251767"))
    FORCE_SUB_CHANNEL = os.environ.get("FORCE_SUB_CHANNEL", "kamai4youpayment")

    PORT = int(os.environ.get("PORT", "8080"))
    BIND_ADRESS = os.environ.get("BIND_ADRESS", "0.0.0.0")
    
    # Strictly using your Heroku App URL
    FQDN = os.environ.get("FQDN", "https://sherdonstreaming-9da5fd1809f7.herokuapp.com")
