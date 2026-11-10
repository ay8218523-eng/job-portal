import os
import datetime
import feedparser
from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: SUPABASE_URL or SUPABASE_KEY missing!")
    exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def manage_lifecycle():
    """तारीख खत्म होने पर Expired करना और 15 दिन बाद पूरी तरह डिलीट कर देना"""
    today = datetime.date.today()
    today_str = today.isoformat()
    fifteen_days_ago = (today - datetime.timedelta(days=15)).isoformat()

    try:
        # 1. जो डेट खत्म हो गई है, उसे Expired स्टेटस में बदलना
        supabase.table("jobs").update({"status": "Expired"}).lt("last_date", today_str).eq("status", "Active").execute()
        print("Status updated to Expired for ended dates.")

        # 2. जो नौकरी खत्म हुए 15 दिन से ज़्यादा हो गए, उसे हमेशा के लिए डिलीट करना
        supabase.table("jobs").delete().lt("last_date", fifteen_days_ago).execute()
        print("Jobs older than 15 days deleted completely.")
    except Exception as e:
        print(f"Lifecycle note: {e}")

def fetch_jobs():
    """इंटरनेट से नई नौकरियाँ लाना"""
    feeds = [
        "https://news.google.com/rss/search?q=sarkari+naukri+recruitment&hl=hi&gl=IN&ceid=IN:hi",
        "https://news.google.com/rss/search?q=latest+govt+jobs+india&hl=en-IN&gl=IN&ceid=IN:en"
    ]
    
    today = datetime.date.today()
    default_expiry = (today + datetime.timedelta(days=30)).isoformat()
    jobs_added = 0

    for url in feeds:
        try:
            parsed = feedparser.parse(url)
            for entry in parsed.entries[:10]:
                title = entry.get("title", "").strip()
                link = entry.get("link", "").strip()

                if not title or not link:
                    continue

                try:
                    existing = supabase.table("jobs").select("id").eq("apply_link", link).execute()
                    if not existing.data:
                        payload = {
                            "title": title,
                            "company_dept": "Govt / Private Dept",
                            "apply_link": link,
                            "last_date": default_expiry,
                            "status": "Active"
                        }
                        supabase.table("jobs").insert(payload).execute()
                        print(f"Job added: {title}")
                        jobs_added += 1
                except Exception as insert_err:
                    print(f"Insert error: {insert_err}")
        except Exception as feed_err:
            print(f"Feed error ({url}): {feed_err}")

if __name__ == "__main__":
    manage_lifecycle()
    fetch_jobs()
    
