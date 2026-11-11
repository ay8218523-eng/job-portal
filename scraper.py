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
    """अंतिम तारीख बीतने पर एक्सपायर और 15 दिन बाद डेटाबेस से साफ़ करना"""
    today = datetime.date.today()
    today_str = today.isoformat()
    fifteen_days_ago = (today - datetime.timedelta(days=15)).isoformat()

    try:
        supabase.table("jobs").update({"status": "Expired"}).lt("last_date", today_str).eq("status", "Active").execute()
        supabase.table("jobs").delete().lt("last_date", fifteen_days_ago).execute()
        print("Lifecycle cleanup completed.")
    except Exception as e:
        print(f"Lifecycle note: {e}")

def get_official_apply_url(title, raw_link):
    """टाइटल के आधार पर सीधा आधिकारिक रिक्रूटमेंट पोर्टल लिंक पहचानना"""
    title_lower = title.lower()
    
    # 1. Staff Selection Commission
    if "ssc" in title_lower:
        return "https://ssc.gov.in/"
    # 2. Railway Recruitment Board
    elif "railway" in title_lower or "rrb" in title_lower or "rrc" in title_lower:
        return "https://rrbapply.gov.in/"
    # 3. UP Subordinate Service Selection
    elif "upsssc" in title_lower:
        return "http://upsssc.gov.in/"
    # 4. UP Police
    elif "up police" in title_lower or "uppbpb" in title_lower:
        return "http://uppbpb.gov.in/"
    # 5. Banking (IBPS, SBI)
    elif "ibps" in title_lower:
        return "https://ibps.in/"
    elif "sbi" in title_lower:
        return "https://bank.sbi/web/careers"
    # 6. Defense (Army, Navy, Airforce, NDA, CDS)
    elif "army" in title_lower or "agniveer" in title_lower:
        return "https://joinindianarmy.nic.in/"
    elif "navy" in title_lower:
        return "https://joinindiannavy.gov.in/"
    elif "airforce" in title_lower or "afcat" in title_lower:
        return "https://afcat.cdac.in/"
    elif "upsc" in title_lower:
        return "https://upsconline.nic.in/"
    elif "bpsc" in title_lower or "bihar" in title_lower:
        return "https://bpsc.bih.nic.in/"
    
    # अगर कोई विशेष पहचान न मिले तो फ़ीड का डायरेक्ट लिंक
    return raw_link

def fetch_jobs():
    """Sarkari, FreeJobAlert और Direct Feeds से डेटा लोड करना"""
    feeds_config = [
        # Sarkari Jobs Feeds
        {
            "category": "sarkari",
            "dept": "Govt Recruitment Board",
            "url": "https://www.freejobalert.com/feed"
        },
        {
            "category": "sarkari",
            "dept": "Central / State Govt",
            "url": "https://news.google.com/rss/search?q=latest+sarkari+naukri+recruitment+online+form&hl=hi&gl=IN&ceid=IN:hi"
        },
        # Private Corporate Jobs
        {
            "category": "private",
            "dept": "Corporate Operations",
            "url": "https://jobstron.com/feed/"
        },
        # Fresher Jobs (0-Exp)
        {
            "category": "fresher",
            "dept": "Fresher Hiring Drive",
            "url": "https://freshershunt.in/feed/"
        }
    ]

    today = datetime.date.today()
    default_expiry = (today + datetime.timedelta(days=30)).strftime("%d-%m-%Y")
    jobs_added = 0

    for feed in feeds_config:
        try:
            parsed = feedparser.parse(feed["url"])
            for entry in parsed.entries[:25]:  # हर फ़ीड से 25 नौकरियाँ
                raw_title = entry.get("title", "").strip()
                link = entry.get("link", "").strip()

                if not raw_title or not link:
                    continue

                # टाइटल को साफ़ करना
                title = raw_title.rsplit(" - ", 1)[0].strip() if " - " in raw_title else raw_title

                # डायरेक्ट आधिकारिक आवेदन लिंक खोजना
                final_apply_link = get_official_apply_url(title, link)

                try:
                    # डुप्लीकेट चेक
                    existing = supabase.table("jobs").select("id").eq("title", title).execute()
                    if not existing.data:
                        payload = {
                            "title": title,
                            "company_dept": feed["dept"],
                            "apply_link": final_apply_link,
                            "last_date": default_expiry,
                            "status": "Active",
                            "category": feed["category"],
                            "fee": "Gen / OBC / EWS: ₹100/- | SC / ST / PH: ₹0/- (नियम अनुसार)",
                            "age_limit": "18 वर्ष से 28 वर्ष (पदानुसार आयु में छूट लागू)",
                            "eligibility": "10वीं / 12वीं / आईटीआई / स्नातक (Graduate) पास उम्मीदवार",
                            "total_posts": "विज्ञप्ति देखें (See Official Notification)"
                        }
                        supabase.table("jobs").insert(payload).execute()
                        print(f"[{feed['category'].upper()}] Added: {title}")
                        jobs_added += 1
                except Exception as insert_err:
                    print(f"Insert error: {insert_err}")
        except Exception as feed_err:
            print(f"Feed error: {feed_err}")

    print(f"Total new jobs synced: {jobs_added}")

if __name__ == "__main__":
    manage_lifecycle()
    fetch_jobs()
    
