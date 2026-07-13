#!/usr/bin/env python3
"""從 大阪素食餐廳地圖.html 匯出 vegan_kansai_places.csv（供 Google My Maps 匯入）。
店家資料有變動後，執行： python3 make_csv.py  就會重新產生 CSV。"""
import re, csv, os

HTML = os.path.join(os.path.dirname(__file__), '大阪素食餐廳地圖.html')
OUT  = os.path.join(os.path.dirname(__file__), 'vegan_kansai_places.csv')

html = open(HTML, encoding='utf-8').read()
js = re.findall(r'<script>(.*?)</script>', html, re.S)[-1]

pblock = re.search(r'const PRICES = \{(.*?)\n\};', js, re.S).group(1)
prices = {int(k): v for k, v in re.findall(r"(\d+)\s*:\s*'([^']*)'", pblock)}

CHECK_OVERRIDE = {32: '2026-07-12', 34: '2026-07-12'}  # 個別重新查證過的店家
def checked(i, region=''):
    if i in CHECK_OVERRIDE:
        return CHECK_OVERRIDE[i]
    if region == 'nara':
        return '2026-07-14'  # 奈良全區出發前重新核實
    if i >= 152:
        return '2026-07-14'  # 天保山/港區灣岸新批
    if i >= 90:
        return '2026-07-12'
    return '2026-06-28' if i <= 25 else '2026-06-29' if i <= 37 else '2026-06-30' if i <= 51 else '2026-07-03'

regionmap = {'': '大阪', 'osaka': '大阪', 'kyoto': '京都', 'nara': '奈良'}

arr = re.search(r'const restaurants = \[(.*?)\n\];', js, re.S).group(1)
starts = [(m.start(), int(m.group(1))) for m in re.finditer(r'\bid:(\d+),\s*rank:', arr)]
rows = []
for idx, (pos, rid) in enumerate(starts):
    end = starts[idx + 1][0] if idx + 1 < len(starts) else len(arr)
    b = arr[pos:end]
    def g(field):
        m = re.search(field, b, re.S); return m.group(1).strip() if m else ''
    nm = re.search(r'\bname:\s*([\'"])(.*?)\1', b, re.S)
    name = nm.group(2) if nm else ''
    region_raw = g(r"region:'([^']*)'") or 'osaka'
    region = regionmap.get(region_raw, '大阪')
    typ = g(r"\btype:\s*'([^']*)'")
    area = g(r"\barea:\s*'([^']*)'")
    address = g(r"\baddress:\s*'([^']*)'")
    lat = g(r"\blat:\s*([\d.]+)"); lng = g(r"\blng:\s*([\d.]+)")
    hours = g(r"\bhours:\s*'([^']*)'").replace('\\n', ' / ')
    g_st = g(r"\bgStars:\s*'([^']*)'")
    rows.append([rid, name, region, typ, area, address, lat, lng, hours, g_st,
                 prices.get(rid, ''),
                 f'https://www.google.com/maps/search/?api=1&query={lat},{lng}', checked(rid, region_raw)])

with open(OUT, 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f)
    w.writerow(['編號', '名稱', '地區', '類型', '地區/大樓', '地址', '緯度', '經度',
                '營業時間', '評分', '每人價位', 'GoogleMaps連結', '核實日期'])
    w.writerows(rows)

print(f'寫出 {len(rows)} 筆 → {OUT}')
missing = [r[0] for r in rows if not r[6] or not r[7]]
print('缺座標:', missing if missing else '無')
