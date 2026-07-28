# 在日本找素食店 → 做成互動地圖 SOP

> 給未來擴充/補查日本各地素食店用的完整流程。
> 主檔案：`大阪素食餐廳地圖.html`（單一 HTML + Leaflet，無 build，直接部署 GitHub Pages）。
> 檔名務必**保留原名**，不要改，否則會破壞 `index.html` 連結與 GitHub Pages 網址。
>
> **現況（2026-07-29）**：已擴為**全日本**，共 **460 家、12 個地區篩選**（`region` 值：`osaka/kyoto/nara/kobe/okinawa/tokyo/hokkaido/kyushu/chubu/hiroshima/tohoku/shikoku`）。id 已編到 462。新店續編最大 id。標題已是「全日本素食餐廳互動地圖」。
> **要再擴充新 macro-region**（例北陸單獨拉出、山陰…）看 §4.5；**要補既有地區的店**直接 append 同 region 即可。

---

## 0. 前提：我們吃什麼（判定的根本依據）

**蛋奶素（ovo-lacto）**：
- ✅ 可吃：蛋、奶製品、蔥、蒜、韭菜、洋蔥
- ❌ 不吃：肉、魚、海鮮、**柴魚高湯（かつおだし）**、肉高湯、魚露、鰹魚/小魚乾等海鮮萃取

> **最大陷阱＝柴魚だし（かつお出汁）**。日式定食、味噌湯、天つゆ、蕎麥麵湯、關東煮、茶碗蒸、燉飯 brodo 幾乎都藏柴魚或肉高湯。看到「和風だし」「一番だし」要當作有柴魚，除非店家能改「昆布／椎茸／精進だし」。
> 因此每家店都要判「這家能不能吃、要不要現場溝通」，這就是卡片上 **✅ 確定素 / ❓ 需詢問** 標籤的來源。

---

## 1. 整體流程總覽

```
蒐集店家(多來源交叉查證) → 抓照片 → 寫進 HTML 三個資料表 → 產生 CSV
   → 本機驗證(語法/瀏覽器/計數) → git add(含圖!) → commit → push → GitHub Pages
```

每一步都有對應的「檢查完成」條件，見 §6 清單。

---

## 2. Step 1 — 蒐集店家資料

### 2.1 來源（依可信度排序，務必交叉查證）
1. **HappyCow** — 素食專門網站，最準；有店家分類（Vegan/Vegetarian/Veg-options）、評分、照片 CDN。
2. **Tabelog（食べログ）** — 日本最大餐廳評論站；有分數、營業時間、`og:image` 照片、公休日。
3. **Google Maps** — 用**近期（2024–2026）評論**核實「仍在營業」，抓營業時間與所在大樓/百貨。Google 精確星等常抓不到 → 改用 HappyCow/Tabelog 分數並標來源。
4. **使用者的 FB 社團「日本素食交流會」**（groups/182598582395878）— 用 claude-in-chrome 控制使用者已登入的 Chrome 讀貼文找被推薦的店；擷取受限時改用上面幾個站交叉查證「社團常被推薦的店」。做法見記憶 `browser-fb-group-access`。
5. **Instagram / Threads / 部落格 / abillion / vegewel** — 補漏、找新店、找照片。

### 2.2 每家要蒐集的欄位（對應 HTML 物件）
`name`(中/簡述)、`nameJa`(日文原名，找店/查資料靠它)、`type`(**用詞會直接決定 badge，見 §4.3**)、`area`、`address`、`lat`/`lng`(座標，Google Maps 右鍵可取)、`hours`(含公休日)、`dishes`(招牌可吃的菜)、`notes`(**柴魚/客製提醒**、預約、座位、語言)、評分(標來源，如「HappyCow 4.5（57 則）」)、`hcUrl`/官網/IG 連結、`phone`、**所在大樓/百貨**(百貨店必填，卡片名稱前綴用得到)、每人價位。

### 2.3 判「營業中」
- Google Maps 有 2025–2026 的評論／照片 → 視為營業。
- Tabelog 標「閉店」「移転」→ **不列入**（如 ナタラジ梅田店已閉店就別放）。
- 百貨改建（如藤井大丸本館 2026 休館）→ 整棟排除或改指向替代館。
- **誠實不灌水**：奈良素食店少就少放；查不到照片就標「查無」，不要硬湊。

