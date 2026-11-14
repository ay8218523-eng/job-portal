import os
import re
import datetime
import feedparser
from bs4 import BeautifulSoup
from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: SUPABASE_URL or SUPABASE_KEY missing!")
    exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def parse_details(title, summary_html, published_str, category):
    soup = BeautifulSoup(summary_html or "", "html.parser")
    text = f"{title} {soup.get_text(' ', strip=True)}"
    t_low = title.lower()

    # 1. असली अंतिम तिथि निकालें, न मिले तो पब्लिश डेट से +25 दिन की संभावित अंतिम तिथि सेट करें
    date_match = re.search(r'(\d{1,2}[\s/\-](?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s/\-]\d{2,4}|\d{1,2}[\-/]\d{1,2}[\-/]\d{2,4})', text, re.IGNORECASE)
    if date_match:
        last_date = date_match.group(1)
    else:
        future_date = (datetime.date.today() + datetime.timedelta(days=25)).strftime("%d/%m/%Y")
        last_date = future_date

    # 2. कुल पद
    post_match = re.search(r'(\d{2,6})\s*(?:posts|vacancies|vacancy|पद|भर्ती)', text, re.IGNORECASE)
    total_posts = f"{post_match.group(1)} Post" if post_match else "Various Post (विज्ञप्ति देखें)"

    # 3. फीस और उम्र (Sarkari Result स्टाइल)
    if category in ["private", "fresher"]:
        fee = "General / OBC / SC / ST : ₹0/- (No Application Fee)"
        age_limit = "Minimum Age : 18 Years | Maximum Age : As per Company Rules"
        eligibility = "10+2 (Intermediate) / Any Graduate / Diploma"
    else:
        if any(k in t_low for k in ["bank", "ibps", "sbi", "rbi"]):
            fee = "General / OBC / EWS : ₹850/- | SC / ST / PH : ₹175/-"
        elif "upsssc" in t_low:
            fee = "All Category (Gen / OBC / SC / ST) : ₹25/-"
        elif "upsc" in t_low:
            fee = "General / OBC : ₹100/- | SC / ST / Female : ₹0/-"
        else:
            fee = "General / OBC / EWS : ₹100/- | SC / ST / Female : ₹0/-"

        age_limit = "Minimum Age : 18 Years | Maximum Age : 27-30 Years (Relaxation Extra)"
        if any(k in t_low for k in ["10th", "mts", "gd", "constable"]):
            eligibility = "Class 10th (High School) Exam Passed from Any Recognized Board."
        elif any(k in t_low for k in ["12th", "chsl", "inter"]):
            eligibility = "Class 12th (Intermediate) Exam Passed from Any Recognized Board."
        else:
            eligibility = "Bachelor Degree / 12th / Diploma (Read Notification for Post Wise Details)."

    return last_date, fee, age_limit, total_posts, eligibility

