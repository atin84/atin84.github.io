# QuickIris

Blogger와 GitHub Pages의 콘텐츠 발행을 한 형식으로 관리하는 운영 기반입니다. Python 3.10 이상과 표준 라이브러리만 사용합니다.

## 사이트 주소와 저장소

- GitHub Pages · QuickIris: [https://atin84.github.io/](https://atin84.github.io/)
- Blogger · Iris: [https://quickiris.blogspot.com/](https://quickiris.blogspot.com/)
- 저장소: [atin84/atin84.github.io](https://github.com/atin84/atin84.github.io)

저장소 이름은 `quickiris`에서 `atin84.github.io`로 변경했습니다. GitHub 사이트는 저장소 경로가 붙지 않는 사용자 사이트 주소를 사용합니다.

## 현재 범위

- 공통 JSON 원고 검증과 플랫폼별 출력
- GitHub Pages용 정적 HTML, canonical, sitemap, RSS, 모바일 스타일, 소개·개인정보 안내
- Blogger 공식 API 발행기: 기본 dry-run, 초안/공개 선택, 원격 중복 확인, 불확실한 요청 기록
- 예약 시간이 지난 `ready` 원고만 빌드
- AdSense ID 연결을 위한 설정
- 두 사이트의 30일 비교 규칙

GitHub 첫 공개 배포를 완료했고 실제 글 본문을 확인했습니다. Chrome 안내 글 1편과 소개·개인정보 안내가 공개되어 있습니다. 두 원고는 `ready`이며 Blogger 원고의 `published_at`은 공개 페이지의 게시 시각에 맞췄습니다. AdSense 계정 ID와 사이트 소유권 확인용 메타태그를 설정했으며 광고는 계속 비활성화되어 있습니다.

`content/`의 첫 원고 2편은 공식 Google·Microsoft 도움말을 검토해 작성했습니다. Blogger 첫 Edge 글은 웹 편집기로 공개 발행했고 본문과 중복 확인용 식별표식을 확인했습니다. 초기 두 글은 연결 확인용이며 검색 수요가 검증된 주제나 플랫폼 비교 표본으로 간주하지 않습니다.

자동 자료 조사, AI 원고 생성, 검색·수익 데이터 수집, Blogger API 무인 발행은 아직 연결 전입니다. 현재 일정은 준비된 원고의 예약 시각을 확인해 사이트를 하루 두 번 다시 빌드하는 작업입니다. 경기 조사부터 공개·갱신까지 이어지는 연결은 완료되지 않았습니다.

## 독자 언어와 편집 방향

2026년 10월 17일 독자용 기본 언어를 영어로 수정했습니다. `config.json`의 언어, 사이트 소개, 초기 Chrome·Edge 원고, GitHub 소개·개인정보 안내가 영어입니다. Blogger 콘텐츠 언어·소개·검색 설명을 영어로 저장하고 기존 Edge 글을 같은 URL에서 영어로 업데이트했습니다. 한국어로 보이는 운영 문서는 관리용이며 독자용 웹 페이지에 배포하지 않습니다.

2026년 10월 17일 확정한 초기 취재 범위는 **NBA와 잉글랜드 프리미어리그(EPL)**입니다. 두 리그를 처음부터 함께 다루고, 선정한 각 기사에 **8개 언어 전체**를 적용한 뒤 데이터로 비교합니다. 초기 대상에 MLB·NFL 등 다른 리그를 자동 추가하지 않습니다. 언어를 먼저 3개로 제한하거나 나머지 언어를 특정 경기에서만 시험하는 제안은 채택하지 않았습니다.

초기 운영은 두 리그의 **스포츠 팬·관람객**을 대상으로 합니다. 경기 전 공지·일정 확정과 경기 후 공식 결과, 연기·취소·정정 등 실제 변화에 맞춰 필요한 기사를 발행하거나 갱신합니다. 시간당·일별 고정 발행량과 플랫폼별 편수 할당량은 두지 않습니다. 수요와 출처 검증을 통과하지 못한 소재는 보류합니다.

편집의 중심은 **팬과 처음 보는 독자가 경기를 더 재미있게 이해하도록 돕는 관전 안내와 해설**입니다. 경기 전에는 볼 만한 이유, 눈으로 확인할 관전 포인트, 검증된 팀·선수의 인연과 현장 관람 정보를 다룹니다. 경기 후에는 쉬운 요약, 흐름이 달라진 장면과 의미, 사전에 제시한 관전 질문에 대한 실제 답을 제공합니다. 첫 운영은 NBA 농구와 EPL 축구에 집중하며, 다른 종목·리그로의 확대는 두 리그·8개 언어의 실제 관측을 바탕으로 결정합니다.

출처가 붙은 팀·선수·상대 관계와 규칙 설명을 재사용하되, 모든 경기의 사연이나 선수 감정을 만들어 넣지 않습니다. 한 언어의 페이지 안에서 짧은 핵심 설명부터 팬을 위한 깊은 맥락까지 읽을 수 있도록 설계합니다. 자세한 기사 구성과 검수 기준은 [스포츠 편집 기준](experiment/editorial-guidelines.md)에 있습니다. 이 문서는 편집 설계이며 새 화면이나 자동 생성 기능의 구현 완료를 뜻하지 않습니다.

정보량이 작은 경기는 하나의 경기 페이지에서 사전 안내와 결과를 갱신할 수 있습니다. 관심이 큰 경기는 사전 안내와 결과 분석에 각각 독립적인 정보가 있을 때 프리뷰·리캡으로 나눌 수 있습니다. 모든 경기에 한 편 또는 두 편을 의무적으로 적용하지 않습니다. 같은 기사의 수정은 기존 URL에서 처리합니다.

Google Trending now에서는 NBA·EPL 경기 후보를 찾기 위해 미국·영국을 우선 관측하고, 8개 언어 독자와 관련된 국가의 검색 추세도 별도로 확인합니다. 4시간 신규 추세, 24시간 검색량 순위, 7일 지속·반복 신호를 구분하며, 공식 경기 일정과 결과·출처 본문의 시각 근거를 함께 검토합니다. 여러 국가를 조사한다는 것은 모든 경기를 발행한다는 뜻이 아닙니다. 서로 다른 기간의 목록을 같은 표본으로 나누거나 별칭 행의 검색량을 더하지 않으며, 아직 조사하지 않은 국가·언어는 수요 0이 아닌 미측정으로 남깁니다.

플랫폼 비교는 같은 언어 조건에서 리그·수요·중요도·예정 시각이 비슷한 서로 다른 경기를 가능하면 짝지어 무작위 배정합니다. 경기 단위로 소유 플랫폼을 유지하고, 같은 경기·같은 기사 의도·같은 언어의 글을 양쪽에 중복 발행하지 않습니다. 후속 설계의 중복 키는 `match_id + article_kind + language`, 번역 그룹은 `match_id + article_kind`입니다. 생성기는 번역 그룹의 경기·기사 종류·언어 일관성을 검사합니다. 지속적인 경기 감지·발행 대기열에 이 키를 적용하는 단계는 아직 미연결입니다.

### 확정한 8개 언어와 발행 원칙

운영 언어는 영어(`en`), 한국어(`ko`), 스페인어(`es`), 일본어(`ja`), 브라질 포르투갈어(`pt-BR`), 프랑스어(`fr`), 독일어(`de`), 힌디어(`hi`)의 **총 8개**입니다. 영어를 작성 기준으로 삼되, 선정한 각 기사에는 나머지 7개 번역본을 모두 준비합니다. NBA와 EPL 모두 같은 언어 구성을 적용합니다. 기존 공개 Chrome·Edge 글은 연결 확인용이며 새 실험 표본이나 번역 의무 대상에 포함하지 않습니다.

모든 경기의 무조건 발행과는 구분합니다. 먼저 두 리그 안에서 기사 가치와 출처를 확인해 경기를 선정하고, 선정한 기사의 8개 언어판을 같은 발행 묶음으로 준비·검수합니다. 개별 언어의 검색 수요가 아직 측정되지 않았다는 이유로 해당 번역을 제외하지 않습니다. 공개 과정의 실패·지연은 미완료 작업으로 기록하고 복구하며, 8개 언어 공개가 모두 확인되기 전에는 해당 묶음을 완료로 표시하지 않습니다.

언어별 별도 URL과 번역 그룹, 언어 전환 링크를 사용하도록 설계합니다. 경기·점수·출처·그래프 수치는 공통으로 관리하고 제목·용어·설명·차트 레이블은 각 언어에 맞게 작성합니다. 국가와 언어를 구분하며 중계·관람 정보는 실제 이용 지역을 명시합니다. 같은 기사 의도의 원문·번역은 경기의 소유 플랫폼에 유지하고, 양 플랫폼에 NBA·EPL과 동일한 8개 언어가 모두 쌓이도록 배정합니다.

첫 비교는 **리그 × 언어**의 16개 조합을 기본으로 하며 플랫폼·기사 의도·실제 독자 국가를 추가로 구분합니다. 특정 리그나 언어를 한 플랫폼에 몰아넣지 않습니다. 고유 경기, 원문, 번역, 갱신은 별도로 집계합니다. 확정한 운영 기준이며 현재 사이트에서 8개 언어 자동 발행이 실행되고 있다는 뜻은 아닙니다. 상세 측정 규칙은 [운영 실험](experiment/protocol.md)에 있습니다.

## 실제 구현 상태와 미연결 단계

글별 다국어 렌더링은 구현했습니다. 지속적인 경기 감지·대기열·발행 묶음 상태와 무인 발행 연결은 추가로 필요합니다. 생성기는 글별 `language`, `league`, `match_id`, `article_kind`, `translation_group`, `updated_at`, `figures`를 지원합니다. GitHub에는 언어별 URL·목록, 상호 `hreflang`, canonical, 실제 수정일 메타데이터를 생성합니다. Blogger의 확정된 `blogger_url`은 목록에 외부 링크로 연결하며 본문을 GitHub에 복제하지 않습니다. Blogger 본문의 `lang`과 그림은 지원하지만 문서 head의 hreflang·canonical은 테마에서 별도로 다뤄야 합니다. Blogger 기존 본문의 `posts.patch` 갱신도 현재 발행기에 없습니다.

- Trends·검색 자료 접근, 공식 경기 조사, 영어 AI 원고 생성과 출처·품질 검수
- 경기·기사 의도·언어 식별, 중복 검사, 발행·갱신 대기열과 지속 상태 저장
- GitHub 원고 저장부터 공개 확인까지의 연결 및 Blogger OAuth·정기 실행·갱신·실패 복구
- Search Console·광고 실적 수집과 관측 기간별 비교

2026년 10월 17일 기준 QuickIris용 ChatGPT 예약 자동화는 생성되지 않았습니다. 확인한 플러그인 검색에서는 사용 가능한 Blogger 플러그인을 찾지 못했습니다. 현재 웹 로그인과 저장소 연결만으로 위 단계가 자동 실행되지는 않습니다. 재빌드 일정만 변경해 전체 자동 발행이 활성화되었다고 표시하지 않습니다.

## 2026-10-17 스포츠 테스트 발행 묶음

사용자가 예정 경기와 최근 종료 경기를 다국어로 테스트 게시하도록 승인했습니다. NBA와 EPL에서 예정 1경기·종료 1경기씩, 총 4경기를 8개 언어로 준비했습니다.

| 기사 | 소유 플랫폼 | 언어판 | 정보 그림 |
|---|---|---:|---|
| Thunder at Spurs, 20 October preview | GitHub | 8 | 슛 기회·리바운드·다음 공격 관전 질문 |
| Bucks 128–127 Pacers, 16 October preseason recap | Blogger | 8 | Herro·Siakam의 2점·3점·자유투 득점 구성 |
| Forest vs Arsenal, 18 October preview | Blogger | 8 | 첫 6리그 경기 득점 5 vs xG 10.3 |
| Everton 0–2 Chelsea, 17 October recap | GitHub | 8 | HT·46분·90분·FT 점수 변화 |

`experiment/evidence/`에는 확인한 원자료와 차트 수치·8개 언어 레이블을 기록했습니다. 차트 32개는 데이터로 만든 SVG이며 독립된 제목·대체 설명을 가집니다. 원고·그림의 완성을 실제 공개 확인과 구분합니다. 이 커밋은 GitHub 배포와 Blogger 웹 게시를 위한 준비이며, 모든 언어의 공개 URL을 확인한 뒤 발행 결과를 기록합니다.

Blogger의 이번 시험은 기존 로그인으로 웹 게시합니다. `scripts/export_blogger_import.py`는 공식 가져오기 화면에 사용할 Atom 파일을 준비하며 네트워크 요청을 하지 않습니다. API OAuth나 시간별 무인 발행을 활성화하지 않습니다.

## 로컬 확인

```bash
python3 -m unittest discover -s tests -v
python3 build.py --config config.json --content content --out dist
python3 scripts/publish_blogger.py --help
```

원고를 `content/<id>.json`에 저장합니다. `draft`는 출력하지 않습니다. `ready`이면서 `published_at`이 빌드 기준시각 이하인 원고만 공개 대상이 됩니다. `--now 2026-10-17T09:00:00+09:00`처럼 기준시각을 고정할 수 있습니다. 같은 원고를 양쪽에 배정하지 않습니다.

```json
{
  "id": "unique-question-id",
  "platform": "github",
  "status": "draft",
  "title": "사용자의 구체적인 질문에 답하는 제목",
  "description": "이 페이지에서 확인할 수 있는 내용",
  "published_at": "2026-10-18T09:00:00+09:00",
  "labels": ["주제"],
  "sections": [
    {"heading": "핵심 답변", "paragraphs": ["검증된 설명"], "bullets": ["확인 사항"]}
  ],
  "sources": [{"title": "공식 근거", "url": "https://example.com/source"}]
}
```

위 예시는 형식 설명용이며 실제 발행 원고가 아닙니다. `platform`은 `github` 또는 `blogger`입니다. 공개한 원고의 `id`는 바꾸지 않습니다. 생성된 Blogger JSON은 `exports/blogger/`에, GitHub 사이트는 `dist/`에 분리됩니다.

## GitHub Pages 연결

현재 `atin84/atin84.github.io`의 Pages 배포 소스는 GitHub Actions로 설정되어 있습니다.

1. 저장소의 Settings → Pages에서 배포 소스가 GitHub Actions인지 확인합니다.
2. 공개할 원고와 사이트 기본 정보를 준비합니다.
3. 저장소 Actions 변수 `PAGES_ENABLED=true`를 설정했습니다.
4. 워크플로는 GitHub가 반환한 실제 `base_url`로 canonical과 사이트맵을 생성합니다.
5. 첫 배포는 준비된 원고를 main에 push해 실행했습니다. 수동 재실행은 Actions → Publish GitHub Pages → Run workflow에서 가능합니다. 변수 변경만으로는 실행되지 않습니다.

현재 Pages 워크플로의 cron은 `17 0,9 * * *`이며 UTC 00:17 / 09:17, 한국시간 09:17 / 18:17에 재빌드합니다. `PAGES_ENABLED=true`일 때 배포 작업이 실행됩니다. `content/` 또는 `site_pages/`를 변경한 push도 배포 대상입니다. 예약 실행은 지연될 수 있고, 비활성 공개 저장소의 예약 작업은 GitHub 조건에 따라 중지될 수 있습니다. 새로운 AI 원고를 작성하는 작업은 이 재빌드 일정과 별도로 연결해야 합니다.

빌더는 시간이 지난 모든 `ready` 원고를 출력하며 경기 상태나 신규 발행·갱신 필요성을 판단하지 않습니다. 경기별 운영을 연결할 때에는 대기열에서 검수된 신규 원고와 기존 기사 수정을 관리해야 합니다. GitHub Actions 내부의 `GITHUB_TOKEN` push는 다른 push 기반 워크플로를 자동 시작하지 않으므로, 자동 원고 저장 이후 빌드·배포 또는 명시적 워크플로 실행까지 연결해야 합니다.

현재 GitHub 사이트의 기준 주소는 `https://atin84.github.io`입니다. 향후 광고를 활성화하면 `ads.txt`를 도메인 루트의 `/ads.txt`에 제공할 수 있습니다. 현재 설정에서는 광고 script와 `ads.txt`를 생성하지 않습니다.

## Blogger 연결

Blogger의 Iris 블로그는 `https://quickiris.blogspot.com`이며 블로그 ID는 `6780211422264222342`입니다. 최초 Edge 글은 Blogger 웹 편집기로 공개했으며 저장소 원고의 발행 정보도 이 공개 기록에 맞춰 관리합니다.

첫 공개 글: [Edge Notifications Keep Appearing After Closing the Browser](https://quickiris.blogspot.com/2026/10/edge-notifications-after-closing-browser.html)

웹 로그인을 통한 초기 설정과 별개로 Blogger API OAuth 연결 및 정기 발행 구성은 아직 완료하지 않았습니다.

Google 계정 로그인과 Blogger API OAuth 권한은 별도의 연결입니다. API를 활성화하고 해당 블로그 계정으로 OAuth 동의를 완료해야 합니다. 발행기는 아래 환경변수를 사용합니다.

- `BLOGGER_BLOG_ID`
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `GOOGLE_REFRESH_TOKEN`

실제 비밀 값은 채팅·소스·공개 저장소에 넣지 않습니다. 운영 환경의 비밀 저장 기능을 사용합니다. OAuth 앱이 외부 Testing 상태라면 일부 범위의 refresh token이 7일 만에 만료될 수 있으므로 무인 운영 전에 앱 상태와 토큰 수명을 확인합니다.

발행기의 기본 동작은 네트워크 요청 없는 dry-run입니다. 실제 쓰기는 `--apply`, 공개 발행은 추가로 `--publish`를 지정합니다. 이미 존재하는 공개 글은 다시 만들지 않으며, 기존 초안은 공개로 전환할 수 있습니다. 기존 글 본문 자동 수정은 구현 범위에 포함하지 않습니다.

발행 상태 저널은 `data/private/`에 유지해야 합니다. 일회성 CI 실행기에서 이 디렉터리를 매번 잃어버리는 방식으로 무인 발행을 활성화하지 않습니다. 원격 중복 조회와 별도로, 네트워크 오류로 결과가 불확실한 요청의 기록을 보존해야 합니다. 현재 Pages 워크플로는 Blogger API를 호출하지 않습니다. 지속 상태 저장과 Google 연결을 검증한 뒤 Blogger의 정기 실행을 연결합니다.

## AdSense와 측정

Blogger에는 기존 AdSense 계정을 연결하고 `quickiris.blogspot.com`을 사이트 목록에 등록했습니다. 사용자 동의 후 2026년 10월 17일 16:32(KST)에 최종 검토 요청을 제출했습니다. AdSense 화면에서 `준비 중`, `사이트의 광고 게재 가능 여부 검토 중`, `리뷰가 요청됨`을 확인했습니다. GitHub와 Blogger 두 사이트 모두 심사 중이며 아직 승인 전입니다. 실제 광고는 게재하지 않으며 Blogger 자동 광고도 꺼져 있습니다.

GitHub 사이트 `atin84.github.io`는 소유권 확인을 완료하고 검토 요청을 제출했습니다. AdSense 화면에서 `준비 중`과 `리뷰가 요청됨`을 확인했습니다. 사이트에는 소유권 확인용 meta만 반영되어 있으며 실제 광고 script는 비활성화 상태입니다. 승인 완료 여부와 광고·동의 관리 설정은 이후 별도로 확인해야 합니다.

`adsense_client_id`에 본인의 `ca-pub-` ID를 설정하고 사이트·동의 관리·개인정보 안내를 확인한 뒤 `adsense_enabled`를 활성화합니다. 공개 원고가 없는 기본 상태에는 광고를 넣지 않습니다. 각 사이트를 Search Console에 연결해 동일 기간과 조건으로 측정합니다.

실험 규칙은 [experiment/protocol.md](experiment/protocol.md)에 있습니다. 후보 선정에 사용하는 Trends 관측과 실제 사이트의 검색·광고 실적은 별개입니다. 아직 사이트 성과의 비교 표본이나 수익 예측은 확보하지 않았습니다. 검색 비교는 같은 언어의 글마다 발행 다음 날부터 14개 완결 Search Console 보고일을 채운 뒤 진행하며, 경기 매칭 표본이 부족하면 판정을 보류합니다. 같은 URL의 갱신으로 관측을 다시 시작하지 않습니다.

고유 경기 수, 신규 원문 수, 신규 번역본 수, 기존 기사 갱신 횟수는 각각 기록합니다. 미측정 국가·언어를 0으로 채우지 않으며, 다른 언어 성과와 플랫폼 차이를 혼합하지 않습니다.

## 공식 문서

- https://developers.google.com/blogger/docs/3.0/reference/posts/insert
- https://developers.google.com/blogger/docs/3.0/reference/posts/publish
- https://developers.google.com/blogger/docs/3.0/reference/posts/patch
- https://developers.google.com/blogger/docs/3.0/reference/blogs
- https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages
- https://docs.github.com/en/pages/quickstart
- https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule
- https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow
- https://support.google.com/trends/answer/3076011?hl=en
- https://support.google.com/trends/answer/4365533?hl=en
- https://developers.google.com/search/docs/fundamentals/using-gen-ai-content
- https://developers.google.com/search/docs/fundamentals/creating-helpful-content
- https://developers.google.com/search/docs/specialty/international/managing-multi-regional-sites
- https://developers.google.com/search/docs/specialty/international/localized-versions
- https://support.google.com/adsense/answer/12169212?hl=ko
