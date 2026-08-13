# XingGraph README è§†è§‰è§„èŒƒ / Visual System

> è¯¥æ–‡æ¡£å†»ç»“ XingGraph åœ¨ GitHub ä»“åº“ä¸ä¸ªäººä¸»é¡µä¸Šæ‰€æœ‰è§†è§‰èµ„äº§çš„ä¸€è‡´æ€§è§„åˆ™ã€‚
> ä»»ä½•æ–°å¢ SVG / ç« èŠ‚ banner / hero æ”¹åŠ¨å‰å…ˆæ ¡å¯¹æœ¬æ–‡æ¡£ã€‚

## Paletteï¼ˆå…­å±‚èŠ‚ç‚¹ + ä¸»å“ç‰Œï¼‰

| è§’è‰²              | Hex        | ç”¨é€”                                |
| ----------------- | ---------- | ----------------------------------- |
| Background        | `#0a0a0d`  | SVG æ•´å›¾åº•è‰²ã€é¢æ¿åº•è‰²              |
| Surface       | `#16122a`  | å†…åµŒé¢æ¿ã€äºŒçº§å®¹å™¨                  |
| Foreground        | `#f3f0fa`  | ä¸»æ ‡é¢˜ã€ä¸»æ–‡å­—                      |
| Muted         | `#9b93ab`  | å‰¯æ–‡å­—ã€metadata                    |
| Muted-2       | `#6f6787`  | å¼±åŒ–è¯´æ˜                            |
| Accent (primary)  | `#a974ff`  | é¡¹ç›®ä¸»è‰²ã€å…³é”®èŠ‚ç‚¹æè¾¹ã€å¼ºè°ƒçº¿      |
| Accent (secondary)| `#4f7bdd`  | èŠ‚ç‚¹ä¹‹é—´çš„"è¿æ¥è¾¹"é¢œè‰²             |
| TextDocument | `#A550FF` | å…­å±‚èŠ‚ç‚¹ 1                          |
| DocumentChunk | `#0DFF00` | å…­å±‚èŠ‚ç‚¹ 2                          |
| ChunkWiki    | `#FF5CA8` | å…­å±‚èŠ‚ç‚¹ 3                          |
| Entity       | `#6510F4` | å…­å±‚èŠ‚ç‚¹ 4                          |
| EntityType   | `#D5C2FF` | å…­å±‚èŠ‚ç‚¹ 5                          |
| TextSummary  | `#FFB454` | å…­å±‚èŠ‚ç‚¹ 6                          |

> ç´«è‰²æ·±è‰²ç³» + çœŸå®èŠ‚ç‚¹å…­è‰²ï¼Œä»ç°æœ‰ svg è‡ªç„¶ç»§æ‰¿ï¼ˆå‚è€ƒ
` `assets/banner.svg` / `assets/principles-ring.svg` / åç«¯ `preprocessor.py:55-69`ï¼‰ã€‚

## Typography

```text
Display: ui-sans-serif, system-ui, -apple-system, "Segoe UI", "PingFang SC", sans-serif
Mono:    ui-monospace, SFMono-Regular, Menlo, "Microsoft YaHei", monospace
```

å­—å·ï¼ˆåŸºäº viewBox 1200ï¼Œ900px å®é™…æ¸²æŸ“ï¼‰ï¼š

| è§’è‰²           | SVG å•ä½ | å®é™…åƒç´ ï¼ˆâ‰ˆï¼‰ | ç”¨ä¾‹                |
| -------------- | -------- | ------------- | ------------------- |
| Hero title     | 56+      | 42px+         | hero ä¸»æ ‡é¢˜         |
| Section title  | 40+      | 30px+         | ç« èŠ‚ banner         |
| Body lead      | 22+      | 16.5px+       | hero ä¸€å¥è¯æ‰¿è¯º     |
| Diagram text   | 20+      | 15px+         | èŠ‚ç‚¹æ ‡ç­¾ã€é¢æ¿æ ‡é¢˜  |
| Label       | 18+      | 13.5px+       | å…³é”® metadata       |
| Caption    | 16       | 12px          | ä»…é™éå¿…è¦è£…é¥°      |

## Shape

- **radius**ï¼šhero `18` / é¢æ¿ `14` / chip `8`
- **stroke**ï¼šhairline `1.5`ã€accent `2.5`ã€èŠ‚ç‚¹å¤–ç¯ `2`
- **spacing**ï¼š8-based gridï¼›hero å·¦å³å†…è¾¹è· 64ï¼›section banner å·¦å³å†…è¾¹è· 48

## Motifï¼ˆé¡¹ç›®ä¸“å±è§†è§‰ç¬¦å·ï¼‰

å…­å±‚ç®¡çº¿èŠ‚ç‚¹ + è¿çº¿ï¼š

```
 Document  â†’  Chunk  â†’  Wiki
                  â†“  â†˜  â†’  Entity  â†’  Type
              Summary