> 派研究可用背景 `Agent`（general-purpose，run_in_background），一次派多個地區平行查；回來的清單要人工比對是否**已存在於 HTML**（避免重複，用 `grep 店名`）。

### 2.4 ⚠️ 研究員範圍要「小」（血淚教訓）
2026-07-28 派**大範圍**研究員（如「中部名古屋以外全部」「東京都心西全區」）多次**串流失敗**（`connection closed mid-response`／`stalled 600s`），回傳被截斷或空。**解法：拆成單城市小範圍、並在 prompt 明確要求「輸出精簡、每家一段、目標 6-10 家」**，再一次平行派多個。改小範圍後全部成功。
- 都會區（東京/大阪級）本來就該拆多 agent（都心西/都心東/近郊）。
- 小城市／低密度區（金澤、東北、四國…）一城一 agent、要精簡格式，回得又快又穩。
- 若某 agent 中途死掉，可用 `SendMessage` 喚醒它「立刻把已查到的倒出來、不要再呼叫工具」；不行就派全新小範圍 agent。
- 每家欄位用 `｜` 分隔的一行式（`名稱｜area｜address｜lat,lng｜vegClass｜type｜hours｜photoUrl｜連結`）比多行更省 token、更不易觸發串流問題。

---

## 3. Step 2 — 抓照片

照片存在 `photos{}`（id→網址）。兩種來源：

### 3.1 HappyCow CDN（優先，可熱連）
格式固定，直接把網址寫進 `photos`：
```
https://images.happycow.net/venues/500/XX/YY/hcmpNNNNNN_MMMMM.jpeg
```
- 用 curl 驗證回 200 再用：`curl -s -o /dev/null -w "%{http_code} %{content_type}\n" "<url>"`
- **研究員有時給 `/venues/1024/…` 或 `/300/…`**（不同尺寸路徑）→ **統一改成 `/500/`**（後面 `XX/YY/hcmpNNN_MMM.jpeg` 不變），curl 驗 200 即可，全站一致。
- **⚠️ 密集 curl `happycow.net` 主站會觸發「Unusual Traffic」機器人封鎖**（瀏覽器會跳到 `/automated-traffic` 頁）。但那只擋主站，**圖片 CDN `images.happycow.net` 不受影響**——瀏覽器實測 `new Image().onload` 仍為 true，真實使用者（GitHub Pages）正常。別因為那個分頁就以為圖壞了。

### 3.2 Tabelog / 官網 照片（**必須下載到本地** `images/`）
Tabelog 的 `og:image` 帶 `?token=` 動態簽章、會過期；官網/Google 網址也會失效。**一律下載存進 repo 的 `images/NNN.jpg`**，HTML 用相對路徑引用。可靠做法（**從頁面抓 og:image、帶 UA 與 referer**）：
```bash
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
dl(){ id="$1"; page="$2";
  img=$(curl -sL -A "$UA" "$page" | grep -oE '<meta property="og:image" content="[^"]+"' | head -1 | sed -E 's/.*content="([^"]+)".*/\1/; s/&amp;/\&/g')
  [ -n "$img" ] && curl -sL -A "$UA" -e "$page" "$img" -o "images/$id.jpg"
  if [ -s "images/$id.jpg" ] && file -b "images/$id.jpg" | grep -q JPEG; then echo "$id ✅"; else rm -f "images/$id.jpg"; echo "$id ❌"; fi; }
dl 212 "https://tabelog.com/osaka/A2701/A270101/27083896/"
```
**照片抓取三大坑（都踩過）**：
1. **別直接 curl 研究員給的 `tblg.k-img.com/.../Rvw/…jpg` 裸網址** → 無 token 會下載到一個 4KB 的 HTML/文字檔（`file` 顯示 ASCII text，不是 JPEG）。**一定要從 Tabelog 店頁的 `<meta og:image>` 取帶 token 的版本**。
2. **Tabelog `/en/` 英文頁 og:image 抓不到** → 把網址改成 **JP 版 `tabelog.com/...`（去掉 `/en`）** 再抓，就有了。
3. **官網常常沒有 og:image**（storeinfo/base.shop/IG 連結多半抓不到）→ 抓不到就**留 emoji 底圖**（卡片 `onerror` 已容錯），別硬湊。低密度區（東北/四國/金澤…）很多店就是查無照片，可接受。