def fetch_jobs():
    # 12 अलग-अलग कैटेगरी फीड्स ताकि एक ही बार में 250-300+ जॉब्स आ जाएं
    feeds_config = [
        # Sarkari Jobs (4 फीड्स = ~100+ जॉब्स)
        {"category": "sarkari", "dept": "सरकारी भर्ती बोर्ड", "url": "https://news.google.com/rss/search?q=Sarkari+Result+Online+Form+2026+when:14d&hl=en-IN&gl=IN&ceid=IN:en"},
        {"category": "sarkari", "dept": "SSC / Railway / Bank भर्ती", "url": "https://news.google.com/rss/search?q=SSC+OR+Railway+OR+IBPS+Recruitment+Online+Form+2026+when:14d&hl=en-IN&gl=IN&ceid=IN:en"},
        {"category": "sarkari", "dept": "राज्य सरकार भर्ती (UP / Bihar / Raj)", "url": "https://news.google.com/rss/search?q=UPSSSC+OR+BPSC+OR+Police+Vacancy+Online+Form+2026+when:14d&hl=en-IN&gl=IN&ceid=IN:en"},
        {"category": "sarkari", "dept": "10th / 12th पास सरकारी नौकरी", "url": "https://news.google.com/rss/search?q=10th+Pass+OR+12th+Pass+Govt+Jobs+Online+Form+2026+when:14d&hl=en-IN&gl=IN&ceid=IN:en"},

        # Private & WFH Jobs (2 फीड्स = ~50+ जॉब्स)
        {"category": "private", "dept": "प्राइवेट एवं कॉर्पोरेट सेक्टर", "url": "https://news.google.com/rss/search?q=Private+Company+Hiring+Apply+Online+India+2026+when:14d&hl=en-IN&gl=IN&ceid=IN:en"},
        {"category": "private", "dept": "Work From Home & Bank Jobs", "url": "https://news.google.com/rss/search?q=Work+From+Home+Jobs+OR+HDFC+OR+ICICI+Hiring+2026+when:14d&hl=en-IN&gl=IN&ceid=IN:en"},

        # Freshers Jobs (2 फीड्स = ~50+ जॉब्स)
        {"category": "fresher", "dept": "फ्रेशर हायरिंग ड्राइव", "url": "https://news.google.com/rss/search?q=Freshers+Off+Campus+Drive+Apply+Online+2026+when:14d&hl=en-IN&gl=IN&ceid=IN:en"},
        {"category": "fresher", "dept": "IT & Graduate Walk-In", "url": "https://news.google.com/rss/search?q=TCS+OR+Infosys+OR+Wipro+Freshers+Hiring+2026+when:14d&hl=en-IN&gl=IN&ceid=IN:en"},

        # Results (2 फीड्स = ~40+ रिजल्ट)
        {"category": "result", "dept": "परीक्षा परिणाम बोर्ड", "url": "https://news.google.com/rss/search?q=Sarkari+Result+Declared+Download+2026+when:14d&hl=en-IN&gl=IN&ceid=IN:en"},
        {"category": "result", "dept": "Merit List & Cut Off", "url": "https://news.google.com/rss/search?q=Exam+Result+Merit+List+Score+Card+2026+when:14d&hl=en-IN&gl=IN&ceid=IN:en"},

        # Admit Card & Answer Key (2 फीड्स = ~40+ अपडेट)
        {"category": "admit", "dept": "प्रवेश पत्र पोर्टल", "url": "https://news.google.com/rss/search?q=Exam+Admit+Card+Hall+Ticket+Download+2026+when:14d&hl=en-IN&gl=IN&ceid=IN:en"},
        {"category": "answerkey", "dept": "आंसर की पोर्टल", "url": "https://news.google.com/rss/search?q=Official+Answer+Key+Download+2026+when:14d&hl=en-IN&gl=IN&ceid=IN:en"}
    ]

    jobs_added = 0
    for feed in feeds_config:
        try:
            parsed = feedparser.parse(feed["url"])
            for entry in parsed.entries[:30]:
                raw_title = entry.get("title", "").strip()
                link = entry.get("link", "").strip()
                summary = entry.get("summary", "")
                published = entry.get("published", "")
                if not raw_title or not link:
                    continue

                title = raw_title.rsplit(" - ", 1)[0].strip() if " - " in raw_title else raw_title

                existing = supabase.table("jobs").select("id").eq("title", title).execute()
                if not existing.data:
                    last_date, fee, age_limit, total_posts, eligibility = parse_details(title, summary, published, feed["category"])
                    payload = {
                        "title": title,
                        "company_dept": feed["dept"],
                        "apply_link": link,
                        "last_date": last_date,
                        "status": "Active",
                        "category": feed["category"],
                        "fee": fee,
                        "age_limit": age_limit,
                        "eligibility": eligibility,
                        "total_posts": total_posts
                    }
                    supabase.table("jobs").insert(payload).execute()
                    jobs_added += 1
        except Exception as e:
            print(f"Feed error: {e}")

    print(f"Total new jobs synced: {jobs_added}")

if __name__ == "__main__":
    fetch_jobs()
    
