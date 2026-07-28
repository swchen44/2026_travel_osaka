#!/usr/bin/env python3
"""掃描 大阪素食餐廳地圖.html 的店家，偵測「疑似歇業/移轉」與「死圖」。
純 curl + 訊號比對，不用 LLM，只吐異常清單供後續人工/小 agent 確認。

用法：
  python3 maintenance_scan.py --region shikoku        # 只掃一個地區（建議：小批）
  python3 maintenance_scan.py --ids 456,457,458
  python3 maintenance_scan.py --all                    # 全掃（慢，已內建限速）
  python3 maintenance_scan.py --region kyushu --happycow  # 額外查 HappyCow 頁(會被限流，僅小批用)
  python3 maintenance_scan.py --region tokyo --photos-only # 只驗照片死連

偵測訊號：
  - Tabelog 店頁 <title> 含【閉店】/【移転】，或內文「掲載を保留」→ 疑似歇業/移轉
  - 官網/部落格 HTTP 404/410/000(DNS失效) → 網域或頁面已死
  - (--happycow) HappyCow 頁 "permanently closed"/"reported ... closed"
  - 照片死連：HappyCow 熱連非 200、或本地 images/NNN.jpg 不存在
輸出：印出異常摘要 + 寫入 maintenance_candidates.tsv（欄位: id  name  region  類型  訊號  url）
"""
import re, os, sys, subprocess, time, argparse

HTML = os.path.join(os.path.dirname(__file__), '大阪素食餐廳地圖.html')
OUT  = os.path.join(os.path.dirname(__file__), 'maintenance_candidates.tsv')
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36'

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('--region')
    p.add_argument('--ids')
    p.add_argument('--all', action='store_true')
    p.add_argument('--happycow', action='store_true', help='額外查 HappyCow 頁(易被限流,小批用)')
    p.add_argument('--photos-only', action='store_true')
    p.add_argument('--sleep', type=float, default=0.7)
    return p.parse_args()

def load():
    html = open(HTML, encoding='utf-8').read()
    js = re.findall(r'<script>(.*?)</script>', html, re.S)[-1]
    arr = re.search(r'const restaurants = \[(.*?)\n\];', js, re.S).group(1)
    pblock = re.search(r'const photos = \{(.*?)\n\};', js, re.S).group(1)
    photos = {int(k): v for k, v in re.findall(r"(\d+):\s*'([^']*)'", pblock)}
    starts = [(m.start(), int(m.group(1))) for m in re.finditer(r'\bid:(\d+),\s*rank:', arr)]
    vens = []
    for idx, (pos, rid) in enumerate(starts):
        end = starts[idx+1][0] if idx+1 < len(starts) else len(arr)
        b = arr[pos:end]
        def g(pat):
            m = re.search(pat, b, re.S); return m.group(1).strip() if m else ''
        nm = re.search(r"\bname:\s*(['\"])(.*?)\1", b, re.S)
        vens.append({
            'id': rid,
            'name': nm.group(2) if nm else '',
            'region': g(r"region:'([^']*)'") or 'osaka',
            'ghours': g(r"ghours:'([^']*)'"),
            'hcUrl': g(r"hcUrl:'([^']*)'"),
            'photo': photos.get(rid, ''),
        })
    return vens

def curl(url, head=False):
    """回傳 (http_code, body)。失敗回 ('000','')。"""
    cmd = ['curl', '-sL', '--max-time', '15', '-A', UA]
    if head:
        cmd += ['-o', '/dev/null', '-w', '%{http_code}', '-I', url]
    else:
        cmd += ['-w', '\n@@CODE@@%{http_code}', url]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=25).stdout
    except Exception:
        return '000', ''
    if head:
        return (out.strip() or '000'), ''
    if '\n@@CODE@@' in out:
        body, code = out.rsplit('\n@@CODE@@', 1)
        return code.strip(), body
    return '000', out

