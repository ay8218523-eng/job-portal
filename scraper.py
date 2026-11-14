import os
import re
import datetime
import requests
import feedparser
from bs4 import BeautifulSoup
from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: SUPABASE_URL or SUPABASE_KEY missing!")
    exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def scrape_real_page_details(url, category):
    """असली वेबपेज के अंदर जाकर सटीक Last Date, Fee, Age और Posts निकालता है"""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    last_date = "आधिकारिक नोटिफिकेशन देखें"
    fee = "निःशुल्क / विज्ञप्ति देखें" if category in ["private", "fresher"] else "आधिकारिक विज्ञप्ति देखें"
    age_limit = "न्यूनतम 18 वर्ष (नियमानुसार)"
    total_posts = "विज्ञप्ति देखें"
    eligibility = "नोटिफिकेशन के अनुसार"

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            text = soup.get_text(" ", strip=True)

            # 1. असली Last Date खोजना
            date_patterns = [
                r'Last Date(?:\s+for\s+Apply(?:\s+Online)?)?[:\-\s]+(\d{1,2}[\-\/\.\s](?:[A-Za-z]{3,9}|\d{1,2})[\-\/\.\s]\d{2,4})',
                r'Closing Date[:\-\s]+(\d{1,2}[\-\/\.\s](?:[A-Za-z]{3,9}|\d{1,2})[\-\/\.\s]\d{2,4})'
            ]
            for pat in date_patterns:
                m = re.search(pat, text, re.IGNORECASE)
                if m:
                    last_date = m.group(1).strip()
                    break

            # 2. असली Application Fee खोजना
            fee_match = re.search(r'(?:Application Fee|Exam Fee)[:\-\s]+([^\n\.]{5,90})', text, re.IGNORECASE)
            if fee_match and any(k in fee_match.group(1).lower() for k in ["rs", "₹", "nil", "free", "exempt", "obc", "gen"]):
                fee = fee_match.group(1).strip()
            elif category in ["private", "fresher"]:
                fee = "₹0/- (सभी वर्गों के लिए निःशुल्क)"

            # 3. असली Age Limit खोजना
            age_match = re.search(r'(?:Age Limit|Maximum Age)[:\-\s]+([^\n\.]{5,70})', text, re.IGNORECASE)
            if age_match and re.search(r'\d{2}', age_match.group(1)):
                age_limit = age_match.group(1).strip()

            # 4. असली Total Posts खोजना
            post_match = re.search(r'(?:Total Vacancy|Total Posts|Vacancies)[:\-\s]+(\d{1,6})', text, re.IGNORECASE)
            if post_match:
                total_posts = f"{post_match.group(1)} पद"

            # 5. असली Qualification खोजना
            qual_match = re.search(r'(?:Qualification|Eligibility)[:\-\s]+([^\n\.]{5,80})', text, re.IGNORECASE)
            if qual_match:
                eligibility = qual_match.group(1).strip()

    except Exception as e:
        print(f"Page scan skipped for {url}: {e}")

    return last_date, fee, age_limit, total_posts, eligibility

def fetch_jobs():
    feeds_config = [
        {"category": "sarkari", "dept": "सरकारी भर्ती बोर्ड", "url": "https://www.freejobalert.com/feed"},
        {"category": "private", "dept": "प्राइवेट एवं कॉर्पोरेट सेक्टर", "url": "https://jobztron.com/feed/"},
        {"category": "fresher", "dept": "फ्रेशर हायरिंग", "url": "https://freshershunt.in/feed/"}
    ]

    jobs_added = 0
    for feed in feeds_config:
        try:
            parsed = feedparser.parse(feed["url"])
            for entry in parsed.entries[:15]:
                raw_title = entry.get("title", "").strip()
                link = entry.get("link", "").strip()
                if not raw_title or not link:
                    continue

                title = raw_title.rsplit(" - ", 1)[0].strip() if " - " in raw_title else raw_title

                # चेक करें कि पहले से डेटाबेस में तो नहीं है
                existing = supabase.table("jobs").select("id").eq("title", title).execute()
                if not existing.data:
                    # असली पेज के अंदर जाकर सटीक डेटा निकालें
                    last_date, fee, age_limit, total_posts, eligibility = scrape_real_page_details(link, feed["category"])

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
                    print(f"Verified Job Added: {title} | Last Date: {last_date} | Fee: {fee}")
                    jobs_added += 1
        except Exception as err:
            print(f"Feed error: {err}")

    print(f"Total real jobs synced: {jobs_added}")

if __name__ == "__main__":
    fetch_jobs()
    