> **教訓**：本地圖片一定要記得 `git add images/`！曾發生 HTML 已提交部署、但圖片漏 add，導致線上一整批破圖（見 §8）。

---

## 4. Step 3 — 寫進 HTML（三個 id-keyed 資料表並存）

主檔案裡有一段 `<script>`，含三個表，新店只需 append：

### 4.1 `restaurants[]`（主資料，一物件一店）
續編最大 id（**不要重用歇業空號**）。範例：
```js
{
  id:212, rank:212, group:'social', region:'osaka',
  name:'ヴィーガン食堂 アジュ Aju（中崎町）', nameJa:'ヴィーガン食堂 アジュ',
  type:'大豆肉日本料理｜全素 Vegan', tags:['social'],
  area:'中崎町・北區（梅田徒步圈）',
  address:'大阪市北区中崎1-10-14',
  lat:34.70641, lng:135.50663,
  hours:'午 11:30-13:30／晚 17:30-21:30；週一公休',
  dishes:'大豆肉燒鳥串・大豆肉お好み焼き・日式咖哩',
  notes:'全素・無柴魚。老闆一人經營、建議預約。HappyCow 4.5(57則)。',
  flag:'🟢 中崎町・全素食堂',
  hcStars:'—', gStars:'HappyCow 4.5（57 則）',
  gmap:'https://www.google.com/maps/search/?api=1&query=34.70641,135.50663',
  ghours:'https://soymeat-aju.jugem.jp/',
  hcUrl:'https://www.happycow.net/reviews/aju-osaka-328650', phone:''
},
```
- 百貨內店家：`name` 用「大樓 樓層｜店名」前綴，例：`'阪急 13F｜おやさいガーデン TIERRA'`。
- 座標同棟可共用（小數 5 位）。

### 4.2 `photos{}` 與 `PRICES{}`（側表）
```js
photos: 212: 'https://images.happycow.net/...'   // 或  212:'images/212.jpg'
PRICES: 212: '午 ¥1,000–1,999／晚 ¥3,000–3,999'
```

### 4.3 `type` 用詞 → 決定 ✅/❓ badge（`certainVeg()`）
判定邏輯（無需逐筆存）：
- `type` 含「**友善／選項／部分素食／有素食／素食菜單／素食套餐／Veg-options**」→ **❓ 需詢問**
- 否則含「**全素／純素／精進／素食／蛋奶素**」→ **✅ 確定素**
- 例外用 `CERTAIN_OVERRIDE = new Set([...])` 強制 ✅（目前 42,51,104）；`ASK_OVERRIDE = new Set([265,...])` 強制 ❓。

> 撰寫規則：純素/全素專門店 `type` 寫「全素」「純素 Vegan」；葷店有素選項、百貨咖啡、共用廚房 → 寫「（蔬食友善）」「素食選項」，讓它落在 ❓。
>
> **⚠️ 假陽性坑**：`type` 若寫「葷店・需預約**素食客製**」，會因含「素食」二字被誤判成 ✅（如 id 265 くにんだ）。**葷店需預約客製的、務必把 id 加進 `ASK_OVERRIDE`**，或用詞避開「素食」二字（寫「蔬食客製」「需預約客製」）。整合完一定用瀏覽器 `certainVeg()` 抽驗一遍該批 ✅ 清單有沒有混進葷店。

### 4.4 `group`（決定 marker 顏色）
`top10`(綠) / `user`(藍) / `other`(灰) / `hotel`(紫) / `social`(粉紅) / `chain`(橘)。
- **新研究/社群蒐集的店一律 `group:'social'`**；連鎖速食備案(CoCo壱番屋/SUBWAY/MOS/星巴克/薩莉亞)用 `'chain'`。
- **要新增一個 group 值，必須同步改 4 處**：CSS `.rank-X`、`makeIcon` 的 `iconX` 常數＋group→icon 三元、popup 的評分顯示三元、圖例 legend-body；再加篩選按鈕與 `getFiltered`。

