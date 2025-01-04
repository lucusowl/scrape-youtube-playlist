# Scrape Youtube Playlist
v1.1.0

지정한 Youtube playlist 의 모든 영상들의 정보를 수집  

[Youtube Data API](https://developers.google.com/youtube/v3/docs), [Google OAuth](https://developers.google.com/identity/protocols/oauth2)을 활용  

## 사용법 How to Use

### 준비 Setup

1. YouTube Data API 와 OAuth 설정

	**재생목록에 접근이 가능한 계정**의 [Google Cloud Platform (GCP)](https://console.cloud.google.com/)에서 프로젝트를 열고  
	YouTube Data API 와 OAuth 인증을 수행  

	1. [Google Cloud Console](https://console.cloud.google.com/)에서 새 프로젝트를 생성
	2. [YouTube Data API](https://console.cloud.google.com/apis/library/youtube.googleapis.com)를 활성화
	3. "OAuth 동의 화면" 구성 -> [가이드, Google Workspace](https://developers.google.com/calendar/api/quickstart/python#configure_the_oauth_consent_screen)
	4. "사용자 인증 정보" 승인 -> [가이드, Google Workspace](https://developers.google.com/calendar/api/quickstart/python#authorize_credentials_for_a_desktop_application)
	5. ["OAuth 2.0 클라이언트 ID"](https://console.cloud.google.com/apis/credentials)에서 생성된 OAuth 클라이언트(credentials)의 JSON 파일을 다운로드
	6. `credential.json` 으로 이름 바꾸어 `main.py`와 같은 경로(`src/`)에 옮기기

2. python 라이브러리 설치

	`google-auth`, `google-auth-oauthlib`, `google-auth-httplib2`, `google-api-python-client` 설치  

	```sh
	pip install -r requirements.txt
	```

3. 재생목록 정보 준비

	[`target.json`](./src/target.json)에 예시와 같이 작성. *key*는 결과물의 이름, *value*는 아래의 항목 중 하나를 선택하여 작성  

	- 재생목록 URL의 Query String에서 `list` 필드의 값 (재생목록ID)
	- [Google Takeout](https://takeout.google.com/)와 같은 방법으로 추출한 [재생목록 csv 파일](## "각 영상의 ID, 재생목록에 추가한 타임스탬프로 구성")의 경로

	```json
	{
		"name1": "playlist1-id",
		"name2": "playlist2-filePath.csv",
		"...": "..."
	}
	```

	> [!NOTE]
	> YouTube Data API로 가져올 수 없는 재생목록은 아래에 해당 [^1] [^2]
	>
	> - "나중에 볼 동영상" (재생목록ID: `WL`)
	> - "시청 기록" (재생목록ID: `HL`)
	>
	> 위 재생목록은 **[Google Takeout](https://takeout.google.com/)을 통해서** 추출 가능.
	> "나중에 볼 동영상"은 CSV 파일로 내보내기, "시청 기록"은 HTML 또는 JSON 파일로 내보내기

### 실행 Run

```bash
cd src
python main.py
```

## Appendix

[^1]: https://developers.google.com/youtube/v3/revision_history#september-15,-2016 "Youtube Data API 업데이트 기록, 2016.09.15 이후 불가"
[^2]: https://stackoverflow.com/questions/46987690/tracking-youtube-watch-history/47117301#47117301 "stackoverflow, 17.10.28, tracking watch history disabled"
