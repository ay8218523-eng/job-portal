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
    today = datetime.date.today()
    today_str = today.isoformat()
    fifteen_days_ago = (today - datetime.timedelta(days=15)).isoformat()

    try:
        supabase.table("jobs").update({"status": "Expired"}).lt("last_date", today_str).eq("status", "Active").execute()
        supabase.table("jobs").delete().lt("last_date", fifteen_days_ago).execute()
        print("Lifecycle cleanup completed.")
    except Exception as e:
        print(f"Lifecycle note: {e}")

def get_direct_form_url(title, raw_link):
    t = title.lower()
    
    # 1. Sarkari Recruitment Portals (Direct Apply / Registration)
    if "ssc" in t:
        return "https://ssc.gov.in/login"
    elif "railway" in t or "rrb" in t or "ntpc" in t or "rrc" in t:
        return "https://www.rrbapply.gov.in/#/auth/home"
    elif "upsssc" in t:
        return "http://upsssc.gov.in/AllNotifications.aspx"
    elif "up police" in t or "uppbpb" in t:
        return "http://uppbpb.gov.in/"
    elif "ibps" in t:
        return "https://ibpsonline.ibps.in/"
    elif "sbi" in t:
        return "https://bank.sbi/web/careers/current-openings"
    elif "army" in t or "agniveer" in t:
        return "https://joinindianarmy.nic.in/Authentication.aspx"
    elif "navy" in t:
        return "https://www.joinindiannavy.gov.in/en/account/login"
    elif "airforce" in t or "afcat" in t:
        return "https://afcat.cdac.in/afcatreg/candidate/login"
    elif "upsc" in t:
        return "https://upsconline.nic.in/upsc/OTRP/"
    elif "bpsc" in t:
        return "https://onlinebpsc.bihar.gov.in/"
    elif "bssc" in t:
        return "https://bssc.bihar.gov.in/"
        
    # 2. Top Private & MNC Portals (Direct Career Form)
    elif "tcs" in t:
        return "https://nextstep.tcs.com/campus/"
    elif "infosys" in t:
        return "https://career.infosys.com/"
    elif "wipro" in t:
        return "https://careers.wipro.com/careers-home/"
    elif "amazon" in t:
        return "https://amazon.jobs/en/search?base_query=India"
    elif "hdfc" in t:
        return "https://www.hdfcbank.com/personal/about-us/careers"
    elif "axis" in t:
        return "https://www.axisbank.com/careers/job-openings"
    elif "flipkart" in t:
        return "https://www.flipkartcareers.com/"
    elif "reliance" in t or "jio" in t:
        return "https://relianceretail.com/careers.html"
    elif "cognizant" in t:
        return "https://careers.cognizant.com/global/en"
    elif "tech mahindra" in t:
        return "https://careers.techmahindra.com/"

    return raw_link

def fetch_jobs():
    feeds_config = [
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
        {
            "category": "private",
            "dept": "Corporate Operations",
            "url": "https://jobstron.com/feed/"
        },
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
            for entry in parsed.entries[:25]:
                raw_title = entry.get("title", "").strip()
                link = entry.get("link", "").strip()

                if not raw_title or not link:
                    continue

                title = raw_title.rsplit(" - ", 1)[0].strip() if " - " in raw_title else raw_title
                direct_url = get_direct_form_url(title, link)

                try:
                    existing = supabase.table("jobs").select("id").eq("title", title).execute()
                    if not existing.data:
                        payload = {
                            "title": title,
                            "company_dept": feed["dept"],
                            "apply_link": direct_url,
                            "last_date": default_expiry,
                            "status": "Active",
                            "category": feed["category"],
                            "fee": "Gen / OBC: ₹100/- | SC / ST / PH: ₹0/- (नियम अनुसार)",
                            "age_limit": "18 वर्ष से 28 वर्ष (पदानुसार आयु में छूट लागू)",
                            "eligibility": "10वीं / 12वीं / आईटीआई / स्नातक (Graduate) पास",
                            "total_posts": "विज्ञप्ति देखें (Official Notification)"
                        }
                        supabase.table("jobs").insert(payload).execute()
                        print(f"[{feed['category'].upper()}] Added: {title}")
                        jobs_added += 1
                except Exception as insert_err:
                    print(f"Insert error: {insert_err}")
        except Exception as feed_err:
            print(f"Feed error: {feed_err}")

    print(f"Total new direct jobs synced: {jobs_added}")

if __name__ == "__main__":
    manage_lifecycle()
    fetch_jobs()
            