### 4.5 `region`（地區篩選）— 加「新 macro-region」的完整清單
目前 12 值：`osaka/kyoto/nara/kobe/okinawa/tokyo/hokkaido/kyushu/chubu/hiroshima/tohoku/shikoku`。舊資料 1–51 無 region 欄位，靠 `r.region||'osaka'` 預設；新店一律明確標 region。

**好消息**：`filterRegion()`／`getFiltered()`（`activeRegion==='all' || (r.region||'osaka')===activeRegion`）／`fitToList()` **都是通用的**，吃任何字串，加新 region **不用動它們**。**legend 也不用改**（legend 是按 `group` 顏色，不是按 region）。

**要加一個全新 region（例 `'tohoku'`），只改這 5 處**（沿用既有 region 的做法照抄）：
1. **地區篩選按鈕**：在那排 `region-btn` 加一顆 `<button class="region-btn" onclick="filterRegion('tohoku',this)">🍎 東北</button>`（選個代表 emoji：關西🟠🟣🟢🔵、沖繩🌺、東京🗼、北海道❄️、九州♨️、中部⛰️、廣島🕊️、東北🍎、四國🌉）。
2. **`checkedDate(id, region)`**：加一條 `if (region === 'tohoku') return '<日期>';`（放 region 判斷那區）。
3. **`make_csv.py` 的 `regionmap`**：加 `'tohoku': '東北'`。
4. **`make_csv.py` 的 `checked()`**：加對應 `if region == 'tohoku': return '<日期>'`（與 HTML 的 checkedDate 一致）。
5. **`<title>` 與 `<h1>`**：把新地區加進去（現行標題已是「全日本…」，通常不用每次改；只在想更新列舉時改）。

> 屬既有 macro-region 的城市（如 神戶屬關西、橫濱/鎌倉/箱根屬 tokyo）**不用開新 region**，直接用該 region 值、`area` 註明城市即可。中部（名古屋+金澤+高山…）也共用 `'chubu'`。

### 4.6 `checkedDate(id, region)`（核實日期，區間判定）
不逐筆存，依「特例集合 → CHECK_OVERRIDE → region → id 區間」順序回傳。新批店家最省事做法：**在最上面加一條 `if (id >= <本批起始id>) return '<日期>';`**。
> **改 HTML 的 `checkedDate` 後，務必同步改 `make_csv.py` 的 `checked()`（兩邊邏輯要一致）**，否則 CSV 日期會對不上。

### 4.7 百貨美食快篩 `depa`（id 白名單）
`getFiltered` 裡 `activeFilter==='depa'` 用 id 白名單判定（目前：90–126、32、34、164–172、[186,192,193,194]）。**加百貨店要把新 id 併進這條白名單。**

### 4.8 大批（10+ 家）用 Python 腳本生成插入（省 token、少手誤）
手寫幾十個 JS 物件又慢又容易漏引號。**改用一支 Python 腳本**：把各店資料存成 tuple 清單，程式產生 `restaurants[]` 物件字串 + `photos`/`PRICES`，再插進 HTML。範式（實例見 scratchpad 的 `insert_tokyo.py`／`insert_finish.py`）：
```python
V=[ (id,region,name,nameJa,type,area,address,lat,lng,hours,dishes,notes,flag,gStars,ghours,hcUrl,phone), ... ]
lines=''.join(f"""  {{
    id:{i}, rank:{i}, group:'social', region:'{rg}', name:'{n}', nameJa:'{j}',
    type:'{t}', tags:['social'], area:'{a}', address:'{ad}', lat:{lat}, lng:{lng},
    hours:'{h}', dishes:'{d}', notes:'{no}', flag:'{f}',
    hcStars:'—', gStars:'{gs}',
    gmap:'https://www.google.com/maps/search/?api=1&query={lat},{lng}',
    ghours:'{gh}', hcUrl:'{hc}', phone:'{ph}'
  }},\n""" for (i,rg,n,j,t,a,ad,lat,lng,h,d,no,f,gs,gh,hc,ph) in V)
ix=html.index('const restaurants = ['); jx=html.index('\n];',ix)   # 插在 restaurants[] 的 ]; 之前
html=html[:jx+1]+lines+html[jx+1:]
# photos/PRICES：直接 replace 'const photos = {\n' → 加上新條目那幾行；assert count==1 防呆
```
**注意**：
- 名稱含撇號（`Elly's`/`Esparza's`/`Ploughman's`）→ 用**全形 `’`**（U+2019）避免破壞單引號 JS 字串；`&` 在字串裡沒問題。
- 插入點用 `html.index('const restaurants = [')` 之後第一個 `\n];`（**別**用店家內文當 anchor，縮排可能不符）。
- 跑完務必 `node --check`（見 §6）。

