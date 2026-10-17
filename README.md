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

자동 자료 조사, AI 원고 생성, 검색·수익 데이터 수집, Blogger API 무인 발행은 아직 연결 전입니다. 현재 일정은 준비된 원고의 예약 시각을 확인해 사이트를 하루 두 번 다시 빌드하는 작업입니다. 매시간 조사부터 공개까지 이어지는 연결은 완료되지 않았습니다.

## 독자 언어와 편집 방향

2026년 10월 17일 독자용 기본 언어를 영어로 수정했습니다. `config.json`의 언어, 사이트 소개, 초기 Chrome·Edge 원고, GitHub 소개·개인정보 안내가 영어입니다. Blogger 콘텐츠 언어·소개·검색 설명을 영어로 저장하고 기존 Edge 글을 같은 URL에서 영어로 업데이트했습니다. 한국어로 보이는 운영 문서는 관리용이며 독자용 웹 페이지에 배포하지 않습니다.

새 운영 목표는 매시간 고유한 영어 기사 한 편, **두 사이트 합계 하루 24개 발행 슬롯, 사이트별 목표 12편**입니다. 검증된 후보가 부족하거나 발행에 실패하면 빈 슬롯이 생길 수 있습니다. 24편 공개가 보장되거나 이미 이 일정이 실행되고 있다는 뜻은 아닙니다.

엔터테인먼트·스트리밍·크리에이터 행사, 스포츠, 계절성 소비자 출시 등 넓은 후보군에서 실측 수요를 기준으로 소재를 고릅니다. 주요 게임·제품도 같은 수요 검증을 통과할 때만 후보가 됩니다. 초기에는 카테고리별 고정 비중을 두지 않습니다.

Google Trending now의 US·GB를 각각 관측해 4시간 신규 추세, 24시간 검색량 순위, 7일 지속·반복 신호를 확인합니다. 24시간 표시 구간 US `50K+` 또는 GB `10K+`를 우선 검토하는 것은 초기 실험 가정이며 검색 유입·수익의 보장이 아닙니다. 작은 신흥 후보에는 실제 공식 사건과 출처 본문의 시각 근거가 필요합니다. 서로 다른 기간의 목록을 같은 표본으로 나누거나 별칭 행의 검색량을 더하지 않습니다.

같은 사건은 별칭을 묶어 한 사이트의 원문 URL로 관리하고, 후속 정보는 그 URL에서 갱신합니다. 다른 사이트에 같은 이야기를 다시 발행하지 않습니다. 가능하면 두 시간 블록 안에서 국가·카테고리·긴급성·수요가 비슷한 서로 다른 사건을 짝지어 플랫폼과 발행 순서를 무작위 배정합니다. 상세 선별·검수·보류·측정 규칙은 [experiment/protocol.md](experiment/protocol.md)를 따릅니다.

## 매시간 발행을 위한 미연결 단계

- Trends·검색 자료 접근, 실제 사건 조사, 영어 AI 원고 생성과 출처·품질 검수
- 두 사이트 공통 시간 슬롯, 사건 식별·중복 검사, 발행 대기열과 지속 상태 저장
- GitHub 원고 저장부터 공개 확인까지의 연결 및 Blogger OAuth·정기 실행·실패 복구
- Search Console·광고 실적 수집과 관측 기간별 비교

2026년 10월 17일 기준 QuickIris용 ChatGPT 예약 자동화는 생성되지 않았습니다. 확인한 플러그인 검색에서는 사용 가능한 Blogger 플러그인을 찾지 못했습니다. 현재 웹 로그인과 저장소 연결만으로 위 단계가 자동 실행되지는 않습니다. 재빌드 일정만 매시간으로 바꿔 전체 자동 발행이 활성화되었다고 표시하지 않습니다.

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

빌더는 시간이 지난 모든 `ready` 원고를 출력하며 신규 발행을 시간당 한 편으로 제한하지 않습니다. 매시간 운영을 연결할 때에는 대기열에서 공개할 신규 기사를 관리해야 합니다. 밀린 예약 원고를 다음 실행에 한꺼번에 공개하는 것을 정상적인 슬롯 이행으로 계산하지 않습니다. GitHub Actions 내부의 `GITHUB_TOKEN` push는 다른 push 기반 워크플로를 자동 시작하지 않으므로, 자동 원고 저장 이후 빌드·배포 또는 명시적 워크플로 실행까지 연결해야 합니다.

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

실험 규칙은 [experiment/protocol.md](experiment/protocol.md)에 있습니다. 후보 선정에 사용하는 Trends 관측과 실제 사이트의 검색·광고 실적은 별개입니다. 아직 사이트 성과의 비교 표본이나 수익 예측은 확보하지 않았습니다. 검색 비교는 글마다 발행 다음 날부터 14개 완결 Search Console 보고일을 채운 뒤 진행하며, 표본이 부족하면 판정을 보류합니다.

## 공식 문서

- https://developers.google.com/blogger/docs/3.0/reference/posts/insert
- https://developers.google.com/blogger/docs/3.0/reference/posts/publish
- https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages
- https://docs.github.com/en/pages/quickstart
- https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule
- https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow
- https://support.google.com/trends/answer/3076011?hl=en
- https://support.google.com/trends/answer/4365533?hl=en
- https://developers.google.com/search/docs/fundamentals/using-gen-ai-content
- https://developers.google.com/search/docs/fundamentals/creating-helpful-content
- https://support.google.com/adsense/answer/12169212?hl=ko
