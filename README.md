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

이번 릴리스는 GitHub 첫 공개 배포를 준비한 상태입니다. Chrome 안내 글 1편은 `ready`이며 `published_at`에 준비 시점의 실제 UTC 시각을 기록했습니다. 소개·개인정보 안내도 함께 빌드합니다. 광고는 비활성화되어 있고 AdSense ID는 비어 있습니다.

`content/`의 첫 원고 2편은 공식 Google·Microsoft 도움말을 검토해 작성했습니다. Blogger 첫 Edge 글은 웹 편집기로 공개 발행했고 본문과 중복 확인용 식별표식을 확인했습니다. 초기 두 글은 연결 확인용이며 검색 수요가 검증된 주제나 플랫폼 비교 표본으로 간주하지 않습니다.

자동 자료 조사, AI 원고 생성, 검색·수익 데이터 수집은 아직 연결 전입니다. 현재 일정은 준비된 원고의 예약 시각을 확인해 사이트를 다시 빌드하는 작업입니다.

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
3. 저장소 Actions 변수 `PAGES_ENABLED`를 `true`로 설정하면 Pages 워크플로가 활성화됩니다.
4. 워크플로는 GitHub가 반환한 실제 `base_url`로 canonical과 사이트맵을 생성합니다.
5. 첫 배포는 Actions → Publish GitHub Pages → Run workflow로 실행합니다. 변수 변경만으로는 실행되지 않습니다.

Pages 워크플로에는 한국시간 09:17 / 18:17 재빌드 일정이 준비되어 있습니다. `PAGES_ENABLED=true`일 때 배포 작업이 실행됩니다. `content/` 또는 `site_pages/`를 변경한 push도 배포 대상입니다. 예약 실행은 지연될 수 있고, 비활성 공개 저장소의 예약 작업은 GitHub 조건에 따라 중지될 수 있습니다. 새로운 AI 원고를 작성하는 작업은 이 재빌드 일정과 별도로 연결해야 합니다.

현재 GitHub 사이트의 기준 주소는 `https://atin84.github.io`입니다. 향후 광고를 활성화하면 `ads.txt`를 도메인 루트의 `/ads.txt`에 제공할 수 있습니다. 현재 설정에서는 광고 script와 `ads.txt`를 생성하지 않습니다.

## Blogger 연결

Blogger의 Iris 블로그는 `https://quickiris.blogspot.com`이며 블로그 ID는 `6780211422264222342`입니다. 최초 Edge 글은 Blogger 웹 편집기로 공개했으며 저장소 원고의 발행 정보도 이 공개 기록에 맞춰 관리합니다.

첫 공개 글: [Edge를 닫았는데도 사이트 알림이 올 때](https://quickiris.blogspot.com/2026/10/edge-notifications-after-closing-browser.html)

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

Blogger에는 기존 AdSense 계정을 연결했습니다. 현재 새 Iris 블로그는 AdSense에서 승인되지 않은 상태이며 자동 광고도 꺼져 있습니다. GitHub의 이번 릴리스도 광고를 비활성화한 상태로 준비합니다. GitHub 사이트의 AdSense 등록·승인은 별도로 확인해야 합니다.

`adsense_client_id`에 본인의 `ca-pub-` ID를 설정하고 사이트·동의 관리·개인정보 안내를 확인한 뒤 `adsense_enabled`를 활성화합니다. 공개 원고가 없는 기본 상태에는 광고를 넣지 않습니다. 각 사이트를 Search Console에 연결해 동일 기간과 조건으로 측정합니다.

실험 규칙은 [experiment/protocol.md](experiment/protocol.md)에 있습니다. 아직 실측 데이터나 수익 예측은 없습니다.

## 공식 문서

- https://developers.google.com/blogger/docs/3.0/reference/posts/insert
- https://developers.google.com/blogger/docs/3.0/reference/posts/publish
- https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages
- https://docs.github.com/en/pages/quickstart
- https://support.google.com/adsense/answer/12169212?hl=ko