---

## 5. Step 4 — 產生 CSV（給 Google My Maps 匯入 + 網頁下載）

```bash
python3 make_csv.py     # 從 HTML 解析 restaurants → vegan_kansai_places.csv
```
- **店家資料一有變動就要重跑，並與 HTML 一起 commit**，讓下載的 CSV 與地圖同步。
- 輸出會印「寫出 N 筆」與「缺座標」清單 → **缺座標必須是「無」**。
- header 的「⬇️ 下載 CSV」是相對連結；「🗺️ 在 Google 地圖開啟」連到使用者自建 My Map（`mid=1i3Don...`，資料需使用者自行在 My Maps 重新匯入才更新）。

---

## 6. Step 5 — 如何檢查完成（驗證清單，逐項打勾）

```bash
# ① HTML 內嵌 JS 語法正確
python3 -c "import re;html=open('大阪素食餐廳地圖.html',encoding='utf-8').read();open('/tmp/c.js','w').write(re.findall(r'<script>(.*?)</script>',html,re.S)[-1])"
node --check /tmp/c.js && echo "語法 OK"

# ② CSV 與 HTML 同步（重跑後應無新差異、缺座標為「無」）
python3 make_csv.py

# ③ 店家總數一致（HTML id 數 == CSV 筆數 == header「共 N 家」）
grep -oE "id:[0-9]+, rank:" 大阪素食餐廳地圖.html | wc -l

# ④ 新加的本地照片都存在、非 0 byte
for n in 212 213 214; do [ -s "images/$n.jpg" ] && echo "$n ✅" || echo "$n ❌"; done

# ⑤ HappyCow 熱連圖抽查 200
curl -s -o /dev/null -w "%{http_code}\n" "<happycow url>"
```

- [ ] `node --check` 通過
- [ ] `make_csv.py` 印「缺座標: 無」，筆數 = 期望家數
- [ ] header `共 N 家`／`index.html` 說明的家數已更新（**家數其實是 `restaurants.length` 動態算，但 `index.html` 卡片描述要手動改**）
- [ ] 新店的 `photos`/`PRICES`/`checkedDate` 都補了
- [ ] 若加了 group/region → 相關 4–6 處都改了
- [ ] 若加了百貨店 → `depa` 白名單擴了
- [ ] **瀏覽器實測**（見下）

### 瀏覽器實測（強烈建議）
```bash
python3 -m http.server 8801   # 若 port 被占：pkill -f "http.server" 後換 port
# 開 http://localhost:8801/大阪素食餐廳地圖.html
```
用 claude-in-chrome 或手動確認：地區/飲食/百貨/連鎖篩選可切換且可疊加、切地區地圖自動對焦(fitBounds)、新店 marker/卡片/照片/價位正常、badge ✅/❓ 判對、手機 FAB 篩選鈕正常。
> 注意：**Geolocation(找附近) 需 HTTPS 或 localhost** 才能用，`file://` 開會失敗。

---

## 7. Step 6 — 輸出到 GitHub（部署）

GitHub Pages 從 `main` 直接部署，**本 repo 慣例直接 commit 到 main**（不開分支，否則不會部署）。

```bash
# ⚠️ 最容易漏：本地新照片一定要一起 add！
git add images/         # 新照片（或逐一列出）
git add 大阪素食餐廳地圖.html vegan_kansai_places.csv make_csv.py index.html
git status --short      # 確認該進的都 staged，尤其 images/*.jpg 顯示 A(新增)

git commit -m "新增 <地區> <N> 家素食店(id AAA–BBB)：...；共 <總數> 家"
git push                # 推 main → 約 1–2 分鐘後 GitHub Pages 生效
git status --short      # 應為空（工作區乾淨）
```
commit 訊息結尾附：
```
Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
```

