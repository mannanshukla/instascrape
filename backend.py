from fastapi import FastAPI, Form, Query
import subprocess
import re
import requests
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import Response

app = FastAPI()

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def extract_username(instagram_input: str) -> str:
    """Extract the username from an Instagram URL or return as is."""
    match = re.search(r"instagram\.com/([^/?]+)", instagram_input)
    return match.group(1) if match else instagram_input

def parse_toutatis_output(raw_output: str):
    """Parses Toutatis' colon-separated output into a dictionary, ensuring missing fields are handled."""
    parsed_data = {}

    for line in raw_output.split("\n"):
        if ":" in line:
            key, value = line.split(":", 1)
            parsed_data[key.strip()] = value.strip()

    # Use regex to extract Followers and Following separately
    if "Follower" in parsed_data:
        match = re.search(r"(\d+)\s*\|\s*Following\s*:\s*(\d+)", parsed_data["Follower"])
        if match:
            parsed_data["Follower"] = match.group(1)  # Extract Followers count
            parsed_data["Following"] = match.group(2)  # Extract Following count
        else:
            parsed_data["Following"] = None  # If Following isn't found, set it to None

    # Ensure all expected fields exist
    expected_fields = [
        "Informations about", "userID", "Full Name", "Verified", "Is buisness Account",
        "Is private Account", "Follower", "Following", "Number of posts", "External url",
        "IGTV posts", "Biography", "Public Email", "Public Phone", "Obfuscated email",
        "Obfuscated phone", "Profile Picture"
    ]

    for field in expected_fields:
        parsed_data.setdefault(field, None)  # Use None instead of "N/A"

    return parsed_data

@app.post("/run_toutatis/")
async def run_toutatis(instagram_input: str = Form(...), session_cookie: str = Form(...)):
    """Runs Toutatis and returns structured Instagram data."""
    username = extract_username(instagram_input)

    try:
        command = ["toutatis", "-u", username, "-s", session_cookie]
        result = subprocess.run(command, capture_output=True, text=True, timeout=10)

        output = result.stdout.strip()
        error = result.stderr.strip()

        if error:
            return {"error": error}

        parsed_data = parse_toutatis_output(output)
        return parsed_data

    except Exception as e:
        return {"error": str(e)}

@app.get("/proxy-image/")
async def proxy_image(url: str = Query(...)):
    """Proxies Instagram profile pictures to bypass CORS issues."""
    headers = {"User-Agent": "Mozilla/5.0"}
    img_response = requests.get(url, headers=headers)
    return Response(content=img_response.content, media_type="image/jpeg")

# Serve frontend
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

@app.get("/")
def home():
    return {"message": "InstaScrape is running!"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)  # Force correct port
