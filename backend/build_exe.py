import PyInstaller.__main__
import os
import shutil

# Make sure we're in the backend directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Configuration
DIST_NAME = "QA-Chat-App"
ICON_PATH = "" # Add icon path here if you have one (.ico)

# Re-build frontend if needed (optional)
# subprocess.run(["npm", "run", "build"], cwd="../frontend")

# Copy the dist folder to the backend to make it easier for PyInstaller to find
temp_dist = os.path.join(os.getcwd(), "dist")
if os.path.exists(temp_dist):
    shutil.rmtree(temp_dist)
shutil.copytree("../frontend/dist", temp_dist)

# Define PyInstaller command
args = [
    'main.py', # Main entry point
    '--name=' + DIST_NAME,
    '--onefile', # Pack into a single .exe
    # '--windowed', # REMOVED: We want to see logs for debugging now
    '--add-data=dist;dist',
    '--add-data=.env;.',
    '--add-data=vector_store.faiss;vector_store.faiss',
    '--add-data=inata_index.txt;.',
    # Extended Hidden imports
    '--hidden-import=langchain_openai',
    '--hidden-import=langchain_google_genai',
    '--hidden-import=langchain_groq',
    '--hidden-import=psycopg2',
    '--hidden-import=flask_cors',
    '--hidden-import=dotenv',
    '--hidden-import=sqlalchemy',
    '--hidden-import=langchain_core',
    '--hidden-import=langchain_community',
    '--noconfirm' 
]

if ICON_PATH:
    args.append('--icon=' + ICON_PATH)

print("Starting build process...")
PyInstaller.__main__.run(args)
print("Build complete! Look in the 'dist' folder for your executable.")