```

ç”¨ `#A550FF #0DFF00 #FF5CA8 #6510F4 #D5C2FF #FFB454` å…­è‰²åˆ†åˆ«å¡«å……å…­ä¸ªèŠ‚ç‚¹ã€‚
è¿™å…­è‰²æ˜¯é¡¹ç›®**çœŸå®çš„èŠ‚ç‚¹ç±»å‹é…è‰²**ï¼Œä¸æ˜¯è£…é¥°ç”¨è‰²â€”â€”ä»»ä½• heroã€section bannerã€å·¥ä½œæµå›¾éƒ½åº”å¤ç”¨æ­¤ motifã€‚

## Composition

- calm / editorial-technical
- sparse densityï¼ˆä¸€å±åªæ”¾ä¸€ä¸ªä¸»å¼ ï¼‰
- 1 ä¸» accent + 1 æ¬¡ accentï¼Œä¸æ··ç”¨ >2 ä¸ªé«˜é¥±å’Œè‰²
- hero æ¯”ä¾‹å›ºå®š 58% æ ‡é¢˜ / 42% proofï¼ˆproo
- hero ±ÈÀı¹Ì¶¨ 58% ±êÌâ / 42% proof£¨proof Çø·ÅÁù²ã¹ÜÏß³éÏó£©
- section banner Áô 50% ×ó²à¿Õ°×¹©±êÌâºôÎü

## ½ûÓÃ

- `<script>`¡¢`<foreignObject>`¡¢ÍâÁ´ CSS / fonts
- remote Í¼Æ¬ÄÚÇ¶£¨GitHub ²»¿É¿¿£©
- `filter url(#glow)`¡¢ÖØÒõÓ°¡¢½¥±äìÅ¹â£¨skill `svg-production.md` ÏÔÊ½·´¶Ô£©
- ¶àÓïÑÔ»ÕÕÂºáÅÅ³¬¹ı 6 ¸ö£¨Ê×ÆÁÓµ¼·£©

## ×Ê²úÇåµ¥

```
assets/readme/
  visual-system.md            ¡û ±¾ÎÄ¼ş
  hero.svg                    ¡û 1200x340 ²Ö¿â hero
  profile-hero.svg            ¡û 1200x260 ¸öÈËÖ÷Ò³ hero
  section-overview.svg        ¡û 1200x160 ¡¸Ò»¸öÀı×Ó¡¹ banner
  section-visualization.svg   ¡û 1200x160 ¡¸Í¼Æ×Õ¹Ê¾¡¹ banner
  section-mechanism.svg       ¡û 1200x160 ¡¸¹¤×÷Ô­Àí¡¹ banner
  pinned-project-card.svg     ¡û 600x120  ¸öÈËÖ÷Ò³ÏîÄ¿¿¨Æ¬Ä£°å£¨6 ÕÅ£©
  made-with-beautify.svg      ¡û 420x64  ¿ÉÑ¡ÖÂĞ»£¨´ıÓÃ»§ÊÚÈ¨£©
```

## Ğ£¶ÔÇåµ¥£¨Ã¿¸öĞÂ SVG ·¢²¼Ç°×Ô¼ì£©

1. `viewBox` ´æÔÚ£¬`<title>` / `<desc>` ´æÔÚ
2. font-family ÓÃÏµÍ³Õ»£¨²»ÉÏ Google Fonts£©
3. ¹Ø¼üÎÄ×Ö ¡İ 18 unit£¨900px ¿í¶ÈÏÂ ¡Ö 13.5px£©
4. ÅäÉ«Ö»ÔÚÉÏ±íµ÷É«°åÀïÌô
5. ÔÚ 900px ×ÀÃæÓë 360px ÊÖ»ú¿í¶ÈÏÂ¶¼²»²ÃÇĞ/²»Òç³ö
6. °µÉ« `#0a0a0d` µ×Í³Ò»£»Ç³É« GitHub Ö÷ÌâÏÂĞèÓĞÍêÕû×ÔÌî±³¾°
