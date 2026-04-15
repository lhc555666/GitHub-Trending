import httpx
import asyncio
import json
import os
from datetime import datetime, timedelta

async def fetch_data():
    print(f"🚀 开始抓取: {datetime.now()}")
    last_week = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    # ⚡ 进阶 1：读取历史“记忆”
    old_data = {}
    if os.path.exists('data.json'):
        try:
            with open('data.json', 'r', encoding='utf-8') as f:
                old_data = json.load(f)
        except Exception as e:
            print(f"读取旧数据失败，将重新开始: {e}")

    # 提取历史的折线图数据
    star_labels = old_data.get("charts", {}).get("starGrowth", {}).get("labels", [])
    star_values = old_data.get("charts", {}).get("starGrowth", {}).get("data", [])
    
    # 清洗掉前端 Vue 里面写的那些默认占位符（比如 'Mon' 或 0）
    if "Mon" in star_labels or star_values == [0, 0, 0, 0, 0]:
        star_labels, star_values = [], []

    # 准备今天的全新基础数据框架
    new_data = {
        "lastUpdate": datetime.now().strftime("%Y/%m/%d %H:%M:%S"),
        "charts": {"languageDistribution": {}, "starGrowth": {}},
        "projects": {}
    }

    async with httpx.AsyncClient(verify=False) as client:
        for cat_name, lang_query in {"All": "", "Python": "language:python", "JavaScript": "language:javascript", "C++": "language:cpp"}.items():
            q = f"created:>{last_week}"
            if lang_query: q += f" {lang_query}"
            url = f"https://api.github.com/search/repositories?q={q}&sort=stars&order=desc"
            
            try:
                res = await client.get(url, headers=headers, timeout=15.0)
                if res.status_code == 200:
                    items = res.json().get("items", [])
                    project_list = []
                    for index, item in enumerate(items[:10], 1):
                        lang = item.get('language') or 'Unknown'
                        p = {
                            "rank": index, "name": item.get('full_name'),
                            "description": item.get('description') or '暂无描述',
                            "language": {"name": lang, "color": "text-gray-500"},
                            "stats": {"todayStars": "-", "totalStars": item.get('stargazers_count'), "forks": item.get('forks_count')},
                            "contributors": [item.get('owner', {}).get('avatar_url')],
                            "tags": [f"#{lang}".replace("#Unknown", "#Trending")]
                        }
                        project_list.append(p)
                        if cat_name == "All" and lang != "Unknown":
                            new_data["charts"]["languageDistribution"][lang] = new_data["charts"]["languageDistribution"].get(lang, 0) + 1
                    
                    new_data["projects"][cat_name] = project_list
                await asyncio.sleep(2) # 礼貌的爬虫
            except Exception as e:
                print(f"❌ 抓取 {cat_name} 异常: {e}")

    # ⚡ 进阶 2：计算今天的核心指标（比如：All 分类下 Top 10 的总 Star 均值）
    all_projects = new_data["projects"].get("All", [])
    if all_projects:
        today_avg_stars = int(sum(p['stats']['totalStars'] for p in all_projects) / len(all_projects))
    else:
        today_avg_stars = 0

    # ⚡ 进阶 3：追加折线图数据
    today_str = datetime.now().strftime("%m-%d") # 例如 "04-15"
    
    # 防止你今天手动点了很多次 Actions，导致同一天的数据重复追加
    if len(star_labels) > 0 and star_labels[-1] == today_str:
        star_values[-1] = today_avg_stars # 如果今天是同一天，就更新它
    else:
        star_labels.append(today_str)     # 如果是新的一天，就追加它
        star_values.append(today_avg_stars)

    # 保持折线图美观，只保留最近 7 天的“滑动窗口”
    new_data["charts"]["starGrowth"] = {
        "labels": star_labels[-7:],
        "data": star_values[-7:]
    }

    # 写入文件
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(new_data, f, ensure_ascii=False, indent=2)
    print("✅ 拥有记忆的数据已成功写入 data.json")

if __name__ == "__main__":
    asyncio.run(fetch_data())