---

## 8. 常見錯誤 / 踩雷清單（血淚版）

| # | 雷 | 後果 / 對策 |
|---|---|---|
| 1 | **本地照片漏 `git add images/`** | 已提交的 HTML 引用 `images/NNN.jpg`，圖沒推上去 → **線上整批破圖**。曾實際發生(212–252)。push 前 `git status` 確認 `images/*.jpg` 都 A。 |
| 2 | **Tabelog / Google 照片直接熱連** | `?token=` 簽章、Google 網址都會過期失效 → 破圖。**一律下載存 `images/`**。只有 HappyCow CDN 可熱連。 |
| 3 | **改 HTML `checkedDate` 沒同步改 `make_csv.py` `checked()`** | CSV 核實日期與網頁對不上。兩處邏輯必須一致。 |
| 4 | **店家變動沒重跑 `make_csv.py`** | 下載 CSV 與地圖不同步。改完一定重跑並一起 commit。 |
| 5 | **柴魚だし判斷太寬鬆** | 把藏柴魚的定食/味噌湯/天つゆ當成可吃。日式高湯預設有柴魚，`type` 別亂寫「素食」，寫「(蔬食友善)」落 ❓，`notes` 註明需指定昆布/精進だし。 |
| 6 | **`type` 用詞害 badge 判錯** | 葷店有素選項卻寫「素食」→ 誤判 ✅。純素才寫「全素/純素」；需客製寫「選項/友善」。必要時用 `CERTAIN_OVERRIDE`/`ASK_OVERRIDE`。 |
| 7 | **新增 group 值只改一處** | marker 無色/圖例缺項/篩選失效。要改 4–6 處（見 §4.4）。 |
| 8 | **重用歇業店的空號 id** | 撞到孤兒 `photos`/`PRICES`。歇業只刪 `restaurants[]` 物件、留空號，新店永遠續編最大 id。 |
| 9 | **座標抓錯（經緯顛倒/度數錯）** | marker 掉到海裡。lat≈34–35、lng≈135(關西)；`make_csv.py` 會印「缺座標」但不會抓顛倒，需肉眼看地圖。 |
| 10 | **改檔名 `大阪素食餐廳地圖.html`** | 破壞 index.html 連結與 GitHub Pages 舊網址。**永遠保留原檔名**，即使已擴成全日本。 |
| 11 | **`index.html` 卡片家數沒改** | header badge 是 `restaurants.length` 動態，但 `index.html` 的描述文字是寫死的，要手動更新。 |
| 12 | **背景研究員的清單沒比對就照抄** | 重複加入已存在的店。整合前先 `grep 店名` 查是否已在 HTML。 |
| 13 | **`file://` 直接開測 GPS** | 找附近功能失效。用 `python3 -m http.server` 開 localhost 測。 |
| 14 | **研究員範圍太大 → 串流失敗** | `connection closed`／`stalled 600s`，回傳被截斷。**拆單城市小範圍＋要求精簡輸出**，平行派。死掉的用 SendMessage 叫它「立刻倒出已查到的」。（見 §2.4） |
| 15 | **直接 curl Tabelog 裸圖網址** | 無 token → 下載到 4KB 文字檔（非 JPEG）。**從 Tabelog 店頁 `<meta og:image>` 抓帶 token 版**；`/en/` 頁抓不到 → 改 JP 版網址。（見 §3.2） |
| 16 | **`type` 含「素食客製」誤判 ✅** | 葷店需預約客製被當確定素。葷店客製者加進 `ASK_OVERRIDE`，整合後用 `certainVeg()` 抽驗該批 ✅ 清單。（見 §4.3） |
| 17 | **HappyCow「Unusual Traffic」誤判圖壞** | 密集 curl 主站被擋，但 `images.happycow.net` CDN 仍正常。用 `new Image().onload` 在瀏覽器實測確認。（見 §3.1） |
| 18 | **背景 http.server 被 pkill 後又啟同 port** | 上一個沒完全放掉 → exit 144/port 佔用。換 port（8801→8811→…）或 `pkill -f http.server; sleep 1` 再啟。 |

