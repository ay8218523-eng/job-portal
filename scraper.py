import os
import datetime
import feedparser
from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def cleanup_expired_jobs():
    today = datetime.date.today().isoformat()
    try:
        supabase.table("jobs").update({"status": "Expired"}).lt("last_date", today).eq("status", "Active").execute()
        print("Expired jobs cleanup completed.")
    except Exception as e:
        print(f"Cleanup error: {e}")

def fetch_jobs():
    feeds = [
        "https://www.freejobalert.com/feed/",
    ]
    today = datetime.date.today()
    default_expiry = (today + datetime.timedelta(days=25)).isoformat()

    for url in feeds:
        parsed = feedparser.parse(url)
        for entry in parsed.entries:
            title = entry.get("title", "").strip()
            link = entry.get("link", "").strip()

            if not title or not link:
                continue

            existing = supabase.table("jobs").select("id").eq("apply_link", link).execute()
            if not existing.data:
                payload = {
                    "title": title,
                    "company_dept": "Central / State Govt",
                    "apply_link": link,
                    "last_date": default_expiry,
                    "status": "Active"
                }
                supabase.table("jobs").insert(payload).execute()
                print(f"New job added: {title}")

if __name__ == "__main__":
    cleanup_expired_jobs()
    fetch_jobs()
  
