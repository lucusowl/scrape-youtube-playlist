import atexit
import csv
import json
import logging
import logging.config
import logging.handlers
import time
from datetime import datetime
import multiprocessing
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
from pathlib import Path

# YOUTUBE API Configuration
SCOPES = ["https://www.googleapis.com/auth/youtube.readonly"]
API_SERVICE_NAME = "youtube"
API_VERSION = "v3"
CREDENTIALS_FILE = "credentials.json"
MAX_REQUEST_ITEM = 50

# 
TARGET_PLAYLIST_FILE = "target.json"
LOG_CONFIG_FILE = "config-log.json"
LOGGER = logging.getLogger("scrap-yt-pl")

def setup_logging() -> None:
	"""Setup logging"""
	with open(LOG_CONFIG_FILE) as f:
		_config = json.load(f)
	logging.config.dictConfig(_config)

	queue_handler:logging.handlers.QueueHandler = logging.getHandlerByName("queue_handler")
	if queue_handler is not None:
		queue_handler.listener.start()
		atexit.register(queue_handler.listener.stop)

def authenticate_youtube():
	"""YouTube API Client 인증 수행"""
	flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
	credentials = flow.run_local_server(port=0)
	youtube = googleapiclient.discovery.build(API_SERVICE_NAME, API_VERSION, credentials=credentials)
	return youtube

def read_target(filename:str) -> dict:
	"""JSON file 읽기"""
	with open(filename, "r", encoding='utf-8') as f:
		target = json.load(f)
	return target

def multiprocess_work(youtube, playlist_id:str, playlist_name:str) -> None:
	"""각 재생목록 별 수행"""

	def get_playlist_items(youtube, playlist_id:str) -> list[dict]:
		"""재생목록의 모든 영상 정보 가져오기"""
		videos = []
		request = youtube.playlistItems().list(
			part="contentDetails,snippet",
			playlistId=playlist_id,
			maxResults=MAX_REQUEST_ITEM
		)

		while request:
			try:
				response = request.execute()
				for item in response["items"]:
					videos.append({
						"videoId": item["contentDetails"]["videoId"],
						"addList": item["snippet"]["publishedAt"]
					})
				request = youtube.playlistItems().list_next(request, response)
			except googleapiclient.errors.HttpError as e:
				LOGGER.error(f'FAIL REQUEST API:{e}:{e.content.decode("utf-8")}')
			except googleapiclient.errors.Error as e:
				LOGGER.error(f'FAIL REQUEST API:{e}')
			except Exception as e:
				LOGGER.error(f'OCCUR Exception:{e}')

		return videos

	def get_playlist_items_from_file(playlist_file_name:str) -> list[dict]:
		"""재생목록 파일의 영상 정보 읽어오기"""
		videos = []
		try:
			with open(Path(playlist_file_name), encoding='utf-8') as f:
				reader = csv.reader(f)
				head_size = len(next(reader))
				for row in reader:
					if len(row) == head_size:
						videos.append({
							"videoId": row[0],
							"addList": row[1]
						})
		except FileNotFoundError as e:
			LOGGER.error(f'No File Existed Found:{playlist_file_name}:{e}')
		except Exception as e:
			LOGGER.error(f'OCCUR Exception:{e}')

		return videos

	def get_video_details(youtube, video_ids:list) -> list[dict]:
		"""영상 상세 정보 가져오기"""
		video_details = []

		for i in range(0, len(video_ids), MAX_REQUEST_ITEM):
			request = youtube.videos().list(
				part="snippet,contentDetails,statistics",
				id=",".join(video_ids[i:i+MAX_REQUEST_ITEM])
			)
			try:
				response = request.execute()
				for item in response["items"]:
					video_details.append({
						"ID": item['id'],
						"Title": item["snippet"]["title"],
						# "URL": f"https://www.youtube.com/watch?v={item['id']}",
						# "thumbnail": item["snippet"]["thumbnails"]["default"]["url"],
						"upload": item["snippet"]["publishedAt"],
						"duration": item["contentDetails"]["duration"],
						"viewCount": item["statistics"].get("viewCount", "0"),
						"channelId": item["snippet"]["channelId"],
						"channelName": item["snippet"]["channelTitle"],
						"requestTime": time.time()
					})
			except googleapiclient.errors.HttpError as e:
				LOGGER.error(f'FAIL REQUEST API:{e}:{e.content.decode("utf-8")}')
			except googleapiclient.errors.Error as e:
				LOGGER.error(f'FAIL REQUEST API:{e}')
			except Exception as e:
				LOGGER.error(f'OCCUR Exception:{e}')
		return video_details

	def save_to_file(data:list[dict], filename:str) -> None:
		"""CSV 파일로 저장"""
		with open(filename, "w", encoding="utf-8", newline="") as f:
			writer = csv.DictWriter(f, fieldnames=data[0].keys())
			writer.writeheader()  # Write column headers
			writer.writerows(data)  # Write rows

	sts = time.perf_counter()

	# 1. 재생목록에서 모든 영상 가져오기
	if playlist_id.endswith('.csv'):
		videos = get_playlist_items_from_file(playlist_id)
	else:
		videos = get_playlist_items(youtube, playlist_id)
	LOGGER.info(f"Get #{len(videos)} videos in {playlist_name}")

	# 2. 영상 상세 정보 가져오기
	video_ids = [video["videoId"] for video in videos]
	video_details = get_video_details(youtube, video_ids)

	# 3. 정보 병합
	for video in videos:
		flag = False
		for details in video_details:
			if video["videoId"] == details["ID"]:
				flag = False
				details["addList"] = video["addList"]
				break
			else:
				flag = True
		if flag:
			# 응답에 없는 영상
			video_details.append({
				"ID": video["videoId"],
				# "URL": f"https://www.youtube.com/watch?v={video['videoId']}",
				"requestTime": time.time(),
				"addList": video["addList"]
			})

	# 4. CSV 파일 저장
	now = datetime.now().strftime("%Y%m%d_%H%M%S")
	save_to_file(video_details, f"{playlist_name}_{now}.csv")

	ets = time.perf_counter()-sts
	LOGGER.info(f"Save #{len(video_details)} videos of {playlist_name} in ({ets:.5f}s).")

def main():
	LOGGER.info("START PROCESS")
	wsts = time.perf_counter()

	# YouTube API 클라이언트 인증
	youtube = authenticate_youtube()

	# 타겟 재생목록 ID 가져오기
	playlist_ids = read_target(TARGET_PLAYLIST_FILE)

	lsts = time.perf_counter()
	# 각 재생목록 별로 멀티프로세싱을 수행
	workers:list[multiprocessing.Process] = []
	for playlist_name, playlist_id in playlist_ids.items():
		worker = multiprocessing.Process(
			target=multiprocess_work, 
			args=(youtube, playlist_id, playlist_name)
		)
		worker.start()
		workers.append(worker)
	for worker in workers:
		worker.join()

	wets = time.perf_counter()
	LOGGER.info(f"FINISH PROCESS in (total:{wets-wsts:.5f}s, focus:{wets-lsts:.5f}s)")

if __name__ == "__main__":
	setup_logging()
	main()