---

## 8b. 各地區「素食可吃」的最大陷阱（寫 notes 時對照）

| 地區 | 陷阱 | 繞過方式 |
|---|---|---|
| 全日本通用 | 柴魚だし（かつお）藏在味噌湯/そば・うどんつゆ/天つゆ/だし | 指定昆布・椎茸・精進だし；選純素專門店免問 |
| 大阪 | たこ焼き/お好み焼き含柴魚・魚粉 | 找純素版（Paprika 等） |
| 京都・鎌倉・高山 | 精進料理相對安全（昆布椎茸だし），但懷石一番だし含柴魚 | 預約時指定精進 course、確認だし |
| 沖繩 | 沖繩そば湯＝豚骨＋柴魚；spam/ソーキ/三枚肉；ゴーヤチャンプルー含豬/spam/柴魚 | 島豆腐/海葡萄(海藻)OK；vegan 版そば（タマテバコ等） |
| 北海道 | 味噌拉麵(豚骨+魚介)、湯咖哩(雞/豬骨)、成吉思汗(羊)、海鮮丼 | vegan 版拉麵/湯咖哩（Beyond Age、めぐり） |
| 九州 | **博多豚骨拉麵**、明太子、もつ鍋、ちゃんぽん、馬肉、地雞 | 全植物復刻豚骨（BUGORO/SUSHI-SHIMA） |
| 名古屋 | 味噌煮込うどん/あんかけ(柴魚+肉)、手羽先、味噌カツ、ひつまぶし | 預約指定素高湯；Grains 有全素ひつまぶし風 |
| 廣島 | お好み焼き含魚粉(かつお)+豬、牡蠣/海鮮 | 點 vegan 版廣島燒（JoGeSaYu/長田屋） |
| 四國 | **讚岐うどんつゆ含いりこ(小魚乾)+柴魚**、海鮮 | 一般烏龍店即使野菜湯也含之，須確認或選純素店 |
| 東北 | 牛舌(仙台)、海鮮、そばつゆ | 素食稀少，多為 macrobi/自然食小店 |
| 溫泉區(別府/由布院/銀山/道後) | 旅館會席預設含魚 | 訂房時交涉素食；別府「地獄蒸」自取蒸蔬菜 |

---

## 9. 一頁速查（換地區時照做）

1. **派研究**（HappyCow/Tabelog/Google/FB社團）→ **小範圍、精簡輸出**、平行多路（§2.4）；每家收齊欄位、核實營業中、標來源。回來 `grep 店名` 比對避免重複。
2. **抓照片**：HappyCow 熱連（統一 `/500/`、curl 驗 200）／Tabelog 從店頁 og:image 下載存 `images/<id>.jpg`（帶 UA+referer、JP 版網址）；查無就 emoji 底圖（§3）。
3. **寫進 HTML**：續編最大 id、用 Python 腳本生成 `restaurants[]`＋`photos`＋`PRICES`（§4.8）；`type` 用詞決定 ✅/❓，葷店客製記得 `ASK_OVERRIDE`。
4. **新 macro-region** → 改 5 處（按鈕/checkedDate/make_csv regionmap+checked/title）（§4.5）；屬既有 region 的城市直接 append。
5. `python3 make_csv.py`（缺座標須「無」）。
6. `node --check`＋瀏覽器實測（region/飲食篩選、fitBounds 對焦、照片載入、`certainVeg()` 抽驗 badge、手機FAB）。
7. `git add`（**含 `images/`！**）→ commit → push main → 等 Pages 部署 → `git status` 應乾淨。
8. `sed -i '' 's/舊家數 家/新家數 家/' index.html`（家數寫死要手動更新）。
9. 對照 §8 逐雷檢查（尤其 #1 漏圖、#14 研究員範圍、#15 裸圖網址、#16 badge 誤判）＋ §8b 各地區陷阱。

---

*相關記憶：`kansai-vegetarian-map`（資料結構細節）、`japan-expansion-roadmap`（全日本擴充進度與各 region 狀態）、`browser-fb-group-access`（用 Chrome 讀 FB 社團）。*
