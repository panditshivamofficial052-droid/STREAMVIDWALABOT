import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    API_ID = int(os.environ.get("API_ID", "22135296"))
    API_HASH = os.environ.get("API_HASH", "b3051c4c2dfe4ef65f7146d172d3ddaf")
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "8758745301:AAGWSGg8biLrL03P5RXL0MAHcMGyeyWlSYk")
    
    _owner_raw = os.environ.get("OWNER_ID", "7893435873").replace(",", " ")
    OWNER_ID = [int(x) for x in _owner_raw.split() if x.strip().isdigit()]
    
    MONGO_URI = os.environ.get("MONGO_URI", "mongodb+srv://samplesamra:samplesamra@samplesamra.qtff1nr.mongodb.net/?appName=samplesamra")
    BIN_CHANNEL = int(os.environ.get("BIN_CHANNEL", "-1003897251767"))
    FORCE_SUB_CHANNEL = os.environ.get("FORCE_SUB_CHANNEL", "kamai4youpayment")

    PORT = int(os.environ.get("PORT", "8080"))
    BIND_ADRESS = os.environ.get("BIND_ADRESS", "0.0.0.0")
    
    # Strictly using your Heroku App URL
    FQDN = os.environ.get("FQDN", "https://herokuacountcreater-50091c02a64d.herokuapp.com")
