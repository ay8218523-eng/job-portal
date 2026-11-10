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

def fetch_jobs():
    feeds = [
        "https://news.google.com/rss/search?q=sarkari+naukri+recruitment&hl=hi&gl=IN&ceid=IN:hi",
        "https://news.google.com/rss/search?q=latest+govt+jobs+india&hl=en-IN&gl=IN&ceid=IN:en"
    ]
    
    today = datetime.date.today()
    default_expiry = (today + datetime.timedelta(days=30)).isoformat()
    jobs_added = 0

    # 1. RSS Feeds se Jobs Lana
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

    # 2. Agar feed se kuch na mile toh Demo Jobs dalna taaki site khali na rahe
    if jobs_added == 0:
        demo_jobs = [
            {
                "title": "SSC CGL Recruitment 2026 - Apply Online",
                "company_dept": "Staff Selection Commission",
                "apply_link": "https://ssc.gov.in",
                "last_date": default_expiry,
                "status": "Active"
            },
            {
                "title": "Railway RRB NTPC Bharti 2026",
                "company_dept": "Railway Recruitment Board",
                "apply_link": "https://indianrailways.gov.in",
                "last_date": default_expiry,
                "status": "Active"
            },
            {
                "title": "UP Police Constable Vacancy 2026",
                "company_dept": "UPPRPB",
                "apply_link": "https://uppbpb.gov.in",
                "last_date": default_expiry,
                "status": "Active"
            }
        ]
        for job in demo_jobs:
            try:
                supabase.table("jobs").insert(job).execute()
                print(f"Demo Job added: {job['title']}")
            except Exception as e:
                print(f"Demo insert error: {e}")

if __name__ == "__main__":
    fetch_jobs()
    