def check_page(url):
    """回傳 (類型, 訊號) 或 None。類型: closed/moved/dead/None"""
    code, body = curl(url)
    low = body.lower()
    if 'tabelog.com' in url:
        title = re.search(r'<title>(.*?)</title>', body, re.S)
        t = title.group(1) if title else ''
        if '【閉店】' in t or 'この店舗は閉店' in body or '閉店しました' in body:
            return 'closed', 'Tabelog 標【閉店】'
        if '【移転】' in t or '移転しました' in body:
            return 'moved', 'Tabelog 標【移転】'
        if '掲載を保留' in body or '情報の掲載を保留' in body:
            return 'closed', 'Tabelog 掲載保留(疑似歇業)'
        if code in ('404', '410'):
            return 'dead', f'Tabelog 頁 HTTP {code}'
        return None
    if 'happycow.net' in url:
        if re.search(r'permanently closed|reported[^<]{0,30}closed|this (restaurant|business|venue) is closed', low):
            return 'closed', 'HappyCow 標 closed'
        return None
    # 官網/部落格
    if code in ('000', '404', '410'):
        return 'dead', f'官網/頁 HTTP {code}(網域或頁面已死)'
    if 'このドメインは' in body or 'domain is for sale' in low or 'お名前.com' in body:
        return 'dead', '網域已失效/待售'
    return None

def check_photo(v):
    p = v['photo']
    if not p:
        return None
    if p.startswith('http'):
        if 'images.happycow.net' in p:
            code, _ = curl(p, head=True)
            if code != '200':
                return 'photo', f'HappyCow 熱連圖 HTTP {code}'
    else:
        local = os.path.join(os.path.dirname(__file__), p)
        if not os.path.exists(local) or os.path.getsize(local) == 0:
            return 'photo', f'本地圖不存在: {p}'
    return None

def main():
    a = parse_args()
    vens = load()
    if a.ids:
        want = set(int(x) for x in a.ids.split(','))
        vens = [v for v in vens if v['id'] in want]
    elif a.region:
        vens = [v for v in vens if v['region'] == a.region]
    elif not a.all:
        print('請指定 --region <名> 或 --ids 1,2 或 --all');  sys.exit(1)

    print(f'掃描 {len(vens)} 家 …（限速 {a.sleep}s/次）')
    rows = []
    for i, v in enumerate(vens, 1):
        flags = []
        # 照片死連
        ph = check_photo(v)
        if ph:
            flags.append(ph)
        if not a.photos_only:
            # 優先查 ghours(多為 Tabelog/官網)，再查 hcUrl；HappyCow 頁預設跳過(易被限流)
            urls = []
            for u in (v['ghours'], v['hcUrl']):
                if u and u not in urls:
                    urls.append(u)
            for u in urls:
                if 'happycow.net' in u and not a.happycow:
                    continue
                if 'instagram.com' in u or 'facebook.com' in u:
                    continue  # 社群頁無法可靠判斷歇業
                res = check_page(u)
                if res:
                    flags.append((res[0], f'{res[1]} → {u}'))
                    break
                time.sleep(a.sleep)
        if flags:
            for typ, sig in flags:
                rows.append((v['id'], v['name'], v['region'], typ, sig))
                print(f"  ⚠️ id{v['id']} [{v['region']}] {v['name'][:24]} → {typ}: {sig}")
        if i % 20 == 0:
            print(f'  …{i}/{len(vens)}')
        time.sleep(a.sleep)

    with open(OUT, 'w', encoding='utf-8') as f:
        f.write('id\tname\tregion\t類型\t訊號\n')
        for r in rows:
            f.write('\t'.join(str(x) for x in r) + '\n')
    print(f'\n完成：{len(rows)} 筆疑似異常 → {OUT}')
    if not rows:
        print('（全部正常，無異常）')
    else:
        print('※ 這只是「疑似」，請人工或小 agent 逐筆確認再決定下架/改資料。')

if __name__ == '__main__':
    main()
